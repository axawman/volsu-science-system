import django
import json
import secrets
import shutil
import re
import smtplib
import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import BadHeaderError, send_mail
from django.core.management import call_command
from django.db.models import Prefetch
from django.db import connection, transaction
from django.core.management.color import no_style
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .decorators import admin_required
from .forms import DataImportForm, GroupChatMessageForm, ProfileEditForm, ProfilePasswordForm, RegisterForm
from .models import GroupChatMessage, Profile
from .services import assign_study_group_from_email
from .signals import create_user_profile, save_user_profile

BACKUP_FILENAME_PREFIX = "science_registry_backup"
FIXTURE_FILENAME = "data.json"
METADATA_FILENAME = "metadata.json"
MEDIA_DIRNAME = "media"
REGISTRATION_CODE_SESSION_KEY = "registration_email_code"
REGISTRATION_CODE_COOLDOWNS_SESSION_KEY = "registration_email_code_cooldowns"
REGISTRATION_CODE_TTL_MINUTES = 5
REGISTRATION_CODE_RESEND_COOLDOWN_SECONDS = 60
LOGIN_CODE_SESSION_KEY = "login_email_code"
LOGIN_CODE_TTL_MINUTES = 5
GROUP_CHAT_ONLINE_WINDOW_SECONDS = 120

EXCLUDED_DUMPDATA_MODELS = [
    "admin.logentry",
    "sessions.session",
    "contenttypes",
    "auth.permission",
]

SEQUENCE_RESET_APPS = [
    "contenttypes",
    "auth",
    "accounts",
    "works",
    "discussions",
    "meetings",
    "events",
    "core",
    "guide",
]


def _normalize_email(email):
    return (email or "").strip().lower()


def _make_username_from_email(email):
    base_username = re.sub(r"[^a-zA-Z0-9_]", "_", email.split("@", 1)[0]).strip("_") or "user"
    username = base_username
    suffix = 1

    while User.objects.filter(username=username).exists():
        suffix += 1
        username = f"{base_username}_{suffix}"

    return username


def _registration_code_is_valid(request, email, code):
    verification = request.session.get(REGISTRATION_CODE_SESSION_KEY) or {}
    expires_at = verification.get("expires_at")

    if not expires_at:
        return False

    expires_at = datetime.fromisoformat(expires_at)
    if timezone.is_naive(expires_at):
        expires_at = timezone.make_aware(expires_at)

    return (
        verification.get("email") == _normalize_email(email)
        and verification.get("code") == (code or "").strip()
        and expires_at >= timezone.now()
    )


@require_POST
def send_registration_code(request):
    email = _normalize_email(request.POST.get("email"))
    cooldowns = request.session.get(REGISTRATION_CODE_COOLDOWNS_SESSION_KEY) or {}
    sent_at = cooldowns.get(email)

    if not email.endswith("@volsu.ru"):
        return JsonResponse({"error": "Введите почту в домене @volsu.ru."}, status=400)

    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse({"error": "Пользователь с такой почтой уже зарегистрирован."}, status=400)

    if sent_at:
        sent_at = datetime.fromisoformat(sent_at)
        if timezone.is_naive(sent_at):
            sent_at = timezone.make_aware(sent_at)

        resend_available_at = sent_at + timedelta(seconds=REGISTRATION_CODE_RESEND_COOLDOWN_SECONDS)
        if resend_available_at > timezone.now():
            retry_after = int((resend_available_at - timezone.now()).total_seconds()) + 1
            return JsonResponse({
                "error": "Отправить код заново можно через минуту.",
                "retry_after": retry_after,
            }, status=429)

    code = f"{secrets.randbelow(1000000):06d}"
    now = timezone.now()
    expires_at = now + timedelta(minutes=REGISTRATION_CODE_TTL_MINUTES)

    try:
        send_mail(
            subject="Код подтверждения регистрации ScienceHub ВолГУ",
            message=f"Ваш код подтверждения: {code}\n\nКод действует {REGISTRATION_CODE_TTL_MINUTES} минут.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except (BadHeaderError, OSError, smtplib.SMTPException, TimeoutError) as error:
        return JsonResponse({"error": f"Не удалось отправить код: {error}"}, status=502)

    request.session[REGISTRATION_CODE_SESSION_KEY] = {
        "email": email,
        "code": code,
        "expires_at": expires_at.isoformat(),
        "sent_at": now.isoformat(),
    }

    fresh_cooldowns = {}
    for cooldown_email, cooldown_sent_at in cooldowns.items():
        cooldown_sent_at = datetime.fromisoformat(cooldown_sent_at)
        if timezone.is_naive(cooldown_sent_at):
            cooldown_sent_at = timezone.make_aware(cooldown_sent_at)

        cooldown_expires_at = cooldown_sent_at + timedelta(seconds=REGISTRATION_CODE_RESEND_COOLDOWN_SECONDS)
        if cooldown_expires_at > now:
            fresh_cooldowns[cooldown_email] = cooldown_sent_at.isoformat()

    fresh_cooldowns[email] = now.isoformat()
    request.session[REGISTRATION_CODE_COOLDOWNS_SESSION_KEY] = fresh_cooldowns
    request.session.modified = True

    return JsonResponse({
        "message": "Код отправлен на почту.",
        "resend_after": REGISTRATION_CODE_RESEND_COOLDOWN_SECONDS,
    })


@require_POST
def verify_registration_code(request):
    email = _normalize_email(request.POST.get("email"))
    code = request.POST.get("code")

    if not _registration_code_is_valid(request, email, code):
        return JsonResponse({"error": "Неверный или устаревший код."}, status=400)

    request.session["registration_email_verified"] = email
    request.session.modified = True
    return JsonResponse({"message": "Почта подтверждена."})


def _get_safe_login_redirect(request):
    redirect_to = request.POST.get("next") or request.GET.get("next") or settings.LOGIN_REDIRECT_URL
    if url_has_allowed_host_and_scheme(
        redirect_to,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect_to
    return settings.LOGIN_REDIRECT_URL


@require_POST
def send_login_code(request):
    email = _normalize_email(request.POST.get("email"))
    user = User.objects.filter(email__iexact=email, is_active=True).first()

    if not user:
        return JsonResponse({"error": "Пользователь с такой почтой не зарегистрирован."}, status=404)

    code = f"{secrets.randbelow(1000000):06d}"
    expires_at = timezone.now() + timedelta(minutes=LOGIN_CODE_TTL_MINUTES)

    try:
        send_mail(
            subject="Код входа ScienceHub ВолГУ",
            message=f"Ваш код входа: {code}\n\nКод действует {LOGIN_CODE_TTL_MINUTES} минут.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except (BadHeaderError, OSError, smtplib.SMTPException, TimeoutError) as error:
        return JsonResponse({"error": f"Не удалось отправить код: {error}"}, status=502)

    request.session[LOGIN_CODE_SESSION_KEY] = {
        "email": email,
        "user_id": user.id,
        "code": code,
        "expires_at": expires_at.isoformat(),
    }
    request.session.modified = True
    return JsonResponse({"message": "Код отправлен на почту."})


@require_POST
def verify_login_code(request):
    email = _normalize_email(request.POST.get("email"))
    code = (request.POST.get("code") or "").strip()
    verification = request.session.get(LOGIN_CODE_SESSION_KEY) or {}
    expires_at = verification.get("expires_at")

    if expires_at:
        expires_at = datetime.fromisoformat(expires_at)
        if timezone.is_naive(expires_at):
            expires_at = timezone.make_aware(expires_at)

    if (
        not expires_at
        or expires_at < timezone.now()
        or verification.get("email") != email
        or verification.get("code") != code
    ):
        return JsonResponse({"error": "Неверный или устаревший код."}, status=400)

    user = get_object_or_404(User, id=verification.get("user_id"), is_active=True)
    login(request, user)
    request.session.pop(LOGIN_CODE_SESSION_KEY, None)
    request.session.modified = True
    return JsonResponse({"redirect_url": _get_safe_login_redirect(request)})


def register_view(request):
    if request.user.is_authenticated:
        return redirect("/accounts/profile/")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            verification_code = request.POST.get("email_verification_code")
            verified_email = request.session.get("registration_email_verified")

            if verified_email != email or not _registration_code_is_valid(request, email, verification_code):
                form.add_error("email", "Подтвердите почту кодом перед регистрацией.")
                return render(request, "accounts/register.html", {"form": form})

            user = form.save(commit=False)
            user.username = _make_username_from_email(email)
            user.email = email
            user.save()

            user.profile.full_name = form.cleaned_data["full_name"]
            user.profile.save()
            assign_study_group_from_email(user.profile)

            login(request, user)
            request.session.pop(REGISTRATION_CODE_SESSION_KEY, None)
            request.session.pop(REGISTRATION_CODE_COOLDOWNS_SESSION_KEY, None)
            request.session.pop("registration_email_verified", None)
            return redirect("/")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile_view(request):
    from works.models import Work

    works = Work.objects.filter(author=request.user).select_related("section").order_by("-updated_at")
    return render(request, "accounts/profile.html", {
        "profile": request.user.profile,
        "profile_user": request.user,
        "works": works,
        "is_own_profile": True,
        "password_form": ProfilePasswordForm(),
        "show_password_form": False,
    })


def public_profile_view(request, username):
    from works.models import Work

    profile_user = get_object_or_404(
        User.objects.select_related("profile"),
        username=username,
    )
    works = Work.objects.filter(
        author=profile_user,
        status="published",
        visibility="public",
    ).select_related("section").order_by("-updated_at")

    return render(request, "accounts/profile.html", {
        "profile": profile_user.profile,
        "profile_user": profile_user,
        "works": works,
        "is_own_profile": request.user.is_authenticated and request.user == profile_user,
        "password_form": ProfilePasswordForm(),
        "show_password_form": False,
    })


@login_required
@require_POST
def change_profile_password_view(request):
    from works.models import Work

    form = ProfilePasswordForm(request.POST)
    if form.is_valid():
        request.user.set_password(form.cleaned_data["password"])
        request.user.save(update_fields=["password"])
        update_session_auth_hash(request, request.user)
        messages.success(request, "Пароль обновлен.")
        return redirect("/accounts/profile/")

    works = Work.objects.filter(author=request.user).select_related("section").order_by("-updated_at")
    return render(request, "accounts/profile.html", {
        "profile": request.user.profile,
        "profile_user": request.user,
        "works": works,
        "is_own_profile": True,
        "password_form": form,
        "show_password_form": True,
    })


@login_required
def edit_profile_view(request):
    profile = request.user.profile

    if request.method == "POST":
        form = ProfileEditForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("/accounts/profile/")
    else:
        form = ProfileEditForm(instance=profile)

    return render(request, "accounts/edit_profile.html", {"form": form})


def _get_user_study_group(user):
    profile = user.profile
    return profile.study_group or assign_study_group_from_email(profile)


def _touch_group_chat_presence(user):
    Profile.objects.filter(id=user.profile.id).update(last_seen_at=timezone.now())
    user.profile.last_seen_at = timezone.now()


def _get_online_member_ids(study_group):
    online_since = timezone.now() - timedelta(seconds=GROUP_CHAT_ONLINE_WINDOW_SECONDS)
    return set(
        study_group.members
        .filter(role="student", last_seen_at__gte=online_since)
        .values_list("user_id", flat=True)
    )


def _get_group_chat_members(study_group):
    return (
        study_group.members
        .select_related("user")
        .filter(role="student")
        .order_by("full_name", "user__username")
    )


def _get_group_chat_messages(study_group, user):
    chat_messages = (
        study_group.messages
        .filter(is_deleted=False)
        .exclude(hidden_for=user)
        .select_related("author", "author__profile", "reply_to", "reply_to__author", "reply_to__author__profile")
        .prefetch_related(
            Prefetch("read_by", queryset=User.objects.only("id")),
        )
        .order_by("-created_at", "-id")[:80]
    )
    chat_messages = list(reversed(chat_messages))
    unread_messages = [
        message
        for message in chat_messages
        if message.author_id != user.id
        and user.id not in {reader.id for reader in message.read_by.all()}
    ]

    for message in unread_messages:
        message.read_by.add(user)

    if unread_messages:
        chat_messages = list(
            study_group.messages
            .filter(is_deleted=False)
            .exclude(hidden_for=user)
            .filter(id__in=[message.id for message in chat_messages])
            .select_related("author", "author__profile", "reply_to", "reply_to__author", "reply_to__author__profile")
            .prefetch_related(Prefetch("read_by", queryset=User.objects.only("id")))
            .order_by("created_at", "id")
        )

    for message in chat_messages:
        message.has_been_read_by_others = any(
            reader.id != message.author_id
            for reader in message.read_by.all()
        )

    previous_author_id = None
    for message in chat_messages:
        message.starts_author_group = message.author_id != previous_author_id
        previous_author_id = message.author_id

    return chat_messages


def _group_chat_payload(request, study_group):
    members = _get_group_chat_members(study_group)
    online_member_ids = _get_online_member_ids(study_group)
    visible_online_member_ids = online_member_ids - {request.user.id}
    chat_messages = _get_group_chat_messages(study_group, request.user)
    html = render_to_string(
        "accounts/_group_chat_messages.html",
        {
            "chat_messages": chat_messages,
            "request": request,
        },
        request=request,
    )

    return {
        "html": html,
        "online_count": len(visible_online_member_ids),
        "online_member_ids": list(online_member_ids),
        "member_count": members.count(),
    }


def _group_chat_json_response(request, study_group):
    return JsonResponse(_group_chat_payload(request, study_group))


@login_required
def group_chat_view(request):
    profile = request.user.profile
    study_group = _get_user_study_group(request.user)

    if not study_group:
        return render(request, "accounts/group_chat.html", {
            "study_group": None,
            "members": [],
            "chat_messages": [],
            "message_form": GroupChatMessageForm(study_group=None),
            "online_member_ids": set(),
            "online_count": 0,
        })

    _touch_group_chat_presence(request.user)

    if request.method == "POST":
        message_form = GroupChatMessageForm(request.POST, study_group=study_group)
        if message_form.is_valid():
            message = message_form.save(commit=False)
            message.study_group = study_group
            message.author = request.user
            message.save()
            message.read_by.add(request.user)
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return _group_chat_json_response(request, study_group)
            return redirect("group_chat")
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"errors": message_form.errors}, status=400)
    else:
        message_form = GroupChatMessageForm(study_group=study_group)

    members = _get_group_chat_members(study_group)
    online_member_ids = _get_online_member_ids(study_group)
    visible_online_member_ids = online_member_ids - {request.user.id}
    chat_messages = _get_group_chat_messages(study_group, request.user)

    return render(request, "accounts/group_chat.html", {
        "study_group": study_group,
        "members": members,
        "online_member_ids": online_member_ids,
        "online_count": len(visible_online_member_ids),
        "member_count": members.count(),
        "chat_messages": chat_messages,
        "message_form": message_form,
    })


@login_required
@require_POST
def edit_group_chat_message_view(request, message_id):
    profile = request.user.profile
    study_group = _get_user_study_group(request.user)
    message = get_object_or_404(
        GroupChatMessage,
        id=message_id,
        author=request.user,
        study_group=study_group,
        is_deleted=False,
    )
    form = GroupChatMessageForm(request.POST, instance=message, study_group=study_group)

    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    if form.is_valid():
        edited_message = form.save(commit=False)
        edited_message.save(update_fields=["text", "reply_to"])
        edited_message.mark_edited()
    elif is_ajax:
        return JsonResponse({"errors": form.errors}, status=400)

    if is_ajax:
        return _group_chat_json_response(request, study_group)

    return redirect("group_chat")


@login_required
@require_POST
def delete_group_chat_message_view(request, message_id):
    profile = request.user.profile
    study_group = _get_user_study_group(request.user)
    message = get_object_or_404(
        GroupChatMessage,
        id=message_id,
        study_group=study_group,
    )
    delete_scope = request.POST.get("scope", "me")

    if delete_scope == "all" and message.author == request.user and not message.is_deleted:
        message.mark_deleted()
    else:
        message.hidden_for.add(request.user)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return _group_chat_json_response(request, study_group)

    return redirect("group_chat")


@login_required
def group_chat_updates_view(request):
    study_group = _get_user_study_group(request.user)
    if not study_group:
        return JsonResponse({"html": "", "online_count": 0, "online_member_ids": []})

    _touch_group_chat_presence(request.user)
    return _group_chat_json_response(request, study_group)


@login_required
def group_chat_message_readers_view(request, message_id):
    study_group = _get_user_study_group(request.user)
    message = get_object_or_404(
        GroupChatMessage.objects.prefetch_related("read_by", "read_by__profile"),
        id=message_id,
        author=request.user,
        study_group=study_group,
    )
    readers = [
        {
            "name": reader.profile.short_name,
            "url": request.build_absolute_uri(f"/accounts/users/{reader.username}/"),
        }
        for reader in message.read_by.all()
        if reader.id != request.user.id
    ]
    return JsonResponse({"readers": readers})


@admin_required
def data_transfer_view(request):
    form = DataImportForm()
    return render(request, "accounts/data_transfer.html", {"form": form})


def _safe_extract_zip(archive_file, destination):
    destination = Path(destination).resolve()
    with zipfile.ZipFile(archive_file) as archive:
        for member in archive.infolist():
            member_path = (destination / member.filename).resolve()
            if not str(member_path).startswith(str(destination)):
                raise ValueError("Архив содержит недопустимые пути")
        archive.extractall(destination)


def _build_export_metadata():
    return {
        "format": 2,
        "project": "volsu-science-system",
        "exported_at": timezone.now().isoformat(),
        "fixture": FIXTURE_FILENAME,
        "media_dir": MEDIA_DIRNAME,
        "django_version": django.get_version(),
        "installed_apps": list(settings.INSTALLED_APPS),
    }


@admin_required
def export_data_view(request):
    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"{BACKUP_FILENAME_PREFIX}_{timestamp}.zip"

    temp_dir = Path(tempfile.mkdtemp(prefix="science_registry_export_"))
    export_dir = temp_dir / "export"
    export_dir.mkdir(parents=True, exist_ok=True)

    try:
        fixture_path = export_dir / FIXTURE_FILENAME
        metadata_path = export_dir / METADATA_FILENAME
        media_export_dir = export_dir / MEDIA_DIRNAME

        with fixture_path.open("w", encoding="utf-8") as fixture_file:
            call_command(
                "dumpdata",
                format="json",
                indent=2,
                natural_foreign=True,
                natural_primary=True,
                exclude=EXCLUDED_DUMPDATA_MODELS,
                stdout=fixture_file,
            )

        metadata_path.write_text(
            json.dumps(_build_export_metadata(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        media_root = Path(settings.MEDIA_ROOT)
        if media_root.exists():
            shutil.copytree(media_root, media_export_dir, dirs_exist_ok=True)
        else:
            media_export_dir.mkdir(parents=True, exist_ok=True)

        archive_path = temp_dir / archive_name
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for file_path in export_dir.rglob("*"):
                if file_path.is_file():
                    archive.write(file_path, arcname=file_path.relative_to(export_dir))

        response = FileResponse(open(archive_path, "rb"), as_attachment=True, filename=archive_name)
        response["X-Backup-Format"] = "2"
        return response
    finally:
        pass


def _disconnect_profile_signals():
    from django.db.models.signals import post_save

    post_save.disconnect(create_user_profile, sender=User)
    post_save.disconnect(save_user_profile, sender=User)


def _reconnect_profile_signals():
    from django.db.models.signals import post_save

    post_save.connect(create_user_profile, sender=User)
    post_save.connect(save_user_profile, sender=User)


def _reset_sequences():
    app_models = []
    for app_label in SEQUENCE_RESET_APPS:
        app_models.extend(apps.get_app_config(app_label).get_models())

    sql_list = connection.ops.sequence_reset_sql(style=no_style(), model_list=app_models)
    if not sql_list:
        return

    with connection.cursor() as cursor:
        for sql in sql_list:
            cursor.execute(sql)


def _restore_database_from_fixture(fixture_path: Path):
    _disconnect_profile_signals()
    try:
        with transaction.atomic():
            call_command("flush", interactive=False, verbosity=0)
            call_command("migrate", interactive=False, verbosity=0)
            call_command("loaddata", str(fixture_path), verbosity=0)
            _reset_sequences()
    finally:
        _reconnect_profile_signals()


def _restore_media(media_dir: Path):
    media_root = Path(settings.MEDIA_ROOT)
    if media_root.exists():
        shutil.rmtree(media_root)
    media_root.mkdir(parents=True, exist_ok=True)

    if not media_dir.exists():
        return

    for item in media_dir.iterdir():
        target = media_root / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def _backup_current_media(temp_dir: Path):
    media_root = Path(settings.MEDIA_ROOT)
    media_backup_dir = temp_dir / "media_backup"
    if media_root.exists():
        shutil.copytree(media_root, media_backup_dir, dirs_exist_ok=True)
    else:
        media_backup_dir.mkdir(parents=True, exist_ok=True)
    return media_backup_dir


def _restore_media_from_backup(media_backup_dir: Path):
    _restore_media(media_backup_dir)


@admin_required
def import_data_view(request):
    if request.method != "POST":
        return redirect("data_transfer")

    form = DataImportForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, "accounts/data_transfer.html", {"form": form})

    uploaded_archive = form.cleaned_data["archive"]
    temp_dir = Path(tempfile.mkdtemp(prefix="science_registry_import_"))
    archive_path = temp_dir / "import.zip"

    media_backup_dir = _backup_current_media(temp_dir)

    try:
        with archive_path.open("wb") as destination:
            for chunk in uploaded_archive.chunks():
                destination.write(chunk)

        extract_dir = temp_dir / "extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)

        try:
            _safe_extract_zip(archive_path, extract_dir)
        except zipfile.BadZipFile:
            form.add_error("archive", "Это не zip-архив")
            return render(request, "accounts/data_transfer.html", {"form": form})
        except ValueError as exc:
            form.add_error("archive", str(exc))
            return render(request, "accounts/data_transfer.html", {"form": form})

        fixture_path = extract_dir / FIXTURE_FILENAME
        metadata_path = extract_dir / METADATA_FILENAME
        media_dir = extract_dir / MEDIA_DIRNAME

        if not fixture_path.exists():
            form.add_error("archive", f"В архиве нет файла {FIXTURE_FILENAME}")
            return render(request, "accounts/data_transfer.html", {"form": form})

        if not metadata_path.exists():
            form.add_error("archive", f"В архиве нет файла {METADATA_FILENAME}")
            return render(request, "accounts/data_transfer.html", {"form": form})

        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            form.add_error("archive", "Файл metadata.json поврежден")
            return render(request, "accounts/data_transfer.html", {"form": form})

        if metadata.get("project") != "volsu-science-system":
            form.add_error("archive", "Архив не относится к этому проекту")
            return render(request, "accounts/data_transfer.html", {"form": form})

        _restore_database_from_fixture(fixture_path)
        _restore_media(media_dir)

        logout(request)
        messages.success(request, "Данные успешно импортированы. Состояние проекта восстановлено. Войдите снова.")
        return redirect("login")
    except Exception as exc:
        try:
            _restore_media_from_backup(media_backup_dir)
        except Exception:
            pass

        form.add_error("archive", f"Ошибка импорта: {exc}")
        return render(request, "accounts/data_transfer.html", {"form": form})
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

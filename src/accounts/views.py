import django
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connection, transaction
from django.core.management.color import no_style
from django.http import FileResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .decorators import admin_required
from .forms import DataImportForm, ProfileEditForm, RegisterForm
from .models import Profile
from .signals import create_user_profile, save_user_profile

BACKUP_FILENAME_PREFIX = "science_registry_backup"
FIXTURE_FILENAME = "data.json"
METADATA_FILENAME = "metadata.json"
MEDIA_DIRNAME = "media"

EXCLUDED_DUMPDATA_MODELS = [
    "admin.logentry",
    "sessions.session",
]

SEQUENCE_RESET_APPS = [
    "contenttypes",
    "auth",
    "accounts",
    "works",
    "discussions",
    "meetings",
    "events",
]


def register_view(request):
    if request.user.is_authenticated:
        return redirect("/accounts/profile/")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.email = form.cleaned_data["email"]
            user.save()

            user.profile.full_name = form.cleaned_data["full_name"]
            user.profile.save()

            login(request, user)
            return redirect("/")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile_view(request):
    return render(request, "accounts/profile.html", {"profile": request.user.profile})


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

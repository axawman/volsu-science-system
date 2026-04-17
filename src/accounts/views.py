import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core import serializers
from django.http import FileResponse, HttpResponse
from django.shortcuts import render, redirect
from django.utils import timezone

from discussions.models import WorkComment
from events.models import Event
from meetings.models import Meeting
from works.models import Work, WorkSection, WorkVersion, WorkVersionFile

from .decorators import admin_required
from .forms import RegisterForm, ProfileEditForm, DataImportForm
from .models import Profile


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


@admin_required
def export_data_view(request):
    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"science_registry_backup_{timestamp}.zip"

    temp_dir = Path(tempfile.mkdtemp(prefix="science_registry_export_"))
    export_dir = temp_dir / "export"
    media_export_dir = export_dir / "media"
    export_dir.mkdir(parents=True, exist_ok=True)

    try:
        models_to_serialize = [
            User,
            Profile,
            WorkSection,
            Work,
            WorkVersion,
            WorkVersionFile,
            WorkComment,
            Meeting,
            Event,
        ]

        data_json_path = export_dir / "data.json"
        data_json_path.write_text(
            serializers.serialize("json", [
                obj
                for model in models_to_serialize
                for obj in model.objects.all()
            ], use_natural_foreign_keys=False, use_natural_primary_keys=False, indent=2),
            encoding="utf-8",
        )

        metadata = {
            "exported_at": timezone.now().isoformat(),
            "format": 1,
            "includes_media": True,
        }
        (export_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

        if Path(settings.MEDIA_ROOT).exists():
            shutil.copytree(settings.MEDIA_ROOT, media_export_dir, dirs_exist_ok=True)
        else:
            media_export_dir.mkdir(parents=True, exist_ok=True)

        archive_path = temp_dir / archive_name
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for file_path in export_dir.rglob("*"):
                if file_path.is_file():
                    archive.write(file_path, arcname=file_path.relative_to(export_dir))

        return FileResponse(open(archive_path, "rb"), as_attachment=True, filename=archive_name)
    finally:
        # FileResponse will keep the opened file handle alive, but temp dirs can still be cleaned later by OS.
        pass


def _safe_extract_zip(archive_file, destination):
    with zipfile.ZipFile(archive_file) as archive:
        for member in archive.infolist():
            member_path = Path(destination) / member.filename
            resolved_destination = Path(destination).resolve()
            resolved_member = member_path.resolve()
            if not str(resolved_member).startswith(str(resolved_destination)):
                raise ValueError("Архив содержит недопустимые пути")
        archive.extractall(destination)


def _replace_all_project_data(data_json_path):
    WorkComment.objects.all().delete()
    WorkVersionFile.objects.all().delete()
    WorkVersion.objects.all().delete()
    Work.objects.all().delete()
    WorkSection.objects.all().delete()
    Meeting.objects.all().delete()
    Event.objects.all().delete()
    Profile.objects.all().delete()
    User.objects.all().delete()

    for obj in serializers.deserialize("json", data_json_path.read_text(encoding="utf-8")):
        obj.save()


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

    try:
        with open(archive_path, "wb") as destination:
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

        data_json_path = extract_dir / "data.json"
        media_dir = extract_dir / "media"

        if not data_json_path.exists():
            form.add_error("archive", "В архиве нет файла data.json")
            return render(request, "accounts/data_transfer.html", {"form": form})

        _replace_all_project_data(data_json_path)

        media_root = Path(settings.MEDIA_ROOT)
        if media_root.exists():
            shutil.rmtree(media_root)
        media_root.mkdir(parents=True, exist_ok=True)

        if media_dir.exists():
            for item in media_dir.iterdir():
                target = media_root / item.name
                if item.is_dir():
                    shutil.copytree(item, target, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, target)

        logout(request)
        messages.success(request, "Данные импортированы. Войдите снова.")
        return redirect("login")
    except Exception as exc:
        form.add_error("archive", f"Ошибка импорта: {exc}")
        return render(request, "accounts/data_transfer.html", {"form": form})
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

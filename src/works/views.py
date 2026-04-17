import os
import zipfile
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.text import slugify

from .forms import WorkCreateForm, WorkEditForm, WorkVersionForm
from .models import Work, WorkSection, WorkVersion, WorkVersionFile
from discussions.forms import WorkCommentForm


def user_can_manage_work(user, work):
    return user == work.author or user.profile.is_admin()


@login_required
def create_work(request):
    if request.method == "POST":
        form = WorkCreateForm(request.POST, request.FILES)
        if form.is_valid():
            work = form.save(commit=False)
            work.author = request.user
            work.save()

            version = WorkVersion.objects.create(
                work=work,
                version_number=1,
                comment=form.cleaned_data.get("comment", ""),
                uploaded_by=request.user,
            )

            for uploaded_file in form.cleaned_data["files"]:
                WorkVersionFile.objects.create(
                    version=version,
                    file=uploaded_file,
                    original_name=uploaded_file.name,
                )

            return redirect("my_works")
    else:
        form = WorkCreateForm()

    return render(request, "works/create_work.html", {"form": form})


@login_required
def update_work(request, work_id):
    work = get_object_or_404(Work.objects.select_related("author", "section"), id=work_id)

    if not user_can_manage_work(request.user, work):
        return HttpResponse("Доступ запрещен")

    if request.method == "POST":
        form = WorkEditForm(request.POST, instance=work)
        if form.is_valid():
            updated_work = form.save(commit=False)
            updated_work.author = work.author

            if "publish" in request.POST:
                updated_work.status = "published"
                messages.success(request, "Работа опубликована")
            elif "save_draft" in request.POST and updated_work.status != "published":
                updated_work.status = "draft"
                messages.success(request, "Изменения сохранены")
            else:
                messages.success(request, "Изменения сохранены")

            updated_work.save()
            return redirect("work_detail", work_id=work.id)
    else:
        form = WorkEditForm(instance=work)

    return render(request, "works/update_work.html", {
        "form": form,
        "work": work,
    })


@login_required
def upload_version(request, work_id):
    work = get_object_or_404(Work, id=work_id)

    if not user_can_manage_work(request.user, work):
        return HttpResponse("Доступ запрещен")

    if request.method == "POST":
        form = WorkVersionForm(request.POST, request.FILES)
        if form.is_valid():
            last_version = work.versions.first()
            next_version_number = 1 if not last_version else last_version.version_number + 1

            version = form.save(commit=False)
            version.work = work
            version.version_number = next_version_number
            version.uploaded_by = request.user
            version.save()

            for uploaded_file in form.cleaned_data["files"]:
                WorkVersionFile.objects.create(
                    version=version,
                    file=uploaded_file,
                    original_name=uploaded_file.name,
                )

            return redirect("work_detail", work_id=work.id)
    else:
        form = WorkVersionForm()

    return render(request, "works/upload_version.html", {
        "form": form,
        "work": work,
    })


@login_required
def my_works(request):
    works = Work.objects.filter(author=request.user).select_related("section").order_by("-created_at")
    return render(request, "works/my_works.html", {"works": works})


@login_required
def all_works(request):
    works = _visible_works_queryset_for_user(request.user)
    return render(request, "works/all_works.html", {"works": works})


def _visible_works_queryset_for_user(user):
    works = Work.objects.select_related("author", "section")

    if user.is_authenticated and user.profile.is_admin():
        return works.order_by("-created_at")
    if user.is_authenticated:
        return works.filter(
            Q(status="published", visibility="public") | Q(author=user)
        ).distinct().order_by("-created_at")
    return works.filter(status="published", visibility="public").order_by("-created_at")


def section_detail(request, section_id):
    section = get_object_or_404(WorkSection, id=section_id)
    works = _visible_works_queryset_for_user(request.user).filter(section=section)

    return render(request, "works/section_detail.html", {
        "section": section,
        "works": works,
    })


def work_detail(request, work_id):
    work = get_object_or_404(Work.objects.select_related("author", "section", "author__profile"), id=work_id)

    is_owner_or_admin = request.user.is_authenticated and (
        request.user == work.author or request.user.profile.is_admin()
    )
    is_publicly_available = work.status == "published" and work.visibility == "public"

    if not is_publicly_available and not is_owner_or_admin:
        return HttpResponse("Доступ запрещен")

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect("login")

        if not is_publicly_available:
            return HttpResponse("Комментарии разрешены только для опубликованных открытых работ")

        comment_form = WorkCommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.work = work
            comment.author = request.user
            comment.save()
            return redirect("work_detail", work_id=work.id)
    else:
        comment_form = WorkCommentForm()

    versions = work.versions.prefetch_related("files", "uploaded_by").all()
    comments = work.comments.select_related("author").order_by("-created_at")
    total_files = WorkVersionFile.objects.filter(version__work=work).count()

    return render(request, "works/work_detail.html", {
        "work": work,
        "is_publicly_available": is_publicly_available,
        "versions": versions,
        "comments": comments,
        "comment_form": comment_form,
        "is_publicly_available": is_publicly_available,
        "total_files": total_files,
    })


def _ensure_work_visible_to_user(request, work):
    if work.visibility == "private":
        if not request.user.is_authenticated:
            raise Http404()
        if request.user != work.author and not request.user.profile.is_admin():
            raise Http404()


@login_required
def download_version_archive(request, work_id, version_id):
    work = get_object_or_404(Work, id=work_id)
    _ensure_work_visible_to_user(request, work)

    version = get_object_or_404(
        WorkVersion.objects.prefetch_related("files"),
        id=version_id,
        work=work,
    )

    archive_buffer = BytesIO()
    archive_name = f"{slugify(work.title) or 'work'}-version-{version.version_number}.zip"

    with zipfile.ZipFile(archive_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for version_file in version.files.all():
            version_file.file.open("rb")
            try:
                archive.writestr(version_file.filename, version_file.file.read())
            finally:
                version_file.file.close()

    archive_buffer.seek(0)
    return FileResponse(archive_buffer, as_attachment=True, filename=archive_name)


def download_version_file(request, work_id, version_id, file_id):
    work = get_object_or_404(Work, id=work_id)
    _ensure_work_visible_to_user(request, work)

    version_file = get_object_or_404(
        WorkVersionFile,
        id=file_id,
        version_id=version_id,
        version__work=work,
    )

    return FileResponse(
        version_file.file.open("rb"),
        as_attachment=True,
        filename=version_file.filename,
    )

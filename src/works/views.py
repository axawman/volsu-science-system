import os
import zipfile
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.text import slugify

from .forms import WorkCreateForm, WorkEditForm, WorkVersionForm
from .models import Work, WorkVersion, WorkVersionFile
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
    work = get_object_or_404(Work, id=work_id)

    if not user_can_manage_work(request.user, work):
        return HttpResponse("Доступ запрещен")

    if request.method == "POST":
        form = WorkEditForm(request.POST, instance=work)
        if form.is_valid():
            updated_work = form.save(commit=False)
            updated_work.author = work.author
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
    works = Work.objects.filter(author=request.user).order_by("-created_at")
    return render(request, "works/my_works.html", {"works": works})


@login_required
def all_works(request):
    works = Work.objects.select_related("author").order_by("-created_at")
    return render(request, "works/all_works.html", {"works": works})


def work_detail(request, work_id):
    work = get_object_or_404(Work, id=work_id)

    if work.visibility == "private":
        if not request.user.is_authenticated:
            return HttpResponse("Доступ запрещен")

        if request.user != work.author and not request.user.profile.is_admin():
            return HttpResponse("Доступ запрещен")

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect("login")

        if work.visibility != "public":
            return HttpResponse("Комментарии разрешены только для публичных работ")

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
        "versions": versions,
        "comments": comments,
        "comment_form": comment_form,
        "total_files": total_files,
    })


def _ensure_work_visible_to_user(request, work):
    if work.visibility == "private":
        if not request.user.is_authenticated:
            raise Http404()
        if request.user != work.author and not request.user.profile.is_admin():
            raise Http404()


@login_required
def download_work_archive(request, work_id):
    work = get_object_or_404(Work, id=work_id)

    if not user_can_manage_work(request.user, work) and work.visibility == "private":
        return HttpResponse("Доступ запрещен")

    archive_buffer = BytesIO()
    archive_name = f"{slugify(work.title) or 'work'}-files.zip"

    with zipfile.ZipFile(archive_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        versions = work.versions.prefetch_related("files").all().order_by("version_number")
        for version in versions:
            version_folder = f"version_{version.version_number}"
            for version_file in version.files.all():
                version_file.file.open("rb")
                try:
                    archive.writestr(
                        os.path.join(version_folder, version_file.filename),
                        version_file.file.read(),
                    )
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

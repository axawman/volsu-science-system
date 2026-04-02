from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404

from .forms import WorkCreateForm, WorkEditForm, WorkVersionForm
from .models import Work, WorkVersion
from discussions.models import WorkComment
from discussions.forms import WorkCommentForm


@login_required
def create_work(request):
    if request.method == "POST":
        form = WorkCreateForm(request.POST, request.FILES)
        if form.is_valid():
            work = form.save(commit=False)
            work.author = request.user
            work.save()

            WorkVersion.objects.create(
                work=work,
                version_number=1,
                file=form.cleaned_data["file"],
                comment=form.cleaned_data.get("comment", ""),
                uploaded_by=request.user,
            )

            return redirect("/works/my/")
    else:
        form = WorkCreateForm()

    return render(request, "works/create_work.html", {"form": form})


@login_required
def update_work(request, work_id):
    work = get_object_or_404(Work, id=work_id)

    if request.user != work.author and not request.user.profile.is_admin():
        return HttpResponse("Доступ запрещен")

    if request.method == "POST":
        form = WorkEditForm(request.POST, instance=work)
        if form.is_valid():
            updated_work = form.save(commit=False)
            updated_work.author = work.author
            updated_work.save()
            return redirect(f"/works/{work.id}/")
    else:
        form = WorkEditForm(instance=work)

    return render(request, "works/update_work.html", {
        "form": form,
        "work": work,
    })


@login_required
def upload_version(request, work_id):
    work = get_object_or_404(Work, id=work_id)

    if request.user != work.author and not request.user.profile.is_admin():
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

            return redirect(f"/works/{work.id}/")
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
            return redirect("/login/")

        if work.visibility != "public":
            return HttpResponse("Комментарии разрешены только для публичных работ")

        comment_form = WorkCommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.work = work
            comment.author = request.user
            comment.save()
            return redirect(f"/works/{work.id}/")
    else:
        comment_form = WorkCommentForm()

    versions = work.versions.all()
    comments = work.comments.select_related("author").order_by("-created_at")

    return render(request, "works/work_detail.html", {
        "work": work,
        "versions": versions,
        "comments": comments,
        "comment_form": comment_form,
    })
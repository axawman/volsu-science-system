from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from .forms import RegisterForm, ProfileEditForm


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
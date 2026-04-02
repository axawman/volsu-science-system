from django.http import HttpResponse
from django.contrib.auth.decorators import login_required


def admin_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, "profile") or not request.user.profile.is_admin():
            return HttpResponse("Доступ запрещен")
        return view_func(request, *args, **kwargs)
    return wrapper

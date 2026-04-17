from django.http import HttpResponse
from django.contrib.auth.decorators import login_required


def admin_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser or request.user.is_staff:
            return view_func(request, *args, **kwargs)

        if hasattr(request.user, "profile") and request.user.profile.is_admin():
            return view_func(request, *args, **kwargs)

        return HttpResponse("Доступ запрещен", status=403)
    return wrapper
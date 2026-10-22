import posixpath

from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.http import Http404
from accounts.forms import EmailOrUsernameAuthenticationForm

urlpatterns = [
    path("admin/", admin.site.urls),

    path("accounts/", include("accounts.urls")),

    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            authentication_form=EmailOrUsernameAuthenticationForm,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(next_page="/"), name="logout"),

    path("", include("core.urls")),
    path("works/", include("works.urls")),
    path("guide/", include("guide.urls")),
]

# Без nginx Django сам отдаёт публичные картинки. Файлы работ и справочника
# сюда не входят: их отдают отдельные view с проверкой доступа.
PUBLIC_MEDIA_DIRS = ("profile_photos", "platform_news")


def public_media(request, path):
    # serve() сам схлопывает "..", поэтому папку проверяем уже у нормализованного пути
    path = posixpath.normpath(path).lstrip("/")
    if path.split("/", 1)[0] not in PUBLIC_MEDIA_DIRS:
        raise Http404
    return serve(request, path, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [
        re_path(r"^media/(?P<path>.+)$", public_media),
    ]

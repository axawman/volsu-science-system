"""Единые правила доступа к научным работам.

Работу видят все, если она опубликована и открыта. Автор и администраторы
видят и могут менять любые свои/все работы — черновики и скрытые тоже.
"""

from django.db.models import Q

from .models import Work


def is_works_admin(user):
    return user.is_authenticated and user.profile.is_admin()


def can_manage_work(user, work):
    return user.is_authenticated and (work.author_id == user.id or is_works_admin(user))


def is_publicly_available(work):
    return work.status == "published" and work.visibility == "public"


def can_view_work(user, work):
    return is_publicly_available(work) or can_manage_work(user, work)


def visible_work_filter(user, prefix=""):
    """Q-условие видимых работ; prefix — путь к работе из другой модели, например "works__"."""
    public = Q(**{f"{prefix}status": "published", f"{prefix}visibility": "public"})

    if is_works_admin(user):
        return Q(**{f"{prefix}pk__isnull": False})
    if user.is_authenticated:
        return public | Q(**{f"{prefix}author": user})
    return public


def visible_works(user):
    return Work.objects.filter(visible_work_filter(user))

from django.utils import timezone

from .views import get_pending_reminders


def personal_reminders(request):
    if not request.user.is_authenticated:
        return {}
    return {"personal_reminders": get_pending_reminders(request.user, timezone.now())}

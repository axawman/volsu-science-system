from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import PersonalEventForm
from .models import PersonalEvent


REMINDER_LOOKAHEAD = timedelta(hours=24)
REMINDER_GRACE = timedelta(days=1)


def personal_event_to_item(event, now):
    local_at = timezone.localtime(event.starts_at)
    return {
        "id": event.id,
        "date": local_at.date().isoformat(),
        "time": local_at.strftime("%H:%M"),
        "title": event.title,
        "type": "personal",
        "kind": "Личное",
        "description": event.description,
        "location": "",
        "is_past": event.starts_at < now,
        "remind_before": event.remind_before,
        "remind_label": event.get_remind_before_display() if event.remind_before is not None else "",
        "update_url": reverse("update_personal_event", kwargs={"event_id": event.id}),
        "delete_url": reverse("delete_personal_event", kwargs={"event_id": event.id}),
    }


def get_pending_reminders(user, now):
    """Напоминания, которые уже наступили или наступят в ближайшие сутки и ещё не скрыты."""
    events = PersonalEvent.objects.filter(
        owner=user,
        remind_at__isnull=False,
        remind_at__lte=now + REMINDER_LOOKAHEAD,
        starts_at__gte=now - REMINDER_GRACE,
        reminder_dismissed_at__isnull=True,
    ).order_by("remind_at")[:10]

    return [reminder_payload(event) for event in events]


def reminder_payload(event):
    return {
        "id": event.id,
        "title": event.title,
        "starts_at": event.starts_at.isoformat(),
        "remind_at": event.remind_at.isoformat(),
        "time_label": timezone.localtime(event.starts_at).strftime("%d.%m.%Y %H:%M"),
        "dismiss_url": reverse("dismiss_personal_reminder", kwargs={"event_id": event.id}),
    }


def _save_personal_event(request, form):
    if not form.is_valid():
        return JsonResponse({"errors": form.errors}, status=400)

    event = form.save()
    now = timezone.now()
    has_pending_reminder = (
        event.remind_at is not None
        and event.reminder_dismissed_at is None
        and event.remind_at <= now + REMINDER_LOOKAHEAD
    )

    return JsonResponse({
        "item": personal_event_to_item(event, now),
        "reminder": reminder_payload(event) if has_pending_reminder else None,
    })


@login_required
@require_POST
def create_personal_event(request):
    form = PersonalEventForm(request.POST, instance=PersonalEvent(owner=request.user))
    return _save_personal_event(request, form)


@login_required
@require_POST
def update_personal_event(request, event_id):
    event = get_object_or_404(PersonalEvent, id=event_id, owner=request.user)
    form = PersonalEventForm(request.POST, instance=event)
    return _save_personal_event(request, form)


@login_required
@require_POST
def delete_personal_event(request, event_id):
    event = get_object_or_404(PersonalEvent, id=event_id, owner=request.user)
    event.delete()
    return JsonResponse({"deleted": event_id})


@login_required
@require_POST
def dismiss_personal_reminder(request, event_id):
    event = get_object_or_404(PersonalEvent, id=event_id, owner=request.user)
    event.reminder_dismissed_at = timezone.now()
    event.save(update_fields=["reminder_dismissed_at"])
    return JsonResponse({"dismissed": event_id})

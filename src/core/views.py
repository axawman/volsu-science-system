from django.shortcuts import render
from django.utils import timezone

from works.models import Work
from meetings.models import Meeting
from events.models import Event


def home(request):
    now = timezone.now()

    latest_works = Work.objects.order_by("-created_at")[:5]
    upcoming_meetings = Meeting.objects.filter(start_at__gte=now).order_by("start_at")[:5]
    upcoming_events = Event.objects.filter(event_date__gte=now).order_by("event_date")[:5]

    calendar_items = []

    for meeting in Meeting.objects.all():
        calendar_items.append({
            "date": meeting.start_at.date().isoformat(),
            "title": meeting.title,
            "type": "meeting",
        })

    for event in Event.objects.all():
        calendar_items.append({
            "date": event.event_date.date().isoformat(),
            "title": event.title,
            "type": "event",
        })

    context = {
        "latest_works": latest_works,
        "upcoming_meetings": upcoming_meetings,
        "upcoming_events": upcoming_events,
        "calendar_items": calendar_items,
        "today": now.date().isoformat(),
    }
    return render(request, "core/home.html", context)
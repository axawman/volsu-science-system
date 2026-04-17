from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone

from works.models import WorkSection
from meetings.models import Meeting
from events.models import Event


def home(request):
    now = timezone.now()

    visible_works_filter = Q(works__status="published", works__visibility="public")
    if request.user.is_authenticated and request.user.profile.is_admin():
        visible_works_filter = Q(works__isnull=False)
    elif request.user.is_authenticated:
        visible_works_filter = Q(works__status="published", works__visibility="public") | Q(works__author=request.user)

    sections = WorkSection.objects.annotate(
        work_count=Count("works", filter=visible_works_filter, distinct=True)
    ).order_by("sort_order", "name")
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
        "sections": sections,
        "upcoming_meetings": upcoming_meetings,
        "upcoming_events": upcoming_events,
        "calendar_items": calendar_items,
        "today": now.date().isoformat(),
    }
    return render(request, "core/home.html", context)
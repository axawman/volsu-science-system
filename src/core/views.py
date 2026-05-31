from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone

from .models import PlatformNews
from works.models import Work, WorkSection
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

    search_query = request.GET.get("q", "").strip()
    search_results = []

    if search_query:
        searchable_works = Work.objects.select_related("author", "author__profile", "section")
        if request.user.is_authenticated and request.user.profile.is_admin():
            pass
        elif request.user.is_authenticated:
            searchable_works = searchable_works.filter(
                Q(status="published", visibility="public") | Q(author=request.user)
            )
        else:
            searchable_works = searchable_works.filter(status="published", visibility="public")

        for term in search_query.split():
            searchable_works = searchable_works.filter(
                Q(title__icontains=term)
                | Q(description__icontains=term)
                | Q(content__icontains=term)
            )

        search_results = searchable_works.distinct().order_by("-updated_at")[:8]

    upcoming_meetings = Meeting.objects.filter(start_at__gte=now).order_by("start_at")[:5]
    upcoming_events = Event.objects.filter(event_date__gte=now).order_by("event_date")[:5]
    upcoming_activity = []

    for meeting in upcoming_meetings:
        upcoming_activity.append({
            "title": meeting.title,
            "kind": "Встреча",
            "type": "meeting",
            "date": meeting.start_at,
            "end_date": None,
            "location": meeting.location,
            "created_by": meeting.created_by,
        })

    for event in upcoming_events:
        upcoming_activity.append({
            "title": event.title,
            "kind": "Событие",
            "type": "event",
            "date": event.event_date,
            "end_date": None,
            "location": event.location,
            "created_by": event.created_by,
        })

    upcoming_activity = sorted(upcoming_activity, key=lambda item: item["date"])[:6]

    calendar_items = []

    for meeting in Meeting.objects.select_related("created_by").all():
        meeting_at = timezone.localtime(meeting.start_at)
        calendar_items.append({
            "date": meeting_at.date().isoformat(),
            "time": meeting_at.strftime("%H:%M"),
            "title": meeting.title,
            "type": "meeting",
            "kind": "Встреча",
            "description": meeting.description,
            "location": meeting.location,
            "created_by": meeting.created_by.username,
            "is_past": meeting.start_at < now,
        })

    for event in Event.objects.select_related("created_by").all():
        event_at = timezone.localtime(event.event_date)
        calendar_items.append({
            "date": event_at.date().isoformat(),
            "time": event_at.strftime("%H:%M"),
            "title": event.title,
            "type": "event",
            "kind": "Событие",
            "description": event.description,
            "location": event.location,
            "created_by": event.created_by.username,
            "is_past": event.event_date < now,
        })

    context = {
        "sections": sections,
        "upcoming_meetings": upcoming_meetings,
        "upcoming_events": upcoming_events,
        "upcoming_activity": upcoming_activity,
        "calendar_items": calendar_items,
        "today": now.date().isoformat(),
        "search_query": search_query,
        "search_results": search_results,
        "platform_news": PlatformNews.objects.filter(is_active=True),
    }
    return render(request, "core/home.html", context)

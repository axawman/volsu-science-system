from datetime import datetime

from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from .models import PlatformNews
from works.models import Work, WorkSection
from meetings.models import Meeting
from events.models import Event
from guide.models import GuideFile, GuideSection


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

    upcoming_activity = get_upcoming_activity(now)

    context = {
        "sections": sections,
        "upcoming_activity": upcoming_activity,
        "guide_sections": GuideSection.objects.filter(is_published=True),
        "guide_files": GuideFile.objects.filter(is_published=True, section__isnull=True),
        "search_query": search_query,
        "search_results": search_results,
        "platform_news": PlatformNews.objects.filter(is_active=True),
    }
    return render(request, "core/home.html", context)


def get_upcoming_activity(now, limit=6):
    upcoming_meetings = (
        Meeting.objects
        .filter(start_at__gte=now)
        .select_related("created_by", "created_by__profile")
        .order_by("start_at")[:limit]
    )
    upcoming_events = (
        Event.objects
        .filter(event_date__gte=now)
        .select_related("created_by", "created_by__profile")
        .order_by("event_date")[:limit]
    )
    upcoming_activity = []

    for meeting in upcoming_meetings:
        upcoming_activity.append({
            "title": meeting.title,
            "kind": "Встреча",
            "type": "meeting",
            "date": meeting.start_at,
            "location": meeting.location,
            "created_by": meeting.created_by,
        })

    for event in upcoming_events:
        upcoming_activity.append({
            "title": event.title,
            "kind": "Событие",
            "type": "event",
            "date": event.event_date,
            "location": event.location,
            "created_by": event.created_by,
        })

    return sorted(upcoming_activity, key=lambda item: item["date"])[:limit]


def calendar_page(request):
    now = timezone.now()

    return render(request, "core/calendar.html", {
        "upcoming_activity": get_upcoming_activity(now),
        "today": timezone.localdate().isoformat(),
    })


def _calendar_item(obj, starts_at, item_type, kind, now):
    local_at = timezone.localtime(starts_at)
    return {
        "date": local_at.date().isoformat(),
        "time": local_at.strftime("%H:%M"),
        "title": obj.title,
        "type": item_type,
        "kind": kind,
        "description": obj.description,
        "location": obj.location,
        "created_by": obj.created_by.username,
        "created_by_name": obj.created_by.profile.short_name,
        "created_by_url": reverse("public_profile", kwargs={"username": obj.created_by.username}),
        "is_past": starts_at < now,
    }


def calendar_items(request):
    try:
        month_start = datetime.strptime(request.GET.get("month", ""), "%Y-%m")
    except ValueError:
        return JsonResponse({"error": "Укажите месяц в формате ГГГГ-ММ"}, status=400)

    if month_start.month == 12:
        month_end = month_start.replace(year=month_start.year + 1, month=1)
    else:
        month_end = month_start.replace(month=month_start.month + 1)

    month_start = timezone.make_aware(month_start)
    month_end = timezone.make_aware(month_end)
    now = timezone.now()

    meetings = (
        Meeting.objects
        .filter(start_at__gte=month_start, start_at__lt=month_end)
        .select_related("created_by", "created_by__profile")
    )
    events = (
        Event.objects
        .filter(event_date__gte=month_start, event_date__lt=month_end)
        .select_related("created_by", "created_by__profile")
    )

    items = [_calendar_item(meeting, meeting.start_at, "meeting", "Встреча", now) for meeting in meetings]
    items += [_calendar_item(event, event.event_date, "event", "Событие", now) for event in events]

    items.sort(key=lambda item: (item["date"], item["time"]))

    return JsonResponse({"items": items})

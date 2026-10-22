"""Отправка напоминаний о личных записях календаря на почту."""

import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone

from .models import PersonalEvent

logger = logging.getLogger(__name__)

# Если отправщик был выключен, старые напоминания не шлём: запись уже давно прошла
MAX_DELAY = timedelta(days=1)


def _message(event):
    starts_at = timezone.localtime(event.starts_at)
    lines = [
        f"Напоминание: {event.title}",
        "",
        f"Когда: {starts_at:%d.%m.%Y в %H:%M}",
    ]
    if event.description:
        lines += ["", event.description]
    lines += ["", f"Календарь: {settings.SITE_URL}{reverse('calendar')}"]
    return "\n".join(lines)


def due_reminders(now):
    return (
        PersonalEvent.objects
        .filter(
            remind_at__isnull=False,
            remind_at__lte=now,
            reminder_emailed_at__isnull=True,
            starts_at__gte=now - MAX_DELAY,
            owner__is_active=True,
        )
        .exclude(owner__email="")
        .select_related("owner")
        .order_by("remind_at")
    )


def send_due_reminders(now=None):
    """Отправляет наступившие напоминания. Возвращает (отправлено, не удалось)."""
    now = now or timezone.now()
    sent = failed = 0

    for event in due_reminders(now):
        # Сначала «забираем» напоминание: второй запущенный отправщик его уже не возьмёт
        claimed = PersonalEvent.objects.filter(
            pk=event.pk,
            reminder_emailed_at__isnull=True,
        ).update(reminder_emailed_at=now)
        if not claimed:
            continue

        try:
            send_mail(
                subject=f"Напоминание: {event.title}",
                message=_message(event),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[event.owner.email],
                fail_silently=False,
            )
        except Exception:
            logger.exception("Не удалось отправить напоминание %s на %s", event.pk, event.owner.email)
            # Вернём в очередь — попробуем на следующем запуске
            PersonalEvent.objects.filter(pk=event.pk).update(reminder_emailed_at=None)
            failed += 1
        else:
            sent += 1

    return sent, failed

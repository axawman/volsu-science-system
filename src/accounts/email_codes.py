"""Выдача и проверка одноразовых кодов из писем с защитой от перебора."""

import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from .models import EmailCode

CODE_TTL = timedelta(minutes=5)
MAX_ATTEMPTS = 5
RESEND_COOLDOWN = timedelta(seconds=60)
MAX_CODES_PER_HOUR = 5


class CodeError(Exception):
    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


def _hash(email, purpose, code):
    return salted_hmac("accounts.email_code", f"{purpose}:{email}:{code}", algorithm="sha256").hexdigest()


def _seconds_until(moment, now):
    return max(1, int((moment - now).total_seconds()) + 1)


def issue_code(email, purpose):
    """Создаёт новый код и аннулирует прежние. Возвращает (код, запись)."""
    now = timezone.now()

    with transaction.atomic():
        recent = list(
            EmailCode.objects
            .select_for_update()
            .filter(email=email, purpose=purpose, created_at__gte=now - timedelta(hours=1))
            .order_by("-created_at")
        )
        if recent and recent[0].created_at + RESEND_COOLDOWN > now:
            raise CodeError(
                "Отправить код заново можно через минуту.",
                retry_after=_seconds_until(recent[0].created_at + RESEND_COOLDOWN, now),
            )
        if len(recent) >= MAX_CODES_PER_HOUR:
            raise CodeError(
                "Слишком много запросов кода. Попробуйте позже.",
                retry_after=_seconds_until(recent[-1].created_at + timedelta(hours=1), now),
            )

        EmailCode.objects.filter(email=email, purpose=purpose, used_at__isnull=True).update(used_at=now)
        code = f"{secrets.randbelow(1000000):06d}"
        record = EmailCode.objects.create(
            email=email,
            purpose=purpose,
            code_hash=_hash(email, purpose, code),
            expires_at=now + CODE_TTL,
        )

    EmailCode.objects.filter(created_at__lt=now - timedelta(days=1)).delete()
    return code, record


def verify_code(email, purpose, code):
    """Проверяет код и погашает его. При ошибке бросает CodeError с текстом для пользователя."""
    now = timezone.now()
    error = None

    # Исключение бросаем только после выхода из транзакции, иначе откатится и счётчик попыток
    with transaction.atomic():
        # Блокировка строки: параллельные попытки не обгонят счётчик
        record = (
            EmailCode.objects
            .select_for_update()
            .filter(email=email, purpose=purpose, used_at__isnull=True, expires_at__gt=now)
            .order_by("-created_at")
            .first()
        )
        if record is None:
            error = "Код устарел или не запрашивался. Запросите новый код."
        elif constant_time_compare(record.code_hash, _hash(email, purpose, (code or "").strip())):
            record.used_at = now
            record.save(update_fields=["used_at"])
        else:
            record.attempts += 1
            if record.attempts >= MAX_ATTEMPTS:
                record.used_at = now
                error = "Слишком много неверных попыток. Запросите новый код."
            else:
                error = f"Неверный код. Осталось попыток: {MAX_ATTEMPTS - record.attempts}."
            record.save(update_fields=["attempts", "used_at"])

    if error:
        raise CodeError(error)

import logging
import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from events.reminders import send_due_reminders

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Отправляет на почту наступившие напоминания о личных записях календаря"

    def add_arguments(self, parser):
        parser.add_argument(
            "--loop",
            action="store_true",
            help="Работать постоянно, проверяя напоминания каждые --interval секунд",
        )
        parser.add_argument("--interval", type=int, default=60, help="Пауза между проверками, секунд")

    def handle(self, *args, **options):
        if not options["loop"]:
            self.run_once()
            return

        self.stdout.write(f"Отправка напоминаний запущена, проверка каждые {options['interval']} с")
        while True:
            # Вне запросов Django сам не закрывает соединения: после перезапуска базы оно было бы мёртвым
            close_old_connections()
            try:
                self.run_once()
            except Exception:
                logger.exception("Ошибка при отправке напоминаний, повторим на следующем цикле")
            time.sleep(options["interval"])

    def run_once(self):
        sent, failed = send_due_reminders()
        if sent or failed:
            self.stdout.write(f"Напоминаний отправлено: {sent}, не удалось: {failed}")

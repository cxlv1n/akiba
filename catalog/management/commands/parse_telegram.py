import asyncio
import logging
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from catalog.services import TelegramParser

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Parse cars from Telegram channel'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Number of recent posts to process (default: 50)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without creating database records'
        )
        parser.add_argument(
            '--channel',
            type=str,
            default=None,
            help='Override default channel username'
        )

    def handle(self, *args, **options):
        # Проверяем настройки
        if not settings.TELEGRAM_API_ID or not settings.TELEGRAM_API_HASH:
            raise CommandError(
                "Telegram API credentials not configured. "
                "Please set TELEGRAM_API_ID and TELEGRAM_API_HASH in your environment."
            )

        limit = options['limit']
        dry_run = options['dry_run']
        channel = options['channel'] or settings.TELEGRAM_CHANNEL

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting Telegram parsing for channel: {channel}"
            )
        )
        self.stdout.write(f"Processing last {limit} posts...")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No database changes will be made"))

        try:
            # Создаем парсер
            parser = TelegramParser()

            # Запускаем парсинг в asyncio
            created_cars = asyncio.run(parser.process_channel_posts(limit))

            # Закрываем соединение
            asyncio.run(parser.close())

            # Выводим результаты
            if created_cars:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully processed {len(created_cars)} cars from Telegram"
                    )
                )

                for car in created_cars:
                    self.stdout.write(
                        f"  - {car.manufacturer} {car.model} {car.year} "
                        f"({car.price}₽, {car.mileage_km}km)"
                    )
            else:
                self.stdout.write(
                    self.style.WARNING("No new cars were created from Telegram posts")
                )

        except Exception as e:
            logger.error(f"Error during Telegram parsing: {e}")
            raise CommandError(f"Failed to parse Telegram channel: {e}")

        self.stdout.write(self.style.SUCCESS("Telegram parsing completed"))
"""
Management команда для импорта данных из Telegram канала.

Использование:
    python manage.py telegram_import
    python manage.py telegram_import --channel akibaautovl --limit 50
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Импорт данных из Telegram канала'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--channel',
            type=str,
            default='akibaautovl',
            help='Username канала (без @)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Максимальное количество сообщений'
        )
        parser.add_argument(
            '--skip-media',
            action='store_true',
            help='Пропустить загрузку медиа'
        )
    
    def handle(self, *args, **options):
        from catalog.services import TelegramImporter
        
        channel = options['channel']
        limit = options['limit']
        skip_media = options['skip_media']
        
        self.stdout.write(self.style.WARNING(
            f'\n=== Импорт из @{channel} ===\n'
        ))
        
        try:
            importer = TelegramImporter()
            result = importer.import_channel(
                channel=channel,
                limit=limit,
                skip_media=skip_media
            )
            
            self.stdout.write('\n--- Результаты ---')
            self.stdout.write(f'Статус: {result.get_status_display()}')
            self.stdout.write(f'Получено сообщений: {result.messages_fetched}')
            self.stdout.write(f'Новых сообщений: {result.messages_new}')
            self.stdout.write(f'Успешно распарсено: {result.messages_parsed_ok}')
            self.stdout.write(f'Частично распарсено: {result.messages_parsed_partial}')
            self.stdout.write(f'Ошибок: {result.messages_failed}')
            self.stdout.write(f'Создано карточек: {result.listings_created}')
            self.stdout.write(f'Загружено фото: {result.photos_downloaded}')
            
            if result.error_message:
                self.stderr.write(self.style.ERROR(f'\nОшибка: {result.error_message}'))
            
            if result.status == 'success':
                self.stdout.write(self.style.SUCCESS('\n✓ Импорт завершён успешно!\n'))
            elif result.status == 'partial':
                self.stdout.write(self.style.WARNING('\n⚠ Импорт завершён с ошибками\n'))
            else:
                self.stdout.write(self.style.ERROR('\n✗ Импорт не удался\n'))
                
        except ValueError as e:
            self.stderr.write(self.style.ERROR(f'\nОшибка конфигурации: {e}\n'))
            self.stdout.write(
                'Запустите авторизацию: python manage.py telegram_auth\n'
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'\nОшибка: {e}\n'))



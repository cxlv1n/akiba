"""
Management команда для авторизации в Telegram.

Использование:
    python manage.py telegram_auth
"""

import os
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Авторизация в Telegram для импорта данных из канала'
    
    def handle(self, *args, **options):
        try:
            from telethon.sync import TelegramClient
            from telethon.sessions import StringSession
        except ImportError:
            self.stderr.write(
                self.style.ERROR('Telethon не установлен. Выполните: pip install telethon')
            )
            return
        
        api_id = os.environ.get('TELEGRAM_API_ID')
        api_hash = os.environ.get('TELEGRAM_API_HASH')
        
        if not api_id or not api_hash:
            self.stderr.write(
                self.style.ERROR(
                    'Не заданы TELEGRAM_API_ID и TELEGRAM_API_HASH.\n'
                    'Получите их на https://my.telegram.org и добавьте в .env файл.'
                )
            )
            return
        
        session_path = os.path.join(settings.BASE_DIR, 'telegram_session')
        
        self.stdout.write(self.style.WARNING(
            '\n=== Авторизация в Telegram ===\n'
            'Сессия будет сохранена в: telegram_session.session\n'
        ))
        
        client = TelegramClient(session_path, int(api_id), api_hash)
        
        client.connect()
        
        if client.is_user_authorized():
            me = client.get_me()
            self.stdout.write(self.style.SUCCESS(
                f'\n✓ Уже авторизован как: {me.first_name} (@{me.username})\n'
            ))
        else:
            self.stdout.write('Введите номер телефона (в формате +79xxxxxxxxx):')
            phone = input().strip()
            
            client.send_code_request(phone)
            
            self.stdout.write('Введите код из Telegram:')
            code = input().strip()
            
            try:
                client.sign_in(phone, code)
            except Exception as e:
                if 'Two-step verification' in str(e) or 'password' in str(e).lower():
                    self.stdout.write('Введите пароль двухфакторной аутентификации:')
                    password = input().strip()
                    client.sign_in(password=password)
                else:
                    raise
            
            me = client.get_me()
            self.stdout.write(self.style.SUCCESS(
                f'\n✓ Успешно авторизован как: {me.first_name} (@{me.username})\n'
            ))
        
        # Проверяем доступ к каналу
        channel = 'akibaautovl'
        try:
            entity = client.get_entity(channel)
            self.stdout.write(self.style.SUCCESS(
                f'✓ Доступ к каналу @{channel}: {entity.title}\n'
            ))
        except Exception as e:
            self.stdout.write(self.style.WARNING(
                f'⚠ Не удалось получить доступ к каналу @{channel}: {e}\n'
            ))
        
        client.disconnect()
        
        self.stdout.write(self.style.SUCCESS(
            '\n=== Готово! ===\n'
            'Теперь можно запускать импорт через админку или командой:\n'
            '  python manage.py telegram_import\n'
        ))


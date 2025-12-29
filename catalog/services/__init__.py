"""
Сервисы каталога автомобилей.

- parser: Парсинг текста Telegram постов
- importer: Импорт данных из Telegram канала
- analytics: Аналитика просмотров
"""

from .parser import TelegramPostParser
from .importer import TelegramImporter, run_telegram_import
from .analytics import AnalyticsService

# Алиас для обратной совместимости
SyncTelegramImporter = TelegramImporter

__all__ = [
    'TelegramPostParser', 
    'TelegramImporter', 
    'SyncTelegramImporter',
    'run_telegram_import',
    'AnalyticsService'
]


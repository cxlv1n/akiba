"""
Сервис импорта данных из Telegram канала.

Использует Telethon для работы с Telegram MTProto API.
Поддерживает инкрементальную загрузку и дедупликацию.
"""

import os
import hashlib
import logging
import traceback
from io import BytesIO
from typing import Optional, List
from datetime import datetime

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class TelegramImporter:
    """
    Импортер данных из Telegram канала (синхронная версия).
    
    Использование:
        importer = TelegramImporter()
        result = importer.import_channel('akibaautovl', user=request.user)
    """
    
    DEFAULT_CHANNEL = 'akibaautovl'
    BATCH_SIZE = 100  # Сообщений за запрос
    PHOTO_MAX_SIZE = 10 * 1024 * 1024  # 10 MB
    
    def __init__(self):
        self.client = None
        self.import_run = None
        self._parser = None
    
    @property
    def parser(self):
        """Lazy-load парсера"""
        if self._parser is None:
            from .parser import TelegramPostParser
            self._parser = TelegramPostParser()
        return self._parser
    
    def import_channel(
        self,
        channel: str = None,
        user=None,
        limit: int = None,
        skip_media: bool = False
    ) -> 'ImportRun':
        """
        Импортирует сообщения из Telegram канала.
        
        Args:
            channel: Username канала (без @)
            user: Django user, запустивший импорт
            limit: Максимальное количество сообщений для импорта
            skip_media: Пропустить загрузку медиа
        
        Returns:
            ImportRun с результатами импорта
        """
        from ..models import (
            TelegramMessage, TelegramMedia, TelegramImportState,
            ImportRun, CarListing, CarPhoto, Brand
        )
        
        channel = channel or self.DEFAULT_CHANNEL
        
        # Создаём запись о запуске импорта
        self.import_run = ImportRun.objects.create(
            channel=channel,
            status=ImportRun.Status.RUNNING,
            started_by=user
        )
        
        try:
            # Инициализируем Telethon клиент (синхронный)
            client = self._get_client()
            
            # Получаем состояние импорта
            state, _ = TelegramImportState.objects.get_or_create(
                channel=channel,
                defaults={'last_msg_id': 0}
            )
            
            # Загружаем сообщения
            messages_data = self._fetch_messages(
                client, channel, state.last_msg_id, limit
            )
            
            self.import_run.messages_fetched = len(messages_data)
            self.import_run.save(update_fields=['messages_fetched'])
            
            logger.info(f"Fetched {len(messages_data)} messages from {channel}")
            
            # Обрабатываем сообщения
            max_msg_id = state.last_msg_id
            
            for msg_data in messages_data:
                try:
                    result = self._process_message(
                        client, channel, msg_data, skip_media
                    )
                    
                    if result['is_new']:
                        self.import_run.messages_new += 1
                    
                    if result['listing_created']:
                        self.import_run.listings_created += 1
                    
                    if result['parse_status'] == TelegramMessage.ParseStatus.PARSED_OK:
                        self.import_run.messages_parsed_ok += 1
                    elif result['parse_status'] == TelegramMessage.ParseStatus.PARSED_PARTIAL:
                        self.import_run.messages_parsed_partial += 1
                    elif result['parse_status'] == TelegramMessage.ParseStatus.PARSE_FAILED:
                        self.import_run.messages_failed += 1
                    
                    self.import_run.photos_downloaded += result.get('photos_count', 0)
                    
                    # Обновляем max_msg_id
                    if msg_data['id'] > max_msg_id:
                        max_msg_id = msg_data['id']
                    
                except Exception as e:
                    logger.error(f"Error processing message {msg_data.get('id')}: {e}")
                    self.import_run.messages_failed += 1
                    continue
            
            # Обновляем состояние
            state.last_msg_id = max_msg_id
            state.last_import_date = timezone.now()
            state.total_imported += self.import_run.messages_new
            state.save()
            
            # Определяем итоговый статус
            if self.import_run.messages_failed == 0:
                status = ImportRun.Status.SUCCESS
            elif self.import_run.messages_parsed_ok > 0:
                status = ImportRun.Status.PARTIAL
            else:
                status = ImportRun.Status.FAILED
            
            self.import_run.mark_finished(status)
            
        except Exception as e:
            logger.exception(f"Import failed: {e}")
            self.import_run.mark_finished(
                ImportRun.Status.FAILED,
                error_message=str(e),
                error_traceback=traceback.format_exc()
            )
        
        finally:
            if self.client and hasattr(self, '_loop'):
                try:
                    self._loop.run_until_complete(self.client.disconnect())
                except Exception:
                    pass
        
        return self.import_run
    
    def _get_client(self):
        """Инициализирует Telethon клиент"""
        import asyncio
        
        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
        except ImportError:
            raise ImportError(
                "Telethon не установлен. Выполните: pip install telethon"
            )
        
        api_id = os.environ.get('TELEGRAM_API_ID')
        api_hash = os.environ.get('TELEGRAM_API_HASH')
        session_string = os.environ.get('TELEGRAM_SESSION_STRING', '')
        
        if not api_id or not api_hash:
            raise ValueError(
                "Не заданы TELEGRAM_API_ID и TELEGRAM_API_HASH. "
                "Получите их на https://my.telegram.org"
            )
        
        # Создаём event loop для текущего потока если его нет
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Используем StringSession для serverless окружения
        if session_string:
            session = StringSession(session_string)
        else:
            # Для локальной разработки используем файловую сессию
            session_path = os.path.join(settings.BASE_DIR, 'telegram_session')
            session = session_path
        
        self.client = TelegramClient(session, int(api_id), api_hash)
        loop.run_until_complete(self.client.connect())
        
        if not loop.run_until_complete(self._check_authorized()):
            raise ValueError(
                "Telegram сессия не авторизована. "
                "Запустите скрипт авторизации: python manage.py telegram_auth"
            )
        
        self._loop = loop
        return self.client
    
    async def _check_authorized(self):
        """Проверяет авторизацию асинхронно"""
        return await self.client.is_user_authorized()
    
    def _fetch_messages(
        self,
        client,
        channel: str,
        min_id: int,
        limit: int = None
    ) -> List[dict]:
        """Загружает сообщения из канала"""
        return self._loop.run_until_complete(
            self._fetch_messages_async(client, channel, min_id, limit)
        )
    
    async def _fetch_messages_async(
        self,
        client,
        channel: str,
        min_id: int,
        limit: int = None
    ) -> List[dict]:
        """Асинхронно загружает сообщения из канала"""
        from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
        
        messages = []
        entity = await client.get_entity(channel)
        
        async for message in client.iter_messages(
            entity,
            min_id=min_id,
            limit=limit or self.BATCH_SIZE,
            reverse=True  # От старых к новым
        ):
            # Собираем данные сообщения
            has_video = False
            if message.media and hasattr(message.media, 'document') and message.media.document:
                mime = getattr(message.media.document, 'mime_type', '')
                has_video = mime.startswith('video') if mime else False
            
            msg_data = {
                'id': message.id,
                'grouped_id': message.grouped_id,
                'date': message.date,
                'text': message.text or '',
                'has_photo': isinstance(message.media, MessageMediaPhoto),
                'has_video': has_video,
                'media': message.media,
                'raw': {
                    'views': message.views,
                    'forwards': message.forwards,
                    'replies': message.replies.replies if message.replies else 0,
                }
            }
            messages.append(msg_data)
        
        return messages
    
    def _process_message(
        self,
        client,
        channel: str,
        msg_data: dict,
        skip_media: bool
    ) -> dict:
        """Обрабатывает одно сообщение"""
        from ..models import (
            TelegramMessage, TelegramMedia, CarListing, CarPhoto, Brand, CarModel
        )
        
        result = {
            'is_new': False,
            'listing_created': False,
            'parse_status': TelegramMessage.ParseStatus.NEW,
            'photos_count': 0
        }
        
        # Проверяем дубликат
        existing = TelegramMessage.objects.filter(
            channel=channel,
            telegram_msg_id=msg_data['id']
        ).first()
        
        if existing:
            logger.debug(f"Message {msg_data['id']} already exists")
            result['parse_status'] = existing.parse_status
            return result
        
        result['is_new'] = True
        
        # Создаём запись сообщения
        tg_message = TelegramMessage.objects.create(
            channel=channel,
            telegram_msg_id=msg_data['id'],
            grouped_id=msg_data['grouped_id'],
            date=msg_data['date'],
            text=msg_data['text'],
            raw=msg_data['raw'],
            has_photo=msg_data['has_photo'],
            has_video=msg_data['has_video'],
            parse_status=TelegramMessage.ParseStatus.NEW
        )
        
        # Загружаем фото (если есть и не пропускаем)
        if msg_data['has_photo'] and not skip_media:
            try:
                photo_data = self._download_photo(client, msg_data['media'])
                if photo_data:
                    TelegramMedia.objects.create(
                        message=tg_message,
                        media_type=TelegramMedia.MediaType.PHOTO,
                        file=photo_data['file'],
                        position=0,
                        telegram_file_id=photo_data.get('file_id'),
                        file_size=photo_data.get('size'),
                        width=photo_data.get('width'),
                        height=photo_data.get('height')
                    )
                    result['photos_count'] = 1
            except Exception as e:
                logger.warning(f"Failed to download photo for message {msg_data['id']}: {e}")
        
        # Парсим текст
        if not msg_data['text'].strip():
            tg_message.parse_status = TelegramMessage.ParseStatus.SKIPPED
            tg_message.save(update_fields=['parse_status'])
            result['parse_status'] = TelegramMessage.ParseStatus.SKIPPED
            return result
        
        parsed = self.parser.parse(msg_data['text'])
        parse_status = self.parser.get_parse_status(parsed)
        
        tg_message.parse_status = parse_status
        if parsed.parse_errors:
            tg_message.parse_errors = parsed.parse_errors
        tg_message.save(update_fields=['parse_status', 'parse_errors'])
        
        result['parse_status'] = parse_status
        
        # Создаём карточку если парсинг успешен
        if parse_status in (
            TelegramMessage.ParseStatus.PARSED_OK,
            TelegramMessage.ParseStatus.PARSED_PARTIAL
        ):
            with transaction.atomic():
                listing = self._create_listing(parsed, tg_message, channel)
                if listing:
                    tg_message.car_listing = listing
                    tg_message.save(update_fields=['car_listing'])
                    result['listing_created'] = True
                    
                    # Копируем фото в карточку
                    for idx, tg_media in enumerate(tg_message.media.filter(
                        media_type=TelegramMedia.MediaType.PHOTO
                    )):
                        CarPhoto.objects.create(
                            car_listing=listing,
                            image=tg_media.file,
                            position=idx,
                            is_main=(idx == 0),
                            telegram_media=tg_media,
                            alt=listing.title
                        )
        
        return result
    
    def _download_photo(self, client, media) -> Optional[dict]:
        """Загружает фото из Telegram"""
        from telethon.tl.types import MessageMediaPhoto
        
        if not isinstance(media, MessageMediaPhoto):
            return None
        
        try:
            return self._loop.run_until_complete(
                self._download_photo_async(client, media)
            )
        except Exception as e:
            logger.error(f"Error downloading photo: {e}")
            return None
    
    async def _download_photo_async(self, client, media) -> Optional[dict]:
        """Асинхронно загружает фото из Telegram"""
        # Скачиваем в память
        buffer = BytesIO()
        await client.download_media(media, buffer)
        buffer.seek(0)
        
        # Получаем метаданные
        photo = media.photo
        size = photo.sizes[-1] if photo.sizes else None
        
        # Создаём Django file
        content = buffer.read()
        file_hash = hashlib.md5(content).hexdigest()[:12]
        filename = f"tg_{photo.id}_{file_hash}.jpg"
        
        return {
            'file': ContentFile(content, name=filename),
            'file_id': str(photo.id),
            'size': len(content),
            'width': size.w if size and hasattr(size, 'w') else None,
            'height': size.h if size and hasattr(size, 'h') else None,
        }
    
    def _create_listing(self, parsed, tg_message, channel: str) -> Optional['CarListing']:
        """Создаёт карточку автомобиля из распарсенных данных"""
        from ..models import CarListing, Brand, CarModel
        
        # Ищем/создаём марку
        brand = None
        if parsed.brand_raw:
            brand, _ = Brand.objects.get_or_create(
                name__iexact=parsed.brand_raw,
                defaults={'name': parsed.brand_raw}
            )
        
        # Ищем/создаём модель
        car_model = None
        if brand and parsed.model_raw:
            car_model, _ = CarModel.objects.get_or_create(
                brand=brand,
                name__iexact=parsed.model_raw,
                defaults={'name': parsed.model_raw}
            )
        
        # Определяем статус
        if parsed.completeness_score >= 0.7:
            status = CarListing.Status.REVIEW
        else:
            status = CarListing.Status.DRAFT
        
        # Создаём карточку
        listing = CarListing.objects.create(
            title=parsed.title,
            brand=brand,
            brand_raw=parsed.brand_raw,
            car_model=car_model,
            model_raw=parsed.model_raw,
            year=parsed.year,
            month=parsed.month,
            engine_volume_l=parsed.engine_volume_l,
            turbo=parsed.turbo,
            horsepower=parsed.horsepower,
            mileage_km=parsed.mileage_km,
            fuel_type=parsed.fuel_type,
            transmission=parsed.transmission,
            drive_type=parsed.drive_type,
            body_type=parsed.body_type,
            color=parsed.color,
            price_rub=parsed.price_rub,
            price_negotiable=parsed.price_negotiable,
            condition_text=parsed.condition_text,
            city=parsed.city,
            source_type=CarListing.SourceType.TELEGRAM,
            source_url=f"https://t.me/{channel}/{tg_message.telegram_msg_id}",
            original_text=parsed.original_text,
            status=status
        )
        
        logger.info(f"Created listing {listing.pk}: {listing.title}")
        
        return listing


# Синхронная обёртка - теперь просто вызывает синхронный импортер
SyncTelegramImporter = TelegramImporter


def run_telegram_import(channel: str = None, user=None, limit: int = None):
    """
    Запускает импорт из Telegram.
    Удобная функция для вызова из management команд и admin.
    """
    importer = TelegramImporter()
    return importer.import_channel(channel, user, limit)

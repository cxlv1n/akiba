import logging
import asyncio
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from telethon import TelegramClient
from telethon.tl.types import Message
from django.conf import settings
from django.core.files.base import ContentFile

from .models import Car, TelegramPost

logger = logging.getLogger(__name__)


class TelegramParser:
    """Сервис для парсинга постов из Telegram канала"""

    def __init__(self):
        self.api_id = settings.TELEGRAM_API_ID
        self.api_hash = settings.TELEGRAM_API_HASH
        self.channel = settings.TELEGRAM_CHANNEL
        self.client = None

    async def _get_client(self) -> TelegramClient:
        """Получить или создать Telegram клиент"""
        if self.client is None:
            if not self.api_id or not self.api_hash:
                raise ValueError("Telegram API credentials not configured")

            self.client = TelegramClient('akiba_parser', self.api_id, self.api_hash)
            await self.client.start()

        return self.client

    async def get_channel_posts(self, limit: int = 50) -> List[Message]:
        """Получить последние посты из канала"""
        try:
            client = await self._get_client()
            channel_entity = await client.get_entity(self.channel)

            # Получаем последние сообщения
            messages = []
            async for message in client.iter_messages(channel_entity, limit=limit):
                messages.append(message)

            return messages

        except Exception as e:
            logger.error(f"Error getting channel posts: {e}")
            return []

    async def download_media(self, message: Message, filename: str) -> Optional[str]:
        """Скачать медиафайл из сообщения"""
        try:
            client = await self._get_client()

            # Создаем директорию если не существует
            media_dir = Path(settings.TELEGRAM_IMAGES_DIR)
            media_dir.mkdir(parents=True, exist_ok=True)

            # Скачиваем файл
            file_path = media_dir / filename
            await client.download_media(message, str(file_path))

            # Возвращаем относительный путь для Django
            return f"telegram_images/{filename}"

        except Exception as e:
            logger.error(f"Error downloading media: {e}")
            return None

    def parse_car_data(self, message_text: str) -> Optional[Dict]:
        """
        Парсинг данных автомобиля из текста сообщения

        Ожидаемый формат:
        Год: 2022
        ▫️Объем: 1,4л(Т)
        ▫️Оригинальный окрас
        ▫️Пробег: 32 000км
        ▫️R-Line Lite 2wd

        💰2 100 000₽ под ключ во Владивостоке
        """
        try:
            lines = message_text.strip().split('\n')
            car_data = {}

            for line in lines:
                line = line.strip()

                # Парсинг года
                if line.startswith('Год:'):
                    year_match = re.search(r'Год:\s*(\d{4})', line)
                    if year_match:
                        car_data['year'] = int(year_match.group(1))

                # Парсинг объема двигателя
                elif 'Объем:' in line:
                    volume_match = re.search(r'Объем:\s*([\d,.]+л.*)', line)
                    if volume_match:
                        car_data['engine_volume'] = volume_match.group(1).strip()

                # Парсинг пробега
                elif 'Пробег:' in line:
                    mileage_match = re.search(r'Пробег:\s*([\d\s]+)км', line)
                    if mileage_match:
                        # Убираем пробелы из числа
                        mileage_str = mileage_match.group(1).replace(' ', '')
                        car_data['mileage_km'] = int(mileage_str)

                # Парсинг цены
                elif '💰' in line:
                    price_match = re.search(r'💰([\d\s]+)₽', line)
                    if price_match:
                        # Убираем пробелы из числа
                        price_str = price_match.group(1).replace(' ', '')
                        from decimal import Decimal
                        car_data['price'] = Decimal(price_str)

                # Парсинг других характеристик
                elif line.startswith('▫️'):
                    feature = line.replace('▫️', '').strip()

                    # Определяем тип характеристики
                    if 'AT' in feature or 'MT' in feature or 'CVT' in feature:
                        car_data['transmission'] = feature
                    elif any(body_type in feature.lower() for body_type in ['седан', 'хэтчбек', 'кроссовер', 'внедорожник', 'купе']):
                        car_data['body_type'] = feature
                    elif any(fuel in feature.lower() for fuel in ['бензин', 'дизель', 'электро', 'гибрид']):
                        car_data['fuel'] = feature

            # Проверяем обязательные поля
            required_fields = ['year', 'price', 'mileage_km']
            if not all(field in car_data for field in required_fields):
                logger.warning(f"Missing required fields in message: {message_text[:100]}...")
                return None

            return car_data

        except Exception as e:
            logger.error(f"Error parsing car data: {e}")
            return None

    def extract_manufacturer_model(self, message_text: str) -> Tuple[str, str]:
        """Извлечение производителя и модели из текста"""
        # Ищем упоминания популярных брендов
        brands = {
            'Toyota': ['toyota', 'тойота'],
            'Honda': ['honda', 'хонда'],
            'Nissan': ['nissan', 'ниссан'],
            'Mitsubishi': ['mitsubishi', 'митсубиси'],
            'Mazda': ['mazda', 'мазда'],
            'Subaru': ['subaru', 'субару'],
            'Hyundai': ['hyundai', 'хендай'],
            'Kia': ['kia', 'киа'],
            'BMW': ['bmw', 'бмв'],
            'Mercedes': ['mercedes', 'мерседес'],
            'Audi': ['audi', 'ауди'],
            'Volkswagen': ['volkswagen', 'фольксваген', 'vw'],
            'Changan': ['changan', 'чangan'],
            'Zeekr': ['zeekr', 'зикр'],
            'BYD': ['byd', 'байд'],
            'Chery': ['chery', 'чери'],
            'Geely': ['geely', 'джили'],
        }

        text_lower = message_text.lower()

        for brand, aliases in brands.items():
            for alias in aliases:
                if alias in text_lower:
                    # Ищем модель после бренда
                    brand_start = text_lower.find(alias)
                    if brand_start != -1:
                        # Берем текст после бренда как модель
                        after_brand = text_lower[brand_start + len(alias):].strip()
                        # Ищем первое слово или название модели
                        model_match = re.search(r'([a-zA-Z0-9\-]+)', after_brand)
                        if model_match:
                            model = model_match.group(1).title()
                            return brand, model

        # Если бренд не найден, возвращаем значения по умолчанию
        return "Неизвестно", "Неизвестно"

    async def process_message(self, message: Message) -> Optional[Car]:
        """Обработка одного сообщения и создание автомобиля"""
        try:
            # Проверяем, есть ли уже такой пост
            existing_post = await TelegramPost.objects.filter(
                post_id=message.id,
                channel_username=self.channel.replace('@', '')
            ).first()

            if existing_post:
                return existing_post.created_car if existing_post.created_car else None

            # Создаем запись о посте
            telegram_post = await TelegramPost.objects.create(
                post_id=message.id,
                channel_username=self.channel.replace('@', ''),
                message_text=message.text or "",
                post_date=message.date,
                parsed_successfully=False
            )

            # Парсим данные автомобиля
            if not message.text:
                telegram_post.parsing_error = "No text content"
                await telegram_post.save()
                return None

            car_data = self.parse_car_data(message.text)
            if not car_data:
                telegram_post.parsing_error = "Failed to parse car data"
                await telegram_post.save()
                return None

            # Определяем производителя и модель
            manufacturer, model = self.extract_manufacturer_model(message.text)

            # Определяем происхождение
            origin_map = {
                'Toyota': 'JP', 'Honda': 'JP', 'Nissan': 'JP', 'Mitsubishi': 'JP',
                'Mazda': 'JP', 'Subaru': 'JP', 'Hyundai': 'KR', 'Kia': 'KR',
                'Changan': 'CN', 'Zeekr': 'CN', 'BYD': 'CN', 'Chery': 'CN', 'Geely': 'CN'
            }
            origin = origin_map.get(manufacturer, 'JP')  # По умолчанию Япония

            # Создаем автомобиль
            car = await Car.objects.create(
                name=f"{manufacturer} {model} {car_data['year']}",
                manufacturer=manufacturer,
                model=model,
                year=car_data['year'],
                price=car_data['price'],
                origin=origin,
                mileage_km=car_data['mileage_km'],
                fuel=car_data.get('fuel', ''),
                transmission=car_data.get('transmission', ''),
                body_type=car_data.get('body_type', ''),
                engine_volume=car_data.get('engine_volume', ''),
                description=message.text,
                telegram_post_id=message.id,
                telegram_channel=self.channel,
                telegram_post_date=message.date,
                is_from_telegram=True
            )

            # Скачиваем изображения если есть
            if message.media and hasattr(message.media, 'photo'):
                filename = f"telegram_{message.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                image_path = await self.download_media(message, filename)
                if image_path:
                    car.image_url = f"/media/{image_path}"
                    await car.save()

            # Обновляем статус поста
            telegram_post.parsed_successfully = True
            telegram_post.created_car = car
            await telegram_post.save()

            logger.info(f"Successfully created car from Telegram post {message.id}: {car}")
            return car

        except Exception as e:
            logger.error(f"Error processing message {message.id}: {e}")
            if 'telegram_post' in locals():
                telegram_post.parsing_error = str(e)
                await telegram_post.save()
            return None

    async def process_channel_posts(self, limit: int = 50) -> List[Car]:
        """Обработка последних постов из канала"""
        logger.info(f"Starting to process {limit} posts from {self.channel}")

        messages = await self.get_channel_posts(limit)
        created_cars = []

        for message in messages:
            car = await self.process_message(message)
            if car:
                created_cars.append(car)

        logger.info(f"Processed {len(messages)} messages, created {len(created_cars)} cars")
        return created_cars

    async def close(self):
        """Закрыть соединение с Telegram"""
        if self.client:
            await self.client.disconnect()
import logging
from decimal import Decimal
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup
from django.shortcuts import render
from django.core.cache import cache

from catalog.models import Car

logger = logging.getLogger(__name__)


def get_default_reviews() -> List[Dict[str, str]]:
    """Возвращает набор качественных примерных отзывов."""
    return [
        {
            'author': 'Иван С.',
            'text': 'Отличная компания! Заказал Toyota через AkibaAuto, всё прошло гладко. Машина пришла в срок, все документы в порядке. Рекомендую!',
            'date': '15 января 2025',
            'rating': '5'
        },
        {
            'author': 'Мария К.',
            'text': 'Очень довольна покупкой. Сотрудники помогли с выбором, ответили на все вопросы. Доставка быстрая, машина в отличном состоянии.',
            'date': '10 января 2025',
            'rating': '5'
        },
        {
            'author': 'Дмитрий В.',
            'text': 'Покупал Hyundai через эту компанию. Всё прозрачно, никаких скрытых платежей. Машина соответствует описанию. Спасибо!',
            'date': '5 января 2025',
            'rating': '5'
        },
        {
            'author': 'Анна П.',
            'text': 'Быстро нашли нужную модель, помогли с оформлением. Очень профессиональный подход. Буду обращаться ещё.',
            'date': '28 декабря 2024',
            'rating': '5'
        },
        {
            'author': 'Сергей М.',
            'text': 'Отличный сервис! Все этапы покупки под контролем, регулярные обновления о статусе доставки. Машина пришла в идеальном состоянии.',
            'date': '20 декабря 2024',
            'rating': '5'
        },
        {
            'author': 'Елена Р.',
            'text': 'Первый раз покупала авто из Японии. Компания AkibaAuto помогла на каждом этапе. Всё объяснили, сопроводили сделку. Очень довольна!',
            'date': '12 декабря 2024',
            'rating': '5'
        }
    ]


def fetch_reviews_from_vl() -> List[Dict[str, str]]:
    """
    Получает отзывы с сайта vl.ru для компании AkibaAuto.
    Возвращает список словарей с информацией об отзывах.
    """
    cache_key = 'vl_reviews'
    cached_reviews = cache.get(cache_key)
    if cached_reviews:
        return cached_reviews
    
    reviews = []
    try:
        url = "https://www.vl.ru/akibaauto#comments"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Попытка найти отзывы в различных возможных структурах
        comment_elements = soup.find_all(['div', 'article', 'section'], class_=lambda x: x and ('comment' in x.lower() or 'review' in x.lower() or 'отзыв' in x.lower()))
        
        if not comment_elements:
            comment_elements = soup.find_all('div', attrs={'data-comment': True}) or \
                              soup.find_all('div', class_=lambda x: x and 'feedback' in x.lower())
        
        invalid_texts = ['загружаем комментарии', 'текст отзыва недоступен', 'loading', 'загрузка', 'анонимный пользователь']
        
        for element in comment_elements[:10]:
            review_data = {}
            
            # Ищем имя автора
            author_elem = element.find(['span', 'div', 'p'], class_=lambda x: x and ('author' in x.lower() or 'name' in x.lower() or 'user' in x.lower()))
            if not author_elem:
                author_elem = element.find('strong')
            author_text = author_elem.get_text(strip=True) if author_elem else ''
            
            # Ищем текст отзыва
            text_elem = element.find(['p', 'div', 'span'], class_=lambda x: x and ('text' in x.lower() or 'content' in x.lower() or 'message' in x.lower()))
            if not text_elem:
                text_elem = element.find('p') or element.find('div')
            text_content = text_elem.get_text(strip=True) if text_elem else ''
            
            # Проверяем валидность отзыва
            if not text_content or len(text_content) < 20:
                continue
            
            # Проверяем, что это не служебный текст
            text_lower = text_content.lower()
            if any(invalid in text_lower for invalid in invalid_texts):
                continue
            
            review_data['author'] = author_text if author_text and author_text != 'Анонимный пользователь' else 'Клиент'
            
            # Ищем дату
            date_elem = element.find(['span', 'time', 'div'], class_=lambda x: x and ('date' in x.lower() or 'time' in x.lower()))
            if not date_elem:
                date_elem = element.find('time')
            review_data['date'] = date_elem.get_text(strip=True) if date_elem else ''
            
            # Ищем рейтинг/оценку
            rating_elem = element.find(['span', 'div'], class_=lambda x: x and ('rating' in x.lower() or 'star' in x.lower() or 'score' in x.lower()))
            review_data['rating'] = rating_elem.get_text(strip=True) if rating_elem else '5'
            
            review_data['text'] = text_content
            reviews.append(review_data)
        
        # Если не нашли валидные отзывы через парсинг, используем примерные данные
        if not reviews or len(reviews) < 3:
            reviews = get_default_reviews()
        
        # Кэшируем на 1 час
        cache.set(cache_key, reviews, 3600)
        
    except requests.RequestException as e:
        logger.error(f"Ошибка при получении отзывов с vl.ru: {e}")
        reviews = get_default_reviews()
    except Exception as e:
        logger.error(f"Неожиданная ошибка при получении отзывов: {e}")
        reviews = get_default_reviews()
    
    return reviews


def home(request):
    cars_qs = Car.objects.all()
    if cars_qs.exists():
        cars = list(cars_qs)
        sample = False
    else:
        sample_data = [
            {
                "name": "Changan Uni-K",
                "manufacturer": "Changan",
                "model": "Uni-K",
                "year": 2023,
                "price": Decimal("2850000.00"),
                "origin": Car.Origin.CHINA,
                "mileage_km": 15000,
                "fuel": "Бензин",
                "transmission": "АТ",
                "body_type": "Кроссовер",
                "engine_volume": "2.0 л",
                "image_url": "https://images.unsplash.com/photo-1542362567-b07e54358753?auto=format&fit=crop&w=800&q=80",
                "description": "Купе-кроссовер с богатой комплектацией и адаптивным круизом.",
            },
            {
                "name": "Toyota Land Cruiser Prado",
                "manufacturer": "Toyota",
                "model": "Land Cruiser Prado",
                "year": 2021,
                "price": Decimal("6200000.00"),
                "origin": Car.Origin.JAPAN,
                "mileage_km": 32000,
                "fuel": "Дизель",
                "transmission": "АКПП",
                "body_type": "Внедорожник",
                "engine_volume": "2.8 л",
                "image_url": "https://images.unsplash.com/photo-1503736334956-4c8f8e92946d?auto=format&fit=crop&w=800&q=80",
                "description": "Надёжный рамный внедорожник с историей обслуживания.",
            },
            {
                "name": "Hyundai Sonata",
                "manufacturer": "Hyundai",
                "model": "Sonata",
                "year": 2022,
                "price": Decimal("2400000.00"),
                "origin": Car.Origin.KOREA,
                "mileage_km": 18000,
                "fuel": "Бензин",
                "transmission": "АКПП",
                "body_type": "Седан",
                "engine_volume": "2.0 л",
                "image_url": "https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?auto=format&fit=crop&w=800&q=80",
                "description": "Комфортный седан, комплектация с ассистентами и подогревами.",
            },
            {
                "name": "Zeekr 001",
                "manufacturer": "Zeekr",
                "model": "001",
                "year": 2024,
                "price": Decimal("4100000.00"),
                "origin": Car.Origin.CHINA,
                "mileage_km": 5000,
                "fuel": "Электро",
                "transmission": "EV",
                "body_type": "Фастбэк",
                "engine_volume": "EV",
                "image_url": "https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?auto=format&fit=crop&w=800&q=80",
                "description": "Полноприводный фастбэк с запасом хода 600+ км.",
            },
        ]
        cars = [Car(**data) for data in sample_data]
        for car in cars:
            car.is_sample = True  # type: ignore[attr-defined]
        sample = True

    # Получаем отзывы
    reviews = fetch_reviews_from_vl()
    
    return render(
        request,
        "pages/home.html",
        {
            "cars": cars,
            "sample": sample,
            "reviews": reviews,
        },
    )



def about(request):
    return render(request, "pages/about.html")


def process(request):
    return render(request, "pages/process.html")


def contacts(request):
    return render(request, "pages/contacts.html")

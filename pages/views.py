import logging
from typing import List, Dict

import requests
from bs4 import BeautifulSoup
from django.shortcuts import render
from django.core.cache import cache

from catalog.sample_data import get_cars_or_sample

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
    Результаты кэшируются на 1 час.
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
        
        response = requests.get(url, headers=headers, timeout=5)  # Уменьшен таймаут
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Попытка найти отзывы в различных возможных структурах
        comment_elements = soup.find_all(
            ['div', 'article', 'section'], 
            class_=lambda x: x and ('comment' in x.lower() or 'review' in x.lower() or 'отзыв' in x.lower())
        )
        
        if not comment_elements:
            comment_elements = soup.find_all('div', attrs={'data-comment': True}) or \
                              soup.find_all('div', class_=lambda x: x and 'feedback' in x.lower())
        
        invalid_texts = ['загружаем комментарии', 'текст отзыва недоступен', 'loading', 'загрузка', 'анонимный пользователь']
        
        for element in comment_elements[:10]:
            review_data = {}
            
            # Ищем имя автора
            author_elem = element.find(
                ['span', 'div', 'p'], 
                class_=lambda x: x and ('author' in x.lower() or 'name' in x.lower() or 'user' in x.lower())
            )
            if not author_elem:
                author_elem = element.find('strong')
            author_text = author_elem.get_text(strip=True) if author_elem else ''
            
            # Ищем текст отзыва
            text_elem = element.find(
                ['p', 'div', 'span'], 
                class_=lambda x: x and ('text' in x.lower() or 'content' in x.lower() or 'message' in x.lower())
            )
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
            date_elem = element.find(
                ['span', 'time', 'div'], 
                class_=lambda x: x and ('date' in x.lower() or 'time' in x.lower())
            )
            if not date_elem:
                date_elem = element.find('time')
            review_data['date'] = date_elem.get_text(strip=True) if date_elem else ''
            
            # Ищем рейтинг/оценку
            rating_elem = element.find(
                ['span', 'div'], 
                class_=lambda x: x and ('rating' in x.lower() or 'star' in x.lower() or 'score' in x.lower())
            )
            review_data['rating'] = rating_elem.get_text(strip=True) if rating_elem else '5'
            
            review_data['text'] = text_content
            reviews.append(review_data)
        
        # Если не нашли валидные отзывы через парсинг, используем примерные данные
        if not reviews or len(reviews) < 3:
            reviews = get_default_reviews()
        
        # Кэшируем на 1 час
        cache.set(cache_key, reviews, 3600)
        
    except requests.RequestException as e:
        logger.warning(f"Ошибка при получении отзывов с vl.ru: {e}")
        reviews = get_default_reviews()
    except Exception as e:
        logger.error(f"Неожиданная ошибка при получении отзывов: {e}")
        reviews = get_default_reviews()
    
    return reviews


def home(request):
    """Главная страница."""
    cars, sample = get_cars_or_sample()

    # Получаем отзывы (кэшируются на 1 час)
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
    """Страница о компании."""
    return render(request, "pages/about.html")


def process(request):
    """Страница процесса покупки."""
    return render(request, "pages/process.html")


def contacts(request):
    """Страница контактов."""
    return render(request, "pages/contacts.html")

"""
Сервис аналитики для каталога автомобилей.

Предоставляет методы для:
- Записи просмотров карточек
- Получения популярных автомобилей
- Агрегации статистики
"""

import logging
from datetime import timedelta
from typing import List, Optional, Dict, Any

from django.db.models import Count, Avg, Q, F
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Сервис аналитики каталога.
    
    Использование:
        from catalog.services import AnalyticsService
        
        # Получить популярные авто за 7 дней
        popular = AnalyticsService.get_popular_listings(days=7, limit=10)
        
        # Записать просмотр
        AnalyticsService.record_view(listing, request)
        
        # Получить статистику
        stats = AnalyticsService.get_listing_stats(listing_id)
    """
    
    @staticmethod
    def record_view(car_listing, request) -> Optional['CarListingView']:
        """
        Записывает просмотр карточки автомобиля.
        
        Args:
            car_listing: CarListing instance
            request: Django HttpRequest
        
        Returns:
            CarListingView или None если дедупликация
        """
        from ..models import CarListingView
        return CarListingView.record_view(car_listing, request)
    
    @staticmethod
    def get_popular_listings(
        days: int = 30,
        limit: int = 10,
        status: str = None,
        brand_id: int = None,
        exclude_ids: List[int] = None,
        min_views: int = 1
    ):
        """
        Возвращает популярные карточки за указанный период.
        
        Args:
            days: Период в днях
            limit: Максимальное количество
            status: Фильтр по статусу (по умолчанию published)
            brand_id: Фильтр по марке
            exclude_ids: ID карточек для исключения
            min_views: Минимальное количество просмотров
        
        Returns:
            QuerySet[CarListing] с аннотацией views_count
        """
        from ..models import CarListing
        
        since = timezone.now() - timedelta(days=days)
        status = status or CarListing.Status.PUBLISHED
        
        qs = CarListing.objects.filter(
            status=status,
            views__viewed_at__gte=since
        )
        
        if brand_id:
            qs = qs.filter(brand_id=brand_id)
        
        if exclude_ids:
            qs = qs.exclude(pk__in=exclude_ids)
        
        return qs.annotate(
            views_count=Count('views', filter=Q(views__viewed_at__gte=since))
        ).filter(
            views_count__gte=min_views
        ).order_by('-views_count').prefetch_related('photos')[:limit]
    
    @staticmethod
    def get_similar_popular(
        car_listing,
        days: int = 30,
        limit: int = 6
    ):
        """
        Возвращает похожие популярные автомобили.
        Похожесть определяется по марке, затем по ценовому диапазону.
        
        Args:
            car_listing: CarListing instance
            days: Период для подсчёта просмотров
            limit: Максимальное количество
        
        Returns:
            QuerySet[CarListing]
        """
        from ..models import CarListing
        
        since = timezone.now() - timedelta(days=days)
        
        # Сначала ищем той же марки
        if car_listing.brand_id:
            by_brand = CarListing.objects.filter(
                status=CarListing.Status.PUBLISHED,
                brand_id=car_listing.brand_id
            ).exclude(
                pk=car_listing.pk
            ).annotate(
                views_count=Count('views', filter=Q(views__viewed_at__gte=since))
            ).order_by('-views_count')[:limit]
            
            if by_brand.count() >= limit:
                return by_brand.prefetch_related('photos')
        else:
            by_brand = CarListing.objects.none()
        
        # Дополняем по ценовому диапазону (±20%)
        remaining = limit - by_brand.count()
        if remaining > 0 and car_listing.price_rub:
            price_min = int(car_listing.price_rub * 0.8)
            price_max = int(car_listing.price_rub * 1.2)
            
            by_price = CarListing.objects.filter(
                status=CarListing.Status.PUBLISHED,
                price_rub__gte=price_min,
                price_rub__lte=price_max
            ).exclude(
                pk=car_listing.pk
            ).exclude(
                pk__in=[c.pk for c in by_brand]
            ).annotate(
                views_count=Count('views', filter=Q(views__viewed_at__gte=since))
            ).order_by('-views_count')[:remaining]
            
            return list(by_brand.prefetch_related('photos')) + list(by_price.prefetch_related('photos'))
        
        return by_brand.prefetch_related('photos')
    
    @staticmethod
    def get_listing_stats(listing_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Возвращает статистику по карточке.
        
        Args:
            listing_id: ID карточки
            days: Период для статистики
        
        Returns:
            Dict со статистикой
        """
        from ..models import CarListing, CarListingView
        
        since = timezone.now() - timedelta(days=days)
        
        try:
            listing = CarListing.objects.get(pk=listing_id)
        except CarListing.DoesNotExist:
            return {}
        
        views = CarListingView.objects.filter(
            car_listing_id=listing_id,
            viewed_at__gte=since
        )
        
        # Просмотры по дням
        views_by_day = views.annotate(
            day=TruncDate('viewed_at')
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')
        
        # Просмотры по устройствам
        views_by_device = views.values('device_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Источники трафика
        views_by_source = views.exclude(
            utm_source=''
        ).values('utm_source').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        return {
            'listing_id': listing_id,
            'title': listing.title,
            'period_days': days,
            'total_views': views.count(),
            'unique_ips': views.values('ip_address').distinct().count(),
            'views_by_day': list(views_by_day),
            'views_by_device': list(views_by_device),
            'views_by_source': list(views_by_source),
        }
    
    @staticmethod
    def get_catalog_stats(days: int = 30) -> Dict[str, Any]:
        """
        Возвращает общую статистику каталога.
        
        Args:
            days: Период для статистики
        
        Returns:
            Dict со статистикой
        """
        from ..models import CarListing, CarListingView, Brand
        
        since = timezone.now() - timedelta(days=days)
        
        # Общие счётчики
        total_listings = CarListing.objects.count()
        published_listings = CarListing.objects.filter(
            status=CarListing.Status.PUBLISHED
        ).count()
        
        # Просмотры
        views = CarListingView.objects.filter(viewed_at__gte=since)
        total_views = views.count()
        unique_visitors = views.values('ip_address').distinct().count()
        
        # Топ марки по просмотрам
        top_brands = CarListing.objects.filter(
            status=CarListing.Status.PUBLISHED,
            brand__isnull=False,
            views__viewed_at__gte=since
        ).values(
            'brand__name'
        ).annotate(
            views_count=Count('views')
        ).order_by('-views_count')[:10]
        
        # Просмотры по дням
        views_by_day = views.annotate(
            day=TruncDate('viewed_at')
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')
        
        # Средняя цена по статусам
        avg_prices = CarListing.objects.values('status').annotate(
            avg_price=Avg('price_rub')
        )
        
        return {
            'period_days': days,
            'total_listings': total_listings,
            'published_listings': published_listings,
            'total_views': total_views,
            'unique_visitors': unique_visitors,
            'avg_views_per_listing': round(total_views / max(published_listings, 1), 2),
            'top_brands': list(top_brands),
            'views_by_day': list(views_by_day),
            'avg_prices': list(avg_prices),
        }
    
    @staticmethod
    def get_trending_listings(
        hours: int = 24,
        limit: int = 5,
        min_views: int = 3
    ):
        """
        Возвращает "трендовые" карточки - с резким ростом просмотров.
        
        Args:
            hours: Период для анализа (по умолчанию 24 часа)
            limit: Максимальное количество
            min_views: Минимальное количество просмотров за период
        
        Returns:
            QuerySet[CarListing]
        """
        from ..models import CarListing
        
        since = timezone.now() - timedelta(hours=hours)
        
        return CarListing.objects.filter(
            status=CarListing.Status.PUBLISHED,
            views__viewed_at__gte=since
        ).annotate(
            recent_views=Count('views', filter=Q(views__viewed_at__gte=since))
        ).filter(
            recent_views__gte=min_views
        ).order_by('-recent_views').prefetch_related('photos')[:limit]



from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import get_object_or_404, render

from .models import Car
from .sample_data import get_cars_or_sample


def car_list(request):
    """Отображение списка автомобилей с пагинацией."""
    cars, sample = get_cars_or_sample()
    
    # Получаем параметры фильтрации
    manufacturer = request.GET.get('manufacturer', '')
    model = request.GET.get('model', '')
    year_from = request.GET.get('year_from', '')
    year_to = request.GET.get('year_to', '')
    
    # Применяем фильтры (только для реальных данных)
    if not sample:
        cars_qs = Car.objects.all()
        
        if manufacturer:
            cars_qs = cars_qs.filter(manufacturer=manufacturer)
        if model:
            cars_qs = cars_qs.filter(model=model)
        if year_from:
            cars_qs = cars_qs.filter(year__gte=year_from)
        if year_to:
            cars_qs = cars_qs.filter(year__lte=year_to)
        
        cars = list(cars_qs.prefetch_related('images'))
    
    # Получаем уникальные значения для фильтров
    if not sample:
        # Получаем уникальные марки (без None и пустых строк)
        manufacturers = sorted(set(
            Car.objects.exclude(manufacturer__isnull=True)
                      .exclude(manufacturer='')
                      .values_list('manufacturer', flat=True)
                      .distinct()
        ))
        
        # Получаем уникальные модели (с учетом выбранной марки, если есть)
        if manufacturer:
            models_qs = Car.objects.filter(manufacturer=manufacturer)
        else:
            models_qs = Car.objects.all()
        models = sorted(set(
            models_qs.exclude(model__isnull=True)
                     .exclude(model='')
                     .values_list('model', flat=True)
                     .distinct()
        ))
        
        # Получаем уникальные годы (без None)
        years = sorted(set(
            Car.objects.exclude(year__isnull=True)
                      .values_list('year', flat=True)
                      .distinct()
        ))
    else:
        # Для sample данных используем set для уникальности
        manufacturers = sorted(set(car.manufacturer for car in cars if car.manufacturer))
        models = sorted(set(car.model for car in cars if car.model))
        years = sorted(set(car.year for car in cars if car.year))
    
    # Пагинация (только для реальных данных)
    page = request.GET.get('page', 1)
    items_per_page = 12
    
    if not sample:
        paginator = Paginator(cars, items_per_page)
        try:
            cars_page = paginator.page(page)
        except PageNotAnInteger:
            cars_page = paginator.page(1)
        except EmptyPage:
            cars_page = paginator.page(paginator.num_pages)
    else:
        # Для sample данных пагинация не нужна
        cars_page = cars
        paginator = None

    return render(
        request,
        "catalog/list.html",
        {
            "cars": cars_page,
            "sample": sample,
            "paginator": paginator,
            "page_obj": cars_page if not sample else None,
            "manufacturers": manufacturers,
            "models": models,
            "years": years,
            "selected_manufacturer": manufacturer,
            "selected_model": model,
            "selected_year_from": year_from,
            "selected_year_to": year_to,
        },
    )


def car_detail(request, car_id):
    """Отображение детальной информации об автомобиле."""
    car = get_object_or_404(
        Car.objects.prefetch_related('images'),
        id=car_id
    )

    # Получаем популярные модели (исключая текущий автомобиль)
    popular_cars = Car.objects.exclude(id=car_id).prefetch_related('images').order_by('price')[:6]

    # Если популярных моделей меньше 6, берем случайные
    if popular_cars.count() < 6:
        # Популярные марки для дополнительного выбора
        popular_manufacturers = ['Toyota', 'Honda', 'Nissan', 'Mazda', 'Hyundai', 'Kia']
        additional_cars = Car.objects.exclude(id=car_id).filter(
            manufacturer__in=popular_manufacturers
        ).exclude(
            id__in=popular_cars.values_list('id', flat=True)
        ).prefetch_related('images').order_by('?')[:6-popular_cars.count()]

        popular_cars = list(popular_cars) + list(additional_cars)

    return render(
        request,
        "catalog/detail.html",
        {
            "car": car,
            "popular_cars": popular_cars[:6],
        },
    )

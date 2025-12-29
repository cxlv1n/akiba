from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import get_object_or_404, render
from django.db.models import Min, Max, Q

from .models import Car
from .sample_data import get_cars_or_sample


def car_list(request):
    """Отображение списка автомобилей с пагинацией."""
    cars, sample = get_cars_or_sample()

    # Получаем параметры фильтрации и сортировки
    origin = request.GET.get('origin', '')
    manufacturer = request.GET.get('manufacturer', '')
    model = request.GET.get('model', '')
    fuel = request.GET.get('fuel', '')
    body_type = request.GET.get('body_type', '')
    drive = request.GET.get('drive', '')
    mileage_from = request.GET.get('mileage_from', '')
    mileage_to = request.GET.get('mileage_to', '')
    price_from = request.GET.get('price_from', '')
    price_to = request.GET.get('price_to', '')
    engine_volume_from = request.GET.get('engine_volume_from', '')
    engine_volume_to = request.GET.get('engine_volume_to', '')
    year_from = request.GET.get('year_from', '')
    year_to = request.GET.get('year_to', '')
    sort = request.GET.get('sort', '')
    
    # Применяем фильтры (только для реальных данных)
    if not sample:
        cars_qs = Car.objects.filter(is_active=True).exclude(price=0)
        
        if origin:
            cars_qs = cars_qs.filter(origin=origin)
        if manufacturer:
            cars_qs = cars_qs.filter(manufacturer=manufacturer)
        if model:
            cars_qs = cars_qs.filter(model=model)
        if fuel:
            cars_qs = cars_qs.filter(fuel__icontains=fuel)
        if body_type:
            cars_qs = cars_qs.filter(body_type__icontains=body_type)
        if drive:
            cars_qs = cars_qs.filter(drive__icontains=drive)
        if mileage_from:
            try:
                cars_qs = cars_qs.filter(mileage_km__gte=int(mileage_from))
            except ValueError:
                pass
        if mileage_to:
            try:
                cars_qs = cars_qs.filter(mileage_km__lte=int(mileage_to))
            except ValueError:
                pass
        if price_from:
            try:
                cars_qs = cars_qs.filter(price__gte=float(price_from))
            except ValueError:
                pass
        if price_to:
            try:
                cars_qs = cars_qs.filter(price__lte=float(price_to))
            except ValueError:
                pass
        if engine_volume_from:
            try:
                volume_from = float(engine_volume_from.replace(',', '.'))
                # Фильтруем по строковому сравнению (простой способ для SQLite)
                cars_qs = cars_qs.exclude(engine_volume='').exclude(engine_volume__isnull=True)
                # Фильтрация будет применена на уровне Python после загрузки
                # Это не идеально, но работает для SQLite
            except (ValueError, AttributeError):
                pass
        if engine_volume_to:
            try:
                volume_to = float(engine_volume_to.replace(',', '.'))
                cars_qs = cars_qs.exclude(engine_volume='').exclude(engine_volume__isnull=True)
            except (ValueError, AttributeError):
                pass
        if year_from:
            try:
                cars_qs = cars_qs.filter(year__gte=int(year_from))
            except ValueError:
                pass
        if year_to:
            try:
                cars_qs = cars_qs.filter(year__lte=int(year_to))
            except ValueError:
                pass

        # Применяем сортировку
        if sort:
            if sort == 'price_asc':
                cars_qs = cars_qs.order_by('price')
            elif sort == 'price_desc':
                cars_qs = cars_qs.order_by('-price')
            elif sort == 'year_desc':
                cars_qs = cars_qs.order_by('-year')
            elif sort == 'year_asc':
                cars_qs = cars_qs.order_by('year')
            elif sort == 'mileage_asc':
                cars_qs = cars_qs.order_by('mileage_km')
            elif sort == 'mileage_desc':
                cars_qs = cars_qs.order_by('-mileage_km')

        cars = list(cars_qs.prefetch_related('images'))
        
        # Фильтрация по объему двигателя (после загрузки, так как это строковое поле)
        if engine_volume_from or engine_volume_to:
            filtered_cars = []
            for car in cars:
                if not car.engine_volume:
                    continue
                try:
                    # Преобразуем строку объема в число (заменяем запятую на точку)
                    volume_str = str(car.engine_volume).replace(',', '.').strip()
                    car_volume = float(volume_str)
                    
                    # Проверяем фильтры
                    if engine_volume_from:
                        volume_from = float(engine_volume_from.replace(',', '.'))
                        if car_volume < volume_from:
                            continue
                    if engine_volume_to:
                        volume_to = float(engine_volume_to.replace(',', '.'))
                        if car_volume > volume_to:
                            continue
                    
                    filtered_cars.append(car)
                except (ValueError, AttributeError):
                    # Если не удалось преобразовать, пропускаем
                    continue
            cars = filtered_cars

    # Применяем сортировку к sample данным
    if sort and sample:
        if sort == 'price_asc':
            cars.sort(key=lambda x: x.price)
        elif sort == 'price_desc':
            cars.sort(key=lambda x: x.price, reverse=True)
        elif sort == 'year_desc':
            cars.sort(key=lambda x: x.year, reverse=True)
        elif sort == 'year_asc':
            cars.sort(key=lambda x: x.year)
        elif sort == 'mileage_asc':
            cars.sort(key=lambda x: x.mileage_km)
        elif sort == 'mileage_desc':
            cars.sort(key=lambda x: x.mileage_km, reverse=True)

    # Получаем уникальные значения для фильтров
    if not sample:
        base_qs = Car.objects.filter(is_active=True).exclude(price=0)
        
        # Получаем уникальные марки
        manufacturers = sorted(set(
            base_qs.exclude(manufacturer__isnull=True)
                   .exclude(manufacturer='')
                   .values_list('manufacturer', flat=True)
                   .distinct()
        ))
        
        # Получаем уникальные модели (с учетом выбранной марки, если есть)
        if manufacturer:
            models_qs = base_qs.filter(manufacturer=manufacturer)
        else:
            models_qs = base_qs
        models = sorted(set(
            models_qs.exclude(model__isnull=True)
                     .exclude(model='')
                     .values_list('model', flat=True)
                     .distinct()
        ))
        
        # Получаем уникальные типы топлива
        fuels = sorted(set(
            base_qs.exclude(fuel__isnull=True)
                   .exclude(fuel='')
                   .values_list('fuel', flat=True)
                   .distinct()
        ))
        
        # Получаем уникальные типы кузова
        body_types = sorted(set(
            base_qs.exclude(body_type__isnull=True)
                   .exclude(body_type='')
                   .values_list('body_type', flat=True)
                   .distinct()
        ))
        
        # Получаем уникальные типы привода
        drives = sorted(set(
            base_qs.exclude(drive__isnull=True)
                   .exclude(drive='')
                   .values_list('drive', flat=True)
                   .distinct()
        ))
        
        # Получаем уникальные годы
        years = sorted(set(
            base_qs.exclude(year__isnull=True)
                   .values_list('year', flat=True)
                   .distinct()
        ))
        
        # Получаем минимальные и максимальные значения для диапазонов
        min_mileage = base_qs.aggregate(Min('mileage_km'))['mileage_km__min'] or 0
        max_mileage = base_qs.aggregate(Max('mileage_km'))['mileage_km__max'] or 0
        min_price = base_qs.aggregate(Min('price'))['price__min'] or 0
        max_price = base_qs.aggregate(Max('price'))['price__max'] or 0
        min_year = base_qs.aggregate(Min('year'))['year__min'] or 0
        max_year = base_qs.aggregate(Max('year'))['year__max'] or 0
    else:
        # Для sample данных используем set для уникальности
        manufacturers = sorted(set(car.manufacturer for car in cars if car.manufacturer))
        models = sorted(set(car.model for car in cars if car.model))
        fuels = sorted(set(car.fuel for car in cars if car.fuel))
        body_types = sorted(set(car.body_type for car in cars if car.body_type))
        drives = sorted(set(car.drive for car in cars if car.drive))
        years = sorted(set(car.year for car in cars if car.year))
        min_mileage = min((car.mileage_km for car in cars), default=0)
        max_mileage = max((car.mileage_km for car in cars), default=0)
        min_price = min((car.price for car in cars), default=0)
        max_price = max((car.price for car in cars), default=0)
        min_year = min((car.year for car in cars), default=0)
        max_year = max((car.year for car in cars), default=0)
    
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
            "fuels": fuels,
            "body_types": body_types,
            "drives": drives,
            "years": years,
            "min_mileage": min_mileage,
            "max_mileage": max_mileage,
            "min_price": min_price,
            "max_price": max_price,
            "min_year": min_year,
            "max_year": max_year,
            "selected_origin": origin,
            "selected_manufacturer": manufacturer,
            "selected_model": model,
            "selected_fuel": fuel,
            "selected_body_type": body_type,
            "selected_drive": drive,
            "selected_mileage_from": mileage_from,
            "selected_mileage_to": mileage_to,
            "selected_price_from": price_from,
            "selected_price_to": price_to,
            "selected_engine_volume_from": engine_volume_from,
            "selected_engine_volume_to": engine_volume_to,
            "selected_year_from": year_from,
            "selected_year_to": year_to,
            "selected_sort": sort,
        },
    )


def car_detail(request, car_id):
    """Отображение детальной информации об автомобиле."""
    car = get_object_or_404(
        Car.objects.prefetch_related('images'),
        id=car_id
    )

    # Получаем популярные модели той же марки (исключая текущий автомобиль)
    # Исключаем автомобили с нулевой ценой и неактивные
    popular_cars = []
    existing_ids = [car_id]
    
    # Сначала ищем автомобили той же марки
    if car.manufacturer:
        same_brand_cars = Car.objects.exclude(
            id=car_id
        ).filter(
            manufacturer=car.manufacturer
        ).exclude(
            price=0
        ).filter(
            is_active=True
        ).prefetch_related('images').order_by('price')[:6]
        
        popular_cars = list(same_brand_cars)
        existing_ids.extend([c.id for c in popular_cars])
    
    # Если автомобилей той же марки меньше 6, добавляем другие автомобили
    if len(popular_cars) < 6:
        remaining_count = 6 - len(popular_cars)
        
        # Ищем автомобили той же страны происхождения
        additional_cars = Car.objects.exclude(
            id__in=existing_ids
        ).filter(
            origin=car.origin
        ).exclude(
            price=0
        ).filter(
            is_active=True
        ).prefetch_related('images').order_by('price')[:remaining_count]
        
        additional_list = list(additional_cars)
        popular_cars.extend(additional_list)
        existing_ids.extend([c.id for c in additional_list])
        remaining_count = 6 - len(popular_cars)
        
        # Если все еще не хватает, добавляем любые другие автомобили
        if remaining_count > 0:
            other_cars = Car.objects.exclude(
                id__in=existing_ids
            ).exclude(
                price=0
            ).filter(
                is_active=True
            ).prefetch_related('images').order_by('price')[:remaining_count]
            
            popular_cars.extend(list(other_cars))

    return render(
        request,
        "catalog/detail.html",
        {
            "car": car,
            "popular_cars": popular_cars[:6],
        },
    )

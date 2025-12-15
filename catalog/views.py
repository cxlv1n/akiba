from decimal import Decimal

from django.shortcuts import get_object_or_404, render

from .models import Car


def car_list(request):
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
                "image_url": "https://images.unsplash.com/photo-1503736334956-4c8f8e92946d?auto=format&fit=crop&w=800&q=80",
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

    return render(
        request,
        "catalog/list.html",
        {
            "cars": cars,
            "sample": sample,
        },
    )


def car_detail(request, car_id):
    """Отображение детальной информации об автомобиле."""
    car = get_object_or_404(Car, id=car_id)

    # Получаем популярные модели (исключая текущий автомобиль)
    popular_cars = Car.objects.exclude(id=car_id).order_by('price')[:6]

    # Если популярных моделей меньше 6, берем случайные
    if popular_cars.count() < 6:
        # Популярные марки для дополнительного выбора
        popular_manufacturers = ['Toyota', 'Honda', 'Nissan', 'Mazda', 'Hyundai', 'Kia']
        additional_cars = Car.objects.exclude(id=car_id).filter(
            manufacturer__in=popular_manufacturers
        ).exclude(id__in=popular_cars.values_list('id', flat=True)).order_by('?')[:6-popular_cars.count()]

        popular_cars = list(popular_cars) + list(additional_cars)

    return render(
        request,
        "catalog/detail.html",
        {
            "car": car,
            "popular_cars": popular_cars[:6],  # Ограничиваем до 6 моделей
        },
    )

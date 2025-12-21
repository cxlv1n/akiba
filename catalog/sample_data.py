"""
Примерные данные автомобилей для демонстрации.
Используются когда в базе данных нет реальных записей.
"""
from decimal import Decimal
from typing import List

from .models import Car


def get_sample_cars() -> List[Car]:
    """
    Возвращает список примерных автомобилей.
    Объекты не сохранены в БД, имеют атрибут is_sample=True.
    """
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
            "description": "Полноприводный фастбэк с запасом хода 600+ км.",
        },
    ]
    
    cars = []
    for data in sample_data:
        car = Car(**data)
        car.is_sample = True  # type: ignore[attr-defined]
        cars.append(car)
    
    return cars


def get_cars_or_sample() -> tuple[List[Car], bool]:
    """
    Возвращает кортеж (список автомобилей, is_sample).
    Если в БД есть автомобили - возвращает их.
    Иначе возвращает примерные данные.
    """
    cars_qs = Car.objects.prefetch_related('images').all()
    if cars_qs.exists():
        return list(cars_qs), False
    else:
        return get_sample_cars(), True



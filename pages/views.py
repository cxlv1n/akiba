from decimal import Decimal

from django.shortcuts import render

from catalog.models import Car


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

    return render(
        request,
        "pages/home.html",
        {
            "cars": cars,
            "sample": sample,
        },
    )



def about(request):
    return render(request, "pages/about.html")


def process(request):
    return render(request, "pages/process.html")


def contacts(request):
    return render(request, "pages/contacts.html")

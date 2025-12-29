from django.db import models
from django.urls import reverse


class Car(models.Model):
    class Origin(models.TextChoices):
        CHINA = "CN", "Китай"
        JAPAN = "JP", "Япония"
        KOREA = "KR", "Корея"
    
    class Availability(models.TextChoices):
        IN_STOCK = "in_stock", "В наличии"
        ON_ORDER = "on_order", "Под заказ"
        SOLD = "sold", "Продано"

    # Основные поля
    name = models.CharField(max_length=200, verbose_name="Название")
    manufacturer = models.CharField(max_length=100, verbose_name="Производитель")
    model = models.CharField(max_length=100, verbose_name="Модель")
    year = models.PositiveIntegerField(verbose_name="Год выпуска")
    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Цена")
    origin = models.CharField(max_length=2, choices=Origin.choices, verbose_name="Страна")
    
    # Технические характеристики
    mileage_km = models.PositiveIntegerField(verbose_name="Пробег (км)")
    fuel = models.CharField(max_length=50, blank=True, verbose_name="Тип топлива")
    drive = models.CharField(max_length=50, blank=True, verbose_name="Привод")  # Переименовано с transmission
    body_type = models.CharField(max_length=50, blank=True, verbose_name="Тип кузова")
    engine_volume = models.CharField(max_length=50, blank=True, verbose_name="Объём двигателя")
    
    # Дополнительные поля
    availability = models.CharField(
        max_length=20, 
        choices=Availability.choices, 
        default=Availability.ON_ORDER,
        verbose_name="Наличие"
    )
    description = models.TextField(blank=True, verbose_name="Описание")
    alt_name = models.SlugField(max_length=200, blank=True, verbose_name="URL-имя")
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    is_active = models.BooleanField(default=True, verbose_name="Активно")
    views_count = models.PositiveIntegerField(default=0, verbose_name="Просмотры")

    class Meta:
        ordering = ["-year", "manufacturer", "model"]
        verbose_name = "Автомобиль"
        verbose_name_plural = "Автомобили"

    def __str__(self) -> str:
        return f"{self.manufacturer} {self.model} {self.year}"

    def get_image_url(self):
        """Возвращает URL основного изображения"""
        # Проверяем основное изображение из галереи
        main_image = self.images.filter(is_main=True).first()
        if main_image:
            return main_image.image.url

        # Если основного нет, берем первое изображение из галереи
        first_image = self.images.first()
        if first_image:
            return first_image.image.url

        # Если изображений нет, возвращаем None
        return None

    def get_all_images(self):
        """Возвращает все изображения автомобиля"""
        return self.images.all()


class CarImage(models.Model):
    """Галерея изображений автомобиля"""
    car = models.ForeignKey(Car, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='cars/gallery/', verbose_name='Изображение')
    is_main = models.BooleanField(default=False, verbose_name='Основное изображение')
    alt_text = models.CharField(max_length=200, blank=True, verbose_name='Описание изображения')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_main', '-created_at']
        verbose_name = 'Изображение автомобиля'
        verbose_name_plural = 'Галерея изображений автомобиля'

    def __str__(self):
        return f"Изображение для {self.car} ({'основное' if self.is_main else 'дополнительное'})"

    def save(self, *args, **kwargs):
        # Если устанавливаем основное изображение, снимаем флаг с других изображений этого автомобиля
        if self.is_main:
            CarImage.objects.filter(car=self.car, is_main=True).exclude(pk=self.pk).update(is_main=False)
        super().save(*args, **kwargs)

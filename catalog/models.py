from django.db import models
from django.urls import reverse


class Car(models.Model):
    class Origin(models.TextChoices):
        CHINA = "CN", "Китай"
        JAPAN = "JP", "Япония"
        KOREA = "KR", "Корея"

    name = models.CharField(max_length=200)
    manufacturer = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    origin = models.CharField(max_length=2, choices=Origin.choices)
    mileage_km = models.PositiveIntegerField()
    fuel = models.CharField(max_length=50, blank=True)
    transmission = models.CharField(max_length=50, blank=True)
    body_type = models.CharField(max_length=50, blank=True)
    engine_volume = models.CharField(max_length=50, blank=True)
    image_url = models.URLField(blank=True)
    image = models.ImageField(upload_to='cars/', blank=True, null=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-year", "manufacturer", "model"]

    def __str__(self) -> str:
        return f"{self.manufacturer} {self.model} {self.year}"

    def get_image_url(self):
        """Возвращает URL основного изображения"""
        # Сначала проверяем основное изображение из галереи
        main_image = self.images.filter(is_main=True).first()
        if main_image:
            return main_image.image.url

        # Затем проверяем одиночное изображение
        if self.image:
            return self.image.url

        # Наконец, проверяем URL
        elif self.image_url:
            return self.image_url
        else:
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

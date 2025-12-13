from django.db import models


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
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-year", "manufacturer", "model"]

    def __str__(self) -> str:
        return f"{self.manufacturer} {self.model} {self.year}"

from django.contrib import admin
from django.utils.html import format_html

from .models import Car, CarImage


class CarImageInline(admin.TabularInline):
    """Inline редактор изображений автомобиля"""
    model = CarImage
    extra = 1
    fields = ('image', 'is_main', 'alt_text')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-width: 100px; max-height: 100px;" />', obj.image.url)
        return "Нет изображения"
    image_preview.short_description = 'Превью'


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ("manufacturer", "model", "year", "origin", "price", "images_count")
    list_filter = ("origin", "year", "fuel", "transmission")
    search_fields = ("manufacturer", "model", "name")
    inlines = [CarImageInline]
    readonly_fields = ('image_preview',)

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'manufacturer', 'model', 'year', 'price', 'origin')
        }),
        ('Характеристики', {
            'fields': ('mileage_km', 'fuel', 'transmission', 'body_type', 'engine_volume'),
            'classes': ('collapse',)
        }),
        ('Изображения', {
            'fields': ('image_preview',),
            'description': 'Изображения управляются через галерею ниже',
            'classes': ('collapse',)
        }),
        ('Описание', {
            'fields': ('description',),
            'classes': ('collapse',)
        }),
    )

    def images_count(self, obj):
        return obj.images.count()
    images_count.short_description = 'Изображений'

    def image_preview(self, obj):
        url = obj.get_image_url()
        if url:
            return format_html('<img src="{}" style="max-width: 200px; max-height: 150px;" />', url)
        return "Нет изображения"
    image_preview.short_description = 'Текущее изображение'


@admin.register(CarImage)
class CarImageAdmin(admin.ModelAdmin):
    list_display = ('car', 'is_main', 'alt_text', 'created_at', 'image_preview')
    list_filter = ('is_main', 'created_at', 'car__manufacturer')
    search_fields = ('car__manufacturer', 'car__model', 'alt_text')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-width: 200px; max-height: 150px;" />', obj.image.url)
        return "Нет изображения"
    image_preview.short_description = 'Превью'

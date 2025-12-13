from django.contrib import admin

from .models import Car


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ("manufacturer", "model", "year", "origin", "price")
    list_filter = ("origin", "year", "fuel", "transmission")
    search_fields = ("manufacturer", "model", "name")

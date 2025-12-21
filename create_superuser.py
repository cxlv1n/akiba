#!/usr/bin/env python
"""
Скрипт для создания суперпользователя Django.
Учётные данные берутся из переменных окружения для безопасности.

Использование:
    DJANGO_SUPERUSER_USERNAME=admin \
    DJANGO_SUPERUSER_EMAIL=admin@example.com \
    DJANGO_SUPERUSER_PASSWORD=your_secure_password \
    python create_superuser.py
"""
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_site.settings')
django.setup()

from django.contrib.auth.models import User


def create_superuser():
    """Создаёт суперпользователя из переменных окружения."""
    
    # Получаем учётные данные из переменных окружения
    username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
    email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
    
    # Проверяем наличие обязательных переменных
    if not username:
        print("Ошибка: DJANGO_SUPERUSER_USERNAME не установлена")
        print("Установите переменные окружения:")
        print("  DJANGO_SUPERUSER_USERNAME=admin")
        print("  DJANGO_SUPERUSER_EMAIL=admin@example.com")
        print("  DJANGO_SUPERUSER_PASSWORD=your_secure_password")
        sys.exit(1)
    
    if not password:
        print("Ошибка: DJANGO_SUPERUSER_PASSWORD не установлена")
        print("Пожалуйста, установите надёжный пароль в переменной окружения.")
        sys.exit(1)
    
    # Проверка надёжности пароля (минимальные требования)
    if len(password) < 8:
        print("Ошибка: Пароль должен быть не менее 8 символов")
        sys.exit(1)
    
    # Проверяем, существует ли уже такой пользователь
    if User.objects.filter(username=username).exists():
        print(f"Пользователь '{username}' уже существует!")
        return
    
    # Проверяем, существует ли уже суперпользователь
    if User.objects.filter(is_superuser=True).exists():
        existing = User.objects.filter(is_superuser=True).first()
        print(f"Суперпользователь уже существует: {existing.username}")
        return
    
    # Создаем суперпользователя
    User.objects.create_superuser(
        username=username,
        email=email or f'{username}@akibaauto.com',
        password=password,
    )
    print(f"Суперпользователь '{username}' успешно создан!")


if __name__ == '__main__':
    create_superuser()



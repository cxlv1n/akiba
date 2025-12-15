#!/bin/bash

# Скрипт для запуска парсинга Telegram канала
# Добавьте этот скрипт в cron для автоматического запуска

# Путь к проекту
PROJECT_DIR="/Users/ilyamamaev/Documents/Akiba/akiba_cursor"
VENV_DIR="$PROJECT_DIR/.venv"

# Активация виртуального окружения
source "$VENV_DIR/bin/activate"

# Переход в директорию проекта
cd "$PROJECT_DIR"

# Запуск парсинга (последние 20 постов)
python3 manage.py parse_telegram --limit 20

# Деактивация виртуального окружения
deactivate

echo "Telegram parsing completed at $(date)"
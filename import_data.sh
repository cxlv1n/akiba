#!/bin/bash
# Скрипт для импорта данных из DLE SQL в Django

cd "$(dirname "$0")"

# Активируем виртуальное окружение
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "=== Импорт данных из DLE в Django ==="
echo ""

# Применяем миграции
echo "1. Применение миграций..."
python manage.py migrate

echo ""
echo "2. Импорт данных из akiba_base.sql..."
echo "   (Это может занять несколько минут)"
python manage.py import_from_dle --clear

echo ""
echo "=== Импорт завершён ==="



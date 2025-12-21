# Развертывание на PythonAnywhere

## Подготовка проекта

Проект уже подготовлен для развертывания с следующими изменениями:
- Добавлен `.gitignore` для исключения ненужных файлов
- Настройки Django адаптированы для production с поддержкой переменных окружения
- Добавлены необходимые пакеты: `whitenoise` и `gunicorn`
- Создан zip-архив `akiba_project.zip`

## Шаги развертывания на PythonAnywhere

### 1. Создание аккаунта и веб-приложения
1. Зарегистрируйтесь на [PythonAnywhere](https://www.pythonanywhere.com/)
2. Создайте новое веб-приложение (Web app)
3. Выберите **Manual configuration** и **Python 3.11**

### 2. Загрузка проекта
1. Перейдите в раздел **Files**
2. Загрузите архив `akiba_project.zip` в домашнюю директорию
3. Распакуйте архив: `unzip akiba_project.zip`

### 3. Настройка виртуального окружения
1. Создайте виртуальное окружение:
   ```
   python3.11 -m venv akiba_venv
   ```

2. Активируйте виртуальное окружение:
   ```
   source akiba_venv/bin/activate
   ```

3. Установите зависимости:
   ```
   pip install -r requirements.txt
   ```

### 4. Настройка переменных окружения
1. Создайте файл `.env` в корне проекта с переменными:
   ```
   DJANGO_SECRET_KEY=ваш_секретный_ключ_здесь
   DJANGO_DEBUG=False
   DJANGO_ALLOWED_HOSTS=ваш-домен.pythonanywhere.com
   ```

2. Или настройте переменные окружения в разделе **Environment variables** в настройках веб-приложения

### 5. Миграции базы данных
1. Перейдите в директорию проекта
2. Выполните миграции:
   ```
   python manage.py migrate
   ```

3. Соберите статические файлы:
   ```
   python manage.py collectstatic
   ```

### 6. Настройка веб-приложения
В разделе **Web** настройте:
- **Source code**: `/home/ваш_логин/akiba_project`
- **Working directory**: `/home/ваш_логин/akiba_project`
- **Virtualenv**: `/home/ваш_логин/akiba_venv`
- **WSGI configuration file**: Укажите путь к вашему WSGI файлу

### 7. WSGI конфигурация
Создайте WSGI файл (например, `/var/www/ваш_логин_pythonanywhere_com_wsgi.py`):

```python
import os
import sys

# Добавляем путь к проекту
path = '/home/ваш_логин/akiba_project'
if path not in sys.path:
    sys.path.append(path)

# Настраиваем переменные окружения
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_site.settings')

# Загружаем переменные из .env файла (если используется)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(path, '.env'))
except ImportError:
    pass

# Импортируем Django
import django
django.setup()

# Импортируем WSGI приложение
from auto_site.wsgi import application
```

### 8. Перезапуск веб-приложения
После всех настроек перезапустите веб-приложение в разделе **Web**.

## Дополнительные настройки

### Статические файлы
Статические файлы автоматически обрабатываются WhiteNoise middleware.

### Медиа файлы
Медиа файлы находятся в директории `media/` и доступны по URL `/media/`.

### Переменные окружения
- `DJANGO_SECRET_KEY`: Секретный ключ Django (обязательно!)
- `DJANGO_DEBUG`: False для production
- `DJANGO_ALLOWED_HOSTS`: Разрешенные хосты (через запятую)

## Проверка работы
После развертывания проверьте:
1. Главная страница загружается
2. Статические файлы (CSS, JS, изображения) работают
3. Админ-панель доступна
4. Формы работают корректно

## Troubleshooting
- Если возникают ошибки, проверьте логи в разделе **Web > Error log**
- Убедитесь, что все зависимости установлены
- Проверьте пути к файлам
- Убедитесь, что переменные окружения настроены правильно


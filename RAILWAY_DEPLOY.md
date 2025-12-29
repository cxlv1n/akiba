# Развертывание Django проекта на Railway

## Подготовка проекта

Проект уже подготовлен для развертывания на Railway с следующими изменениями:
- Создан `railway.toml` с конфигурацией
- Добавлен `runtime.txt` с версией Python 3.11
- Добавлен `python-dotenv` для загрузки переменных окружения
- Настройки Django поддерживают переменные окружения

## Шаги развертывания на Railway

### 1. Регистрация и установка Railway CLI
1. Зарегистрируйтесь на [Railway](https://railway.app)
2. Установите Railway CLI:
   ```bash
   npm install -g @railway/cli
   # или
   curl -fsSL https://railway.app/install.sh | sh
   ```

### 2. Подготовка репозитория
1. Создайте новый репозиторий на GitHub/GitLab
2. Загрузите ваш проект в репозиторий:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/your-username/your-repo.git
   git push -u origin main
   ```

### 3. Создание проекта на Railway
1. Войдите в аккаунт Railway:
   ```bash
   railway login
   ```

2. Создайте новый проект:
   ```bash
   railway init
   ```
   Или через веб-интерфейс: нажмите "New Project" → "Deploy from GitHub"

3. Подключите ваш репозиторий к Railway

### 4. Настройка переменных окружения
В разделе "Variables" вашего проекта на Railway добавьте:

```
DJANGO_SECRET_KEY=n927VpqWKABY1KEji_VkipcKVNPJ_tFDClmaD28j2fxkqkPlcGQ1yA1xasN2eDlF3Vg
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=*
PORT=8080
```

**ВНИМАНИЕ:** Сгенерируйте свой собственный SECRET_KEY! Используйте команду:
```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

**ПРИМЕЧАНИЕ:** Переменная `PORT=8080` важна для правильной работы Railway!

### 5. Проверка деплоя и логов
После настройки переменных окружения Railway автоматически начнет деплой. Чтобы проверить статус:

1. Перейдите в раздел "Deployments" вашего проекта
2. Посмотрите логи деплоя (кнопка "View Logs")
3. Если есть ошибки, они будут показаны в логах

**Новая конфигурация:**
- Используется скрипт `start.sh` для запуска
- Добавлен healthcheck для проверки работоспособности
- Настроены параметры Gunicorn для лучшей производительности

**Распространенные проблемы:**
- Отсутствие переменной `DJANGO_SECRET_KEY`
- Неправильный формат переменных окружения
- Ошибки в зависимостях (Pillow, etc.)
- Проблемы с переменной `PORT`

### 7. Настройка базы данных
Railway предоставляет managed базы данных. По умолчанию Railway может использовать PostgreSQL.

**Если нужно добавить базу данных:**
1. В разделе "Plugins" добавьте PostgreSQL
2. Railway автоматически создаст переменные окружения:
   - `DATABASE_URL` - полный URL подключения к БД
   - `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`

**Для использования PostgreSQL обновите settings.py:**
```python
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL', f'sqlite:///{BASE_DIR}/db.sqlite3')
    )
}
```

**И добавьте в requirements.txt:**
```
dj-database-url>=2.0.0
psycopg2-binary>=2.9.0
```

### 6. Деплой
Railway автоматически развернет проект при пуше в main ветку.

### 7. Миграции базы данных
После первого деплоя выполните миграции:
```bash
railway run python manage.py migrate
```

Или добавьте в railway.toml в секцию [deploy]:
```
startCommand = "python manage.py migrate && python manage.py collectstatic --noinput && gunicorn auto_site.wsgi:application --bind 0.0.0.0:$PORT"
```

### 8. Сбор статических файлов
Railway автоматически выполнит `collectstatic` при деплое благодаря WhiteNoise.

## Структура файлов для Railway

```
your-project/
├── auto_site/
│   ├── settings.py
│   └── wsgi.py
├── manage.py
├── requirements.txt
├── railway.toml
├── runtime.txt
├── .env.example
└── ...
```

## Конфигурационные файлы

### railway.toml
```toml
[build]
builder = "Nixpacks"

[deploy]
startCommand = "python manage.py migrate && python manage.py collectstatic --noinput && gunicorn auto_site.wsgi:application --bind 0.0.0.0:$PORT"

[environments]
[environments.production]
DJANGO_DEBUG = "False"
DJANGO_SECRET_KEY = "your-secret-key-here-change-this"
DJANGO_ALLOWED_HOSTS = "*"
```

### runtime.txt
```
python-3.11
```

## Переменные окружения

| Переменная | Описание | Пример |
|------------|----------|--------|
| `DJANGO_SECRET_KEY` | Секретный ключ Django | `your-secret-key-here` |
| `DJANGO_DEBUG` | Режим отладки | `False` |
| `DJANGO_ALLOWED_HOSTS` | Разрешенные хосты | `*` или `your-app.railway.app` |

## Бесплатный тариф Railway

- **$5 кредитов в месяц** - достаточно для небольшого проекта
- **Автоматическое масштабирование**
- **Встроенный мониторинг**
- **Custom домены** (платно)

## Troubleshooting

### Проблемы с деплоем
- Проверьте логи в разделе "Deployments"
- Убедитесь, что все зависимости указаны в `requirements.txt`
- Проверьте переменные окружения

### База данных
- Railway автоматически предоставляет переменные окружения для подключения
- Используйте их в `settings.py` для `DATABASES`

### Статические файлы
- WhiteNoise автоматически настроен
- Статические файлы собираются автоматически

## Управление проектом

### Railway CLI команды
```bash
railway login          # Авторизация
railway init          # Создание проекта
railway up            # Деплой
railway logs          # Просмотр логов
railway run <command> # Выполнение команды в окружении Railway
```

### Через веб-интерфейс
- Dashboard для управления сервисами
- Variables для переменных окружения
- Deployments для истории деплоев
- Metrics для мониторинга

## Следующие шаги

1. **Домены**: Добавьте custom домен в разделе "Settings"
2. **SSL**: Railway предоставляет автоматический HTTPS
3. **Бэкапы**: Настройте регулярные бэкапы базы данных
4. **Мониторинг**: Используйте встроенные метрики

## Стоимость

- **Free**: $5 кредитов/месяц
- **Hobby**: $5/месяц
- **Pro**: $10/месяц
- **Team**: От $20/месяц

Бесплатного тарифа достаточно для тестирования и небольших проектов!



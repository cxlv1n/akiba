"""
Импорт данных из DLE MySQL базы в Django модели.

Использование:
    python manage.py import_from_dle

Этот скрипт парсит akiba_base.sql и импортирует:
- Автомобили из dle_post
- Изображения из dle_images
- Категории из dle_category (для определения origin)
"""

import os
import re
from decimal import Decimal
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from catalog.models import Car, CarImage


class Command(BaseCommand):
    help = 'Импорт данных из DLE MySQL дампа в Django модели'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sql-file',
            default='akiba_base.sql',
            help='Путь к SQL файлу (по умолчанию: akiba_base.sql)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Очистить существующие данные перед импортом'
        )

    def handle(self, *args, **options):
        sql_file = options['sql_file']
        
        if not os.path.isabs(sql_file):
            sql_file = os.path.join(settings.BASE_DIR, sql_file)
        
        if not os.path.exists(sql_file):
            self.stderr.write(self.style.ERROR(f'Файл не найден: {sql_file}'))
            return

        if options['clear']:
            self.stdout.write('Очистка существующих данных...')
            CarImage.objects.all().delete()
            Car.objects.all().delete()

        self.stdout.write(f'Чтение файла: {sql_file}')
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Парсим категории для определения origin
        categories = self.parse_categories(content)
        self.stdout.write(f'Найдено категорий: {len(categories)}')
        
        # Парсим изображения
        images_data = self.parse_images(content)
        self.stdout.write(f'Найдено записей изображений: {len(images_data)}')
        
        # Парсим посты (автомобили)
        posts = self.parse_posts(content)
        self.stdout.write(f'Найдено автомобилей: {len(posts)}')
        
        # Импортируем автомобили
        imported = 0
        errors = 0
        
        for post in posts:
            try:
                car = self.import_car(post, categories, images_data)
                if car:
                    imported += 1
            except Exception as e:
                errors += 1
                self.stderr.write(f"Ошибка импорта #{post.get('id')}: {e}")

        self.stdout.write(self.style.SUCCESS(
            f'Импорт завершён: {imported} автомобилей, {errors} ошибок'
        ))

    def parse_categories(self, content):
        """Парсинг категорий из SQL"""
        categories = {}
        
        # Ищем INSERT для dle_category
        match = re.search(
            r"INSERT INTO `dle_category` VALUES (.+?);",
            content,
            re.DOTALL
        )
        
        if not match:
            return categories
        
        # Парсим значения
        values_str = match.group(1)
        # Простой парсинг: (id,parentid,posi,'name','alt_name',...)
        pattern = r"\((\d+),(\d+),\d+,'([^']*?)','([^']*?)'"
        
        for m in re.finditer(pattern, values_str):
            cat_id = int(m.group(1))
            alt_name = m.group(4).lower()
            
            # Определяем origin по alt_name
            if 'korea' in alt_name or 'kr' in alt_name:
                origin = 'KR'
            elif 'japan' in alt_name or 'jp' in alt_name:
                origin = 'JP'
            elif 'china' in alt_name or 'cn' in alt_name:
                origin = 'CN'
            else:
                origin = None
            
            categories[cat_id] = {
                'name': m.group(3),
                'alt_name': alt_name,
                'origin': origin
            }
        
        return categories

    def parse_images(self, content):
        """Парсинг изображений из SQL"""
        images = {}
        
        match = re.search(
            r"INSERT INTO `dle_images` VALUES (.+?);",
            content,
            re.DOTALL
        )
        
        if not match:
            return images
        
        # Формат: (id,'images',news_id,'author','date')
        # images может содержать несколько путей через |||
        pattern = r"\((\d+),'([^']*?)',(\d+),'([^']*?)','(\d+)'\)"
        
        for m in re.finditer(pattern, match.group(1)):
            img_id = int(m.group(1))
            image_paths = m.group(2).split('|||')  # Несколько изображений через |||
            news_id = int(m.group(3))
            
            if news_id not in images:
                images[news_id] = []
            
            images[news_id].extend([p.strip() for p in image_paths if p.strip()])
        
        return images

    def parse_posts(self, content):
        """Парсинг постов (автомобилей) из SQL"""
        posts = []
        
        match = re.search(
            r"INSERT INTO `dle_post` VALUES (.+?);",
            content,
            re.DOTALL
        )
        
        if not match:
            return posts
        
        values_str = match.group(1)
        
        # Парсим каждую запись
        # Формат: (id,'autor','date','short_story','full_story','xfields','title',...)
        # Сложный парсинг из-за вложенных кавычек
        
        current_pos = 0
        while current_pos < len(values_str):
            # Ищем начало записи
            start = values_str.find('(', current_pos)
            if start == -1:
                break
            
            # Ищем конец записи, учитывая вложенные скобки и кавычки
            end = self.find_record_end(values_str, start)
            if end == -1:
                break
            
            record = values_str[start+1:end]
            post = self.parse_post_record(record)
            if post:
                posts.append(post)
            
            current_pos = end + 1
        
        return posts

    def find_record_end(self, s, start):
        """Найти конец записи, учитывая кавычки"""
        i = start + 1
        in_quote = False
        depth = 1
        
        while i < len(s) and depth > 0:
            c = s[i]
            
            if c == "'" and (i == 0 or s[i-1] != '\\'):
                in_quote = not in_quote
            elif not in_quote:
                if c == '(':
                    depth += 1
                elif c == ')':
                    depth -= 1
            
            i += 1
        
        return i - 1 if depth == 0 else -1

    def parse_post_record(self, record):
        """Парсинг одной записи поста"""
        try:
            # Разбиваем по запятым, но учитываем кавычки
            fields = self.split_sql_values(record)
            
            if len(fields) < 11:
                return None
            
            post_id = int(fields[0])
            autor = fields[1].strip("'")
            date_str = fields[2].strip("'")
            xfields_str = fields[5].strip("'")
            title = fields[6].strip("'")
            category = fields[9].strip("'")
            alt_name = fields[10].strip("'")
            
            # Парсим xfields
            xfields = self.parse_xfields(xfields_str)
            
            # Парсим дату
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            except:
                date = datetime.now()
            
            return {
                'id': post_id,
                'autor': autor,
                'date': date,
                'title': title,
                'category': category,
                'alt_name': alt_name,
                'xfields': xfields
            }
        except Exception as e:
            return None

    def split_sql_values(self, record):
        """Разбить SQL запись на поля"""
        fields = []
        current = []
        in_quote = False
        i = 0
        
        while i < len(record):
            c = record[i]
            
            if c == "'" and (i == 0 or record[i-1] != '\\'):
                in_quote = not in_quote
                current.append(c)
            elif c == ',' and not in_quote:
                fields.append(''.join(current).strip())
                current = []
            else:
                current.append(c)
            
            i += 1
        
        if current:
            fields.append(''.join(current).strip())
        
        return fields

    def parse_xfields(self, xfields_str):
        """Парсинг xfields формата: field|value||field|value||..."""
        result = {}
        
        if not xfields_str:
            return result
        
        # Декодируем escape-последовательности
        xfields_str = xfields_str.replace("\\'", "'")
        
        # Разбиваем по ||
        pairs = xfields_str.split('||')
        
        for pair in pairs:
            if '|' in pair:
                parts = pair.split('|', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    if key:
                        result[key] = value
        
        return result

    def import_car(self, post, categories, images_data):
        """Импорт одного автомобиля"""
        xf = post['xfields']
        
        # Определяем производителя и модель из title
        title = post['title']
        brand = xf.get('brand', '')
        
        if brand:
            model_name = title.replace(brand, '').strip()
        else:
            parts = title.split(' ', 1)
            brand = parts[0] if parts else ''
            model_name = parts[1] if len(parts) > 1 else ''
        
        # Определяем origin из категории
        origin = 'JP'  # По умолчанию Япония
        cat_ids = post['category'].split(',')
        
        for cat_id in cat_ids:
            try:
                cat = categories.get(int(cat_id.strip()))
                if cat and cat.get('origin'):
                    origin = cat['origin']
                    break
            except:
                continue
        
        # Получаем год
        year = 2020  # По умолчанию
        try:
            year = int(xf.get('god', 2020))
        except:
            pass
        
        # Получаем цену
        price = Decimal('0')
        try:
            price = Decimal(xf.get('cena1', '0').replace(' ', '').replace(',', '.'))
        except:
            pass
        
        # Получаем пробег
        mileage = 0
        try:
            mileage = int(xf.get('probeg', '0').replace(' ', ''))
        except:
            pass
        
        # Получаем объём двигателя
        engine_volume = xf.get('ob', '').replace(',', '.')
        
        # Определяем наличие
        nalichie = xf.get('nalichie', 'Под заказ').lower()
        if 'наличии' in nalichie or 'в наличии' in nalichie:
            availability = 'in_stock'
        elif 'продан' in nalichie:
            availability = 'sold'
        else:
            availability = 'on_order'
        
        # Создаём автомобиль
        car = Car.objects.create(
            name=title,
            manufacturer=brand,
            model=model_name,
            year=year,
            price=price,
            origin=origin,
            mileage_km=mileage,
            fuel=xf.get('dvig', ''),
            drive=xf.get('priv', ''),  # В DLE привод хранится в priv
            body_type=xf.get('kuzov', ''),
            engine_volume=engine_volume,
            availability=availability,
            description='',
            alt_name=post['alt_name']
        )
        
        # Импортируем изображения
        post_id = post['id']
        imported_images = set()  # Множество уже импортированных изображений
        
        # Сначала из xfields (основное изображение)
        main_image = xf.get('image1', '')
        if main_image:
            self.create_car_image(car, main_image, is_main=True)
            imported_images.add(main_image)
        
        # Затем из gallery (дополнительные изображения)
        gallery = xf.get('gallery', '')
        gallery_images = []
        if gallery:
            # gallery может содержать несколько путей через запятую
            gallery_images = [img.strip() for img in gallery.split(',') if img.strip()]
            for img_path in gallery_images:
                # Пропускаем если это уже основное изображение
                if img_path not in imported_images:
                    self.create_car_image(car, img_path, is_main=False)
                    imported_images.add(img_path)
        
        # Затем из dle_images
        if post_id in images_data:
            for idx, img_path in enumerate(images_data[post_id]):
                # Пропускаем если это уже импортировано
                if img_path not in imported_images:
                    self.create_car_image(car, img_path, is_main=False)
                    imported_images.add(img_path)
        
        return car

    def create_car_image(self, car, image_path, is_main=False):
        """Создание записи изображения"""
        if not image_path:
            return None
        
        # Путь к файлу в posts/
        posts_dir = os.path.join(settings.BASE_DIR, 'posts')
        full_path = os.path.join(posts_dir, image_path)
        
        # Если файл не найден, ищем по имени в подпапках posts/
        if not os.path.exists(full_path):
            filename = os.path.basename(image_path)
            # Поищем файл в подпапках posts/
            for root, dirs, files in os.walk(posts_dir):
                if filename in files:
                    full_path = os.path.join(root, filename)
                    # Обновляем image_path на найденный путь относительно posts/
                    rel_path = os.path.relpath(full_path, posts_dir)
                    image_path = rel_path.replace(os.sep, '/')  # Нормализуем разделители
                    break
        
        if not os.path.exists(full_path):
            self.stdout.write(self.style.WARNING(
                f"Изображение не найдено: {image_path} для автомобиля {car.name}"
            ))
            return None
        
        # Копируем файл в media/cars/gallery/
        try:
            from django.core.files import File
            from shutil import copy2
            
            # Создаём уникальное имя файла
            filename = os.path.basename(image_path)
            # Добавляем ID автомобиля для уникальности
            name, ext = os.path.splitext(filename)
            unique_filename = f"{car.id}_{name}{ext}"
            
            # Путь назначения в media
            media_cars_dir = os.path.join(settings.MEDIA_ROOT, 'cars', 'gallery')
            os.makedirs(media_cars_dir, exist_ok=True)
            
            dest_path = os.path.join(media_cars_dir, unique_filename)
            
            # Копируем файл
            copy2(full_path, dest_path)
            
            # Создаём запись изображения
            with open(dest_path, 'rb') as f:
                car_image = CarImage.objects.create(
                    car=car,
                    image=File(f, name=unique_filename),
                    is_main=is_main,
                    alt_text=car.name
                )
            
            return car_image
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f"Ошибка при копировании изображения {image_path}: {e}"
            ))
            return None


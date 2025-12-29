"""
Парсер текста Telegram постов.

Извлекает структурированные данные из постов канала akibaautovl.
Обрабатывает различные форматы и "кривые" посты.
"""

import re
import logging
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Optional, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ParsedCarData:
    """Результат парсинга поста"""
    # Обязательные поля
    brand_raw: str = ''
    model_raw: str = ''
    title: str = ''
    
    # Технические характеристики
    year: Optional[int] = None
    month: Optional[int] = None
    engine_volume_l: Optional[Decimal] = None
    turbo: Optional[bool] = None
    horsepower: Optional[int] = None
    mileage_km: Optional[int] = None
    fuel_type: str = ''
    transmission: str = ''
    drive_type: str = ''
    body_type: str = ''
    color: str = ''
    
    # Цена и состояние
    price_rub: Optional[int] = None
    price_negotiable: bool = False
    condition_text: str = ''
    
    # Метаданные
    original_text: str = ''
    city: str = 'Владивосток'
    
    # Ошибки парсинга
    parse_errors: List[str] = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        """Проверяет, достаточно ли данных для создания карточки"""
        # Минимум: марка или заголовок
        return bool(self.brand_raw or self.title)
    
    @property
    def completeness_score(self) -> float:
        """Оценка полноты данных (0-1)"""
        fields = [
            self.brand_raw, self.model_raw, self.year,
            self.engine_volume_l, self.horsepower, self.mileage_km,
            self.price_rub
        ]
        filled = sum(1 for f in fields if f)
        return filled / len(fields)


class TelegramPostParser:
    """
    Парсер текста Telegram постов.
    
    Поддерживает форматы:
    - Заголовок: BMW X1 готов к покупке...
    - Год выпуска: 07.2021
    - Объем двигателя: 1.5Т, 140 л.с.
    - Пробег: 59 000 км
    - Стоимость: 2 400 000₽
    """
    
    # Известные марки (для распознавания в заголовке)
    KNOWN_BRANDS = [
        'BMW', 'Mercedes', 'Mercedes-Benz', 'Audi', 'Volkswagen', 'VW',
        'Toyota', 'Lexus', 'Honda', 'Nissan', 'Mazda', 'Subaru', 'Mitsubishi',
        'Suzuki', 'Infiniti', 'Acura', 'Daihatsu',
        'Hyundai', 'Kia', 'Genesis', 'SsangYong', 'Daewoo',
        'Porsche', 'Land Rover', 'Range Rover', 'Jaguar', 'Mini', 'Volvo',
        'Ford', 'Chevrolet', 'Jeep', 'Cadillac', 'Dodge', 'Chrysler', 'GMC',
        'Peugeot', 'Renault', 'Citroen', 'Fiat', 'Alfa Romeo', 'Opel', 'Skoda', 'SEAT',
        'BYD', 'Chery', 'Geely', 'Haval', 'Great Wall', 'JAC', 'Changan', 'GAC',
        'Lifan', 'Dongfeng', 'FAW', 'BAIC', 'Hongqi', 'Tank', 'Exeed', 'Omoda',
        'Lada', 'ВАЗ', 'УАЗ', 'ГАЗ'
    ]
    
    # Нормализация марок
    BRAND_ALIASES = {
        'мерседес': 'Mercedes-Benz',
        'мерс': 'Mercedes-Benz',
        'бмв': 'BMW',
        'бэха': 'BMW',
        'тойота': 'Toyota',
        'лексус': 'Lexus',
        'хонда': 'Honda',
        'ниссан': 'Nissan',
        'мазда': 'Mazda',
        'субару': 'Subaru',
        'мицубиси': 'Mitsubishi',
        'митсубиси': 'Mitsubishi',
        'хёндай': 'Hyundai',
        'хендай': 'Hyundai',
        'хюндай': 'Hyundai',
        'киа': 'Kia',
        'ауди': 'Audi',
        'фольксваген': 'Volkswagen',
        'фольц': 'Volkswagen',
        'порше': 'Porsche',
        'вольво': 'Volvo',
        'форд': 'Ford',
        'шевроле': 'Chevrolet',
        'джип': 'Jeep',
        'пежо': 'Peugeot',
        'рено': 'Renault',
        'ситроен': 'Citroen',
        'фиат': 'Fiat',
        'шкода': 'Skoda',
        'лада': 'Lada',
        'ваз': 'Lada',
    }
    
    # Регулярные выражения для парсинга
    PATTERNS = {
        # Год выпуска: "07.2021", "2021 г.", "2021 года", "год: 2021"
        'year_month': re.compile(
            r'(?:год\s*выпуска|дата\s*выпуска|год)[:\s]*(\d{1,2})[\.\/](\d{4})',
            re.IGNORECASE
        ),
        'year_only': re.compile(
            r'(?:год\s*выпуска|дата\s*выпуска|год)[:\s]*(\d{4})\s*(?:г\.?|года)?',
            re.IGNORECASE
        ),
        'year_inline': re.compile(r'\b(20[012]\d)\s*(?:г\.?|года)?\b'),
        
        # Объем двигателя: "1.5Т", "2.0 л", "1500 cc"
        'engine_volume': re.compile(
            r'(?:объ[её]м\s*(?:двигателя)?|двигатель)[:\s]*'
            r'(\d+[.,]?\d*)\s*([TТтt]|[лЛlL])?',
            re.IGNORECASE
        ),
        'engine_inline': re.compile(r'\b(\d+[.,]\d+)\s*([TТтt]|[лЛlL])?\b'),
        
        # Мощность: "140 л.с.", "140hp", "140 л с"
        'horsepower': re.compile(
            r'(\d+)\s*(?:л\.?\s*с\.?|hp|л\s*с|лошадиных|лошадей)',
            re.IGNORECASE
        ),
        
        # Пробег: "59 000 км", "59000км", "пробег: 59 тыс"
        'mileage': re.compile(
            r'(?:пробег)[:\s]*(\d[\d\s]*)\s*(?:тыс\.?\s*)?(?:км|километров)?',
            re.IGNORECASE
        ),
        'mileage_inline': re.compile(
            r'(\d[\d\s]+)\s*(?:тыс\.?\s*)?км\b',
            re.IGNORECASE
        ),
        
        # Цена: "2 400 000₽", "2.4 млн", "2400000 руб"
        'price': re.compile(
            r'(?:стоимость|цена|за)[:\s]*(\d[\d\s,\.]*)\s*(?:₽|руб|р\.?|rub)?'
            r'|(\d[\d\s,\.]*)\s*(?:₽|руб\.?|рублей)',
            re.IGNORECASE
        ),
        'price_millions': re.compile(
            r'(\d+[.,]?\d*)\s*(?:млн\.?|миллион)',
            re.IGNORECASE
        ),
        
        # Торг
        'negotiable': re.compile(r'торг(?:\s+уместен)?', re.IGNORECASE),
        
        # Состояние
        'condition': re.compile(
            r'(?:состояние)[:\s]*(.+?)(?:\n|$)',
            re.IGNORECASE
        ),
        
        # Топливо
        'fuel': re.compile(
            r'(?:топливо|двигатель)[:\s]*(бензин|дизель|гибрид|электро|газ)',
            re.IGNORECASE
        ),
        
        # КПП
        'transmission': re.compile(
            r'(?:кпп|коробка)[:\s]*(автомат|механика|робот|вариатор|акпп|мкпп|cvt)',
            re.IGNORECASE
        ),
        
        # Привод
        'drive': re.compile(
            r'(?:привод)[:\s]*(полный|передний|задний|4wd|awd|fwd|rwd)',
            re.IGNORECASE
        ),
        
        # Кузов
        'body': re.compile(
            r'(?:кузов|тип)[:\s]*(седан|хэтчбек|универсал|кроссовер|внедорожник|купе|минивэн|пикап|suv)',
            re.IGNORECASE
        ),
        
        # Цвет
        'color': re.compile(
            r'(?:цвет)[:\s]*(\w+)',
            re.IGNORECASE
        ),
    }
    
    def __init__(self):
        # Компилируем регулярку для марок
        brands_pattern = '|'.join(re.escape(b) for b in sorted(self.KNOWN_BRANDS, key=len, reverse=True))
        self.brand_pattern = re.compile(
            rf'\b({brands_pattern})\s+(\S+)',
            re.IGNORECASE
        )
    
    def parse(self, text: str) -> ParsedCarData:
        """
        Парсит текст поста и возвращает структурированные данные.
        
        Args:
            text: Текст Telegram поста
        
        Returns:
            ParsedCarData с извлечёнными данными
        """
        result = ParsedCarData(original_text=text)
        
        if not text or not text.strip():
            result.parse_errors.append("Пустой текст")
            return result
        
        # Очищаем текст от эмодзи и лишних пробелов
        clean_text = self._clean_text(text)
        
        # Извлекаем марку и модель из заголовка
        brand, model = self._extract_brand_model(clean_text)
        result.brand_raw = brand
        result.model_raw = model
        
        # Формируем заголовок
        if brand:
            result.title = f"{brand} {model}".strip() if model else brand
        else:
            # Берём первую строку как заголовок
            first_line = clean_text.split('\n')[0][:200]
            result.title = first_line
        
        # Извлекаем год выпуска
        year, month = self._extract_year(clean_text)
        result.year = year
        result.month = month
        
        # Извлекаем технические характеристики
        result.engine_volume_l, result.turbo = self._extract_engine(clean_text)
        result.horsepower = self._extract_horsepower(clean_text)
        result.mileage_km = self._extract_mileage(clean_text)
        
        # Цена
        result.price_rub = self._extract_price(clean_text)
        result.price_negotiable = bool(self.PATTERNS['negotiable'].search(clean_text))
        
        # Дополнительные характеристики
        result.fuel_type = self._extract_pattern(clean_text, 'fuel')
        result.transmission = self._extract_pattern(clean_text, 'transmission')
        result.drive_type = self._extract_pattern(clean_text, 'drive')
        result.body_type = self._extract_pattern(clean_text, 'body')
        result.color = self._extract_pattern(clean_text, 'color')
        
        # Состояние
        condition_match = self.PATTERNS['condition'].search(clean_text)
        if condition_match:
            result.condition_text = condition_match.group(1).strip()
        
        # Логируем результат
        logger.debug(
            f"Parsed: brand={result.brand_raw}, model={result.model_raw}, "
            f"year={result.year}, price={result.price_rub}, "
            f"score={result.completeness_score:.2f}"
        )
        
        return result
    
    def _clean_text(self, text: str) -> str:
        """Очищает текст от эмодзи и лишних символов"""
        # Удаляем эмодзи (Unicode emoji ranges)
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        text = emoji_pattern.sub(' ', text)
        
        # Нормализуем пробелы
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n+', '\n', text)
        
        return text.strip()
    
    def _extract_brand_model(self, text: str) -> Tuple[str, str]:
        """Извлекает марку и модель из текста"""
        # Пробуем найти известную марку
        match = self.brand_pattern.search(text)
        if match:
            brand = match.group(1)
            model = match.group(2)
            
            # Нормализуем марку
            brand_lower = brand.lower()
            if brand_lower in self.BRAND_ALIASES:
                brand = self.BRAND_ALIASES[brand_lower]
            else:
                # Приводим к правильному регистру
                for known in self.KNOWN_BRANDS:
                    if known.lower() == brand_lower:
                        brand = known
                        break
            
            return brand, model
        
        # Пробуем найти марку на русском
        text_lower = text.lower()
        for alias, brand in self.BRAND_ALIASES.items():
            if alias in text_lower:
                # Пытаемся найти модель после марки
                idx = text_lower.index(alias)
                rest = text[idx + len(alias):].strip()
                model_match = re.match(r'^[\s\-]*(\S+)', rest)
                model = model_match.group(1) if model_match else ''
                return brand, model
        
        return '', ''
    
    def _extract_year(self, text: str) -> Tuple[Optional[int], Optional[int]]:
        """Извлекает год и месяц выпуска"""
        # Сначала ищем формат MM.YYYY
        match = self.PATTERNS['year_month'].search(text)
        if match:
            try:
                month = int(match.group(1))
                year = int(match.group(2))
                if 1 <= month <= 12 and 1990 <= year <= 2030:
                    return year, month
            except ValueError:
                pass
        
        # Ищем только год
        match = self.PATTERNS['year_only'].search(text)
        if match:
            try:
                year = int(match.group(1))
                if 1990 <= year <= 2030:
                    return year, None
            except ValueError:
                pass
        
        # Ищем год в тексте
        match = self.PATTERNS['year_inline'].search(text)
        if match:
            try:
                year = int(match.group(1))
                if 1990 <= year <= 2030:
                    return year, None
            except ValueError:
                pass
        
        return None, None
    
    def _extract_engine(self, text: str) -> Tuple[Optional[Decimal], Optional[bool]]:
        """Извлекает объём двигателя и флаг турбо"""
        turbo = None
        volume = None
        
        # Ищем в формате "Объем: 1.5Т"
        match = self.PATTERNS['engine_volume'].search(text)
        if match:
            try:
                vol_str = match.group(1).replace(',', '.')
                volume = Decimal(vol_str)
                turbo_marker = match.group(2)
                if turbo_marker and turbo_marker.upper() in ('T', 'Т'):
                    turbo = True
            except (ValueError, InvalidOperation):
                pass
        
        # Если не нашли, ищем inline
        if volume is None:
            match = self.PATTERNS['engine_inline'].search(text)
            if match:
                try:
                    vol_str = match.group(1).replace(',', '.')
                    vol = Decimal(vol_str)
                    # Фильтруем нереалистичные значения
                    if Decimal('0.5') <= vol <= Decimal('10'):
                        volume = vol
                        turbo_marker = match.group(2)
                        if turbo_marker and turbo_marker.upper() in ('T', 'Т'):
                            turbo = True
                except (ValueError, InvalidOperation):
                    pass
        
        return volume, turbo
    
    def _extract_horsepower(self, text: str) -> Optional[int]:
        """Извлекает мощность в л.с."""
        match = self.PATTERNS['horsepower'].search(text)
        if match:
            try:
                hp = int(match.group(1))
                # Фильтруем нереалистичные значения
                if 30 <= hp <= 2000:
                    return hp
            except ValueError:
                pass
        return None
    
    def _extract_mileage(self, text: str) -> Optional[int]:
        """Извлекает пробег в км"""
        # Сначала ищем с меткой "пробег"
        match = self.PATTERNS['mileage'].search(text)
        if match:
            return self._parse_number(match.group(1))
        
        # Ищем inline формат "XX XXX км"
        match = self.PATTERNS['mileage_inline'].search(text)
        if match:
            mileage = self._parse_number(match.group(1))
            # Проверяем, что это похоже на пробег (не год)
            if mileage and mileage > 100:
                return mileage
        
        return None
    
    def _extract_price(self, text: str) -> Optional[int]:
        """Извлекает цену в рублях"""
        # Ищем формат "X млн"
        match = self.PATTERNS['price_millions'].search(text)
        if match:
            try:
                millions = float(match.group(1).replace(',', '.'))
                return int(millions * 1_000_000)
            except ValueError:
                pass
        
        # Ищем обычный формат
        match = self.PATTERNS['price'].search(text)
        if match:
            price_str = match.group(1) or match.group(2)
            if price_str:
                price = self._parse_number(price_str)
                # Фильтруем нереалистичные значения
                if price and 10_000 <= price <= 100_000_000:
                    return price
        
        return None
    
    def _extract_pattern(self, text: str, pattern_name: str) -> str:
        """Извлекает значение по паттерну"""
        match = self.PATTERNS.get(pattern_name)
        if match:
            result = match.search(text)
            if result:
                return result.group(1).strip()
        return ''
    
    def _parse_number(self, s: str) -> Optional[int]:
        """Парсит число из строки с пробелами и разделителями"""
        if not s:
            return None
        
        # Удаляем пробелы и разделители
        clean = re.sub(r'[\s\.,]', '', s)
        
        try:
            return int(clean)
        except ValueError:
            return None
    
    def get_parse_status(self, data: ParsedCarData) -> str:
        """Определяет статус парсинга"""
        from ..models import TelegramMessage
        
        if not data.is_valid:
            return TelegramMessage.ParseStatus.PARSE_FAILED
        
        if data.completeness_score >= 0.7:
            return TelegramMessage.ParseStatus.PARSED_OK
        
        if data.completeness_score >= 0.3:
            return TelegramMessage.ParseStatus.PARSED_PARTIAL
        
        return TelegramMessage.ParseStatus.PARSE_FAILED


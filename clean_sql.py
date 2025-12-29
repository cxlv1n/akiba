#!/usr/bin/env python3
"""
Скрипт для очистки akiba_base.sql от пустых и ненужных таблиц.

Использование:
    python clean_sql.py

Создаёт файл akiba_clean.sql с только нужными таблицами.
"""

import re
import os

# Таблицы, которые нужно сохранить (содержат данные и полезны для Django)
TABLES_TO_KEEP = {
    'dle_category',      # Категории (Корея, Япония, Китай)
    'dle_post',          # Автомобили (основная таблица)
    'dle_images',        # Изображения автомобилей
    'dle_post_extras',   # Дополнительная информация (просмотры)
    'dle_post_extras_cats',  # Связь постов с категориями
    'dle_users',         # Пользователи (для истории)
    'dle_static',        # Статические страницы
}

# Пустые таблицы (будут удалены)
EMPTY_TABLES = {
    'dle_banned',
    'dle_banners_logs',
    'dle_banners_rubrics',
    'dle_comment_rating_log',
    'dle_comments',
    'dle_comments_files',
    'dle_complaint',
    'dle_dle_filter_files',
    'dle_dle_filter_news',
    'dle_dle_filter_news_temp',
    'dle_dle_filter_pages',
    'dle_files',
    'dle_flood',
    'dle_ignore_list',
    'dle_links',
    'dle_login_log',
    'dle_logs',
    'dle_lostdb',
    'dle_mail_log',
    'dle_metatags',
    'dle_notice',
    'dle_plugins',
    'dle_plugins_files',
    'dle_plugins_logs',
    'dle_pm',
    'dle_poll',
    'dle_poll_log',
    'dle_post_log',
    'dle_post_pass',
    'dle_question',
    'dle_read_log',
    'dle_redirects',
    'dle_sendlog',
    'dle_social_login',
    'dle_spam_log',
    'dle_static_files',
    'dle_subscribe',
    'dle_tags',
    'dle_twofactor',
    'dle_views',
    'dle_vote_result',
    'dle_xfsearch',
}

# Служебные таблицы DLE (не нужны в Django)
DLE_SERVICE_TABLES = {
    'dle_admin_logs',
    'dle_admin_sections',
    'dle_banners',
    'dle_dle_filter_statistics',
    'dle_email',
    'dle_rss',
    'dle_rssinform',
    'dle_usergroups',
    'dle_vote',
}


def clean_sql(input_file, output_file):
    """Очистка SQL файла от ненужных таблиц."""
    
    print(f"Чтение файла: {input_file}")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Разбиваем на секции по таблицам
    # Ищем паттерн: -- Table structure for table `table_name` ... до следующей такой секции
    
    # Заголовок MySQL
    header_match = re.search(r'^(.*?)(?=--\s*Table structure)', content, re.DOTALL)
    header = header_match.group(1) if header_match else ''
    
    # Футер
    footer = """
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;
/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed
"""
    
    # Находим все секции таблиц
    table_pattern = r'(--\s*\n--\s*Table structure for table `(\w+)`\s*\n--\s*\n.*?)(?=--\s*\n--\s*Table structure for table|$)'
    
    tables_found = []
    tables_kept = []
    tables_removed = []
    
    result_sections = [header.strip()]
    
    for match in re.finditer(table_pattern, content, re.DOTALL):
        section = match.group(1)
        table_name = match.group(2)
        tables_found.append(table_name)
        
        if table_name in TABLES_TO_KEEP:
            result_sections.append(section.strip())
            tables_kept.append(table_name)
        else:
            tables_removed.append(table_name)
    
    result_sections.append(footer.strip())
    
    # Записываем результат
    result = '\n\n'.join(result_sections)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(result)
    
    # Статистика
    print(f"\n{'='*60}")
    print(f"СТАТИСТИКА ОЧИСТКИ SQL")
    print(f"{'='*60}")
    print(f"Всего таблиц найдено: {len(tables_found)}")
    print(f"Таблиц сохранено: {len(tables_kept)}")
    print(f"Таблиц удалено: {len(tables_removed)}")
    
    print(f"\n--- Сохранённые таблицы ({len(tables_kept)}) ---")
    for t in sorted(tables_kept):
        print(f"  ✓ {t}")
    
    print(f"\n--- Удалённые таблицы ({len(tables_removed)}) ---")
    for t in sorted(tables_removed):
        reason = ""
        if t in EMPTY_TABLES:
            reason = "(пустая)"
        elif t in DLE_SERVICE_TABLES:
            reason = "(служебная DLE)"
        print(f"  ✗ {t} {reason}")
    
    # Размер файлов
    original_size = os.path.getsize(input_file) / 1024
    new_size = os.path.getsize(output_file) / 1024
    
    print(f"\n--- Размер файлов ---")
    print(f"Оригинал: {original_size:.1f} KB")
    print(f"Очищенный: {new_size:.1f} KB")
    print(f"Сжатие: {(1 - new_size/original_size)*100:.1f}%")
    
    print(f"\nРезультат сохранён в: {output_file}")


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, 'akiba_base.sql')
    output_file = os.path.join(script_dir, 'akiba_clean.sql')
    
    if not os.path.exists(input_file):
        print(f"Ошибка: файл {input_file} не найден!")
        exit(1)
    
    clean_sql(input_file, output_file)


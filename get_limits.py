#!/usr/bin/env python3
"""
Программа для получения информации о лимитах Cursor
"""

import os
import sys
import json
import sqlite3
from typing import Optional, Dict, Any
from colorama import Fore, Style, init

# Инициализация colorama
init()

# Эмодзи для вывода
EMOJI = {
    "INFO": "ℹ️",
    "SUCCESS": "✅",
    "ERROR": "❌",
    "WARNING": "⚠️",
    "LIMIT": "📊",
    "USAGE": "📈",
}

def is_arch_linux() -> bool:
    """Проверить, является ли система Arch Linux"""
    if sys.platform != "linux":
        return False
    return os.path.exists("/etc/arch-release")

def get_cursor_storage_path() -> str:
    """Получить путь к файлу storage.json Cursor"""
    if sys.platform == "win32":
        appdata = os.getenv("APPDATA")
        if appdata:
            return os.path.join(appdata, "Cursor", "User", "globalStorage", "storage.json")
        else:
            return os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Cursor", "User", "globalStorage", "storage.json")
    elif sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Cursor", "User", "globalStorage", "storage.json")
    else:
        return os.path.join(os.path.expanduser("~"), ".config", "Cursor", "User", "globalStorage", "storage.json")

def get_cursor_sqlite_path() -> str:
    """Получить путь к SQLite базе данных Cursor"""
    if sys.platform == "win32":
        appdata = os.getenv("APPDATA")
        if appdata:
            return os.path.join(appdata, "Cursor", "User", "globalStorage", "state.vscdb")
        else:
            return os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Cursor", "User", "globalStorage", "state.vscdb")
    elif sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Cursor", "User", "globalStorage", "state.vscdb")
    else:
        return os.path.join(os.path.expanduser("~"), ".config", "Cursor", "User", "globalStorage", "state.vscdb")

def search_limits_in_dict(data: Dict[str, Any], prefix: str = "", results: Optional[Dict] = None) -> Dict[str, Any]:
    """Рекурсивный поиск информации о лимитах в словаре"""
    if results is None:
        results = {}
    
    # Ключевые слова для поиска лимитов (более специфичные)
    limit_keywords = [
        'limit', 'usage', 'quota', 'subscription', 'requests', 
        'tokens', 'remaining', 'used', 'total', 'free',
        'premium', 'pro', 'tier', 'plan', 'credits', 'balance',
        'grace', 'period', 'hours', 'minutes', 'count'
    ]
    
    # Исключаем ключи, которые точно не связаны с лимитами
    exclude_keywords = [
        'profile', 'workspace', 'recommendation', 'association',
        'settings', 'configuration', 'preference', 'history'
    ]
    
    for key, value in data.items():
        key_lower = key.lower()
        
        # Пропускаем ключи, которые точно не связаны с лимитами
        if any(exclude in key_lower for exclude in exclude_keywords):
            continue
        
        # Проверяем, содержит ли ключ слова, связанные с лимитами
        if any(keyword in key_lower for keyword in limit_keywords):
            full_key = f"{prefix}.{key}" if prefix else key
            # Пропускаем пустые значения и очень длинные строки
            if value is not None and (not isinstance(value, str) or len(value) < 1000):
                results[full_key] = value
        
        # Рекурсивно ищем во вложенных словарях (но не слишком глубоко)
        if isinstance(value, dict) and len(prefix.split('.')) < 5:
            search_limits_in_dict(value, f"{prefix}.{key}" if prefix else key, results)
        elif isinstance(value, list) and len(value) < 10:
            # Проверяем элементы списка
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    search_limits_in_dict(item, f"{prefix}.{key}[{i}]" if prefix else f"{key}[{i}]", results)
    
    return results

def get_limits_from_storage(storage_path: str) -> Dict[str, Any]:
    """Получить лимиты из storage.json"""
    limits = {}
    
    if not os.path.exists(storage_path):
        print(f"{Fore.YELLOW}{EMOJI['WARNING']} Файл storage.json не найден: {storage_path}{Style.RESET_ALL}")
        return limits
    
    try:
        with open(storage_path, "r", encoding="utf-8") as f:
            storage_data = json.load(f)
        
        # Ищем информацию о лимитах
        limits = search_limits_in_dict(storage_data)
        
        # Также ищем специфичные ключи Cursor
        cursor_specific_keys = [
            'cursor.usage',
            'cursor.limits',
            'cursor.subscription',
            'cursor.quota',
            'cursor.requests',
            'cursor.tokens',
            'cursor.credits',
            'cursor.balance',
        ]
        
        for key in cursor_specific_keys:
            if key in storage_data:
                limits[key] = storage_data[key]
        
    except json.JSONDecodeError as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} Ошибка при чтении JSON: {e}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} Ошибка при чтении storage.json: {e}{Style.RESET_ALL}")
    
    return limits

def get_limits_from_sqlite(sqlite_path: str) -> Dict[str, Any]:
    """Получить лимиты из SQLite базы данных"""
    limits = {}
    
    if not os.path.exists(sqlite_path):
        print(f"{Fore.YELLOW}{EMOJI['WARNING']} SQLite база данных не найдена: {sqlite_path}{Style.RESET_ALL}")
        return limits
    
    try:
        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()
        
        # Получаем все таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        # Ищем информацию о лимитах в таблице ItemTable (стандартная таблица VS Code/Cursor)
        try:
            cursor.execute("SELECT key, value FROM ItemTable")
            rows = cursor.fetchall()
            
            limit_keywords = [
                'limit', 'usage', 'quota', 'subscription', 'requests', 
                'tokens', 'remaining', 'used', 'total', 'free',
                'premium', 'pro', 'tier', 'plan', 'credits', 'balance',
                'grace', 'period', 'hours', 'minutes'
            ]
            
            # Исключаем ключи, которые точно не связаны с лимитами
            exclude_keywords = [
                'profile', 'workspace', 'recommendation', 'association',
                'settings', 'configuration', 'preference', 'history',
                'extension', 'github', 'git'
            ]
            
            for key, value in rows:
                key_lower = key.lower()
                
                # Пропускаем исключенные ключи
                if any(exclude in key_lower for exclude in exclude_keywords):
                    continue
                
                if any(keyword in key_lower for keyword in limit_keywords):
                    # Пытаемся распарсить JSON значение
                    try:
                        parsed_value = json.loads(value)
                        limits[key] = parsed_value
                    except (json.JSONDecodeError, TypeError):
                        # Если не JSON, сохраняем как есть (если не слишком длинное)
                        if not isinstance(value, str) or len(value) < 500:
                            limits[key] = value
        except sqlite3.OperationalError:
            # Таблица ItemTable может не существовать
            pass
        
        # Проверяем другие таблицы
        for table_name, in tables:
            if 'limit' in table_name.lower() or 'usage' in table_name.lower() or 'quota' in table_name.lower():
                try:
                    cursor.execute(f"SELECT * FROM {table_name}")
                    rows = cursor.fetchall()
                    if rows:
                        limits[f"table_{table_name}"] = rows
                except sqlite3.OperationalError:
                    pass
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} Ошибка при работе с SQLite: {e}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} Ошибка при чтении SQLite: {e}{Style.RESET_ALL}")
    
    return limits

def get_category(key: str) -> str:
    """Определить категорию лимита по ключу"""
    key_lower = key.lower()
    
    if any(word in key_lower for word in ['subscription', 'tier', 'plan', 'premium', 'pro']):
        return "Подписка"
    elif any(word in key_lower for word in ['remaining', 'hours', 'minutes', 'grace', 'period']):
        return "Оставшееся время"
    elif any(word in key_lower for word in ['usage', 'used', 'count']):
        return "Использование"
    elif any(word in key_lower for word in ['limit', 'quota', 'total', 'max']):
        return "Лимиты"
    elif any(word in key_lower for word in ['tokens', 'requests', 'credits', 'balance']):
        return "Ресурсы"
    else:
        return "Прочее"

def format_value(value: Any, key: str = "") -> str:
    """Форматирование значения для вывода"""
    if isinstance(value, dict):
        # Для словарей показываем компактный формат
        items = []
        for k, v in value.items():
            if isinstance(v, (int, float, str, bool)):
                items.append(f"{k}: {v}")
            else:
                items.append(f"{k}: ...")
        result = ", ".join(items[:3])
        if len(items) > 3:
            result += f" ... (+{len(items) - 3} еще)"
        return result
    elif isinstance(value, list):
        if len(value) == 0:
            return "пусто"
        elif len(value) <= 3:
            return ", ".join(str(v) for v in value)
        else:
            return f"{len(value)} элементов: {', '.join(str(v) for v in value[:2])} ..."
    elif isinstance(value, (int, float)):
        # Для числовых значений добавляем форматирование
        key_lower = key.lower()
        
        # Форматирование времени
        if 'hours' in key_lower or 'minutes' in key_lower or 'remaining' in key_lower:
            if isinstance(value, (int, float)) and value >= 0:
                if 'minutes' in key_lower and value >= 60:
                    hours = int(value // 60)
                    minutes = int(value % 60)
                    if hours > 0 and minutes > 0:
                        return f"{hours} ч. {minutes} мин."
                    elif hours > 0:
                        return f"{hours} ч."
                    else:
                        return f"{int(value)} мин."
                elif 'hours' in key_lower or 'remaining' in key_lower:
                    hours = int(value)
                    if hours >= 24:
                        days = hours // 24
                        remaining_hours = hours % 24
                        if days > 0 and remaining_hours > 0:
                            return f"{days} дн. {remaining_hours} ч."
                        elif days > 0:
                            return f"{days} дн."
                    return f"{hours} ч."
        
        # Форматирование чисел
        if value >= 1000:
            return f"{value:,.0f}".replace(",", " ")
        return f"{value:,.0f}".replace(",", " ") if isinstance(value, float) else str(int(value))
    elif isinstance(value, bool):
        return f"{Fore.GREEN}✓ Да{Style.RESET_ALL}" if value else f"{Fore.RED}✗ Нет{Style.RESET_ALL}"
    else:
        str_value = str(value)
        # Пропускаем очень длинные URL и технические строки
        if len(str_value) > 80:
            return str_value[:77] + "..."
        return str_value

def get_display_name(key: str) -> str:
    """Получить понятное название для ключа"""
    key_lower = key.lower()
    
    # Убираем префиксы источников
    clean_key = key.replace('storage.', '').replace('sqlite.', '')
    parts = clean_key.split('/')
    last_part = parts[-1]
    
    # Маппинг ключей на понятные названия
    name_mapping = {
        'remaining': 'Осталось',
        'used': 'Использовано',
        'total': 'Всего',
        'limit': 'Лимит',
        'quota': 'Квота',
        'subscription': 'Подписка',
        'tier': 'Тариф',
        'plan': 'План',
        'tokens': 'Токены',
        'requests': 'Запросы',
        'credits': 'Кредиты',
        'balance': 'Баланс',
        'hours': 'Часы',
        'minutes': 'Минуты',
        'grace': 'Льготный период',
        'period': 'Период',
        'premium': 'Премиум',
        'pro': 'Про',
        'free': 'Бесплатно',
        'newprivacymodehoursremainingingraceperiod': 'Льготный период (часы)',
    }
    
    # Ищем точное совпадение
    if last_part.lower() in name_mapping:
        return name_mapping[last_part.lower()]
    
    # Ищем частичные совпадения
    for word, display in name_mapping.items():
        if word in key_lower:
            # Если есть контекст в пути, добавляем его
            if len(parts) > 1 and parts[-2]:
                context = parts[-2].replace('_', ' ').title()
                return f"{display} ({context})"
            return display
    
    # Если не нашли, форматируем последнюю часть ключа
    formatted = last_part.replace('_', ' ').replace('-', ' ')
    # Делаем первую букву заглавной
    if formatted:
        formatted = formatted[0].upper() + formatted[1:]
    return formatted if formatted else key

def print_progress_bar(used: float, total: float, label: str = ""):
    """Вывести прогресс-бар для использованных/оставшихся лимитов"""
    if total <= 0:
        return
    
    percentage = (used / total) * 100
    bar_length = 30
    filled = int(bar_length * used / total)
    
    bar = "█" * filled + "░" * (bar_length - filled)
    
    color = Fore.GREEN
    if percentage >= 90:
        color = Fore.RED
    elif percentage >= 70:
        color = Fore.YELLOW
    
    print(f"  {label}")
    print(f"  {color}{bar}{Style.RESET_ALL} {used:,.0f} / {total:,.0f} ({percentage:.1f}%)")

def print_limits(limits: Dict[str, Any], source: str):
    """Вывод лимитов в консоль с группировкой по категориям"""
    if not limits:
        print(f"{Fore.YELLOW}{EMOJI['WARNING']} Информация о лимитах не найдена в {source}{Style.RESET_ALL}")
        return
    
    # Группируем лимиты по категориям
    categories = {}
    for key, value in limits.items():
        category = get_category(key)
        if category not in categories:
            categories[category] = []
        categories[category].append((key, value))
    
    print(f"\n{Fore.CYAN}{'='*70}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{EMOJI['LIMIT']} Лимиты из {source}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")
    
    # Выводим категории в определенном порядке
    category_order = ["Подписка", "Оставшееся время", "Использование", "Лимиты", "Ресурсы", "Прочее"]
    
    for category in category_order:
        if category not in categories:
            continue
        
        print(f"{Fore.MAGENTA}{'─'*70}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}📁 {category}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}{'─'*70}{Style.RESET_ALL}\n")
        
        # Сортируем элементы в категории
        items = sorted(categories[category], key=lambda x: x[0])
        
        for key, value in items:
            display_name = get_display_name(key)
            formatted_value = format_value(value, key)
            
            # Определяем цвет в зависимости от типа значения
            if isinstance(value, (int, float)):
                if 'remaining' in key.lower() or 'free' in key.lower():
                    if value > 0:
                        color = Fore.GREEN
                    else:
                        color = Fore.RED
                elif 'used' in key.lower() or 'usage' in key.lower():
                    color = Fore.YELLOW
                else:
                    color = Fore.CYAN
            else:
                color = Fore.WHITE
            
            # Выводим в табличном формате
            key_display = display_name.ljust(40)
            
            # Для булевых значений цвет уже включен в formatted_value
            if isinstance(value, bool):
                print(f"  {Fore.GREEN}{key_display}{Style.RESET_ALL} {formatted_value}")
            else:
                print(f"  {Fore.GREEN}{key_display}{Style.RESET_ALL} {color}{formatted_value}{Style.RESET_ALL}")
            
            # Если есть пара used/total или remaining/total, показываем прогресс-бар
            if isinstance(value, (int, float)) and value > 0:
                # Ищем связанные значения для прогресс-бара
                key_lower = key.lower()
                if 'remaining' in key_lower:
                    # Ищем total для этого ключа
                    for other_key, other_value in limits.items():
                        if 'total' in other_key.lower() and key.split('/')[-2] in other_key:
                            if isinstance(other_value, (int, float)):
                                used_val = other_value - value
                                print_progress_bar(used_val, other_value, "  Использование:")
                                break
        
        print()
    
    # Если есть необработанные категории
    for category, items in categories.items():
        if category not in category_order:
            print(f"{Fore.MAGENTA}{'─'*70}{Style.RESET_ALL}")
            print(f"{Fore.MAGENTA}📁 {category}{Style.RESET_ALL}")
            print(f"{Fore.MAGENTA}{'─'*70}{Style.RESET_ALL}\n")
            
            for key, value in sorted(items, key=lambda x: x[0]):
                display_name = get_display_name(key)
                formatted_value = format_value(value, key)
                key_display = display_name.ljust(35)
                print(f"  {Fore.GREEN}{key_display}{Style.RESET_ALL} {Fore.WHITE}{formatted_value}{Style.RESET_ALL}")
            print()

def merge_limits(storage_limits: Dict[str, Any], sqlite_limits: Dict[str, Any]) -> Dict[str, Any]:
    """Объединить лимиты из разных источников"""
    merged = {}
    
    # Добавляем лимиты из storage.json
    for key, value in storage_limits.items():
        merged[f"storage.{key}"] = value
    
    # Добавляем лимиты из SQLite (приоритет, если есть дубликаты)
    for key, value in sqlite_limits.items():
        # Если ключ уже есть, добавляем префикс sqlite
        if f"storage.{key}" in merged:
            merged[f"sqlite.{key}"] = value
        else:
            merged[key] = value
    
    return merged

def main():
    """Главная функция"""
    print(f"\n{Fore.CYAN}{'='*70}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{EMOJI['INFO']}  Получение информации о лимитах Cursor{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")
    
    # Получаем пути к файлам
    storage_path = get_cursor_storage_path()
    sqlite_path = get_cursor_sqlite_path()
    
    print(f"{Fore.CYAN}{EMOJI['INFO']}  Анализ файлов Cursor...{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   📄 storage.json: {storage_path}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   💾 SQLite БД:    {sqlite_path}{Style.RESET_ALL}\n")
    
    # Получаем лимиты из обоих источников
    storage_limits = get_limits_from_storage(storage_path)
    sqlite_limits = get_limits_from_sqlite(sqlite_path)
    
    # Объединяем лимиты
    all_limits = merge_limits(storage_limits, sqlite_limits)
    
    # Если ничего не найдено
    if not all_limits:
        print(f"{Fore.YELLOW}{EMOJI['WARNING']}  Информация о лимитах не найдена.{Style.RESET_ALL}")
        print(f"{Fore.CYAN}ℹ️   Убедитесь, что:{Style.RESET_ALL}")
        print(f"   • Cursor установлен и использовался")
        print(f"   • Файлы конфигурации существуют")
        print(f"   • Вы использовали функции, которые имеют лимиты\n")
    else:
        # Выводим объединенные лимиты
        print_limits(all_limits, "Cursor")
    
    print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{EMOJI['SUCCESS']}  Анализ завершен{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}{EMOJI['WARNING']} Прервано пользователем{Style.RESET_ALL}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Fore.RED}{EMOJI['ERROR']} Критическая ошибка: {e}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


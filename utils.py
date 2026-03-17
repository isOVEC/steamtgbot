"""
Вспомогательные утилиты для бота
"""

import re
from typing import Optional, Tuple


def validate_steam_id64(steam_id: str) -> bool:
    """
    Валидация SteamID64
    
    Args:
        steam_id: Строка с SteamID64
        
    Returns:
        True если валидный, иначе False
    """
    # SteamID64 должен быть 17-значным числом
    pattern = r'^\d{17}$'
    return bool(re.match(pattern, steam_id))


def validate_custom_id(steam_id: str) -> bool:
    """
    Валидация Custom ID (vanity URL)
    
    Args:
        steam_id: Строка с custom ID
        
    Returns:
        True если валидный, иначе False
    """
    # Custom ID: 2-32 символа, буквы, цифры, подчёркивание
    pattern = r'^[a-zA-Z0-9_]{2,32}$'
    return bool(re.match(pattern, steam_id))


def parse_steam_url(url: str) -> Optional[str]:
    """
    Извлечение SteamID64 из URL
    
    Args:
        url: URL профиля Steam
        
    Returns:
        SteamID64 если найден, иначе None
    """
    # Формат: https://steamcommunity.com/profiles/76561198000000000
    profile_pattern = r'steamcommunity\.com/profiles/(\d{17})'
    match = re.search(profile_pattern, url)
    if match:
        return match.group(1)
    
    # Формат: https://steamcommunity.com/id/customid
    id_pattern = r'steamcommunity\.com/id/([a-zA-Z0-9_]+)'
    match = re.search(id_pattern, url)
    if match:
        return match.group(1)
    
    return None


def steamid64_to_steam2(steamid64: str) -> str:
    """
    Конвертация SteamID64 в SteamID2 (STEAM_0:1:12345678)
    
    Args:
        steamid64: SteamID64
        
    Returns:
        SteamID2
    """
    try:
        id64 = int(steamid64)
        auth_server = (id64 - 76561197960265728) & 1
        auth_id = (id64 - 76561197960265728 - auth_server) // 2
        return f"STEAM_0:{auth_server}:{auth_id}"
    except (ValueError, TypeError):
        return ""


def steamid64_to_steam3(steamid64: str) -> str:
    """
    Конвертация SteamID64 в SteamID3 ([U:1:12345678])
    
    Args:
        steamid64: SteamID64
        
    Returns:
        SteamID3
    """
    try:
        id64 = int(steamid64)
        account_id = id64 - 76561197960265728
        return f"[U:1:{account_id}]"
    except (ValueError, TypeError):
        return ""


def format_price(price: float, currency: str = "RUB") -> str:
    """
    Форматирование цены
    
    Args:
        price: Цена
        currency: Валюта
        
    Returns:
        Отформатированная цена
    """
    symbols = {
        "RUB": "₽",
        "USD": "$",
        "EUR": "€",
        "GBP": "£"
    }
    
    symbol = symbols.get(currency, currency)
    return f"{price:.2f} {symbol}"


def truncate_string(text: str, max_length: int = 50) -> str:
    """
    Обрезание строки до указанной длины
    
    Args:
        text: Текст
        max_length: Максимальная длина
        
    Returns:
        Обрезанная строка
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


class SteamIDConverter:
    """Класс для конвертации Steam ID"""
    
    @staticmethod
    def is_steam_id64(value: str) -> bool:
        """Проверка является ли значение SteamID64"""
        return validate_steam_id64(value)
    
    @staticmethod
    def is_custom_id(value: str) -> bool:
        """Проверка является ли значение custom ID"""
        return validate_custom_id(value)
    
    @staticmethod
    def detect_type(value: str) -> Tuple[str, Optional[str]]:
        """
        Определение типа Steam ID
        
        Returns:
            (type, value) - тип и нормализованное значение
        """
        if validate_steam_id64(value):
            return ("id64", value)
        
        if validate_custom_id(value):
            return ("custom", value)
        
        # Пробуем извлечь из URL
        parsed = parse_steam_url(value)
        if parsed:
            if validate_steam_id64(parsed):
                return ("id64", parsed)
            return ("custom", parsed)
        
        return ("unknown", None)
    
    @staticmethod
    def to_all_formats(steamid64: str) -> dict:
        """
        Конвертация во все форматы
        
        Returns:
            Словарь со всеми форматами
        """
        if not validate_steam_id64(steamid64):
            return {}
        
        return {
            "id64": steamid64,
            "steam2": steamid64_to_steam2(steamid64),
            "steam3": steamid64_to_steam3(steamid64),
            "profile": f"https://steamcommunity.com/profiles/{steamid64}",
            "inventory": f"https://steamcommunity.com/profiles/{steamid64}/inventory/"
        }

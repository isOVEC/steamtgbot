"""
Модуль для работы со Steam API
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import aiohttp
from steampy.client import SteamClient
from steampy.utils import GameOptions

logger = logging.getLogger(__name__)


# Карта игр
GAMES = {
    "cs2": GameOptions.CS,
    "csgo": GameOptions.CS,
    "dota2": GameOptions.DOTA2,
    "tf2": GameOptions.TF2,
}


@dataclass
class InventoryItem:
    """Предмет инвентаря"""
    assetid: str
    classid: str
    instanceid: str
    market_name: str
    icon_url: str
    game: str


class SteamAPI:
    """Класс для работы со Steam API"""

    def __init__(self, api_key: str, proxy_url: Optional[str] = None):
        self.api_key = api_key
        self.proxy_url = proxy_url
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Получение или создание сессии"""
        if self._session is None or self._session.closed:
            if self.proxy_url:
                self._session = aiohttp.ClientSession(
                    proxy=self.proxy_url,
                    timeout=aiohttp.ClientTimeout(total=30)
                )
            else:
                self._session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=30)
                )
        return self._session

    async def close(self) -> None:
        """Закрытие сессии"""
        if self._session and not self._session.closed:
            await self._session.close()

    def _get_game_options(self, game: str) -> GameOptions:
        """Получение параметров игры"""
        return GAMES.get(game.lower(), GameOptions.CS)

    async def get_inventory(
        self, 
        steam_id64: str, 
        game: str = "cs2",
        merge: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Получение инвентаря пользователя
        
        Args:
            steam_id64: SteamID64 пользователя
            game: Название игры (cs2, dota2, tf2)
            merge: Объединять ли данные с описаниями
            
        Returns:
            Список предметов инвентаря
        """
        try:
            game_options = self._get_game_options(game)
            
            # Используем aiohttp для асинхронного запроса
            session = await self._get_session()
            
            # URL для получения инвентаря
            url = f"https://steamcommunity.com/inventory/{steam_id64}/{game_options.app_id}/2"
            
            headers = {
                "User-Agent": "SteamInventoryBot/1.0"
            }
            
            async with session.get(url, headers=headers) as response:
                if response.status == 429:
                    logger.warning(f"Rate limited при запросе инвентаря для {steam_id64}")
                    raise Exception("Rate limited by Steam")
                
                if response.status == 403:
                    logger.warning(f"Приватный инвентарь для {steam_id64}")
                    raise Exception("Private inventory")
                
                if response.status != 200:
                    logger.error(f"Ошибка HTTP {response.status}")
                    raise Exception(f"HTTP error {response.status}")
                
                data = await response.json()
                
                if "error" in data:
                    raise Exception(data.get("error", "Unknown error"))
                
                # Обработка данных инвентаря
                items = self._process_inventory_data(data, game)
                
                if merge and data.get("descriptions"):
                    items = self._merge_descriptions(items, data["descriptions"])
                
                logger.info(f"Получено {len(items)} предметов для {steam_id64}")
                return items
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout при получении инвентаря для {steam_id64}")
            raise Exception("Request timeout")
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка клиента: {e}")
            raise Exception(f"Client error: {str(e)}")
        except Exception as e:
            logger.error(f"Ошибка получения инвентаря: {e}")
            raise

    def _process_inventory_data(self, data: Dict[str, Any], game: str) -> List[Dict[str, Any]]:
        """Обработка данных инвентаря"""
        items = []
        
        for item in data.get("assets", []):
            # Создаём уникальный ключ из classid и instanceid
            classid = item.get("classid", "")
            instanceid = item.get("instanceid", "0")
            
            items.append({
                "assetid": item.get("assetid"),
                "classid": classid,
                "instanceid": instanceid,
                "contextid": item.get("contextid"),
                "amount": item.get("amount", "1"),
                "market_name": "",  # Заполним позже
                "icon_url": "",      # Заполним позже
                "game": game
            })
        
        return items

    def _merge_descriptions(
        self, 
        items: List[Dict[str, Any]], 
        descriptions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Объединение данных предметов с описаниями"""
        # Создаём словарь описаний по ключу classid + instanceid
        desc_dict = {}
        for desc in descriptions:
            key = f"{desc.get('classid', '')}_{desc.get('instanceid', '0')}"
            desc_dict[key] = desc
        
        # Применяем описания к предметам
        for item in items:
            key = f"{item.get('classid', '')}_{item.get('instanceid', '0')}"
            if key in desc_dict:
                desc = desc_dict[key]
                item["market_name"] = desc.get("market_name", "Unknown")
                item["icon_url"] = desc.get("icon_url", "")
                item["market_hash_name"] = desc.get("market_hash_name", "")
                item["type"] = desc.get("type", "")
                item["rarity"] = desc.get("rarity", "")
                item["tags"] = desc.get("tags", [])
            else:
                item["market_name"] = f"Item {item.get('classid', '')}"
                item["icon_url"] = ""
        
        return items

    async def get_player_summary(self, steam_id64: str) -> Optional[Dict[str, Any]]:
        """Получение информации о профиле игрока"""
        try:
            session = await self._get_session()
            
            url = f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"
            params = {
                "key": self.api_key,
                "steamids": steam_id64
            }
            
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                players = data.get("response", {}).get("players", [])
                
                if players:
                    return players[0]
                return None
                
        except Exception as e:
            logger.error(f"Ошибка получения профиля: {e}")
            return None

    async def is_profile_public(self, steam_id64: str) -> bool:
        """Проверка, является ли профиль публичным"""
        try:
            inventory = await self.get_inventory(steam_id64, "cs2")
            return True
        except Exception as e:
            if "Private inventory" in str(e):
                return False
            return False


class InventoryComparator:
    """Класс для сравнения инвентарей"""

    @staticmethod
    def create_item_key(item: Dict[str, Any]) -> str:
        """Создание уникального ключа предмета"""
        return f"{item.get('classid', '')}_{item.get('instanceid', '0')}"

    def compare(
        self, 
        old_inventory: List[Dict[str, Any]], 
        new_inventory: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Сравнение двух снимков инвентаря
        
        Returns:
            (added_items, removed_items)
        """
        # Создаём словари для быстрого поиска
        old_items = {self.create_item_key(item): item for item in old_inventory}
        new_items = {self.create_item_key(item): item for item in new_inventory}
        
        # Находим добавленные предметы
        added = []
        for key, item in new_items.items():
            if key not in old_items:
                item["event_type"] = "ADD"
                added.append(item)
        
        # Находим удалённые предметы
        removed = []
        for key, item in old_items.items():
            if key not in new_items:
                item["event_type"] = "REMOVE"
                removed.append(item)
        
        return added, removed


class RateLimiter:
    """Класс для управления rate limiting"""

    def __init__(self, max_retries: int = 3, base_delay: float = 5.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self._delays: Dict[str, float] = {}

    async def execute_with_retry(self, func, *args, **kwargs):
        """Выполнение функции с retry логикой"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if "Rate limited" in str(e) or "429" in str(e):
                    # Exponential backoff
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(f"Rate limited, ожидание {delay} сек...")
                    await asyncio.sleep(delay)
                else:
                    raise
        
        raise last_exception

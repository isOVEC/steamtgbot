"""
Модуль мониторинга инвентаря Steam
"""

import asyncio
import logging
from typing import Dict, List, Any, Callable, Optional
from datetime import datetime

from steam_api import SteamAPI, InventoryComparator, RateLimiter
from database import Database

logger = logging.getLogger(__name__)


class InventoryMonitor:
    """Класс для мониторинга инвентарей Steam"""

    def __init__(
        self,
        database: Database,
        steam_api: SteamAPI,
        rate_limiter: Optional[RateLimiter] = None
    ):
        self.db = database
        self.steam_api = steam_api
        self.comparator = InventoryComparator()
        self.rate_limiter = rate_limiter or RateLimiter()
        
        self._monitoring_tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        self._notification_callback: Optional[Callable] = None

    def set_notification_callback(self, callback: Callable) -> None:
        """Установка callback для уведомлений"""
        self._notification_callback = callback

    async def start(self) -> None:
        """Запуск мониторинга"""
        self._running = True
        logger.info("Мониторинг запущен")
        
        # Загружаем активные аккаунты
        accounts = await self.db.get_active_accounts()
        
        for account in accounts:
            await self.start_monitoring_account(
                account["steam_id64"],
                account.get("game", "cs2"),
                account.get("interval_minutes", 5)
            )

    async def stop(self) -> None:
        """Остановка мониторинга"""
        self._running = False
        
        # Останавливаем все задачи
        for task in self._monitoring_tasks.values():
            task.cancel()
        
        self._monitoring_tasks.clear()
        logger.info("Мониторинг остановлен")

    async def start_monitoring_account(
        self, 
        steam_id64: str, 
        game: str = "cs2",
        interval_minutes: int = 5
    ) -> None:
        """Запуск мониторинга конкретного аккаунта"""
        if steam_id64 in self._monitoring_tasks:
            logger.warning(f"Мониторинг для {steam_id64} уже запущен")
            return
        
        # Создаём задачу
        task = asyncio.create_task(
            self._monitor_account(steam_id64, game, interval_minutes)
        )
        self._monitoring_tasks[steam_id64] = task
        logger.info(f"Запущен мониторинг для {steam_id64} (интервал: {interval_minutes} мин)")

    async def stop_monitoring_account(self, steam_id64: str) -> None:
        """Остановка мониторинга конкретного аккаунта"""
        if steam_id64 in self._monitoring_tasks:
            self._monitoring_tasks[steam_id64].cancel()
            del self._monitoring_tasks[steam_id64]
            logger.info(f"Остановлен мониторинг для {steam_id64}")

    async def check_inventory(self, steam_id64: str, game: str = "cs2") -> Dict[str, Any]:
        """
        Проверка инвентаря аккаунта
        
        Returns:
            {
                "added": List[Dict],  # Добавленные предметы
                "removed": List[Dict], # Удалённые предметы
                "error": str or None   # Ошибка если есть
            }
        """
        # Получаем старый инвентарь из БД
        old_inventory = await self.db.get_inventory(steam_id64)
        
        try:
            # Получаем новый инвентарь
            if self.rate_limiter:
                new_inventory = await self.rate_limiter.execute_with_retry(
                    self.steam_api.get_inventory, steam_id64, game
                )
            else:
                new_inventory = await self.steam_api.get_inventory(steam_id64, game)
            
            # Сравниваем инвентари
            added, removed = self.comparator.compare(old_inventory, new_inventory)
            
            # Сохраняем новый инвентарь
            await self.db.update_inventory(steam_id64, new_inventory)
            
            # Записываем историю
            for item in added:
                await self.db.add_history_event(
                    steam_id64,
                    item.get("market_name", "Unknown"),
                    "ADD",
                    item.get("assetid"),
                    item.get("classid"),
                    item.get("instanceid"),
                    game
                )
            
            for item in removed:
                await self.db.add_history_event(
                    steam_id64,
                    item.get("market_name", "Unknown"),
                    "REMOVE",
                    item.get("assetid"),
                    item.get("classid"),
                    item.get("instanceid"),
                    game
                )
            
            return {
                "added": added,
                "removed": removed,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Ошибка проверки инвентаря для {steam_id64}: {e}")
            return {
                "added": [],
                "removed": [],
                "error": str(e)
            }

    async def _monitor_account(
        self, 
        steam_id64: str, 
        game: str,
        interval_minutes: int
    ) -> None:
        """Основной цикл мониторинга аккаунта"""
        while self._running and steam_id64 in self._monitoring_tasks:
            try:
                # Проверяем инвентарь
                result = await self.check_inventory(steam_id64, game)
                
                if result["error"]:
                    logger.warning(
                        f"Ошибка мониторинга {steam_id64}: {result['error']}"
                    )
                else:
                    # Отправляем уведомления
                    if self._notification_callback:
                        await self._notification_callback(
                            steam_id64, 
                            result["added"], 
                            result["removed"],
                            game
                        )
                
                # Ждём следующей проверки
                await asyncio.sleep(interval_minutes * 60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга {steam_id64}: {e}")
                # При ошибке ждём перед повторной попыткой
                await asyncio.sleep(60)


async def create_test_inventory(steam_id64: str, game: str = "cs2") -> List[Dict[str, Any]]:
    """Создание тестового инвентаря для демонстрации"""
    return [
        {
            "assetid": "123456789",
            "classid": "150",
            "instanceid": "0",
            "market_name": "AK-47 | Redline",
            "icon_url": "fT9n9nZ5j9N8G7K6",
            "game": game
        },
        {
            "assetid": "123456790",
            "classid": "151",
            "instanceid": "0",
            "market_name": "AWP | Dragon Lore",
            "icon_url": "fT9n9nZ5j9N8G7K7",
            "game": game
        }
    ]

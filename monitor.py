"""
Модуль мониторинга инвентаря Steam
"""

import asyncio
import logging
from typing import Dict, List, Any, Callable, Optional
from datetime import datetime

from steam_api import SteamAPI, InventoryComparator, RateLimiter
from database import Database
from config import CHECK_INTERVAL_MINUTES, MIN_CHECK_INTERVAL, MAX_CHECK_INTERVAL

logger = logging.getLogger(__name__)


class InventoryMonitor:
    """Класс для мониторинга инвентарей Steam"""

    def __init__(
        self,
        database: Database,
        steam_api: SteamAPI,
        rate_limiter: Optional[RateLimiter] = None,
        check_interval_minutes: Optional[int] = None
    ):
        self.db = database
        self.steam_api = steam_api
        self.comparator = InventoryComparator()
        self.rate_limiter = rate_limiter or RateLimiter()
        
        # Интервал проверки (с проверкой границ)
        if check_interval_minutes is not None:
            self.check_interval = max(MIN_CHECK_INTERVAL, min(MAX_CHECK_INTERVAL, check_interval_minutes))
        else:
            self.check_interval = CHECK_INTERVAL_MINUTES
        
        self._monitoring_tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        self._notification_callback: Optional[Callable] = None
        self._accounts_to_monitor: Dict[str, Dict[str, Any]] = {}  # steam_id64 -> {game, interval, ...}

    def set_notification_callback(self, callback: Callable) -> None:
        """Установка callback для уведомлений"""
        self._notification_callback = callback

    async def start(self) -> None:
        """Запуск мониторинга"""
        self._running = True
        logger.info(f"Мониторинг запущен (интервал проверки: {self.check_interval} минут)")
        
        # Загружаем активные аккаунты
        accounts = await self.db.get_active_accounts()
        
        for account in accounts:
            steam_id64 = account["steam_id64"]
            game = account.get("game", "cs2")
            # Запускаем индивидуальную задачу для каждого аккаунта
            await self.start_monitoring_account(steam_id64, game)

    async def stop(self) -> None:
        """Остановка мониторинга"""
        self._running = False
        
        # Останавливаем все задачи мониторинга
        for steam_id64, task in list(self._monitoring_tasks.items()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self._monitoring_tasks.clear()
        self._accounts_to_monitor.clear()
        logger.info("Мониторинг остановлен")

    async def start_monitoring_account(
        self, 
        steam_id64: str, 
        game: str = "cs2",
        interval_minutes: Optional[int] = None
    ) -> None:
        """Добавление аккаунта в мониторинг"""
        if steam_id64 in self._monitoring_tasks:
            logger.warning(f"Аккаунт {steam_id64} уже в мониторинге")
            return
        
        # Используем переданный интервал или глобальный
        interval = interval_minutes or self.check_interval
        interval = max(MIN_CHECK_INTERVAL, min(MAX_CHECK_INTERVAL, interval))
        
        self._accounts_to_monitor[steam_id64] = {
            "game": game,
            "interval": interval
        }
        
        # Создаём задачу мониторинга для этого аккаунта
        task = asyncio.create_task(
            self._monitor_account_loop(steam_id64, game, interval),
            name=f"monitor_{steam_id64}"
        )
        self._monitoring_tasks[steam_id64] = task
        
        logger.info(f"Аккаунт {steam_id64} добавлен в мониторинг (интервал: {interval} мин)")

    async def stop_monitoring_account(self, steam_id64: str) -> None:
        """Удаление аккаунта из мониторинга"""
        if steam_id64 in self._monitoring_tasks:
            self._monitoring_tasks[steam_id64].cancel()
            try:
                await self._monitoring_tasks[steam_id64]
            except asyncio.CancelledError:
                pass
            del self._monitoring_tasks[steam_id64]
        
        if steam_id64 in self._accounts_to_monitor:
            del self._accounts_to_monitor[steam_id64]
        
        logger.info(f"Аккаунт {steam_id64} удалён из мониторинга")

    async def _monitor_account_loop(
        self, 
        steam_id64: str, 
        game: str, 
        interval_minutes: int
    ) -> None:
        """
        Цикл мониторинга отдельного аккаунта
        
        Args:
            steam_id64: Steam ID64 аккаунта
            game: Игра для мониторинга
            interval_minutes: Интервал проверки в минутах
        """
        interval_seconds = interval_minutes * 60
        
        # Небольшая начальная задержка для распределения нагрузки
        # (чтобы не проверять все аккаунты одновременно)
        await asyncio.sleep(5)
        
        while self._running and steam_id64 in self._accounts_to_monitor:
            try:
                logger.debug(f"Проверка аккаунта {steam_id64} (интервал: {interval_minutes} мин)")
                
                result = await self.check_inventory(steam_id64, game)
                
                if result["error"]:
                    logger.warning(f"Ошибка проверки {steam_id64}: {result['error']}")
                else:
                    # Отправляем уведомление только если есть изменения
                    if (result["added"] or result["removed"]) and self._notification_callback:
                        await self._notification_callback(
                            steam_id64, 
                            result["added"], 
                            result["removed"],
                            game
                        )
                
                # Ждём до следующей проверки
                await asyncio.sleep(interval_seconds)
                
            except asyncio.CancelledError:
                logger.debug(f"Мониторинг аккаунта {steam_id64} остановлен")
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга {steam_id64}: {e}")
                # При ошибке ждём минуту перед повторной попыткой
                await asyncio.sleep(60)

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

    def get_monitoring_status(self) -> Dict[str, Any]:
        """Получение статуса мониторинга"""
        return {
            "running": self._running,
            "check_interval_minutes": self.check_interval,
            "accounts_count": len(self._accounts_to_monitor),
            "accounts": {
                steam_id: {
                    "game": info["game"],
                    "interval": info["interval"]
                }
                for steam_id, info in self._accounts_to_monitor.items()
            }
        }


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

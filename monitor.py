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
        
        self._running = False
        self._main_task: Optional[asyncio.Task] = None
        self._notification_callback: Optional[Callable] = None
        self._dashboard_callback: Optional[Callable] = None
        self._accounts_to_monitor: Dict[str, Dict[str, Any]] = {}
        self._last_dashboard_results: List[Dict] = []

    def set_notification_callback(self, callback: Callable) -> None:
        """Установка callback для уведомлений"""
        self._notification_callback = callback

    async def start(self) -> None:
        """Запуск основного цикла мониторинга"""
        if self._running:
            logger.warning("Мониторинг уже запущен.")
            return

        self._running = True
        self._main_task = asyncio.create_task(self._main_monitoring_loop())
        logger.info("Основной цикл мониторинга запущен.")

    async def stop(self) -> None:
        """Остановка основного цикла мониторинга"""
        if not self._running or not self._main_task:
            logger.warning("Мониторинг не запущен.")
            return

        self._running = False
        self._main_task.cancel()
        try:
            await self._main_task
        except asyncio.CancelledError:
            logger.info("Основной цикл мониторинга успешно остановлен.")
        
        self._accounts_to_monitor.clear()
        self._main_task = None

    def get_last_dashboard_results(self) -> List[Dict]:
        """Возвращает результаты последнего завершенного цикла проверок."""
        return self._last_dashboard_results

    async def initial_check(self) -> None:
        """Выполняет первоначальную проверку всех аккаунтов при запуске."""
        logger.info("Начало первоначальной проверки всех аккаунтов...")
        accounts = list(self._accounts_to_monitor.keys())
        if not accounts:
            logger.info("Нет аккаунтов для первоначальной проверки.")
            return

        dashboard_results = []
        for steam_id64 in accounts:
            account_info = self._accounts_to_monitor.get(steam_id64)
            if not account_info:
                continue

            game = account_info.get("game", "cs2")
            result = await self.check_inventory(steam_id64, game)
            dashboard_results.append({"steam_id": steam_id64, "game": game, **result})
            # Небольшая задержка между запросами, чтобы не перегружать API
            await asyncio.sleep(1)

        self._last_dashboard_results = dashboard_results
        logger.info("Первоначальная проверка всех аккаунтов завершена.")



    async def _main_monitoring_loop(self) -> None:
        """Главный цикл, который управляет проверками всех аккаунтов."""
        logger.info("Главный цикл мониторинга начал работу.")
        while self._running:
            try:
                accounts = list(self._accounts_to_monitor.keys())
                if not accounts:
                    await asyncio.sleep(5)  # Ждем, если нет аккаунтов
                    continue

                dashboard_results = []
                # Глобальный интервал используется как базовый
                interval_seconds = self.check_interval * 60
                
                # Вычисляем "шаг лесенки"
                step_delay = interval_seconds / len(accounts)
                step_delay = max(1, step_delay) # Не менее 1 секунды

                logger.info(f"Начинается новый цикл проверки для {len(accounts)} аккаунтов. "
                            f"Общий интервал: {self.check_interval} мин, шаг: {step_delay:.2f} сек.")

                for steam_id64 in accounts:
                    if not self._running:
                        break
                    
                    account_info = self._accounts_to_monitor.get(steam_id64)
                    if not account_info:
                        continue

                    game = account_info.get("game", "cs2")
                    logger.debug(f"Проверка аккаунта: {steam_id64}")
                    
                    result = await self.check_inventory(steam_id64, game)
                    dashboard_results.append({"steam_id": steam_id64, "game": game, **result})

                    # Отправляем мгновенное уведомление, если есть изменения
                    if (result["added"] or result["removed"]) and self._notification_callback:
                        await self._notification_callback(
                            steam_id64,
                            result["added"],
                            result["removed"],
                            game
                        )
                    
                    await asyncio.sleep(step_delay)

                # Отправка дэшборда после завершения цикла
                if self._running and self._dashboard_callback:
                    await self._dashboard_callback(dashboard_results)
                
                logger.info("Цикл проверки завершен.")

            except asyncio.CancelledError:
                logger.info("Главный цикл мониторинга был прерван.")
                break
            except Exception as e:
                logger.error(f"Критическая ошибка в главном цикле мониторинга: {e}", exc_info=True)
                await asyncio.sleep(60) # Пауза перед перезапуском цикла в случае ошибки

    def set_dashboard_callback(self, callback: Callable) -> None:
        """Установка callback для дэшборда."""
        self._dashboard_callback = callback

    async def start_monitoring_account(
        self, 
        steam_id64: str, 
        game: str = "cs2",
        interval_minutes: Optional[int] = None
    ) -> None:
        """Добавление аккаунта в мониторинг."""
        if steam_id64 in self._accounts_to_monitor:
            logger.warning(f"Аккаунт {steam_id64} уже отслеживается.")
            return

        interval = interval_minutes or self.check_interval
        self._accounts_to_monitor[steam_id64] = {
            "game": game,
            "interval": interval
        }
        logger.info(f"Аккаунт {steam_id64} добавлен в список мониторинга.")

    async def stop_monitoring_account(self, steam_id64: str) -> None:
        """Удаление аккаунта из мониторинга."""
        if steam_id64 in self._accounts_to_monitor:
            del self._accounts_to_monitor[steam_id64]
            logger.info(f"Аккаунт {steam_id64} удален из списка мониторинга.")
        else:
            logger.warning(f"Попытка удалить несуществующий аккаунт {steam_id64} из мониторинга.")

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
            
            logger.info(f"Сбор инвентаря для {steam_id64} (игра: {game}) завершен. Найдено {len(new_inventory)} предметов.")
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
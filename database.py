"""
Модуль базы данных для Steam Inventory Monitor Bot
"""

import aiosqlite
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с SQLite базой данных"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._connection: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        """Установка соединения с БД"""
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._create_tables()
        logger.info("База данных подключена")

    async def close(self) -> None:
        """Закрытие соединения с БД"""
        if self._connection:
            await self._connection.close()
            logger.info("База данных отключена")

    async def _create_tables(self) -> None:
        """Создание таблиц в БД"""
        async with self._connection.cursor() as cursor:
            # Таблица целевых аккаунтов для мониторинга
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS target_accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    steam_id64 TEXT UNIQUE NOT NULL,
                    interval_minutes INTEGER DEFAULT 5,
                    is_active INTEGER DEFAULT 1,
                    game TEXT DEFAULT 'cs2',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Таблица текущего состояния инвентаря
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS current_inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    steam_id64 TEXT NOT NULL,
                    assetid TEXT NOT NULL,
                    classid TEXT,
                    instanceid TEXT,
                    market_name TEXT,
                    icon_url TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(steam_id64, assetid)
                )
            """)

            # Таблица истории изменений инвентаря
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS inventory_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    steam_id64 TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    assetid TEXT,
                    classid TEXT,
                    instanceid TEXT,
                    event_type TEXT NOT NULL,
                    game TEXT DEFAULT 'cs2',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Таблица пользователей Telegram
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS telegram_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    is_admin INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Таблица настроек
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            await self._connection.commit()
            logger.info("Таблицы БД созданы")

    # === Работа с целевыми аккаунтами ===

    async def add_target_account(self, steam_id64: str, interval_minutes: int = 5, 
                                   game: str = "cs2") -> bool:
        """Добавление аккаунта для мониторинга"""
        try:
            async with self._connection.cursor() as cursor:
                await cursor.execute("""
                    INSERT OR REPLACE INTO target_accounts 
                    (steam_id64, interval_minutes, is_active, game)
                    VALUES (?, ?, 1, ?)
                """, (steam_id64, interval_minutes, game))
                await self._connection.commit()
                logger.info(f"Добавлен аккаунт {steam_id64} для мониторинга")
                return True
        except Exception as e:
            logger.error(f"Ошибка добавления аккаунта: {e}")
            return False

    async def remove_target_account(self, steam_id64: str) -> bool:
        """Удаление аккаунта из мониторинга"""
        try:
            async with self._connection.cursor() as cursor:
                await cursor.execute("""
                    DELETE FROM target_accounts WHERE steam_id64 = ?
                """, (steam_id64,))
                await cursor.execute("""
                    DELETE FROM current_inventory WHERE steam_id64 = ?
                """, (steam_id64,))
                await self._connection.commit()
                logger.info(f"Удален аккаунт {steam_id64} из мониторинга")
                return True
        except Exception as e:
            logger.error(f"Ошибка удаления аккаунта: {e}")
            return False

    async def get_target_accounts(self) -> List[Dict[str, Any]]:
        """Получение списка целевых аккаунтов"""
        async with self._connection.cursor() as cursor:
            cursor.execute("""
                SELECT steam_id64, interval_minutes, is_active, game, created_at
                FROM target_accounts ORDER BY created_at DESC
            """)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_active_accounts(self) -> List[Dict[str, Any]]:
        """Получение списка активных аккаунтов"""
        async with self._connection.cursor() as cursor:
            cursor.execute("""
                SELECT steam_id64, interval_minutes, game
                FROM target_accounts WHERE is_active = 1
            """)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def set_account_active(self, steam_id64: str, is_active: bool) -> bool:
        """Установка статуса аккаунта"""
        try:
            async with self._connection.cursor() as cursor:
                await cursor.execute("""
                    UPDATE target_accounts SET is_active = ? WHERE steam_id64 = ?
                """, (1 if is_active else 0, steam_id64))
                await self._connection.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка изменения статуса: {e}")
            return False

    async def update_interval(self, steam_id64: str, interval_minutes: int) -> bool:
        """Обновление интервала проверки"""
        try:
            async with self._connection.cursor() as cursor:
                await cursor.execute("""
                    UPDATE target_accounts SET interval_minutes = ? WHERE steam_id64 = ?
                """, (interval_minutes, steam_id64))
                await self._connection.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка обновления интервала: {e}")
            return False

    # === Работа с инвентарём ===

    async def update_inventory(self, steam_id64: str, items: List[Dict[str, Any]]) -> None:
        """Обновление текущего состояния инвентаря"""
        async with self._connection.cursor() as cursor:
            # Удаляем старые записи
            await cursor.execute("""
                DELETE FROM current_inventory WHERE steam_id64 = ?
            """, (steam_id64,))

            # Вставляем новые
            for item in items:
                await cursor.execute("""
                    INSERT INTO current_inventory 
                    (steam_id64, assetid, classid, instanceid, market_name, icon_url)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    steam_id64,
                    item.get('assetid'),
                    item.get('classid'),
                    item.get('instanceid'),
                    item.get('market_name'),
                    item.get('icon_url')
                ))

            await self._connection.commit()

    async def get_inventory(self, steam_id64: str) -> List[Dict[str, Any]]:
        """Получение текущего состояния инвентаря"""
        async with self._connection.cursor() as cursor:
            cursor.execute("""
                SELECT assetid, classid, instanceid, market_name, icon_url
                FROM current_inventory WHERE steam_id64 = ?
            """, (steam_id64,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def add_history_event(self, steam_id64: str, item_name: str, 
                                 event_type: str, assetid: str = None,
                                 classid: str = None, instanceid: str = None,
                                 game: str = "cs2") -> None:
        """Добавление события в историю"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO inventory_history 
                (steam_id64, item_name, assetid, classid, instanceid, event_type, game)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (steam_id64, item_name, assetid, classid, instanceid, event_type, game))
            await self._connection.commit()

    async def get_recent_history(self, steam_id64: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение последних изменений инвентаря"""
        async with self._connection.cursor() as cursor:
            cursor.execute("""
                SELECT item_name, event_type, game, timestamp
                FROM inventory_history 
                WHERE steam_id64 = ?
                ORDER BY timestamp DESC LIMIT ?
            """, (steam_id64, limit))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # === Работа с пользователями Telegram ===

    async def add_user(self, chat_id: int, username: str = None, 
                       first_name: str = None) -> None:
        """Добавление пользователя"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                INSERT OR REPLACE INTO telegram_users 
                (chat_id, username, first_name)
                VALUES (?, ?, ?)
            """, (chat_id, username, first_name))
            await self._connection.commit()

    async def get_admins(self) -> List[int]:
        """Получение списка администраторов"""
        async with self._connection.cursor() as cursor:
            cursor.execute("SELECT chat_id FROM telegram_users WHERE is_admin = 1")
            rows = await cursor.fetchall()
            return [row['chat_id'] for row in rows]

    # === Настройки ===

    async def get_setting(self, key: str) -> Optional[str]:
        """Получение настройки"""
        async with self._connection.cursor() as cursor:
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = await cursor.fetchone()
            return row['value'] if row else None

    async def set_setting(self, key: str, value: str) -> None:
        """Установка настройки"""
        async with self._connection.cursor() as cursor:
            await cursor.execute("""
                INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
            """, (key, value))
            await self._connection.commit()

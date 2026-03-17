"""
Telegram бот для мониторинга Steam инвентаря
"""

import asyncio
import logging
import re
from typing import Optional

from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    constants
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

from database import Database
from steam_api import SteamAPI, RateLimiter
from monitor import InventoryMonitor
from config import (
    TELEGRAM_BOT_TOKEN,
    STEAM_API_KEY,
    DATABASE_PATH,
    DEFAULT_INTERVAL,
    MIN_INTERVAL,
    MAX_INTERVAL,
    PROXY_ENABLED,
    PROXY_URL
)

logger = logging.getLogger(__name__)


class SteamMonitorBot:
    """Класс Telegram бота для мониторинга Steam инвентаря"""

    def __init__(self):
        self.db: Optional[Database] = None
        self.steam_api: Optional[SteamAPI] = None
        self.monitor: Optional[InventoryMonitor] = None
        self.app: Optional[Application] = None
        
    async def initialize(self) -> None:
        """Инициализация бота"""
        # Инициализация базы данных
        self.db = Database(DATABASE_PATH)
        await self.db.connect()
        
        # Инициализация Steam API
        proxy = PROXY_URL if PROXY_ENABLED else None
        self.steam_api = SteamAPI(STEAM_API_KEY, proxy)
        
        # Инициализация монитора
        rate_limiter = RateLimiter()
        self.monitor = InventoryMonitor(self.db, self.steam_api, rate_limiter)
        
        # Установка callback для уведомлений
        self.monitor.set_notification_callback(self.send_inventory_update)
        
        # Запуск мониторинга
        await self.monitor.start()
        
        logger.info("Бот инициализирован")

    async def shutdown(self) -> None:
        """Выключение бота"""
        if self.monitor:
            await self.monitor.stop()
        if self.steam_api:
            await self.steam_api.close()
        if self.db:
            await self.db.close()
        logger.info("Бот выключен")

    async def send_inventory_update(
        self,
        steam_id64: str,
        added: list,
        removed: list,
        game: str
    ) -> None:
        """Отправка уведомления об изменении инвентаря"""
        if not added and not removed:
            return
        
        # Получаем всех админов
        admins = await self.db.get_admins()
        
        if not admins:
            return
        
        text = ""
        
        # Формируем сообщение о добавленных предметах
        if added:
            text += "🟢 <b>Добавлены предметы:</b>\n"
            for item in added[:10]:  # Ограничиваем до 10 предметов
                name = item.get("market_name", "Unknown")
                text += f"• {name}\n"
            if len(added) > 10:
                text += f"... и ещё {len(added) - 10}\n"
            text += "\n"
        
        # Формируем сообщение об удалённых предметах
        if removed:
            text += "🔴 <b>Удалены предметы:</b>\n"
            for item in removed[:10]:
                name = item.get("market_name", "Unknown")
                text += f"• {name}\n"
            if len(removed) > 10:
                text += f"... и ещё {len(removed) - 10}\n"
        
        text += f"\n<i>Аккаунт: {steam_id64}</i>"
        
        # Отправляем всем админам
        for chat_id in admins:
            try:
                await self.app.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=constants.ParseMode.HTML
                )
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления: {e}")

    def run(self) -> None:
        """Запуск бота"""
        # Создаём приложение
        self.app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Регистрируем обработчики команд
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("add", self.add_command))
        self.app.add_handler(CommandHandler("remove", self.remove_command))
        self.app.add_handler(CommandHandler("list", self.list_command))
        self.app.add_handler(CommandHandler("set_interval", self.set_interval_command))
        self.app.add_handler(CommandHandler("status", self.status_command))
        self.app.add_handler(CommandHandler("check", self.check_command))
        self.app.add_handler(CommandHandler("history", self.history_command))
        
        # Обработчик ошибок
        self.app.add_error_handler(self.error_handler)
        
        # Запуск бота
        logger.info("Запуск бота...")
        self.app.run_polling(drop_pending_updates=True)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /start"""
        user = update.effective_user
        
        # Сохраняем пользователя
        await self.db.add_user(
            user.id,
            user.username,
            user.first_name
        )
        
        text = f"""
👋 Привет, {user.first_name}!

Я бот для мониторинга Steam инвентаря.

📋 <b>Доступные команды:</b>
/add [steamid] - Добавить аккаунт
/remove [steamid] - Удалить аккаунт
/list - Список отслеживаемых аккаунтов
/set_interval [минуты] - Изменить интервал
/check [steamid] - Проверить инвентарь сейчас
/history [steamid] - История изменений
/status - Статус мониторинга
/help - Помощь

🔗 Для добавления аккаунта используйте SteamID64
"""
        
        await update.message.reply_text(text, parse_mode=constants.ParseMode.HTML)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /help"""
        text = """
🔧 <b>Помощь по боту</b>

<b>Как добавить аккаунт:</b>
Используйте команду /add и SteamID64 аккаунта
Пример: /add 76561198000000000

<b>Как узнать SteamID64:</b>
1. Откройте профиль в Steam
2. Скопируйте ссылку из адресной строки
3. Используйте https://steamcommunity.com/id/[ваш_ид] -> https://steamcommunity.com/profiles/[steamid64]

<b>Поддерживаемые игры:</b>
- CS2 (CS:GO)
- Dota 2
- TF2

<b>Интервал проверки:</b>
Минимум 1 минута, максимус 60 минут
"""
        
        await update.message.reply_text(text, parse_mode=constants.ParseMode.HTML)

    async def add_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /add"""
        if not context.args:
            await update.message.reply_text(
                "❌ Укажите SteamID64\n"
                "Пример: /add 76561198000000000"
            )
            return
        
        steam_id = context.args[0]
        
        # Валидация SteamID
        if not self._validate_steam_id(steam_id):
            await update.message.reply_text(
                "❌ Неверный формат SteamID64\n"
                "SteamID64 должен содержать 17 цифр"
            )
            return
        
        # Добавляем аккаунт
        success = await self.db.add_target_account(steam_id, DEFAULT_INTERVAL)
        
        if success:
            # Запускаем мониторинг
            await self.monitor.start_monitoring_account(steam_id, "cs2", DEFAULT_INTERVAL)
            
            await update.message.reply_text(
                f"✅ Аккаунт {steam_id} добавлен для мониторинга\n"
                f"Интервал проверки: {DEFAULT_INTERVAL} минут"
            )
        else:
            await update.message.reply_text(
                f"❌ Не удалось добавить аккаунт {steam_id}"
            )

    async def remove_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /remove"""
        if not context.args:
            await update.message.reply_text(
                "❌ Укажите SteamID64\n"
                "Пример: /remove 76561198000000000"
            )
            return
        
        steam_id = context.args[0]
        
        # Останавливаем мониторинг
        await self.monitor.stop_monitoring_account(steam_id)
        
        # Удаляем из БД
        success = await self.db.remove_target_account(steam_id)
        
        if success:
            await update.message.reply_text(
                f"✅ Аккаунт {steam_id} удалён из мониторинга"
            )
        else:
            await update.message.reply_text(
                f"❌ Не удалось удалить аккаунт {steam_id}"
            )

    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /list"""
        accounts = await self.db.get_target_accounts()
        
        if not accounts:
            await update.message.reply_text(
                "📭 Нет аккаунтов для мониторинга"
            )
            return
        
        text = "📋 <b>Отслеживаемые аккаунты:</b>\n\n"
        
        keyboard = []
        
        for account in accounts:
            steam_id = account["steam_id64"]
            interval = account["interval_minutes"]
            active = account["is_active"]
            
            status = "🟢" if active else "🔴"
            text += f"{status} <a href='https://steamcommunity.com/profiles/{steam_id}'>{steam_id}</a>\n"
            text += f"   Интервал: {interval} мин\n\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"📦 Инвентарь {steam_id[:8]}...", 
                    url=f"https://steamcommunity.com/profiles/{steam_id}/inventory/"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            text, 
            parse_mode=constants.ParseMode.HTML,
            reply_markup=reply_markup
        )

    async def set_interval_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /set_interval"""
        if not context.args:
            await update.message.reply_text(
                f"❌ Укажите интервал в минутах ({MIN_INTERVAL}-{MAX_INTERVAL})\n"
                f"Пример: /set_interval 5"
            )
            return
        
        try:
            interval = int(context.args[0])
            
            if interval < MIN_INTERVAL or interval > MAX_INTERVAL:
                await update.message.reply_text(
                    f"❌ Интервал должен быть от {MIN_INTERVAL} до {MAX_INTERVAL} минут"
                )
                return
            
            # Обновляем все аккаунты
            accounts = await self.db.get_target_accounts()
            
            for account in accounts:
                await self.db.update_interval(account["steam_id64"], interval)
                await self.monitor.stop_monitoring_account(account["steam_id64"])
                await self.monitor.start_monitoring_account(
                    account["steam_id64"], 
                    account.get("game", "cs2"),
                    interval
                )
            
            await update.message.reply_text(
                f"✅ Интервал проверки изменён на {interval} минут"
            )
            
        except ValueError:
            await update.message.reply_text(
                "❌ Укажите число"
            )

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /status"""
        accounts = await self.db.get_target_accounts()
        active_count = sum(1 for a in accounts if a["is_active"])
        
        text = f"""
📊 <b>Статус мониторинга</b>

Аккаунтов: {len(accounts)}
Активных: {active_count}
Мониторинг: {'🔴 Остановлен' if not self.monitor._running else '🟢 Запущен'}
"""
        
        await update.message.reply_text(text, parse_mode=constants.ParseMode.HTML)

    async def check_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /check"""
        if not context.args:
            await update.message.reply_text(
                "❌ Укажите SteamID64\n"
                "Пример: /check 76561198000000000"
            )
            return
        
        steam_id = context.args[0]
        
        await update.message.reply_text("⏳ Проверяю инвентарь...")
        
        try:
            result = await self.monitor.check_inventory(steam_id, "cs2")
            
            if result["error"]:
                await update.message.reply_text(
                    f"❌ Ошибка: {result['error']}"
                )
                return
            
            text = f"📦 Проверка инвентаря для {steam_id}:\n\n"
            
            if result["added"]:
                text += "🟢 <b>Добавлено:</b>\n"
                for item in result["added"]:
                    text += f"• {item.get('market_name', 'Unknown')}\n"
            
            if result["removed"]:
                text += "\n🔴 <b>Удалено:</b>\n"
                for item in result["removed"]:
                    text += f"• {item.get('market_name', 'Unknown')}\n"
            
            if not result["added"] and not result["removed"]:
                text += "Изменений нет"
            
            await update.message.reply_text(
                text, 
                parse_mode=constants.ParseMode.HTML
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")

    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /history"""
        if not context.args:
            await update.message.reply_text(
                "❌ Укажите SteamID64\n"
                "Пример: /history 76561198000000000"
            )
            return
        
        steam_id = context.args[0]
        
        history = await self.db.get_recent_history(steam_id)
        
        if not history:
            await update.message.reply_text(
                f"📭 Нет истории для {steam_id}"
            )
            return
        
        text = f"📜 История для {steam_id}:\n\n"
        
        for event in history[:10]:
            icon = "🟢" if event["event_type"] == "ADD" else "🔴"
            name = event["item_name"]
            timestamp = event["timestamp"]
            text += f"{icon} {name} - {timestamp}\n"
        
        await update.message.reply_text(text)

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик ошибок"""
        logger.error(f"Ошибка: {context.error}")

    @staticmethod
    def _validate_steam_id(steam_id: str) -> bool:
        """Валидация SteamID64"""
        # Проверяем, что это 17-значное число
        pattern = r'^\d{17}$'
        return bool(re.match(pattern, steam_id))


# Глобальный экземпляр бота
bot: Optional[SteamMonitorBot] = None


async def main():
    """Главная функция"""
    global bot
    
    # Создаём и инициализируем бота
    bot = SteamMonitorBot()
    
    try:
        await bot.initialize()
        bot.run()
    except KeyboardInterrupt:
        pass
    finally:
        await bot.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

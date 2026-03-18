"""
Telegram бот для мониторинга Steam инвентаря
"""

import asyncio
import logging
import re
from typing import Optional
from datetime import datetime

from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    BotCommand,
    constants
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from telegram.request import HTTPXRequest

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
        
        # Установка callback для уведомлений и дэшборда
        self.monitor.set_notification_callback(self.send_inventory_update)
        self.monitor.set_dashboard_callback(self.send_dashboard_summary)
        
        # Инициализация Telegram Application
        builder = Application.builder().token(TELEGRAM_BOT_TOKEN)

        if PROXY_ENABLED and PROXY_URL:
            logger.info(f"Использование прокси для Telegram: {PROXY_URL}")
            request = HTTPXRequest(proxy_url=PROXY_URL)
            builder.request(request)
            builder.get_updates_request(request)

        self.app = builder.build()
        
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
        self.app.add_handler(CommandHandler("proxy", self.proxy_command))
        self.app.add_handler(CommandHandler("dashboard", self.dashboard_command))

        # Обработчик callback (inline кнопки)
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Обработчик ошибок
        self.app.add_error_handler(self.error_handler)
        
        # Установка меню команд
        await self._setup_commands()

        # Загружаем активные аккаунты из БД и добавляем в монитор
        accounts = await self.db.get_active_accounts()
        for account in accounts:
            await self.monitor.start_monitoring_account(
                account["steam_id64"],
                account.get("game", "cs2"),
                account.get("interval_minutes")
            )

        # Выполняем первоначальную проверку
        await self.monitor.initial_check()
        
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

    async def send_startup_notification(self, accounts: list) -> None:
        """Отправка уведомления о запуске бота и текущем статусе."""
        admins = await self.db.get_admins()
        if not admins:
            return

        text = f"🚀 <b>Бот запущен!</b>\n\n"
        text += f"Отслеживается аккаунтов: {len(accounts)}\n"
        if accounts:
            text += "\n<b>Список аккаунтов:</b>\n"
            for acc in accounts:
                steam_id = acc["steam_id64"]
                interval = acc.get("interval_minutes", self.monitor.check_interval)
                text += f"- <a href='https://steamcommunity.com/profiles/{steam_id}'>{steam_id}</a> (интервал: {interval} мин)\n"
        
        for chat_id in admins:
            try:
                await self.app.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=constants.ParseMode.HTML,
                    disable_web_page_preview=True
                )
            except Exception as e:
                logger.error(f"Ошибка отправки стартового уведомления: {e}")

    async def send_dashboard_summary(self, results: list) -> None:
        """Отправка сводного отчета (дэшборда) по всем аккаунтам."""
        admins = await self.db.get_admins()
        if not admins:
            return

        summary_parts = []
        has_changes = False

        for result in results:
            steam_id = result["steam_id"]
            profile_url = f"https://steamcommunity.com/profiles/{steam_id}"
            part = f"👤 <a href='{profile_url}'>{steam_id}</a>:"

            if result["error"]:
                part += f" ❌ Ошибка: {result['error']}"
                has_changes = True # Считаем ошибку изменением для отправки
            elif not result["added"] and not result["removed"]:
                part += " ✅ Изменений нет"
            else:
                has_changes = True
                if result["added"]:
                    part += f" 🟢 {len(result['added'])} доб."
                if result["removed"]:
                    part += f" 🔴 {len(result['removed'])} уб."
            
            summary_parts.append(part)

        # Отправляем дэшборд, только если были изменения или ошибки
        if has_changes:
            header = f"📊 <b>Сводка за {datetime.now().strftime('%H:%M')}</b> 📊\n\n"
            full_message = header + "\n".join(summary_parts)
            
            for chat_id in admins:
                try:
                    await self.app.bot.send_message(
                        chat_id=chat_id,
                        text=full_message,
                        parse_mode=constants.ParseMode.HTML,
                        disable_web_page_preview=True
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки дэшборда: {e}")
        else:
            logger.info("Дэшборд не отправлен, так как не было изменений.")

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
        
        # Формируем ссылку на профиль и инвентарь
        profile_url = f"https://steamcommunity.com/profiles/{steam_id64}"
        inventory_url = f"{profile_url}/inventory/"
        
        # Заголовок с информацией об аккаунте
        game_names = {
            "cs2": "CS2",
            "csgo": "CS2",
            "dota2": "Dota 2",
            "tf2": "Team Fortress 2"
        }
        game_name = game_names.get(game.lower(), game.upper())
        
        text = f"📊 <b>Изменения в инвентаре</b>\n\n"
        text += f"👤 <b>Аккаунт:</b> <a href='{profile_url}'>{steam_id64}</a>\n"
        text += f"🎮 <b>Игра:</b> {game_name}\n"
        text += f"📅 <b>Дата проверки:</b> {__import__('datetime').datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        text += "─" * 25 + "\n\n"
        
        # Формируем сообщение о добавленных предметах
        if added:
            text += f"🟢 <b>Добавлено ({len(added)}):</b>\n"
            for i, item in enumerate(added[:15], 1):  # Ограничиваем до 15 предметов
                name = item.get("market_name", "Unknown")
                text += f"{i}. {name}\n"
            if len(added) > 15:
                text += f"   ... и ещё {len(added) - 15} предметов\n"
            text += "\n"
        
        # Формируем сообщение об удалённых предметах
        if removed:
            text += f"🔴 <b>Удалено ({len(removed)}):</b>\n"
            for i, item in enumerate(removed[:15], 1):
                name = item.get("market_name", "Unknown")
                text += f"{i}. {name}\n"
            if len(removed) > 15:
                text += f"   ... и ещё {len(removed) - 15} предметов\n"
            text += "\n"
        
        text += f"<a href='{inventory_url}'>🔗 Открыть инвентарь</a>"
        
        # Отправляем всем админам
        for chat_id in admins:
            try:
                await self.app.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=constants.ParseMode.HTML,
                    disable_web_page_preview=True
                )
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления: {e}")

    def run(self) -> None:
        """Запуск бота (синхронный метод для обратной совместимости)"""
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
/dashboard - 📊 Ручной вызов сводки
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
        logger.info(f"[DEBUG] add_command вызван с args: {context.args}")
        
        if not context.args:
            await update.message.reply_text(
                "❌ Укажите SteamID64\n"
                "Пример: /add 76561198000000000"
            )
            return
        
        steam_id = context.args[0]
        logger.info(f"[DEBUG] Попытка добавить аккаунт: {steam_id}")
        
        # Валидация SteamID
        if not self._validate_steam_id(steam_id):
            await update.message.reply_text(
                "❌ Неверный формат SteamID64\n"
                "SteamID64 должен содержать 17 цифр"
            )
            return
        
        # Добавляем аккаунт
        logger.info(f"[DEBUG] Вызов db.add_target_account для {steam_id}")
        success = await self.db.add_target_account(steam_id, DEFAULT_INTERVAL)
        logger.info(f"[DEBUG] db.add_target_account вернул: {success}")
        
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
            # Показываем список аккаунтов для выбора
            accounts = await self.db.get_target_accounts()
            
            if not accounts:
                await update.message.reply_text(
                    "📭 Нет отслеживаемых аккаунтов\n"
                    "Добавьте аккаунт: /add <SteamID64>"
                )
                return
            
            # Создаем inline кнопки для каждого аккаунта
            keyboard = []
            for account in accounts:
                steam_id = account["steam_id64"]
                keyboard.append([
                    InlineKeyboardButton(
                        f"📦 {steam_id}",
                        callback_data=f"history:{steam_id}"
                    )
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "📜 Выберите аккаунт для просмотра истории:",
                reply_markup=reply_markup
            )
            return
        
        steam_id = context.args[0]
        await self._show_history(update, context, steam_id, update.message)

    async def proxy_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /proxy"""
        if not context.args:
            # Показать текущий статус прокси
            from config import PROXY_ENABLED, PROXY_URL
            status = "🔴 Выключен" if not PROXY_ENABLED else "🟢 Включен"
            await update.message.reply_text(
                f"🌐 <b>Статус прокси:</b> {status}\n"
                f"URL: <code>{PROXY_URL}</code>\n\n"
                f"<b>Команды:</b>\n"
                f"/proxy on - Включить прокси\n"
                f"/proxy off - Выключить прокси\n"
                f"/proxy set [url] - Установить URL прокси\n\n"
                f"<i>Примечание: Изменения требуют перезапуска бота</i>",
                parse_mode=constants.ParseMode.HTML
            )
            return
        
        action = context.args[0].lower()
        
        if action == "on":
            await update.message.reply_text(
                "✅ Для включения прокси добавьте в .env файл:\n"
                "<code>PROXY_ENABLED=true</code>\n"
                "<code>PROXY_URL=http://ip:port</code>\n\n"
                "Затем перезапустите бота.",
                parse_mode=constants.ParseMode.HTML
            )
        elif action == "off":
            await update.message.reply_text(
                "✅ Для выключения прокси измените в .env файле:\n"
                "<code>PROXY_ENABLED=false</code>\n\n"
                "Затем перезапустите бота.",
                parse_mode=constants.ParseMode.HTML
            )
        elif action == "set" and len(context.args) > 1:
            proxy_url = " ".join(context.args[1:])
            await update.message.reply_text(
                f"✅ Для установки прокси добавьте в .env файл:\n"
                f"<code>PROXY_URL={proxy_url}</code>\n\n"
                "Затем перезапустите бота.",
                parse_mode=constants.ParseMode.HTML
            )
        else:
            await update.message.reply_text(
                "❌ Неверная команда\n"
                "Используйте:\n"
                "/proxy on - Включить\n"
                "/proxy off - Выключить\n"
                "/proxy set [url] - Установить URL"
            )

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик ошибок"""
        logger.error(f"Ошибка: {context.error}")

    @staticmethod
    def _validate_steam_id(steam_id: str) -> bool:
        """Валидация SteamID64"""
        # Проверяем, что это 17-значное число
        pattern = r'^\d{17}$'
        return bool(re.match(pattern, steam_id))

    async def _setup_commands(self) -> None:
        """Установка меню команд бота"""
        commands = [
            BotCommand("start", "Запустить бота"),
            BotCommand("add", "Добавить Steam аккаунт"),
            BotCommand("remove", "Удалить Steam аккаунт"),
            BotCommand("list", "Список отслеживаемых аккаунтов"),
            BotCommand("history", "История изменений"),
            BotCommand("check", "Проверить инвентарь"),
            BotCommand("status", "Статус бота"),
            BotCommand("proxy", "Настройки прокси"),
            BotCommand("help", "❓ Помощь"),
            BotCommand("dashboard", "📊 Ручной вызов сводки")
        ]
        await self.app.bot.set_my_commands(commands)
        logger.info("Меню команд установлено")

    async def dashboard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /dashboard для ручного вызова сводки."""
        results = self.monitor.get_last_dashboard_results()
        if not results:
            await update.message.reply_text("Еще не было собрано данных для дэшборда. Пожалуйста, подождите завершения первого цикла проверки.")
            return

        summary_parts = []
        for result in results:
            steam_id = result["steam_id"]
            profile_url = f"https://steamcommunity.com/profiles/{steam_id}"
            part = f"👤 <a href='{profile_url}'>{steam_id}</a>:"

            if result["error"]:
                part += f" ❌ Ошибка: {result['error']}"
            elif not result["added"] and not result["removed"]:
                part += " ✅ Изменений нет"
            else:
                if result["added"]:
                    part += f" 🟢 {len(result['added'])} доб."
                if result["removed"]:
                    part += f" 🔴 {len(result['removed'])} уб."
            
            summary_parts.append(part)

        header = f"📊 <b>Сводка за {datetime.now().strftime('%H:%M')}</b> 📊\n\n"
        full_message = header + "\n".join(summary_parts)
        
        await update.message.reply_text(
            text=full_message,
            parse_mode=constants.ParseMode.HTML,
            disable_web_page_preview=True
        )


    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик нажатия inline кнопок"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("history:"):
            steam_id = data.split(":")[1]
            await self._show_history(update, context, steam_id, query.message)
        elif data == "back_to_menu":
            await self._show_main_menu(update, context, query.message)

    async def _show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                              message) -> None:
        """Показать главное меню"""
        user = update.effective_user
        
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
        
        await message.edit_text(text, parse_mode=constants.ParseMode.HTML)

    async def _show_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                           steam_id: str, message) -> None:
        """Показать историю изменений для аккаунта"""
        history = await self.db.get_recent_history(steam_id)
        
        if not history:
            keyboard = [[InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await message.edit_text(
                f"📭 Нет истории для {steam_id}",
                reply_markup=reply_markup
            )
            return
        
        text = f"📜 История для {steam_id}:\n\n"
        
        for event in history[:10]:
            icon = "🟢" if event["event_type"] == "ADD" else "🔴"
            name = event["item_name"]
            timestamp = event["timestamp"]
            text += f"{icon} {name} - {timestamp}\n"
        
        # Кнопка возврата в меню
        keyboard = [[InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.edit_text(text, reply_markup=reply_markup)


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
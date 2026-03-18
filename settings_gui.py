"""
GUI для настройки Steam Inventory Tracker
Использует customtkinter для современного интерфейса
"""

import logging
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.info("[DIAGNOSTIC] settings_gui.py загружен")

# Проверка импорта customtkinter
try:
    import customtkinter as ctk
    from customtkinter import CTk, CTkFrame, CTkLabel, CTkEntry, CTkButton, CTkSwitch, CTkTextbox, CTkTabview, CTkOptionMenu
    logger.info("[DIAGNOSTIC] customtkinter импортирован успешно")
except ImportError as e:
    logger.error(f"[DIAGNOSTIC] ОШИБКА: customtkinter не установлен! {e}")
    print("=" * 60)
    print("ОШИБКА: Библиотека customtkinter не установлена!")
    print("Установите: pip install customtkinter>=5.2.0")
    print("=" * 60)
    sys.exit(1)

import os
from pathlib import Path
from dotenv import load_dotenv, set_key, dotenv_values

# Настройка темы
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class SettingsGUI:
    def __init__(self):
        logger.info("[DIAGNOSTIC] SettingsGUI.__init__ начало создания окна")
        self.root = CTk()
        self.root.title("Steam Inventory Tracker - Настройки")
        self.root.geometry("700x600")
        self.root.resizable(False, False)
        logger.info("[DIAGNOSTIC] CTk окно создано")
        
        # Путь к .env файлу
        self.env_path = Path(".env")
        
        # Загрузка текущих настроек
        self.current_settings = self._load_settings()
        logger.info("[DIAGNOSTIC] Настройки загружены")
        
        self._create_ui()
        logger.info("[DIAGNOSTIC] UI создан")
        
    def _load_settings(self) -> dict:
        """Загрузка текущих настроек из .env"""
        if self.env_path.exists():
            load_dotenv(self.env_path)
            return {
                "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", ""),
                "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID", ""),
                "STEAM_API_KEY": os.getenv("STEAM_API_KEY", ""),
                "PROXY_URL": os.getenv("PROXY_URL", ""),
                "CHECK_INTERVAL_MINUTES": os.getenv("CHECK_INTERVAL_MINUTES", "30"),
            }
        return {}
    
    def _create_ui(self):
        """Создание интерфейса"""
        # Заголовок
        header = CTkLabel(
            self.root,
            text="⚙️ Настройки Steam Inventory Tracker",
            font=("Arial", 20, "bold")
        )
        header.pack(pady=20)
        
        # Создаем вкладки
        tabview = CTkTabview(self.root, width=650, height=450)
        tabview.pack(pady=10, padx=20, fill="both", expand=True)
        
        # Вкладка Telegram
        tab_telegram = tabview.add("📱 Telegram")
        self._create_telegram_tab(tab_telegram)
        
        # Вкладка Steam
        tab_steam = tabview.add("🎮 Steam")
        self._create_steam_tab(tab_steam)
        
        # Вкладка Прокси
        tab_proxy = tabview.add("🌐 Прокси")
        self._create_proxy_tab(tab_proxy)
        
        # Кнопки внизу
        button_frame = CTkFrame(self.root, fg_color="transparent")
        button_frame.pack(pady=20, fill="x", padx=20)
        
        save_btn = CTkButton(
            button_frame,
            text="💾 Сохранить настройки",
            command=self._save_settings,
            width=200,
            height=40,
            font=("Arial", 14, "bold"),
            fg_color="#2ecc71",
            hover_color="#27ae60"
        )
        save_btn.pack(side="left", padx=10)
        
        test_btn = CTkButton(
            button_frame,
            text="🔍 Проверить соединение",
            command=self._test_connection,
            width=200,
            height=40,
            font=("Arial", 14),
            fg_color="#3498db",
            hover_color="#2980b9"
        )
        test_btn.pack(side="left", padx=10)
        
        run_btn = CTkButton(
            button_frame,
            text="🚀 Запустить бота",
            command=self._run_bot,
            width=200,
            height=40,
            font=("Arial", 14, "bold"),
            fg_color="#9b59b6",
            hover_color="#8e44ad"
        )
        run_btn.pack(side="right", padx=10)
        
        # Статусная строка
        self.status_label = CTkLabel(
            self.root,
            text="Готов к работе",
            font=("Arial", 12),
            text_color="gray"
        )
        self.status_label.pack(pady=5)
        
    def _create_telegram_tab(self, parent):
        """Создание вкладки Telegram"""
        # Bot Token
        token_label = CTkLabel(parent, text="🔑 Bot Token:", font=("Arial", 14, "bold"))
        token_label.pack(pady=(20, 5), anchor="w", padx=20)
        
        token_info = CTkLabel(
            parent,
            text="Получите у @BotFather в Telegram",
            font=("Arial", 10),
            text_color="gray"
        )
        token_info.pack(anchor="w", padx=20)
        
        self.token_entry = CTkEntry(parent, width=600, height=35, show="•")
        self.token_entry.pack(pady=5, padx=20)
        self.token_entry.insert(0, self.current_settings.get("TELEGRAM_BOT_TOKEN", ""))
        
        # Show/Hide token
        show_token_btn = CTkButton(
            parent,
            text="👁 Показать/скрыть",
            command=self._toggle_token_visibility,
            width=150,
            height=28,
            font=("Arial", 11)
        )
        show_token_btn.pack(anchor="w", padx=20, pady=(0, 15))
        
        # Chat ID
        chat_label = CTkLabel(parent, text="💬 Chat ID:", font=("Arial", 14, "bold"))
        chat_label.pack(pady=(10, 5), anchor="w", padx=20)
        
        chat_info = CTkLabel(
            parent,
            text="Ваш ID в Telegram (получите у @userinfobot)",
            font=("Arial", 10),
            text_color="gray"
        )
        chat_info.pack(anchor="w", padx=20)
        
        self.chat_entry = CTkEntry(parent, width=600, height=35)
        self.chat_entry.pack(pady=5, padx=20)
        self.chat_entry.insert(0, self.current_settings.get("TELEGRAM_CHAT_ID", ""))
        
        # Кнопка получения Chat ID
        get_chat_btn = CTkButton(
            parent,
            text="❓ Как получить Chat ID",
            command=lambda: self._show_help(
                "Для получения Chat ID:\n"
                "1. Напишите @userinfobot в Telegram\n"
                "2. Бот отправит ваш ID\n"
                "3. Скопируйте число (без @)"
            ),
            width=200,
            height=30,
            font=("Arial", 11),
            fg_color="#e67e22",
            hover_color="#d35400"
        )
        get_chat_btn.pack(anchor="w", padx=20, pady=15)
        
    def _create_steam_tab(self, parent):
        """Создание вкладки Steam"""
        # API Key
        api_label = CTkLabel(parent, text="🔑 Steam API Key:", font=("Arial", 14, "bold"))
        api_label.pack(pady=(20, 5), anchor="w", padx=20)
        
        api_info = CTkLabel(
            parent,
            text="Получите на steamcommunity.com/dev/apikey",
            font=("Arial", 10),
            text_color="gray"
        )
        api_info.pack(anchor="w", padx=20)
        
        self.api_entry = CTkEntry(parent, width=600, height=35, show="•")
        self.api_entry.pack(pady=5, padx=20)
        self.api_entry.insert(0, self.current_settings.get("STEAM_API_KEY", ""))
        
        # Show/Hide API key
        show_api_btn = CTkButton(
            parent,
            text="👁 Показать/скрыть",
            command=self._toggle_api_visibility,
            width=150,
            height=28,
            font=("Arial", 11)
        )
        show_api_btn.pack(anchor="w", padx=20, pady=(0, 10))
        
        # Интервал проверки
        interval_frame = CTkFrame(parent, fg_color="transparent")
        interval_frame.pack(pady=(15, 5), fill="x", padx=20)
        
        interval_label = CTkLabel(interval_frame, text="⏱ Интервал проверки:", font=("Arial", 14, "bold"))
        interval_label.pack(anchor="w")
        
        interval_info = CTkLabel(
            parent,
            text="Как часто проверять инвентарь (5 мин - 24 часа)",
            font=("Arial", 10),
            text_color="gray"
        )
        interval_info.pack(anchor="w", padx=20)
        
        # Слайдер и значение
        slider_frame = CTkFrame(parent, fg_color="transparent")
        slider_frame.pack(pady=5, fill="x", padx=20)
        
        self.interval_slider = ctk.CTkSlider(
            slider_frame,
            from_=5,
            to=1440,
            number_of_steps=287,  # Шаг 5 минут
            command=self._update_interval_label,
            width=450
        )
        self.interval_slider.pack(side="left")
        
        # Текущее значение
        current_interval = int(self.current_settings.get("CHECK_INTERVAL_MINUTES", "30"))
        self.interval_slider.set(current_interval)
        
        self.interval_value_label = CTkLabel(
            slider_frame,
            text=self._format_interval(current_interval),
            font=("Arial", 12, "bold"),
            width=100
        )
        self.interval_value_label.pack(side="left", padx=(15, 0))
        
        # Метки мин/макс
        range_frame = CTkFrame(parent, fg_color="transparent")
        range_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        CTkLabel(range_frame, text="5 мин", font=("Arial", 10), text_color="gray").pack(side="left")
        CTkLabel(range_frame, text="24 часа", font=("Arial", 10), text_color="gray").pack(side="right")
        
        # Инструкция
        instruction = CTkTextbox(parent, width=600, height=150, font=("Arial", 11))
        instruction.pack(pady=15, padx=20)
        instruction.insert("1.0",
            "Инструкция по получению Steam API Key:\n\n"
            "1. Перейдите на: steamcommunity.com/dev/apikey\n"
            "2. Авторизуйтесь в Steam\n"
            "3. Введите любое название домена (например: localhost)\n"
            "4. Нажмите 'Register'\n"
            "5. Скопируйте ключ и вставьте выше\n\n"
            "⚠️ API Key нужен для получения информации об инвентаре"
        )
        instruction.configure(state="disabled")
        
    def _create_proxy_tab(self, parent):
        """Создание вкладки Прокси"""
        # Включение прокси
        proxy_frame = CTkFrame(parent, fg_color="transparent")
        proxy_frame.pack(pady=(20, 10), fill="x", padx=20)
        
        proxy_label = CTkLabel(proxy_frame, text="🌐 Использовать прокси:", font=("Arial", 14, "bold"))
        proxy_label.pack(side="left")
        
        self.proxy_switch = CTkSwitch(
            proxy_frame,
            text="",
            command=self._toggle_proxy_fields,
            width=50
        )
        self.proxy_switch.pack(side="left", padx=10)
        
        # Тип прокси
        type_label = CTkLabel(parent, text="Тип прокси:", font=("Arial", 12))
        type_label.pack(anchor="w", padx=20, pady=(10, 5))
        
        self.proxy_type = CTkOptionMenu(
            parent,
            values=["HTTP", "HTTPS", "SOCKS5"],
            width=200,
            height=30,
            font=("Arial", 12)
        )
        self.proxy_type.pack(anchor="w", padx=20)
        self.proxy_type.set("HTTP")
        
        # URL прокси
        url_label = CTkLabel(parent, text="URL прокси:", font=("Arial", 12))
        url_label.pack(anchor="w", padx=20, pady=(15, 5))
        
        url_info = CTkLabel(
            parent,
            text="Формат: http://user:pass@host:port или http://host:port",
            font=("Arial", 10),
            text_color="gray"
        )
        url_info.pack(anchor="w", padx=20)
        
        self.proxy_entry = CTkEntry(parent, width=600, height=35)
        self.proxy_entry.pack(pady=5, padx=20)
        self.proxy_entry.insert(0, self.current_settings.get("PROXY_URL", ""))
        
        # Проверяем, есть ли прокси
        has_proxy = bool(self.current_settings.get("PROXY_URL", ""))
        self.proxy_switch.select() if has_proxy else self.proxy_switch.deselect()
        self._toggle_proxy_fields()
        
        # Примеры
        examples = CTkTextbox(parent, width=600, height=120, font=("Arial", 10))
        examples.pack(pady=20, padx=20)
        examples.insert("1.0",
            "Примеры URL прокси:\n\n"
            "• С авторизацией: http://user:password@proxy.com:8080\n"
            "• Без авторизации: http://proxy.com:8080\n"
            "• SOCKS5: socks5://user:pass@proxy.com:1080\n"
            "• Локальный: http://127.0.0.1:8080"
        )
        examples.configure(state="disabled")
        
    def _toggle_token_visibility(self):
        """Переключение видимости токена"""
        current = self.token_entry.cget("show")
        self.token_entry.configure(show="" if current == "•" else "•")
        
    def _toggle_api_visibility(self):
        """Переключение видимости API ключа"""
        current = self.api_entry.cget("show")
        self.api_entry.configure(show="" if current == "•" else "•")
        
    def _toggle_proxy_fields(self):
        """Включение/выключение полей прокси"""
        enabled = self.proxy_switch.get()
        self.proxy_type.configure(state="normal" if enabled else "disabled")
        self.proxy_entry.configure(state="normal" if enabled else "disabled")
        
    def _update_interval_label(self, value):
        """Обновление метки интервала"""
        minutes = int(value)
        self.interval_value_label.configure(text=self._format_interval(minutes))
        
    def _format_interval(self, minutes: int) -> str:
        """Форматирование интервала в человекочитаемый вид"""
        if minutes < 60:
            return f"{minutes} мин"
        elif minutes == 60:
            return "1 час"
        elif minutes < 1440:
            hours = minutes // 60
            mins = minutes % 60
            if mins == 0:
                return f"{hours} ч"
            else:
                return f"{hours} ч {mins} мин"
        else:
            return "24 часа"
        
    def _save_settings(self):
        """Сохранение настроек в .env"""
        try:
            # Создаем .env файл если не существует
            if not self.env_path.exists():
                self.env_path.touch()
            
            # Сохраняем значения
            settings = {
                "TELEGRAM_BOT_TOKEN": self.token_entry.get().strip(),
                "TELEGRAM_CHAT_ID": self.chat_entry.get().strip(),
                "STEAM_API_KEY": self.api_entry.get().strip(),
                "PROXY_URL": self.proxy_entry.get().strip() if self.proxy_switch.get() else "",
                "CHECK_INTERVAL_MINUTES": str(int(self.interval_slider.get())),
            }
            
            for key, value in settings.items():
                set_key(self.env_path, key, value)
            
            self._update_status("✅ Настройки сохранены успешно!", "#2ecc71")
            
        except Exception as e:
            self._update_status(f"❌ Ошибка сохранения: {str(e)}", "#e74c3c")
            
    def _test_connection(self):
        """Проверка соединения"""
        import asyncio
        from telegram import Bot
        from steam_api import SteamAPI
        
        async def test():
            results = []
            
            # Проверка Telegram
            token = self.token_entry.get().strip()
            if token:
                try:
                    bot = Bot(token)
                    me = await bot.get_me()
                    results.append(f"✅ Telegram: Подключено (@{me.username})")
                    await bot.session.close()
                except Exception as e:
                    results.append(f"❌ Telegram: {str(e)}")
            else:
                results.append("⚠️ Telegram: Токен не указан")
            
            # Проверка Steam
            api_key = self.api_entry.get().strip()
            if api_key:
                try:
                    steam = SteamAPI(api_key)
                    # Пробуем получить инвентарь тестового аккаунта
                    test_id = "76561198000000000"
                    await steam.get_inventory(test_id)
                    results.append("✅ Steam API: Подключено")
                    await steam.close()
                except Exception as e:
                    if "403" in str(e):
                        results.append("✅ Steam API: Подключено (API ключ валидный)")
                    else:
                        results.append(f"⚠️ Steam API: {str(e)}")
            else:
                results.append("⚠️ Steam: API ключ не указан")
            
            # Проверка прокси
            if self.proxy_switch.get():
                proxy = self.proxy_entry.get().strip()
                if proxy:
                    results.append(f"ℹ️ Прокси: {self.proxy_type.get()} настроен")
                else:
                    results.append("⚠️ Прокси: Включен, но URL не указан")
            
            return "\n".join(results)
        
        try:
            self._update_status("🔄 Проверка соединения...", "#f39c12")
            result = asyncio.run(test())
            
            # Показываем результат в диалоге
            dialog = ctk.CTkToplevel(self.root)
            dialog.title("Результат проверки")
            dialog.geometry("500x300")
            dialog.transient(self.root)
            dialog.grab_set()
            
            text = CTkTextbox(dialog, font=("Arial", 12))
            text.pack(pady=20, padx=20, fill="both", expand=True)
            text.insert("1.0", result)
            text.configure(state="disabled")
            
            CTkButton(dialog, text="Закрыть", command=dialog.destroy).pack(pady=10)
            
            self._update_status("✅ Проверка завершена", "#2ecc71")
            
        except Exception as e:
            self._update_status(f"❌ Ошибка проверки: {str(e)}", "#e74c3c")
            
    def _run_bot(self):
        """Запуск бота"""
        import subprocess
        import sys
        
        logger.info("[DIAGNOSTIC] Кнопка 'Запустить бота' нажата")
        try:
            # Сначала сохраняем настройки
            self._save_settings()
            logger.info("[DIAGNOSTIC] Настройки сохранены перед запуском бота")
            
            # Запускаем бота в новом процессе
            logger.info(f"[DIAGNOSTIC] Запуск subprocess: {sys.executable} main.py")
            process = subprocess.Popen([sys.executable, "main.py"], 
                           creationflags=subprocess.CREATE_NEW_CONSOLE)
            logger.info(f"[DIAGNOSTIC] Бот запущен, PID: {process.pid}")
            
            self._update_status("🚀 Бот запущен в отдельном окне!", "#9b59b6")
            
        except Exception as e:
            logger.error(f"[DIAGNOSTIC] Ошибка запуска бота: {e}", exc_info=True)
            self._update_status(f"❌ Ошибка запуска: {str(e)}", "#e74c3c")
            
    def _show_help(self, text: str):
        """Показать справку"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Справка")
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        textbox = CTkTextbox(dialog, font=("Arial", 12))
        textbox.pack(pady=20, padx=20, fill="both", expand=True)
        textbox.insert("1.0", text)
        textbox.configure(state="disabled")
        
        CTkButton(dialog, text="Закрыть", command=dialog.destroy).pack(pady=10)
        
    def _update_status(self, message: str, color: str = "gray"):
        """Обновление статусной строки"""
        self.status_label.configure(text=message, text_color=color)
        
    def run(self):
        """Запуск GUI"""
        logger.info("[DIAGNOSTIC] SettingsGUI.run() вызван, запуск mainloop()")
        self.root.mainloop()
        logger.info("[DIAGNOSTIC] mainloop() завершен")


def main():
    """Точка входа"""
    try:
        logger.info("[DIAGNOSTIC] main() GUI вызван")
        app = SettingsGUI()
        app.run()
    except Exception as e:
        logger.error(f"[DIAGNOSTIC] Критическая ошибка GUI: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    logger.info("[DIAGNOSTIC] settings_gui.py запущен как основной модуль")
    main()

"""
Конфигурация Steam Inventory Monitor Bot
"""

import os
from dotenv import load_dotenv

# Загрузка переменных из .env файла
load_dotenv()

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")

# Steam API Configuration
STEAM_API_KEY = os.getenv("STEAM_API_KEY", "YOUR_STEAM_API_KEY")

# Proxy Configuration (опционально)
# Поддерживает: "true", "1", "yes" (без учета регистра)
PROXY_ENABLED = os.getenv("PROXY_ENABLED", "").lower() in ("true", "1", "yes")
PROXY_URL = os.getenv("PROXY_URL", "http://username:password@ip:port")

# Database Configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", "steam_monitor.db")

# Monitoring Settings
# Интервал проверки инвентаря (в минутах)
# Диапазон: 5 минут - 1440 минут (24 часа)
# По умолчанию: 30 минут
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "30"))
MIN_CHECK_INTERVAL = int(os.getenv("MIN_CHECK_INTERVAL", "5"))  # минимум 5 минут
MAX_CHECK_INTERVAL = int(os.getenv("MAX_CHECK_INTERVAL", "1440"))  # максимум 24 часа (1440 минут)

# Проверка и корректировка интервала
if CHECK_INTERVAL_MINUTES < MIN_CHECK_INTERVAL:
    CHECK_INTERVAL_MINUTES = MIN_CHECK_INTERVAL
elif CHECK_INTERVAL_MINUTES > MAX_CHECK_INTERVAL:
    CHECK_INTERVAL_MINUTES = MAX_CHECK_INTERVAL

# Алиасы для совместимости с bot.py
DEFAULT_INTERVAL = CHECK_INTERVAL_MINUTES
MIN_INTERVAL = MIN_CHECK_INTERVAL
MAX_INTERVAL = MAX_CHECK_INTERVAL

# Rate Limiting Settings
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY = float(os.getenv("RETRY_DELAY", "5"))
EXPONENTIAL_BACKOFF = os.getenv("EXPONENTIAL_BACKOFF", "true").lower() in ("true", "1", "yes")

# Steam Games (для мониторинга)
DEFAULT_GAME = os.getenv("DEFAULT_GAME", "cs2")  # cs2, dota2, tf2

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = "bot.log"

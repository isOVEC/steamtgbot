"""
Конфигурация Steam Inventory Monitor Bot
"""

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # Получить у @BotFather

# Steam API Configuration
STEAM_API_KEY = "YOUR_STEAM_API_KEY"  # Получить на https://steamcommunity.com/dev/apikey

# Proxy Configuration (опционально)
PROXY_ENABLED = False
PROXY_URL = "http://username:password@ip:port"

# Database Configuration
DATABASE_PATH = "steam_monitor.db"

# Monitoring Settings
DEFAULT_INTERVAL = 5  # минут
MIN_INTERVAL = 1  # минут
MAX_INTERVAL = 60  # минут

# Rate Limiting Settings
MAX_RETRIES = 3
RETRY_DELAY = 5  # секунд
EXPONENTIAL_BACKOFF = True

# Steam Games (для мониторинга)
DEFAULT_GAME = "cs2"  # cs2, dota2, tf2

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = "bot.log"

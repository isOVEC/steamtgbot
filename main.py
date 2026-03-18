"""
Steam Inventory Monitor Bot - Главный файл запуска
"""

import asyncio
import logging
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Главная функция"""
    logger.info("[DIAGNOSTIC] main() начало выполнения")
    try:
        from bot import SteamMonitorBot
        logger.info("[DIAGNOSTIC] Импорт SteamMonitorBot успешен")
        
        bot = SteamMonitorBot()
        logger.info("[DIAGNOSTIC] Экземпляр бота создан")
        
        # Запускаем бота. Вся логика теперь внутри bot.run()
        bot.run()
        
    except Exception as e:
        logger.critical(f"Критическая ошибка на верхнем уровне: {e}", exc_info=True)
        # В случае критической ошибки, выходим с кодом 1
        sys.exit(1)

if __name__ == "__main__":
    logger.info("[DIAGNOSTIC] main.py запущен как основной модуль")
    main()
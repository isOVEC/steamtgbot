"""
Steam Inventory Monitor Bot - Главный файл запуска
"""

import asyncio
import logging
import sys
from telegram.ext import Application

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


async def main():
    """Главная функция"""
    from bot import SteamMonitorBot
    
    bot = SteamMonitorBot()
    
    try:
        await bot.initialize()
        logger.info("Бот успешно запущен")
        
        # Запускаем polling
        await bot.app.run_polling(drop_pending_updates=True)
        
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
    finally:
        logger.info("Выключение бота...")
        await bot.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")

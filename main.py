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


async def main():
    """Главная функция"""
    logger.info("[DIAGNOSTIC] main() начало выполнения")
    from bot import SteamMonitorBot
    
    logger.info("[DIAGNOSTIC] Импорт SteamMonitorBot успешен")
    bot = SteamMonitorBot()
    logger.info("[DIAGNOSTIC] Экземпляр бота создан")
    
    try:
        await bot.initialize()
        logger.info("[DIAGNOSTIC] Бот инициализирован успешно")
        
        # Инициализируем и запускаем polling
        await bot.app.initialize()
        await bot.app.updater.start_polling(drop_pending_updates=True)
        await bot.app.start()
        
        # Блокируем выполнение до получения сигнала остановки
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
    finally:
        logger.info("Выключение бота...")
        if bot.app.running:
            await bot.app.stop()
        if bot.app.updater.running:
            await bot.app.updater.stop()
        await bot.shutdown()


if __name__ == "__main__":
    logger.info("[DIAGNOSTIC] main.py запущен как основной модуль")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("[DIAGNOSTIC] Бот остановлен пользователем")
        print("Бот остановлен")
    except Exception as e:
        logger.error(f"[DIAGNOSTIC] Критическая ошибка в main: {e}", exc_info=True)
        raise

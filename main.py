"""
Steam Inventory Monitor Bot - Главный файл запуска
"""

import asyncio
import logging
import sys
import signal

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ],
    force=True
)

logger = logging.getLogger(__name__)

# Глобальный флаг для отслеживания состояния
shutdown_requested = False


def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    global shutdown_requested
    logger.info(f"Получен сигнал {signum}, инициируем завершение...")
    shutdown_requested = True


def main():
    """Главная функция"""
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("[DIAGNOSTIC] main() начало выполнения")
    
    exit_code = 0
    
    try:
        from bot import SteamMonitorBot
        logger.info("[DIAGNOSTIC] Импорт SteamMonitorBot успешен")
        
        bot = SteamMonitorBot()
        logger.info("[DIAGNOSTIC] Экземпляр бота создан")
        
        # Запускаем бота. Вся логика теперь внутри bot.run()
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем (Ctrl+C)")
        exit_code = 0
    except SystemExit as e:
        logger.info(f"Бот завершил работу с кодом: {e.code}")
        exit_code = e.code
    except Exception as e:
        logger.critical(f"Критическая ошибка на верхнем уровне: {e}", exc_info=True)
        exit_code = 1
    
    logger.info(f"Выход с кодом: {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    logger.info("[DIAGNOSTIC] main.py запущен как основной модуль")
    main()
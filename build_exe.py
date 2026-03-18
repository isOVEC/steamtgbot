"""
Скрипт для сборки Steam Inventory Tracker в EXE файл
Использует PyInstaller
"""

import PyInstaller.__main__
import os
import sys
from pathlib import Path


def build_exe():
    """Сборка приложения в EXE"""
    
    print("🚀 Начинаю сборку Steam Inventory Tracker...")
    
    # Проверяем наличие необходимых файлов
    required_files = [
        "main.py",
        "bot.py",
        "config.py",
        "database.py",
        "monitor.py",
        "steam_api.py",
        "logger_config.py",
        "utils.py",
        "settings_gui.py",
    ]
    
    for file in required_files:
        if not Path(file).exists():
            print(f"❌ Отсутствует файл: {file}")
            return False
    
    # Аргументы для PyInstaller
    args = [
        "main.py",  # Главный файл
        "--name=SteamInventoryTracker",  # Имя приложения
        "--onefile",  # Один EXE файл
        "--windowed",  # Оконное приложение (без консоли)
        "--icon=NONE",  # Без иконки (можно добавить .ico)
        "--clean",  # Очистка временных файлов
        "--noconfirm",  # Без подтверждения
        
        # Добавляем все файлы проекта
        "--add-data", "bot.py;.",
        "--add-data", "config.py;.",
        "--add-data", "database.py;.",
        "--add-data", "monitor.py;.",
        "--add-data", "steam_api.py;.",
        "--add-data", "logger_config.py;.",
        "--add-data", "utils.py;.",
        "--add-data", "settings_gui.py;.",
        "--add-data", ".env.example;.",
        "--add-data", "README.md;.",
        
        # Скрытые импорты
        "--hidden-import", "telegram",
        "--hidden-import", "telegram.ext",
        "--hidden-import", "customtkinter",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL._tkinter_finder",
        "--hidden-import", "dotenv",
        "--hidden-import", "aiohttp",
        "--hidden-import", "aiosqlite",
        "--hidden-import", "deepdiff",
        "--hidden-import", "ordered_set",
    ]
    
    # Добавляем иконку если есть
    if Path("icon.ico").exists():
        args[3] = "--icon=icon.ico"
        print("✅ Найдена иконка: icon.ico")
    
    try:
        print("📦 Запуск PyInstaller...")
        PyInstaller.__main__.run(args)
        
        print("\n" + "="*60)
        print("✅ Сборка завершена успешно!")
        print("="*60)
        print(f"\n📁 EXE файл находится в: dist/SteamInventoryTracker.exe")
        print("\n📋 Инструкция по использованию:")
        print("1. Скопируйте SteamInventoryTracker.exe в отдельную папку")
        print("2. Запустите SteamInventoryTracker.exe")
        print("3. При первом запуске создастся .env файл")
        print("4. Настройте параметры через GUI или отредактируйте .env")
        print("\n💡 Для настройки через GUI:")
        print("   - Нажмите Win+R, введите cmd")
        print("   - Перейдите в папку с exe: cd путь/к/папке")
        print("   - Запустите с параметром --settings")
        print("   - SteamInventoryTracker.exe --settings")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка сборки: {str(e)}")
        return False


def build_with_console():
    """Сборка с консолью для отладки"""
    
    print("🚀 Сборка версии с консолью (для отладки)...")
    
    args = [
        "main.py",
        "--name=SteamInventoryTracker_Debug",
        "--onefile",
        "--console",  # С консолью
        "--icon=NONE",
        "--clean",
        "--noconfirm",
        "--add-data", "bot.py;.",
        "--add-data", "config.py;.",
        "--add-data", "database.py;.",
        "--add-data", "monitor.py;.",
        "--add-data", "steam_api.py;.",
        "--add-data", "logger_config.py;.",
        "--add-data", "utils.py;.",
        "--add-data", "settings_gui.py;.",
        "--hidden-import", "telegram",
        "--hidden-import", "customtkinter",
        "--hidden-import", "PIL",
        "--hidden-import", "dotenv",
        "--hidden-import", "aiohttp",
        "--hidden-import", "aiosqlite",
    ]
    
    try:
        PyInstaller.__main__.run(args)
        print("\n✅ Отладочная версия создана: dist/SteamInventoryTracker_Debug.exe")
        return True
    except Exception as e:
        print(f"\n❌ Ошибка: {str(e)}")
        return False


def create_installer_script():
    """Создание скрипта для установки зависимостей"""
    
    script_content = '''@echo off
chcp 65001 >nul
echo ========================================
echo Steam Inventory Tracker - Установщик
echo ========================================
echo.

:: Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден!
    echo Пожалуйста, установите Python 3.9+ с python.org
    pause
    exit /b 1
)

echo ✅ Python найден
echo.

:: Установка зависимостей
echo 📦 Установка зависимостей...
pip install -r requirements.txt

if errorlevel 1 (
    echo ❌ Ошибка установки зависимостей
    pause
    exit /b 1
)

echo.
echo ✅ Установка завершена!
echo.
echo 🚀 Для запуска бота выполните: python main.py
echo ⚙️  Для настройки через GUI: python settings_gui.py
echo.
pause
'''
    
    with open("install.bat", "w", encoding="utf-8") as f:
        f.write(script_content)
    
    print("✅ Создан install.bat для установки зависимостей")


def create_run_scripts():
    """Создание скриптов для запуска"""
    
    # Скрипт запуска бота
    run_bot = '''@echo off
chcp 65001 >nul
echo 🚀 Запуск Steam Inventory Tracker...
python main.py
pause
'''
    
    with open("run_bot.bat", "w", encoding="utf-8") as f:
        f.write(run_bot)
    
    # Скрипт запуска настроек
    run_settings = '''@echo off
chcp 65001 >nul
echo ⚙️  Запуск настроек Steam Inventory Tracker...
python settings_gui.py
'''
    
    with open("run_settings.bat", "w", encoding="utf-8") as f:
        f.write(run_settings)
    
    # Скрипт сборки
    build_script = '''@echo off
chcp 65001 >nul
echo 🔨 Сборка Steam Inventory Tracker в EXE...
python build_exe.py
pause
'''
    
    with open("build.bat", "w", encoding="utf-8") as f:
        f.write(build_script)
    
    print("✅ Созданы скрипты запуска:")
    print("   - run_bot.bat (запуск бота)")
    print("   - run_settings.bat (настройки)")
    print("   - build.bat (сборка EXE)")


def main():
    """Главная функция"""
    
    print("="*60)
    print("Steam Inventory Tracker - Builder")
    print("="*60)
    print()
    
    # Создаем вспомогательные скрипты
    create_installer_script()
    create_run_scripts()
    
    print()
    
    # Меню выбора
    print("Выберите действие:")
    print("1. Собрать EXE (оконное приложение)")
    print("2. Собрать EXE с консолью (для отладки)")
    print("3. Создать только вспомогательные скрипты")
    print("4. Всё сразу")
    print()
    
    choice = input("Введите номер (1-4): ").strip()
    
    if choice == "1":
        build_exe()
    elif choice == "2":
        build_with_console()
    elif choice == "3":
        print("✅ Скрипты созданы")
    elif choice == "4":
        build_exe()
        build_with_console()
    else:
        print("❌ Неверный выбор")
    
    print()
    input("Нажмите Enter для выхода...")


if __name__ == "__main__":
    main()

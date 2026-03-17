# Steam Inventory Monitor Bot

Telegram-бот для мониторинга изменений в инвентаре Steam-аккаунтов.

## Требования

- Python 3.10+
- Telegram Bot Token
- Steam API Key

## Установка

1. Клонируйте репозиторий
2. Установите зависимости:
```bash
pip install -r requirements.txt
```
3. Настройте конфигурацию в `config.py`
4. Запустите бота:
```bash
python main.py
```

## Команды бота

- `/start` - Запуск бота
- `/add <steamid>` - Добавить аккаунт для мониторинга
- `/remove <steamid>` - Удалить аккаунт из мониторинга
- `/list` - Список отслеживаемых аккаунтов
- `/set_interval <минуты>` - Установить интервал проверки
- `/status` - Статус мониторинга

## Поддерживаемые игры

- CS2 (CS:GO)
- Dota 2
- TF2
- и другие игры Steam

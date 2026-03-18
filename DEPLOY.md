# Деплой Steam Inventory Bot на VPS

## Вариант 1: Docker (рекомендуется)

### Требования
- VPS с установленным Docker
- Docker Compose

### Установка

1. **Скопируйте проект на VPS:**
```bash
git clone https://github.com/your-repo/steamtgbot.git
cd steamtgbot
```

2. **Настройте переменные окружения:**
```bash
# Скопировать готовый .env с тестовыми данными
cp deploy/.env.production .env
```

3. **Отредактируйте .env если нужно:**
```bash
nano .env
```

Тестовые данные уже добавлены:
- `TELEGRAM_BOT_TOKEN=8022071544:AAF9BH9ZsdKsku4Ps5TUu5vTf9tHytPeCl0`
- `STEAM_API_KEY=D6F0E8D6197B5E4B8A3F939CBC779ACD`
- `CHECK_INTERVAL_MINUTES=5`

4. **Соберите и запустите:**
```bash
cd deploy
docker-compose up -d --build
```

5. **Проверьте статус:**
```bash
docker-compose logs -f steam-bot
```

### Команды управления
```bash
# Перезапуск
docker-compose restart

# Остановка
docker-compose down

# Просмотр логов
docker-compose logs -f

# Обновление и пересборка
docker-compose up -d --build
```

---

## Вариант 2: Systemd (без Docker)

### Требования
- VPS с Ubuntu/Debian
- Python 3.11+

### Установка

1. **Скопируйте проект на VPS:**
```bash
git clone https://github.com/your-repo/steamtgbot.git
cd steamtgbot
```

2. **Запустите скрипт установки:**
```bash
chmod +x deploy/install.sh
sudo ./deploy/install.sh
```

3. **Скопируйте .env:**
```bash
cp deploy/.env.production /opt/steam-inventory-bot/.env
nano /opt/steam-inventory-bot/.env
```

4. **Установите systemd сервис:**
```bash
sudo cp deploy/steam-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable steam-bot
sudo systemctl start steam-bot
```

5. **Проверьте статус:**
```bash
sudo systemctl status steam-bot
sudo journalctl -u steam-bot -f
```

### Команды управления
```bash
# Перезапуск
sudo systemctl restart steam-bot

# Остановка
sudo systemctl stop steam-bot

# Просмотр логов
sudo journalctl -u steam-bot -f

# Автозапуск при загрузке
sudo systemctl enable steam-bot
```

---

## Вариант 3: Screen/Tmux (простой)

### Использование screen
```bash
# Установка
apt install -y screen

# Запуск в screen сессии
screen -S steam-bot
cd /opt/steam-inventory-bot
python3 main.py

# Отключение от сессии (бот продолжит работать)
Ctrl+A, затем D
```

### Использование tmux
```bash
# Установка
apt install -y tmux

# Запуск
tmux new -s steam-bot
cd /opt/steam-inventory-bot
python3 main.py

# Отключение
Ctrl+B, затем D
```

---

## Проверка работы

### Телеграм бот должен отвечать на команды:
- `/start` - Запуск бота
- `/status` - Проверить статус мониторинга
- `/add <steam_id>` - Добавить Steam аккаунт
- `/list` - Список отслеживаемых аккаунтов
- `/remove <steam_id>` - Удалить аккаунт
- `/settings` - Настройки

---

## Troubleshooting

### Бот не запускается
```bash
# Проверьте логи
docker-compose logs steam-bot
# или
sudo journalctl -u steam-bot -n 50
```

### Проблемы с правами
```bash
sudo chown -R steam-bot:steam-bot /opt/steam-inventory-bot
```

### Переустановка
```bash
# Docker
docker-compose down
docker-compose up -d

# Systemd
sudo systemctl stop steam-bot
sudo systemctl daemon-reload
sudo systemctl start steam-bot
```

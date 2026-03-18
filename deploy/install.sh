#!/bin/bash
# Steam Inventory Bot - VPS Install Script

set -e

echo "=========================================="
echo "Steam Inventory Bot - Установка на VPS"
echo "=========================================="

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверка root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Запустите скрипт от root (sudo ./install.sh)${NC}"
    exit 1
fi

# Шаг 1: Обновление системы
echo -e "${YELLOW}[1/6] Обновление системы...${NC}"
apt update && apt upgrade -y

# Шаг 2: Установка Python и зависимостей
echo -e "${YELLOW}[2/6] Установка Python и зависимостей...${NC}"
apt install -y python3 python3-pip python3-venv git

# Шаг 3: Создание пользователя для бота
echo -e "${YELLOW}[3/6] Создание пользователя...${NC}"
if ! id -u steam-bot &>/dev/null; then
    useradd -m -s /bin/bash steam-bot
    echo "Пользователь steam-bot создан"
fi

# Шаг 4: Создание директории
echo -e "${YELLOW}[4/6] Создание директорий...${NC}"
mkdir -p /opt/steam-inventory-bot
mkdir -p /var/log/steam-bot

# Шаг 5: Копирование файлов
echo -e "${YELLOW}[5/6] Копирование файлов бота...${NC}"
# Скопируйте файлы проекта в /opt/steam-inventory-bot
# (это нужно сделать вручную или через git)

# Шаг 6: Установка Python зависимостей
echo -e "${YELLOW}[6/6] Установка Python зависимостей...${NC}"
cd /opt/steam-inventory-bot
pip3 install -r requirements.txt

# Настройка прав
chown -R steam-bot:steam-bot /opt/steam-inventory-bot
chown -R steam-bot:steam-bot /var/log/steam-bot

echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}Установка завершена!${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo "Следующие шаги:"
echo "1. Отредактируйте /opt/steam-inventory-bot/.env"
echo "2. Скопируйте deploy/steam-bot.service в /etc/systemd/system/"
echo "3. Запустите: systemctl daemon-reload"
echo "4. Запустите бота: systemctl start steam-bot"
echo "5. Проверьте статус: systemctl status steam-bot"

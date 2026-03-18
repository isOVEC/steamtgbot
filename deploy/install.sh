#!/bin/bash
# Steam Inventory Bot - VPS Install Script

set -e

echo "=========================================="
echo "Steam Inventory Bot - Установка на VPS (Docker preferred)"
echo "=========================================="

# Проверка Ubuntu/Debian
if ! lsb_release -a 2>/dev/null | grep -qE "(Ubuntu|Debian)"; then
    echo -e "${RED}Поддерживается только Ubuntu/Debian${NC}"
    exit 1
fi

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

# Шаг 2: Установка Docker и Docker Compose
echo -e "${YELLOW}[2/7] Установка Docker и Docker Compose...${NC}"
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
usermod -aG docker steam-bot
systemctl enable docker --now

# Шаг 2.1: Python for systemd fallback
apt install -y python3 python3-pip git

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

# Шаг 5: Клонирование и настройка
echo -e "${YELLOW}[5/7] Клонирование репозитория...${NC}"
cd /opt
rm -rf steam-inventory-bot  # full replace old copy
git clone https://github.com/isOVEC/steamtgbot.git steam-inventory-bot
chown -R steam-bot:steam-bot steam-inventory-bot

# Шаг 6: Docker запуск
echo -e "${YELLOW}[6/7] Запуск Docker...${NC}"
cd /opt/steam-inventory-bot/deploy
cp .env.example .env
chown steam-bot:steam-bot .env
echo -e "${YELLOW}Edit .env now (nano .env) then press Enter to continue...${NC}"
read
docker compose up -d --build

echo -e "${GREEN}✅ Docker бот запущен!${NC}"
echo -e "${GREEN}Логи: docker compose logs -f${NC}"
echo -e "${GREEN}Остановка: docker compose down${NC}"

# Steam Inventory Monitor Bot - Docker образ
FROM python:3.11-slim

# Установка зависимостей системы
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копирование зависимостей
COPY requirements.txt .

# Установка Python-зависимостей (без GUI-библиотек)
RUN pip install --no-cache-dir \
    python-telegram-bot>=20.0 \
    steampy>=0.14.0 \
    aiohttp>=3.8.0 \
    deepdiff>=6.0.0 \
    python-dotenv>=1.0.0

# Копирование кода бота
COPY bot.py .
COPY main.py .
COPY config.py .
COPY database.py .
COPY monitor.py .
COPY steam_api.py .
COPY logger_config.py .
COPY utils.py .

# Точка входа

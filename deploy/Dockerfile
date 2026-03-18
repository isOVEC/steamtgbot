# Steam Inventory Monitor Bot - Docker образ
FROM python:3.11-slim

# Установка зависимостей системы
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ \
    && pip cache purge \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копирование Docker-зависимостей
COPY deploy/requirements-docker.txt ./requirements-docker.txt

RUN pip install --no-cache-dir -r requirements-docker.txt

# Копирование кода бота
COPY bot.py .
COPY main.py .
COPY config.py .
COPY database.py .
COPY monitor.py .
COPY steam_api.py .
COPY logger_config.py .
COPY utils.py .

# Создание non-root пользователя
RUN useradd --create-home --shell /bin/bash steam-bot \
    && chown -R steam-bot:steam-bot /app

USER steam-bot

# Точка входа
CMD ["python", "main.py"]

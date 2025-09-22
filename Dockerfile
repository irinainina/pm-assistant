# Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Устанавливаем системные зависимости, если нужны сборки пакетов
RUN apt-get update && \
    apt-get install -y build-essential gcc --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

# Скопируем только requirements и установим зависимости (ускорит сборку)
COPY ./backend/requirements.txt /usr/src/app/requirements.txt
RUN pip install --upgrade pip && pip install -r /usr/src/app/requirements.txt

# Скопируем весь бэкенд
COPY ./backend /usr/src/app

EXPOSE 8000

# Запуск через gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--timeout", "600", "--preload", "main:app"]

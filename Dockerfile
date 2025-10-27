# FROM python:3.11-slim

# ENV PYTHONDONTWRITEBYTECODE=1
# ENV PYTHONUNBUFFERED=1
# ENV PORT=8000

# RUN apt-get update && \
#     apt-get install -y build-essential gcc --no-install-recommends && \
#     rm -rf /var/lib/apt/lists/*

# WORKDIR /usr/src/app

# COPY ./backend/requirements.txt /usr/src/app/requirements.txt
# RUN pip install --upgrade pip && pip install -r /usr/src/app/requirements.txt

# COPY ./backend /usr/src/app

# EXPOSE 8000

# CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--timeout", "600", "--workers", "1", "main:app"]


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

# Скачаем модель sentence-transformer заранее (это займет ~500MB)
# Устанавливаем переменные окружения для кеширования
ENV HF_HOME=/usr/src/app/.cache
ENV SENTENCE_TRANSFORMERS_HOME=/usr/src/app/.cache
ENV HF_HUB_DISABLE_TELEMETRY=1

# Загружаем модель
RUN python -c "from sentence_transformers import SentenceTransformer; \
    print('Downloading sentence-transformer model...'); \
    model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'); \
    print('Model downloaded successfully to cache')"

# Скопируем весь бэкенд
COPY ./backend /usr/src/app

EXPOSE 8000

# Запуск через gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--timeout", "600", "--workers", "1", "main:app"]

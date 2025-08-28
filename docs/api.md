# PM-assistant API Documentation

Документация по API проекта **PM-assistant**  

---

## Статус

API в процессе разработки. Здесь перечислены текущие методы.

---

## Эндпоинты
### 1. Health-check
**GET** `http://localhost:5000/api/health`

Проверка, что сервер работает. Возвращает простой ответ "ok".

---

### 2. Получение документов из Notion
**GET `http://localhost:5000/api/notion/documents/parsed`

Возвращает список документов из Notion, включая их метаданные и содержимое.

### 3. Обновление векторной базы данных
**POST** `http://localhost:5000/api/notion/update_vector_db`

Полностью обновляет векторную базу данных: очищает текущую коллекцию и загружает все документы из Notion заново.
Ответ:

```
json
{
  "status": "success",
  "message": "Vector database updated successfully with 150 chunks",
  "documents_processed": 15
}
```

### 4. Проверка статуса актуальности базы данных
**GET** `http://localhost:5000/api/notion/status`

Проверяет, были ли изменения в Notion после последнего обновления векторной базы.
Ответ:

```
json
{
  "is_actual": false,
  "notion_last_edited": "2024-01-15T10:30:00.000Z",
  "our_last_update": 1705313400.123456
}
```

is_actual: true если база актуальна, false если требуется обновление

notion_last_edited: время последнего изменения в Notion (ISO строка)

our_last_update: время последнего обновления нашей базы (timestamp)

### 5. Поиск по базе документов
**GET** `http://localhost:5000/api/chroma?q=тренды веб дизайна`

Ищет документы по введённому запросу.

Возвращает список из 15 чанков (частей документа) и ссылки на 3-5 документов, наиболее релевантных запросу.

---

### 6. Ответ AI
**GET** `http://localhost:5000/api/search?q=тренды веб дизайна`

Возвращает ответ AI на основе найденных документов, включая источники информации.

---

### 7. Вопрос к AI (Ask)
**POST** `http://localhost:5000/api/ask`

Body:

```
json
{
  "query": "тренды веб дизайна",
  "conversation_id": "default"
}
```

Отправляет вопрос AI и возвращает ответ с источниками. Используется для чат-интерфейса.


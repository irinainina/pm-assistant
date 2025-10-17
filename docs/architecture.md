# 1. Архитектуа проекта PM-assistant

![Схема архитектуры проекта](img/architecture.png)

1. Frontend отправляет вопрос пользователя на Backend API
2. Backend обрабатывает запрос и взаимодействует с другими сервисами:
  - Через Notion Integration получает доступ к базе знаний
  - В Vector DB ищет релевантные фрагменты информации
  - Передаёт найденные данные в AI Engine для генерации ответа
  - Backend возвращает готовый ответ с источниками на Frontend
3. Связь Notion → Vector DB: Данные из Notion периодически загружаются и индексируются в векторной базе для быстрого поиска.


## Структура проекта

```
Frontend (Next.js 15)
/frontend
├── app/
│   ├── api/
│   │   └── auth/
│   │       └── [...nextauth]/
│   │           └── route.js              # NextAuth API route
│   ├── providers.jsx                     # SessionProvider
│   ├── layout.js                         # корневой layout
│   └── page.js                           # главная страница 
├── components/
│   ├── AgentSection/
│   │   └── AgentSection.jsx              # компонент чата
│   └── Auth/
│       └── Auth.jsx                      # компонент аутентификации
├── lib/
│   ├── auth.js                           # конфигурация NextAuth
│   └── prisma.js                         # инициализация Prisma Client
├── prisma/
│   └── schema.prisma                     # схема базы данных
├── auth.config.js                        # конфиг провайдеров NextAuth
├── .env.local                            # переменные окружения Next.js
└── .env                                  # переменные для Prisma


Backend (Python + Flask)
/backend
├── main.py                 # Flask приложение
├── requirements.txt        # библиотеки
├── .env                    # env переменные бекенда
├── /routes
│   ├── ask.py              # возвращает ответ AI, включая источники информации
│   ├── notion.py           # проверка актуальности базы данных, обновление векторной базы данных
│   ├── health.py           # проверка, что сервер работает
│   ├── notion_parsed.py    # получение документов из Notion
│   ├── chroma.py           # поиск по векторной базе данных
│   └── search.py           # возвращает ответ AI, GET-версия эндпойнта /ask
├── /services
│   ├── notion_client.py    # коннектор к Notion API
│   ├── embeddings.py       # генерация эмбеддингов
│   ├── chroma_client.py    # работа с ChromaDB
│   └── ai_engine.py        # запросы к OpenAI, формирование ответа
└── /utils
    ├── db_state.py         # требуется ли обновление Notion DB
    └── config.py           # ключи и настройки

Документация
/docs
  ├── requirements.md       # требования
  ├── architecture.md       # архитектура
  ├── api.md                # описание эндпойнтов
  └── plan.md               # план работы над проектом

База данных (Supabase PostgreSQL)
- Таблица: users (id, email, name, image, created_at, emailVerified)
- Таблица: accounts (OAuth аккаунты Google)
- Таблица: sessions (сессии пользователей)

```
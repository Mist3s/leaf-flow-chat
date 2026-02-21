# LeafFlow Chat Service

Микросервис чата "пользователь - поддержка" с REST API, WebSocket, outbox-pattern и Redis backplane.

Сервис предоставляет:
- Чат пользователя с поддержкой через веб-клиент
- Административный интерфейс для управления диалогами
- Realtime-доставку сообщений через WebSocket
- Идемпотентность отправки (защита от дубликатов)
- Горизонтальное масштабирование через Redis Pub/Sub backplane
- Transactional outbox для надёжной публикации событий
- Потребление внешних событий из LeafFlow через Redis Streams

## Архитектура

### Hexagonal Architecture (Ports & Adapters)

Проект построен по принципу гексагональной архитектуры. Бизнес-логика изолирована от инфраструктуры через протоколы (Python `Protocol`).

```
                    ┌──────────────────────────────┐
                    │         API Layer            │
                    │  REST routers, WS router,    │
                    │  schemas, middleware, deps    │
                    └──────────┬───────────────────┘
                               │ вызывает
                    ┌──────────▼───────────────────┐
                    │       Services Layer          │
                    │  conversation_service         │
                    │  message_service              │
                    │  admin_service                │
                    │  read_state_service           │
                    └──────────┬───────────────────┘
                               │ зависит от портов (Protocol)
          ┌────────────────────┼────────────────────┐
          │                    │                     │
┌─────────▼──────┐  ┌─────────▼──────┐  ┌──────────▼─────┐
│  Application   │  │    Domain      │  │  Application   │
│  Ports         │  │  Entities &    │  │  Policies      │
│  (UoW, repos,  │  │  Value Objects │  │  (permissions, │
│   auth, bus)   │  │  Events        │  │   rate limit)  │
└─────────┬──────┘  └────────────────┘  └────────────────┘
          │ реализуют
┌─────────▼──────────────────────────────────────────────┐
│              Infrastructure Layer                       │
│  SQLAlchemy repos, mappers, UoW                        │
│  HS256/JWKS verifiers                                  │
│  Redis Pub/Sub publisher/subscriber                    │
│  Redis Streams consumer                                │
│  WebSocket ConnectionManager                           │
└────────────────────────────────────────────────────────┘
```

**Правило зависимостей:** сервисы и application-слой никогда не импортируют инфраструктуру напрямую. Они работают через протоколы (`UnitOfWork`, `ConversationReader`, `MessageWriter`, `TokenVerifier`, `EventPublisher`). Конкретные реализации подключаются в `api/deps.py` через FastAPI Dependency Injection.

### Структура каталогов

```
src/chat_service/
├── domain/                    # Ядро: не зависит ни от чего
│   ├── entities/              #   Conversation, Message, Participant, ReadState
│   ├── events/                #   MessageCreated, ConversationCreated/Updated
│   └── value_objects/         #   Enums (status, kind, type), type aliases
│
├── application/               # Use-case контракты: зависит только от domain
│   ├── dto/                   #   Principal, SendMessageDTO, ConversationFilterDTO
│   ├── exceptions.py          #   NotFoundError, ForbiddenError, ConflictError
│   ├── policies/              #   Проверки прав доступа
│   ├── ports/                 #   Протоколы: auth, bus, clock
│   ├── repositories/          #   Протоколы: conversation, message, participant, outbox, read_state
│   └── uow.py                #   UnitOfWork protocol
│
├── infrastructure/            # Адаптеры: реализации портов
│   ├── auth/                  #   HS256Verifier, JWKSVerifier
│   ├── bus/                   #   RedisPubSubPublisher/Subscriber, RedisStreamConsumer, serializer
│   ├── db/
│   │   ├── models/            #   SQLAlchemy ORM-модели (5 таблиц)
│   │   ├── mappers/           #   ORM model <-> domain entity
│   │   ├── repositories/      #   Реализации репозиториев на SQLAlchemy
│   │   ├── base.py            #   DeclarativeBase с naming conventions
│   │   ├── session.py         #   AsyncEngine + AsyncSessionLocal
│   │   └── uow.py            #   SqlAlchemyUoW — реализация UnitOfWork
│   └── ws/
│       ├── manager.py         #   ConnectionManager (in-process WS registry)
│       └── protocol.py        #   WsInbound / WsOutbound pydantic models
│
├── services/                  # Use-cases: зависят от application ports
│   ├── conversation_service   #   get_or_create_support, list, get
│   ├── message_service        #   send_message (idempotent), list_messages
│   ├── admin_service          #   assign, close, list (admin)
│   └── read_state_service     #   mark_read
│
├── api/                       # HTTP/WS интерфейс
│   ├── deps.py                #   DI: get_uow, get_current_principal, get_current_admin
│   ├── middleware/             #   CorrelationId, RequestTiming
│   └── v1/
│       ├── routers/           #   conversations, messages, admin_conversations, ws, health
│       └── schemas/           #   Pydantic request/response models
│
├── workers/                   # Background-процессы
│   ├── outbox_worker.py       #   Polling outbox -> Redis Pub/Sub
│   └── leaf_events_consumer.py#   Redis Streams XREADGROUP -> обработка
│
├── scripts/                   #   create_consumer_group, seed_dev_data
├── config.py                  #   Pydantic Settings
├── app.py                     #   FastAPI create_app(), lifespan, exception handlers
└── __main__.py                #   Entrypoint: uvicorn
```

### Unit of Work (UoW)

Все операции записи выполняются внутри одной транзакции через UoW. Он объединяет все репозитории с общей `AsyncSession`, гарантируя атомарность:

```
┌─ UoW (одна транзакция) ──────────────────────────┐
│                                                    │
│  conversations   (reader + writer)                │
│  participants    (reader + writer)                │
│  messages        (reader + writer)                │
│  read_state_w    (writer)                         │
│  outbox          (writer)                         │
│                                                    │
│  commit() / rollback() / flush()                  │
└────────────────────────────────────────────────────┘
```

Пример: `send_message` в одной транзакции создаёт сообщение, пишет в outbox и обновляет `last_message_at` диалога. Если что-то падает — всё откатывается.

### Процесс отправки сообщения

```
Клиент                 API/WS             Service          DB            Outbox Worker     Redis Pub/Sub      Другие инстансы
  │                      │                  │               │                 │                  │                  │
  │──POST /messages──────▶                  │               │                 │                  │                  │
  │  {client_msg_id}     │                  │               │                 │                  │                  │
  │                      │──send_message───▶│               │                 │                  │                  │
  │                      │                  │               │                 │                  │                  │
  │                      │                  │──INSERT msg───▶               │                  │                  │
  │                      │                  │  ON CONFLICT   │                 │                  │                  │
  │                      │                  │  DO NOTHING    │                 │                  │                  │
  │                      │                  │               │                 │                  │                  │
  │                      │                  │──INSERT outbox▶               │                  │                  │
  │                      │                  │               │                 │                  │                  │
  │                      │                  │──UPDATE conv──▶               │                  │                  │
  │                      │                  │  last_message  │                 │                  │                  │
  │                      │                  │               │                 │                  │                  │
  │                      │                  │──COMMIT────────▶               │                  │                  │
  │                      │                  │               │                 │                  │                  │
  │◀─── 201 Created ─────│                  │               │                 │                  │                  │
  │                      │                  │               │                 │                  │                  │
  │                      │                  │               │──poll pending──▶│                  │                  │
  │                      │                  │               │                 │──PUBLISH─────────▶                  │
  │                      │                  │               │                 │  chat.fanout     │                  │
  │                      │                  │               │──mark sent─────▶│                  │                  │
  │                      │                  │               │                 │                  │──subscriber──────▶
  │                      │                  │               │                 │                  │  broadcast WS    │
  │                      │                  │               │                 │                  │                  │──▶ WS clients
```

**Ключевые моменты:**

1. **Идемпотентность**: `INSERT ... ON CONFLICT (conversation_id, sender_kind, sender_id, client_msg_id) DO NOTHING`. Повторная отправка с тем же `client_msg_id` не создаёт дубль, а возвращает существующее сообщение.

2. **Transactional Outbox**: сообщение и запись в outbox создаются в одной транзакции. Это гарантирует, что событие не потеряется (at-least-once delivery).

3. **Outbox Worker**: отдельный процесс, который в цикле:
   - `SELECT ... FOR UPDATE SKIP LOCKED` — забирает pending-записи (без блокировки других воркеров)
   - Публикует в Redis Pub/Sub
   - Помечает `status=sent`
   - При ошибке — exponential backoff (`5s, 10s, 20s, 40s, ...`, max 300s)

4. **Redis Pub/Sub fanout**: каждый инстанс API подписан на канал `chat.fanout`. Получив событие, он рассылает его по WS всем подключённым клиентам этого диалога.

### Multi-instance масштабирование

```
                        ┌──────────────┐
                        │   Redis      │
                        │  Pub/Sub     │
                        │ chat.fanout  │
                        └──┬───────┬───┘
                  subscribe│       │subscribe
              ┌────────────▼──┐ ┌──▼────────────┐
              │  Instance 1   │ │  Instance 2   │
              │  WS clients:  │ │  WS clients:  │
              │  user:42      │ │  admin:1      │
              │  user:99      │ │  user:55      │
              └───────────────┘ └───────────────┘
```

Когда пользователь `user:42` отправляет сообщение через Instance 1:
1. Instance 1 сохраняет в БД + outbox
2. Outbox Worker публикует событие в Redis `chat.fanout`
3. Оба инстанса получают событие через свои subscriber'ы
4. Каждый инстанс рассылает по WS только тем клиентам, которые подписаны на этот диалог

### Потребление внешних событий (LeafFlow)

```
LeafFlow ──XADD──▶ Redis Stream    ──XREADGROUP──▶ leaf_events_consumer
                   leaf.events                      (consumer group: chat-service)
                                                    │
                                                    ├── user.blocked → запрет отправки
                                                    └── user.updated → обновление данных
```

Consumer использует `XREADGROUP` с consumer group, что обеспечивает:
- Каждое сообщение обрабатывается ровно одним consumer'ом
- `XACK` после успешной обработки
- При сбое сообщение остаётся в pending и будет переобработано

## Быстрый старт

### Docker Compose (рекомендуется)

```bash
cp .env.example .env
# отредактировать .env при необходимости

docker compose up --build
```

Поднимается 5 сервисов:
- `chat-db` — PostgreSQL 16
- `redis` — Redis 7
- `chat-migrations` — одноразовый контейнер, выполняет `alembic upgrade head`
- `chat-api` — FastAPI на порту 8000
- `chat-outbox-worker` — фоновый worker для outbox
- `chat-leaf-consumer` — consumer внешних событий LeafFlow

Swagger UI: http://localhost:8000/docs

### Локальная разработка

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Убедиться, что PostgreSQL и Redis запущены, заполнить .env

# Применить миграции
PYTHONPATH=src alembic upgrade head

# Засеять тестовые данные (опционально)
PYTHONPATH=src python -m chat_service.scripts.seed_dev_data

# Запустить API
python -m chat_service

# В отдельных терминалах:
python -m chat_service.workers.outbox_worker
python -m chat_service.workers.leaf_events_consumer
```

## REST API

### Авторизация

Все эндпоинты (кроме `/healthz`, `/readyz`) требуют JWT Bearer-токен.

В Swagger UI (`/docs`) нажмите кнопку **Authorize** и введите токен.

Генерация токена для разработки:

```bash
python3 -c "
import jwt
# user token
print('USER:', jwt.encode({'sub': '42', 'kind': 'user', 'roles': []}, 'YOUR_JWT_SECRET'))
# admin token
print('ADMIN:', jwt.encode({'sub': '1', 'kind': 'admin', 'roles': ['admin']}, 'YOUR_JWT_SECRET'))
"
```

JWT payload:
```json
{
  "sub": "42",
  "kind": "user",
  "roles": []
}
```

- `sub` — ID пользователя (string)
- `kind` — `user` или `admin`
- `roles` — массив ролей (для admin: `["admin"]`)

### User endpoints

| Method | Path | Описание |
|--------|------|----------|
| POST | `/api/v1/chat/conversations/support` | Получить или создать support-диалог для текущего пользователя |
| GET | `/api/v1/chat/conversations` | Список диалогов пользователя (cursor-пагинация) |
| GET | `/api/v1/chat/conversations/{id}` | Детали конкретного диалога |
| GET | `/api/v1/chat/conversations/{id}/messages` | История сообщений (cursor-пагинация) |
| POST | `/api/v1/chat/conversations/{id}/messages` | Отправить сообщение |

### Admin endpoints

| Method | Path | Описание |
|--------|------|----------|
| GET | `/api/v1/chat/admin/conversations` | Все диалоги с фильтрами (status, assignee, cursor, limit) |
| GET | `/api/v1/chat/admin/conversations/{id}` | Детали диалога |
| PATCH | `/api/v1/chat/admin/conversations/{id}` | Назначить админа или закрыть диалог |
| GET | `/api/v1/chat/admin/conversations/{id}/messages` | История сообщений диалога |
| POST | `/api/v1/chat/admin/conversations/{id}/messages` | Отправить сообщение от админа |

### Cursor-пагинация

Вместо `offset` используется cursor-based пагинация для стабильности при вставках.

```
GET /api/v1/chat/conversations/{id}/messages?limit=50
GET /api/v1/chat/conversations/{id}/messages?cursor=<token>&limit=50
```

`cursor` — это URL-safe Base64 закодированная строка формата `<timestamp>|<uuid>`, указывающая на позицию последнего полученного элемента. Сервер автоматически обрабатывает потерю символов выравнивания (`=`) в конце строки при передаче в URL.

### Пример: отправка сообщения

```bash
curl -X POST http://localhost:8000/api/v1/chat/conversations/{id}/messages \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client_msg_id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "text",
    "body": "Привет!"
  }'
```

`client_msg_id` генерируется клиентом (UUID v4). При повторной отправке с тем же ID дубль не создаётся.

### Пример: назначить диалог на админа

```bash
curl -X PATCH http://localhost:8000/api/v1/chat/admin/conversations/{id} \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"assignee_admin_id": 1}'
```

### Пример: закрыть диалог

```bash
curl -X PATCH http://localhost:8000/api/v1/chat/admin/conversations/{id} \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "closed"}'
```

## WebSocket протокол

### Подключение

```
ws://localhost:8000/ws/chat?token=<JWT>
```

Токен передаётся через query parameter. При невалидном токене соединение закрывается с кодом `4001`.

### Типы сообщений

#### Client -> Server

**ping** — проверка соединения:
```json
{"type": "ping", "data": {}}
```

**subscribe** — подписка на обновления диалога:
```json
{"type": "subscribe", "data": {"conversation_id": "uuid-here"}}
```

**message.send** — отправка сообщения через WS:
```json
{"type": "message.send", "data": {
  "conversation_id": "uuid-here",
  "client_msg_id": "uuid-here",
  "type": "text",
  "body": "Текст сообщения"
}}
```

**mark_read** — отметка о прочтении:
```json
{"type": "mark_read", "data": {
  "conversation_id": "uuid-here",
  "last_message_id": "uuid-here"
}}
```

#### Server -> Client

**pong** — ответ на ping и серверный heartbeat:
```json
{"type": "pong", "data": {}}
```

**message.created** — новое сообщение в диалоге:
```json
{"type": "message.created", "data": {
  "conversation_id": "uuid-here",
  "message": {
    "id": "uuid-here",
    "conversation_id": "uuid-here",
    "sender_kind": "user",
    "sender_id": 42,
    "type": "text",
    "body": "Текст",
    "client_msg_id": "uuid-here",
    "created_at": "2026-02-13T17:00:00+00:00"
  }
}}
```

**conversation.updated** — изменение диалога (назначение, закрытие):
```json
{"type": "conversation.updated", "data": {
  "conversation_id": "uuid-here",
  "action": "assigned",
  "assignee_admin_id": 1
}}
```

**error** — ошибка обработки:
```json
{"type": "error", "data": {"code": "invalid_payload", "detail": "..."}}
```

### Heartbeat

Сервер отправляет `pong` каждые `WS_HEARTBEAT_SECONDS` (по умолчанию 30с). Если клиент не получает heartbeat в течение 2-3 интервалов, соединение считается потерянным.

### Типичный сценарий

1. Клиент подключается: `ws://localhost:8000/ws/chat?token=...`
2. Клиент подписывается на диалог: `{"type": "subscribe", "data": {"conversation_id": "..."}}`
3. Клиент отправляет сообщение: `{"type": "message.send", ...}`
4. Сервер рассылает `message.created` всем подписчикам диалога (включая отправителя)
5. Админ назначает себя на диалог через REST PATCH
6. Все подписчики получают `conversation.updated`

## Схема БД

### conversations
- `id` UUID PK — идентификатор диалога
- `topic_type` text — тип: `support`, `order`
- `topic_id` bigint nullable — привязка к внешней сущности (напр. order_id)
- `status` text — `open` или `closed`
- `assignee_admin_id` bigint nullable — назначенный админ
- `last_message_at` timestamptz nullable — время последнего сообщения (для сортировки)
- `created_at`, `updated_at` timestamptz
- **Индексы:** `(status, last_message_at DESC)`, `(topic_type, topic_id)`

### participants
- `id` UUID PK
- `conversation_id` UUID FK -> conversations
- `kind` text — `user` или `admin`
- `subject_id` bigint — ID пользователя/админа
- `joined_at` timestamptz
- **UNIQUE:** `(conversation_id, kind, subject_id)`
- **Индекс:** `(kind, subject_id, conversation_id)` — быстрый поиск "в каких диалогах участвует user:42"

### messages
- `id` UUID PK
- `conversation_id` UUID FK -> conversations
- `sender_kind` text, `sender_id` bigint — отправитель
- `type` text — `text`, `system`, `attachment`
- `body` text nullable — текст сообщения
- `payload` jsonb nullable — дополнительные данные (для system/attachment)
- `client_msg_id` UUID — ключ идемпотентности, генерируется клиентом
- `created_at` timestamptz
- **UNIQUE:** `(conversation_id, sender_kind, sender_id, client_msg_id)` — защита от дубликатов
- **Индекс:** `(conversation_id, created_at, id)` — быстрая cursor-пагинация

### read_state
- `id` UUID PK
- `conversation_id` UUID FK -> conversations
- `kind` text, `subject_id` bigint — кто прочитал
- `last_read_message_id` UUID FK -> messages nullable
- `updated_at` timestamptz
- **UNIQUE:** `(conversation_id, kind, subject_id)`

### outbox_messages
- `id` bigserial PK
- `event_type` text — например `chat.message_created`
- `payload` jsonb — данные события
- `status` text — `pending` -> `processing` -> `sent` / `failed`
- `attempts` int — количество попыток
- `next_retry_at` timestamptz nullable — время следующей попытки (exponential backoff)
- `created_at`, `updated_at` timestamptz
- **Индекс:** `(status, next_retry_at, created_at)` — для `SELECT ... FOR UPDATE SKIP LOCKED`

## Тесты

```bash
# Запуск всех тестов (env загружается из .env.test автоматически)
pytest

# Только unit
pytest tests/unit -v

# Только integration
pytest tests/integration -v
```

- **Unit-тесты** (`tests/unit/`): сервисы тестируются с in-memory FakeUoW, без БД и Redis
- **Integration-тесты** (`tests/integration/`): REST API через FastAPI TestClient с подменой зависимостей

## Переменные окружения

| Переменная | Обязательна | По умолчанию | Описание |
|------------|-------------|--------------|----------|
| `POSTGRES_USER` | да | — | Пользователь PostgreSQL |
| `POSTGRES_PASSWORD` | да | — | Пароль PostgreSQL |
| `POSTGRES_DB` | да | — | Имя базы данных |
| `DB_HOST` | нет | `localhost` | Хост PostgreSQL (в Docker: `chat-db`) |
| `DB_PORT` | нет | `5432` | Порт PostgreSQL |
| `DB_POOL_SIZE` | нет | `10` | Размер пула соединений |
| `DB_MAX_OVERFLOW` | нет | `20` | Макс. дополнительных соединений сверх пула |
| `REDIS_URL` | нет | `redis://localhost:6379/0` | URL Redis (в Docker: `redis://redis:6379/0`) |
| `JWT_SECRET` | нет | `""` | Секрет для HS256 JWT |
| `JWT_VERIFY_MODE` | нет | `hs256` | Режим верификации: `hs256` или `jwks` |
| `JWKS_URL` | нет | — | URL для JWKS (если `JWT_VERIFY_MODE=jwks`) |
| `CORS_ORIGINS` | нет | `["*"]` | Разрешённые CORS origins |
| `OUTBOX_POLL_INTERVAL` | нет | `1.0` | Интервал опроса outbox (секунды) |
| `OUTBOX_BATCH_SIZE` | нет | `50` | Размер батча outbox worker |
| `OUTBOX_MAX_ATTEMPTS` | нет | `5` | Макс. попыток публикации |
| `WS_HEARTBEAT_SECONDS` | нет | `30` | Интервал WS heartbeat |
| `REDIS_PUBSUB_CHANNEL` | нет | `chat.fanout` | Redis Pub/Sub канал |
| `LEAF_EVENTS_STREAM` | нет | `leaf.events` | Redis Stream для LeafFlow |
| `LEAF_EVENTS_GROUP` | нет | `chat-service` | Consumer group для Stream |

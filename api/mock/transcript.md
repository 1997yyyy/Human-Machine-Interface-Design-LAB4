# Протокол проверки Mock-сервера

Контракт: `api/openapi.yaml` (OpenAPI 3.0.3). Mock-сервер: Prism 5, адрес `http://127.0.0.1:4012`.
Прогон: `python api/mock/smoke.py`, 09.11.2026 01:26.

| Сценарий | Запрос | Код | Итог |
|---|---|---|---|
| Афиша: успешный список | `GET /events?size=2&page=1` | 200 | PASS |
| Создание мероприятия: черновик принят | `POST /events` | 201 | PASS |
| Запись на сессию: место есть | `POST /sessions/c3000000-0000-4000-8000-000000000001/registrations` | 201 | PASS |
| Запись на сессию: свободных мест нет | `POST /sessions/c3000000-0000-4000-8000-000000000001/registrations` | 409 | PASS |
| Запись без токена | `POST /sessions/c3000000-0000-4000-8000-000000000001/registrations` | 401 | PASS |
| Список заявок модерации: другая организация | `GET /moderation/requests` | 403 | PASS |
| Создание мероприятия: поле не прошло проверку | `POST /events` | 422 | PASS |
| Афиша: превышен лимит запросов | `GET /events` | 429 | PASS |

Пройдено **8 из 8**. Коды ошибок запрошены заголовком `Prefer: code=<код>`:
Mock-сервер умеет отдавать любой ответ, описанный в контракте, поэтому проверка
не зависит от случайной генерации.

### Афиша: успешный список

**Запрос**

```http
GET http://127.0.0.1:4012/events?size=2&page=1
Content-Type: application/json
```

**Ответ** — `200`, 81 мс

```json
{
  "items": [
    {
      "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
      "title": "Хакатон FPMI-2026",
      "categoryCode": "it",
      "posterUrl": "string",
      "nearestStartsAt": "2019-08-24T14:15:22Z",
      "freeSeats": 12,
      "status": "Черновик"
    }
  ],
  "total": 42,
  "page": 1
}
```

### Создание мероприятия: черновик принят

**Запрос**

```http
POST http://127.0.0.1:4012/events
Content-Type: application/json
```

```json
{
  "title": "Хакатон FPMI-2026",
  "description": "Сорок восемь часов на прототип учебного сервиса",
  "categoryCode": "it",
  "clubId": "a1000000-0000-4000-8000-000000000001",
  "publishMode": "Свободный",
  "sessions": [
    {
      "startsAt": "2026-11-20T18:00:00+03:00",
      "endsAt": "2026-11-20T21:00:00+03:00",
      "building": "Главный корпус",
      "room": "ауд. 721",
      "capacity": 60
    }
  ]
}
```

**Ответ** — `201`, 39 мс

```json
{
  "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
  "title": "Хакатон FPMI-2026",
  "categoryCode": "it",
  "posterUrl": "string",
  "nearestStartsAt": "2019-08-24T14:15:22Z",
  "freeSeats": 12,
  "status": "Черновик",
  "description": "string",
  "clubId": "4836dcb0-4b52-43b6-8d75-7f08a8fbf3a0",
  "publishMode": "Свободный",
  "capacity": 0,
  "version": 0,
  "sessions": [
    {
      "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
      "startsAt": "2019-08-24T14:15:22Z",
      "endsAt": "2019-08-24T14:15:22Z",
      "building": "string",
      "room": "string",
      "capacity": 0,
      "taken": 0,
      "freeSeats": 0
    }
  ],
  "createdAt": "2019-08-24T14:15:22Z",
  "publishedAt": "2019-08-24T14:15:22Z"
}
```

### Запись на сессию: место есть

**Запрос**

```http
POST http://127.0.0.1:4012/sessions/c3000000-0000-4000-8000-000000000001/registrations
Content-Type: application/json
```

```json
{
  "source": "Приложение"
}
```

**Ответ** — `201`, 10 мс

```json
{
  "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
  "sessionId": "f6567dd8-e069-418e-8893-7d22fcf12459",
  "userId": "2c4a230c-5085-4924-a3e1-25fb4fc5965b",
  "status": "Записан",
  "waitlistPosition": 0,
  "source": "Приложение",
  "ticket": {
    "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
    "registrationId": "cb67e1cd-0e53-4115-9a51-243e5b471e8b",
    "qrPayload": "e5000000-0000-4000-8000-000000000001|c3000000-0000-4000-8000-000000000001|2026-10-21T10:00:00Z",
    "status": "Действителен",
    "issuedAt": "2019-08-24T14:15:22Z",
    "usedAt": "2019-08-24T14:15:22Z"
  },
  "createdAt": "2019-08-24T14:15:22Z",
  "attendedAt": "2019-08-24T14:15:22Z"
}
```

### Запись на сессию: свободных мест нет

**Запрос**

```http
POST http://127.0.0.1:4012/sessions/c3000000-0000-4000-8000-000000000001/registrations
Content-Type: application/json
Prefer: code=409
```

```json
{
  "source": "Приложение"
}
```

**Ответ** — `409`, 26 мс

```json
{
  "code": "NO_SEATS",
  "message": "Свободных мест нет. Можно встать в лист ожидания.",
  "field": null,
  "traceId": "3f2a1b4c-5d6e-4f70-8a91-b2c3d4e5f604"
}
```

### Запись без токена

**Запрос**

```http
POST http://127.0.0.1:4012/sessions/c3000000-0000-4000-8000-000000000001/registrations
Content-Type: application/json
```

```json
{
  "source": "Приложение"
}
```

**Ответ** — `401`, 32 мс

```json
{
  "code": "TOKEN_EXPIRED",
  "message": "Сессия истекла, войдите через CAS заново",
  "field": null,
  "traceId": "3f2a1b4c-5d6e-4f70-8a91-b2c3d4e5f601"
}
```

### Список заявок модерации: другая организация

**Запрос**

```http
GET http://127.0.0.1:4012/moderation/requests
Content-Type: application/json
Prefer: code=403
```

**Ответ** — `403`, 23 мс

```json
{
  "code": "NOT_OWNER",
  "message": "Мероприятие принадлежит другому организатору",
  "field": null,
  "traceId": "3f2a1b4c-5d6e-4f70-8a91-b2c3d4e5f602"
}
```

### Создание мероприятия: поле не прошло проверку

**Запрос**

```http
POST http://127.0.0.1:4012/events
Content-Type: application/json
Prefer: code=422
```

```json
{
  "title": ""
}
```

**Ответ** — `422`, 25 мс

```json
{
  "code": "VALIDATION_FAILED",
  "message": "Поле не прошло проверку формата или ограничения",
  "field": "title",
  "traceId": "3f2a1b4c-5d6e-4f70-8a91-b2c3d4e5f606"
}
```

### Афиша: превышен лимит запросов

**Запрос**

```http
GET http://127.0.0.1:4012/events
Content-Type: application/json
Prefer: code=429
```

**Ответ** — `429`, 15 мс

```json
{
  "code": "RATE_LIMITED",
  "message": "Слишком много запросов, попробуйте через минуту",
  "field": null,
  "traceId": "3f2a1b4c-5d6e-4f70-8a91-b2c3d4e5f607"
}
```

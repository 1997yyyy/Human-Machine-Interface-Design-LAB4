# Проверка MCP-сервера через официальный MCP Inspector

Официальный Inspector (`@modelcontextprotocol/inspector` 2.13.0) умеет работать в
режиме CLI: это тот же клиент, что и web-панель, но без браузера — обмен идёт по
stdio, и каждый ответ протокола виден в терминале. Так проверка воспроизводится
одной строкой и не зависит от снимка экрана.

Среда: MCP Python SDK 2.3.0, Node.js 22, mock-база `mcp/campus.db`.

## Запуск

```bash
python mcp/make_mock_db.py                       # пересобрать mock-базу
npx -y @modelcontextprotocol/inspector --cli python mcp/server.py --method tools/list
```

Web-вариант того же Inspector — `npx @modelcontextprotocol/inspector python mcp/server.py`,
дальше вкладки *Tools*, *Resources*, *Prompts* в браузере.

## Что проверено

| Метод протокола | Запрос | Результат |
|---|---|---|
| `tools/list` | — | 3 инструмента: `create_registration`, `cancel_registration`, `check_in_ticket`, у каждого JSON-схема аргументов и обязательные поля |
| `resources/list` | — | `catalog://events` — каталог с сессиями и свободными местами |
| `resources/templates/list` | — | `registrations://user/{user_id}` — записи конкретного пользователя |
| `prompts/list` | — | `registration_help` с необязательным аргументом `event_title` |
| `tools/call` | `create_registration(s-0002, u-0006)` | билет `t-0f81df63`, `free_seats: 39` |
| `tools/call` | `check_in_ticket(qr)` дважды | первый раз `already_marked: false`, второй — `true`, время отметки не изменилось |
| `tools/call` | `create_registration(s-9999, u-0006)` | `ok: false`, `code: NOT_FOUND`, «Сессия s-9999 не найдена» |
| `resources/read` | `catalog://events` | JSON афиши: два мероприятия, у каждой сессии `capacity`, `taken`, `free_seats` |
| `prompts/get` | `registration_help` | трёхшаговый шаблон: прочитать каталог → проверить места → вызвать инструмент |

## Обмен

### tools/list

```json
{
  "tools": [
    {
      "name": "create_registration",
      "description": "Записать пользователя на сессию. Возвращает билет с QR-кодом...",
      "inputSchema": {
        "type": "object",
        "properties": {
          "session_id": { "title": "Session Id", "type": "string" },
          "user_id": { "title": "User Id", "type": "string" }
        },
        "required": ["session_id", "user_id"]
      }
    },
    { "name": "cancel_registration", "required": ["registration_id"] },
    { "name": "check_in_ticket", "required": ["qr_payload"] }
  ]
}
```

Схемы типизированы: у каждого аргумента есть тип и описание, обязательные поля
перечислены в `required`, поэтому ассистент не может вызвать инструмент
наугад — модели передаются только те параметры, которые сервер объявил.

### tools/call: запись на сессию

```bash
npx -y @modelcontextprotocol/inspector --cli python mcp/server.py \
  --method tools/call --tool-name create_registration \
  --tool-arg session_id=s-0002 --tool-arg user_id=u-0006
```

```json
{
  "content": [{ "type": "text", "text": "{
      \"ok\": true,
      \"registration_id\": \"r-6cf1162b\",
      \"ticket_id\": \"t-0f81df63\",
      \"qr_payload\": \"r-6cf1162b|s-0002|2026-11-08T23:46:17+00:00\",
      \"status\": \"Записан\",
      \"free_seats\": 39,
      \"participant\": \"Морозова Дарья Павловна\"
    }" }],
  "isError": false
}
```

Инструмент возвращает не текстовую фразу, а структурированный результат: агент
показывает билет и остаток мест, не разбирая прозу.

### tools/call: идемпотентность отметки билета

Один и тот же `qr_payload` отправлен дважды:

```json
{ "ok": true, "ticket_id": "t-0f81df63", "marked_at": "...23:55:02...", "already_marked": false }
{ "ok": true, "ticket_id": "t-0f81df63", "marked_at": "...23:55:02...", "already_marked": true }
```

Время отметки не перезаписалось, второй вызов вернул признак повтора.
Идемпотентность подтверждена на уровне протокола, а не только в юнит-тесте.

### tools/call: ошибка состояния

```json
{ "ok": false, "code": "NOT_FOUND", "message": "Сессия s-9999 не найдена" }
```

Ошибки домена возвращаются телом с машинным кодом (как `code` в REST-ошибках
API), а не флагом `isError`: агент читает `code` и выбирает следующий шаг —
предложить другую сессию, лист ожидания или сообщить об отказе.

### resources/read: catalog://events

```json
{
  "id": "e-0002", "title": "Турнир по волейболу", "category": "sport",
  "sessions": [{ "id": "s-0003", "capacity": 20, "taken": 0, "free_seats": 20 }]
}
```

Ресурс отдаёт ровно то, что нужно для ответа «есть ли места»: `free_seats`
считается на стороне сервера, ассистенту не приходится вычитать `taken` из
`capacity`.

### prompts/get: registration_help

```text
1. Прочитай ресурс catalog://events и найди мероприятие и его сессии.
2. Если свободных мест нет — не вызывай create_registration, а предложи лист ожидания.
3. Иначе вызови create_registration(session_id, user_id) и покажи билет с QR-кодом.
```

Шаблон задаёт порядок «сначала данные, потом действие» — так агент не пишет в
базу, не проверив состояние.

## Итог

Inspector видит всё, что объявлено в `server.py`: 3 инструмента с типизированными
схемами, 2 ресурса, 1 шаблон промпта. Проверены успешный вызов, повторный вызов
(идемпотентность) и обращение к несуществующей сессии. Тот же сценарий прогоняется
скриптом `mcp/test_mcp.py` (10 проверок) — Inspector подтверждает, что сервер
корректно работает не только с собственным тестом, но и с эталонным клиентом
протокола.

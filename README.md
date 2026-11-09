# Campus Events — API и MCP-сервер

## Project Name

**Campus Events** — афиша и запись на мероприятия БГУ. Лабораторная работа № 4
по курсу «Проектирование человеко-машинных интерфейсов», группа 13.

## Description

Campus Events заменяет запись на мероприятия через формы и чаты единой афишей с
электронным билетом. Студент видит свободные места, записывается в два действия и
получает билет с QR-кодом, который работает без сети. Организатор публикует
мероприятие за четыре шага, отмечает присутствие сканированием и выгружает список
участников. Администратор рассматривает заявки на публикацию и управляет ролями.
В этой работе к системе добавлен REST API (29 методов), спецификация OpenAPI с
Mock-сервером и MCP-сервер, через который AI-ассистент выполняет те же действия.

## Installation

Требуется Python 3.11+, JDK 17+ (только для пересборки ER-диаграммы), Node.js 18+
(только для MCP Inspector).

```bash
git clone https://github.com/1997yyyy/Human-Machine-Interface-Design-LAB4.git
cd Human-Machine-Interface-Design-LAB4

# 1. Виртуальное окружение и зависимости
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux, macOS
pip install -r requirements.txt

# 2. База данных: вариант А — Docker
docker compose up -d postgres
#    проверить, что ограничения и триггеры действительно работают
docker exec -i campus-events-db psql -U campus -d campus_events < db/verify.sql
# вариант Б — свой PostgreSQL
psql -U postgres -c "CREATE DATABASE campus_events;"
psql -U postgres -d campus_events -f db/schema.sql -f db/seed.sql

# 3. Mock-база для MCP-сервера (SQLite, отдельно от PostgreSQL)
python mcp/make_mock_db.py

# 4. Проверка MCP-сервера без LLM
python mcp/test_mcp.py
```

## Sub modules

| Репозиторий | Назначение |
|---|---|
| `api/` | OpenAPI-спецификация, примеры запросов, Mock-сервер |
| `mcp/` | MCP-сервер: инструменты, ресурсы, шаблон промпта |
| `db/` | Физическая модель: DDL, демонстрационные данные, проверка ограничений |
| `docs/` | Документация: требования, база данных, API, спецификация |

Веб- и мобильное приложение появятся в отдельных репозиториях (`campus-events-web`,
`campus-events-mobile`); ссылки добавляются по мере готовности.

## Usage

**Просмотреть API.** Скопировать `api/openapi.yaml` в Swagger Editor
(editor.swagger.io) или импортировать в SwaggerHub / Postman / Bruno. Mock-сервер
поднимается автоматически при импорте в SwaggerHub; в Bruno — через
`Mock Server → Run`.

**Проверить запросы вручную.** Готовые тела запросов лежат в `api/examples/`.
Минимальная последовательность:

1. `GET /events` — выбрать сессию, запомнить `sessionId`;
2. `POST /sessions/{sid}/registrations` с телом `{"source": "Приложение"}` — получить билет;
3. повторить тот же запрос — ответ `409 ALREADY_REGISTERED`;
4. `POST /checkins/batch` с тем же `qrPayload` дважды — второй ответ `alreadyMarked: true`.

**Подключить MCP-сервер к ассистенту.** Для Claude Desktop в
`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "campus-events": {
      "command": "python",
      "args": ["D:/大四上/ПЧМИ/LAB4/mcp/server.py"],
      "env": { "CAMPUS_DB": "D:/大四上/ПЧМИ/LAB4/mcp/campus.db" }
    }
  }
}
```

Для проверки без ассистента: `npx @modelcontextprotocol/inspector python mcp/server.py`.

Пример диалога: «Запиши меня на хакатон» → ассистент читает `catalog://events`,
находит свободную сессию, вызывает `create_registration` и показывает билет.

## Contributing

Работа индивидуальная, группа 13.

| Участник | Зона ответственности |
|---|---|
| Zeng Yaoxin | Задания 1–5: модель требований, физическая модель БД и DDL, маршруты и эндпоинты, OpenAPI и Mock-сервер, MCP-сервер |

Проект ведётся в GitHub Projects: колонки To do / In progress / To check / Done,
одна задача — один issue. Работа индивидуальная, поэтому коммиты идут в `main`
небольшими шагами «одна задача — один коммит»; при доработке после проверки
заводится отдельная ветка под задачу и сливается обратно после прогона тестов.

![Канбан GitHub Projects: шесть задач по заданиям 1–5 и документации](https://1997yyyy.github.io/Human-Machine-Interface-Design-LAB4/assets/projects-board.png)

Тексты задач для доски — в `docs/issues.md`; каждая задача ссылается на
артефакты репозитория и критерий приёмки.

## Структура репозитория

```
LAB4/
├─ README.md                  этот файл: шесть обязательных разделов
├─ docker-compose.yml         PostgreSQL 16 с автозагрузкой schema.sql и seed.sql
├─ requirements.txt           зависимости Python для MCP-сервера
├─ index.html                 сайт GitHub Pages
├─ assets/                    изображения для README, вики и сайта
│  ├─ use-cases.png           диаграмма вариантов использования (20 UC)
│  ├─ files-diagram.png       диаграмма файлов репозитория
│  ├─ erd-physical.png        ER-диаграмма физической модели
│  ├─ presentation.pdf        презентация проекта, 12 слайдов
│  ├─ projects-board.png      канбан GitHub Projects
│  ├─ mock/                   скриншоты ответов Mock-сервера в Bruno (201, 409, 403)
│  └─ mcp/                    снимок MCP Inspector
├─ db/
│  ├─ erd.puml                исходник ER-диаграммы
│  ├─ schema.sql              DDL: 14 таблиц, 13 перечислений, индексы, триггеры
│  ├─ seed.sql                демонстрационные данные
│  └─ verify.sql              15 проверок ограничений и триггеров на живой СУБД
├─ api/
│  ├─ openapi.yaml            спецификация OpenAPI 3.0.3, 29 операций
│  ├─ index.html              читаемая версия спецификации для сайта
│  ├─ examples/               тела запросов для проверки на Mock-сервере
│  └─ mock/                   Mock-сервер: инструкция, коллекция запросов, протокол прогона
├─ mcp/
│  ├─ server.py               MCP-сервер: 3 инструмента, 2 ресурса, 1 промпт
│  ├─ make_mock_db.py         сборка mock-базы SQLite
│  ├─ test_mcp.py             проверка без LLM-клиента (10 сценариев)
│  ├─ inspector-cli.md        протокол проверки через официальный MCP Inspector
│  ├─ campus.db               mock-база (генерируется)
│  └─ README.md               инструкция по развёртыванию MCP-сервера
├─ docs/                      страницы вики
│  ├─ 01-home.md              главная
│  ├─ 02-requirements.md      функциональные требования и реестр UC
│  ├─ 03-files.md             диаграмма файлов приложения
│  ├─ 04-spec.md              дополнительная спецификация
│  ├─ 05-database.md          схема БД и словарь полей
│  ├─ 06-api.md               маршруты, конечные точки, коды ошибок, скриншоты Bruno
│  ├─ 07-presentation.md      презентация проекта
│  ├─ 08-mcp.md               MCP-сервер: инструменты, ресурсы, проверка в Inspector
│  └─ issues.md               тексты задач для GitHub Projects
└─ tools/
   ├─ gen_db.py               генератор DDL, словаря полей и ER из одной модели
   └─ push_wiki.ps1           публикация docs/ в GitHub Wiki
```

# -*- coding: utf-8 -*-
"""Прогон Mock-сервера по api/openapi.yaml и запись протокола в transcript.md.

Запуск (Mock-сервер уже поднят, см. README.md):
    python api/mock/smoke.py                 # → api/mock/transcript.md
    MOCK_URL=http://127.0.0.1:4012 python api/mock/smoke.py

Сценарии покрывают требования задания 4: успешные ответы (200/201) и ошибки,
которые обязан описывать контракт (401, 403, 409, 422, 429). Конкретный код
ошибки запрашивается заголовком `Prefer: code=<код>` — так Mock-сервер отдаёт
не случайный ответ, а именно тот, который нужно показать.
"""
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "transcript.md")
BASE = os.environ.get("MOCK_URL", "http://127.0.0.1:4010").rstrip("/")

SID = "c3000000-0000-4000-8000-000000000001"
TID = "f6000000-0000-4000-8000-000000000001"
CLUB = "a1000000-0000-4000-8000-000000000001"

EVENT_BODY = {
    "title": "Хакатон FPMI-2026",
    "description": "Сорок восемь часов на прототип учебного сервиса",
    "categoryCode": "it",
    "clubId": CLUB,
    "publishMode": "Свободный",
    "sessions": [{
        "startsAt": "2026-11-20T18:00:00+03:00",
        "endsAt": "2026-11-20T21:00:00+03:00",
        "building": "Главный корпус",
        "room": "ауд. 721",
        "capacity": 60,
    }],
}

REG_BODY = {"source": "Приложение"}

AUTH = {"Authorization": "Bearer mock-access-token"}

# (подпись, ожидаемый код, метод, путь, тело, заголовки)
CASES = [
    ("Афиша: успешный список",
     200, "GET", "/events?size=2&page=1", None, {}),
    ("Создание мероприятия: черновик принят",
     201, "POST", "/events", EVENT_BODY, AUTH),
    ("Запись на сессию: место есть",
     201, "POST", "/sessions/%s/registrations" % SID, REG_BODY, AUTH),
    ("Запись на сессию: свободных мест нет",
     409, "POST", "/sessions/%s/registrations" % SID, REG_BODY,
     dict(AUTH, **{"Prefer": "code=409"})),
    ("Запись без токена",
     401, "POST", "/sessions/%s/registrations" % SID, REG_BODY, {}),
    ("Список заявок модерации: другая организация",
     403, "GET", "/moderation/requests", None,
     dict(AUTH, **{"Prefer": "code=403"})),
    ("Создание мероприятия: поле не прошло проверку",
     422, "POST", "/events", {"title": ""}, dict(AUTH, **{"Prefer": "code=422"})),
    ("Афиша: превышен лимит запросов",
     429, "GET", "/events", None, {"Prefer": "code=429"}),
]


def call(method, path, body, headers):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    for k, v in headers.items():
        req.add_header(k, v)
    started = time.time()
    try:
        r = urllib.request.urlopen(req, timeout=20)
        code, raw, why = r.status, r.read().decode("utf-8"), ""
    except urllib.error.HTTPError as e:
        code, raw, why = e.code, e.read().decode("utf-8"), str(e.reason)
    except urllib.error.URLError as e:
        print("Mock-сервер недоступен:", e.reason)
        print("Поднимите его: npx @stoplight/prism-cli mock api/openapi.yaml -p 4010")
        sys.exit(1)
    ms = (time.time() - started) * 1000
    try:
        pretty = json.dumps(json.loads(raw), ensure_ascii=False, indent=2)
    except ValueError:
        pretty = raw or why
    return code, pretty, ms


def main():
    rows, blocks, ok = [], [], 0
    for title, expect, method, path, body, headers in CASES:
        code, pretty, ms = call(method, path, body, headers)
        mark = "PASS" if code == expect else "FAIL"
        ok += code == expect
        rows.append("| %s | `%s %s` | %d | %s |" % (title, method, path, code, mark))
        req_headers = {"Content-Type": "application/json"}
        req_headers.update(headers)
        blocks.append("### %s\n\n**Запрос**\n\n```http\n%s %s%s\n%s\n```\n" % (
            title, method, BASE, path,
            "\n".join("%s: %s" % kv for kv in req_headers.items() if kv[0] != "Authorization")))
        if body is not None:
            blocks.append("```json\n%s\n```\n" % json.dumps(body, ensure_ascii=False, indent=2))
        blocks.append("**Ответ** — `%d`, %.0f мс\n\n```json\n%s\n```\n" % (code, ms, pretty))

    head = """# Протокол проверки Mock-сервера

Контракт: `api/openapi.yaml` (OpenAPI 3.0.3). Mock-сервер: Prism 5, адрес `%s`.
Прогон: `python api/mock/smoke.py`, %s.

| Сценарий | Запрос | Код | Итог |
|---|---|---|---|
%s

Пройдено **%d из %d**. Коды ошибок запрошены заголовком `Prefer: code=<код>`:
Mock-сервер умеет отдавать любой ответ, описанный в контракте, поэтому проверка
не зависит от случайной генерации.

""" % (BASE, time.strftime("%d.%m.%Y %H:%M"), "\n".join(rows), ok, len(CASES))

    io.open(OUT, "w", encoding="utf-8", newline="\n").write(head + "\n".join(blocks))
    print("Пройдено %d из %d → %s" % (ok, len(CASES), OUT))
    for r in rows:
        print("  " + r)


if __name__ == "__main__":
    main()

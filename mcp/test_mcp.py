# -*- coding: utf-8 -*-
"""Проверка MCP-сервера без LLM-клиента: те же вызовы, что делает инспектор.

Запуск:  python mcp/test_mcp.py
Печатает список примитивов и результат каждого сценария.
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import make_mock_db  # noqa: E402
import server  # noqa: E402


def show(title, value):
    print(f"\n=== {title} ===")
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


async def main():
    db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "campus.db")
    make_mock_db.main(db)
    server.DB_PATH = db

    tools = await server.mcp.list_tools()
    print("Инструменты:", [t.name for t in tools])
    res = await server.mcp.list_resources()
    print("Ресурсы:", [str(r.uri) for r in res])
    tmpl = await server.mcp.list_resource_templates()
    print("Шаблоны ресурсов:", [getattr(t, "uri_template", getattr(t, "uriTemplate", "")) for t in tmpl])
    prompts = await server.mcp.list_prompts()
    print("Промпты:", [p.name for p in prompts])

    async def call(name, args):
        result = await server.mcp.call_tool(name, args)
        if getattr(result, "structuredContent", None):
            payload = result.structuredContent
            if isinstance(payload, dict) and set(payload) == {"result"}:
                payload = payload["result"]
        else:
            payload = [c.text for c in result.content]
        return payload

    show("1. Запись на s-0001 (2 из 3 занято)", await call(
        "create_registration", {"session_id": "s-0001", "user_id": "u-0005"}))
    show("2. Повторная запись того же пользователя", await call(
        "create_registration", {"session_id": "s-0001", "user_id": "u-0005"}))
    show("3. Запись, когда мест не осталось", await call(
        "create_registration", {"session_id": "s-0001", "user_id": "u-0006"}))
    show("4. Отмена записи r-0001 (место уходит в очередь)", await call(
        "cancel_registration", {"registration_id": "r-0001", "reason": "Передумал"}))
    show("5. Отметка билета t-0002", await call(
        "check_in_ticket", {"qr_payload": "r-0002|s-0001|2026-11-08T12:00:00Z"}))
    show("6. Повторная отметка того же билета", await call(
        "check_in_ticket", {"qr_payload": "r-0002|s-0001|2026-11-08T12:00:00Z"}))
    show("7. Отметка отозванного билета", await call(
        "check_in_ticket", {"qr_payload": "r-0003|s-0001|2026-11-08T12:00:00Z"}))

    cat = await server.mcp.read_resource("catalog://events")
    body = cat[0].content if cat else ""
    print("\n=== 8. Ресурс catalog://events (первые 600 символов) ===")
    print(json.dumps(json.loads(body), ensure_ascii=False, indent=2)[:600])

    regs = await server.mcp.read_resource("registrations://user/u-0001")
    print("\n=== 9. Ресурс registrations://user/u-0001 ===")
    print(regs[0].content if regs else "")

    pr = await server.mcp.get_prompt("registration_help", {"event_title": "Хакатон FPMI-2026"})
    print("\n=== 10. Промпт registration_help ===")
    print(pr.messages[0].content.text if hasattr(pr.messages[0].content, "text") else pr.messages[0])


if __name__ == "__main__":
    asyncio.run(main())

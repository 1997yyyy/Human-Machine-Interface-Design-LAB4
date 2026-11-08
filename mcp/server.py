# -*- coding: utf-8 -*-
"""MCP-сервер проекта Campus Events (задание 5, MVP).

Даёт AI-ассистенту три действия и два источника данных по афише студенческих
мероприятий: записать на сессию, отменить запись, отметить билет и прочитать
каталог/свои записи.

Запуск (stdio, как требуют Claude Desktop, Cursor и MCP Inspector):
    python mcp/server.py

Проверка через официальный инспектор:
    npx @modelcontextprotocol/inspector python mcp/server.py

Переменные окружения:
    CAMPUS_DB — путь к mock-базе; по умолчанию mcp/campus.db
"""
import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

try:  # MCP SDK 1.x
    from mcp.server.fastmcp import FastMCP as _Server
except ImportError:  # MCP SDK 2.x: FastMCP переименован в MCPServer
    from mcp.server.mcpserver import MCPServer as _Server

DB_PATH = os.environ.get(
    "CAMPUS_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "campus.db"))

mcp = _Server(
    "campus-events",
    instructions=(
        "Сервер афиши Campus Events. Запись оформляется действием create_registration, "
        "отмена — cancel_registration, проход — check_in_ticket. Перед записью прочитайте "
        "ресурс catalog://events, чтобы узнать свободные места. Если действие вернуло "
        "code=NO_SEATS, предложите пользователю лист ожидания, а не повторяйте вызов."
    ),
)


# ------------------------------------------------------------------ доступ к данным

def _db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _err(code: str, message: str, **extra: Any) -> dict:
    """Единый формат ошибки — как в OpenAPI-спецификации (docs/06-api.md)."""
    payload = {"ok": False, "code": code, "message": message}
    payload.update(extra)
    return payload


# ------------------------------------------------------------------ инструменты

@mcp.tool()
def create_registration(session_id: str, user_id: str) -> dict:
    """Записать пользователя на сессию и выдать билет.

    Args:
        session_id: идентификатор сессии, например s-0001.
        user_id: идентификатор пользователя, например u-0001.

    Returns:
        ok, registration_id, ticket_id, qr_payload, free_seats — либо code и message.
        Коды ошибок: NOT_FOUND, ALREADY_REGISTERED, NO_SEATS, SESSION_CLOSED.
    """
    con = _db()
    try:
        s = con.execute(
            "SELECT s.*, e.status AS event_status, e.title FROM session s "
            "JOIN event e ON e.id = s.event_id WHERE s.id = ?", (session_id,)).fetchone()
        if s is None:
            return _err("NOT_FOUND", f"Сессия {session_id} не найдена")
        if s["event_status"] not in ("Опубликовано",):
            return _err("SESSION_CLOSED",
                        f"Мероприятие «{s['title']}» не опубликовано, запись закрыта")
        u = con.execute("SELECT id, full_name FROM app_user WHERE id = ?", (user_id,)).fetchone()
        if u is None:
            return _err("NOT_FOUND", f"Пользователь {user_id} не найден")

        dup = con.execute(
            "SELECT id, status FROM registration WHERE session_id = ? AND user_id = ? "
            "AND status <> 'Отменено'", (session_id, user_id)).fetchone()
        if dup is not None:
            return _err("ALREADY_REGISTERED", "Пользователь уже записан на эту сессию",
                        registration_id=dup["id"], status=dup["status"])

        if s["taken"] >= s["capacity"]:
            wait = con.execute(
                "SELECT count(*) FROM registration WHERE session_id = ? AND status = 'В листе ожидания'",
                (session_id,)).fetchone()[0]
            return _err("NO_SEATS", "Свободных мест нет",
                        free_seats=0, waitlist_length=wait)

        reg_id = f"r-{uuid.uuid4().hex[:8]}"
        tick_id = f"t-{uuid.uuid4().hex[:8]}"
        stamp = _now()
        qr = f"{reg_id}|{session_id}|{stamp}"
        con.execute(
            "INSERT INTO registration (id, session_id, user_id, status, created_at) "
            "VALUES (?,?,?,'Записан',?)", (reg_id, session_id, user_id, stamp))
        con.execute(
            "INSERT INTO ticket (id, registration_id, qr_payload, status, issued_at) "
            "VALUES (?,?,?,'Действителен',?)", (tick_id, reg_id, qr, stamp))
        con.execute("UPDATE session SET taken = taken + 1 WHERE id = ?", (session_id,))
        con.commit()
        return {"ok": True, "registration_id": reg_id, "ticket_id": tick_id,
                "qr_payload": qr, "status": "Записан",
                "free_seats": s["capacity"] - s["taken"] - 1,
                "participant": u["full_name"]}
    finally:
        con.close()


@mcp.tool()
def cancel_registration(registration_id: str, reason: str = "") -> dict:
    """Отменить запись, отозвать билет и передать место следующему в очереди.

    Args:
        registration_id: идентификатор записи, например r-0001.
        reason: необязательная причина отмены для журнала.

    Returns:
        ok, status, freed_seat, offer_to — либо code и message.
        Коды ошибок: NOT_FOUND, ALREADY_CANCELLED, TICKET_USED.
    """
    con = _db()
    try:
        r = con.execute("SELECT * FROM registration WHERE id = ?", (registration_id,)).fetchone()
        if r is None:
            return _err("NOT_FOUND", f"Запись {registration_id} не найдена")
        if r["status"] == "Отменено":
            return _err("ALREADY_CANCELLED", "Запись уже отменена", status="Отменено")
        if r["attended_at"] is not None:
            return _err("TICKET_USED", "Билет уже использован, отменить запись нельзя")

        stamp = _now()
        con.execute("UPDATE registration SET status='Отменено', cancelled_at=? WHERE id=?",
                    (stamp, registration_id))
        con.execute("UPDATE ticket SET status='Отозван' WHERE registration_id=?", (registration_id,))

        freed = r["status"] in ("Записан", "Посетил")
        if freed:
            con.execute("UPDATE session SET taken = max(taken - 1, 0) WHERE id = ?",
                        (r["session_id"],))

        offer_to = None
        if freed:
            nxt = con.execute(
                "SELECT id, user_id FROM registration WHERE session_id = ? "
                "AND status = 'В листе ожидания' ORDER BY waitlist_position LIMIT 1",
                (r["session_id"],)).fetchone()
            if nxt is not None:
                until = (datetime.now(timezone.utc) + timedelta(minutes=30)).replace(
                    microsecond=0).isoformat()
                con.execute(
                    "INSERT INTO seat_offer (id, session_id, registration_id, issued_at, expires_at) "
                    "VALUES (?,?,?,?,?)",
                    (f"o-{uuid.uuid4().hex[:8]}", r["session_id"], nxt["id"], stamp, until))
                offer_to = {"registration_id": nxt["id"], "user_id": nxt["user_id"],
                            "expires_at": until}

        con.commit()
        return {"ok": True, "status": "Отменено", "freed_seat": freed,
                "reason": reason or None, "offer_to": offer_to}
    finally:
        con.close()


@mcp.tool()
def check_in_ticket(qr_payload: str) -> dict:
    """Отметить присутствие по строке из QR-кода. Операция идемпотентна.

    Args:
        qr_payload: строка, считанная с QR-кода билета.

    Returns:
        ok, ticket_id, participant, marked_at, already_marked — либо code и message.
        Коды ошибок: NOT_FOUND, TICKET_REVOKED.
    """
    con = _db()
    try:
        row = con.execute(
            "SELECT t.*, r.status AS reg_status, r.user_id, u.full_name "
            "FROM ticket t JOIN registration r ON r.id = t.registration_id "
            "JOIN app_user u ON u.id = r.user_id WHERE t.qr_payload = ?",
            (qr_payload,)).fetchone()
        if row is None:
            return _err("NOT_FOUND", "Билет с такой строкой QR не найден")
        if row["status"] == "Отозван":
            return _err("TICKET_REVOKED", "Билет отозван, запись была отменена")
        if row["status"] == "Использован":
            return {"ok": True, "ticket_id": row["id"], "participant": row["full_name"],
                    "marked_at": row["used_at"], "already_marked": True}

        stamp = _now()
        con.execute("UPDATE ticket SET status='Использован', used_at=? WHERE id=?",
                    (stamp, row["id"]))
        con.execute("UPDATE registration SET status='Посетил', attended_at=? WHERE id=?",
                    (stamp, row["registration_id"]))
        con.commit()
        return {"ok": True, "ticket_id": row["id"], "participant": row["full_name"],
                "marked_at": stamp, "already_marked": False}
    finally:
        con.close()


# ------------------------------------------------------------------ ресурсы

@mcp.resource("catalog://events")
def catalog_events() -> str:
    """Каталог опубликованных мероприятий с сессиями и свободными местами."""
    con = _db()
    try:
        events = con.execute(
            "SELECT id, title, category_code, description FROM event "
            "WHERE status = 'Опубликовано' ORDER BY title").fetchall()
        out = []
        for e in events:
            sessions = con.execute(
                "SELECT id, starts_at, building, room, capacity, taken FROM session "
                "WHERE event_id = ? ORDER BY starts_at", (e["id"],)).fetchall()
            out.append({
                "id": e["id"], "title": e["title"], "category": e["category_code"],
                "description": e["description"],
                "sessions": [
                    {"id": s["id"], "starts_at": s["starts_at"], "building": s["building"],
                     "room": s["room"], "capacity": s["capacity"], "taken": s["taken"],
                     "free_seats": s["capacity"] - s["taken"]}
                    for s in sessions],
            })
        return json.dumps({"events": out}, ensure_ascii=False, indent=2)
    finally:
        con.close()


@mcp.resource("registrations://user/{user_id}")
def user_registrations(user_id: str) -> str:
    """Записи пользователя со статусами и признаком действующего билета.

    Персональные данные не отдаются: только ФИО, статус и время —
    это то, что нужно ассистенту для ответа, и ничего сверх.
    """
    con = _db()
    try:
        rows = con.execute(
            "SELECT r.id, r.status, r.created_at, r.attended_at, s.id AS session_id, "
            "s.starts_at, e.title, t.status AS ticket_status "
            "FROM registration r JOIN session s ON s.id = r.session_id "
            "JOIN event e ON e.id = s.event_id "
            "LEFT JOIN ticket t ON t.registration_id = r.id "
            "WHERE r.user_id = ? ORDER BY r.created_at DESC", (user_id,)).fetchall()
        return json.dumps(
            {"user_id": user_id, "registrations": [dict(x) for x in rows]},
            ensure_ascii=False, indent=2)
    finally:
        con.close()


# ------------------------------------------------------------------ шаблон промпта

@mcp.prompt()
def registration_help(event_title: str = "") -> str:
    """Шаблон диалога «помоги записаться»: сначала данные, потом действие."""
    return (
        "Пользователь хочет записаться на мероприятие" +
        (f" «{event_title}»" if event_title else "") + ".\n\n"
        "Порядок работы:\n"
        "1. Прочитай ресурс catalog://events и найди мероприятие и его сессии.\n"
        "2. Если свободных мест нет — не вызывай create_registration, а предложи лист ожидания.\n"
        "3. Иначе вызови create_registration(session_id, user_id) и покажи билет.\n"
        "4. Если вернулся код NO_SEATS — объясни причину и предложи очередь.\n"
        "5. Если ALREADY_REGISTERED — покажи существующую запись, не создавай новую.\n"
        "Отвечай кратко, на русском, с указанием даты, времени и аудитории."
    )


if __name__ == "__main__":
    mcp.run()

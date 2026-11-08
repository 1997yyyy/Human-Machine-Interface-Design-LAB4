# -*- coding: utf-8 -*-
"""Mock-база SQLite для MCP-сервера (задание 5).

Физическая модель ЛР № 4 написана для PostgreSQL (перечисления, частичные
индексы, триггеры). Для MVP MCP-сервера достаточно подмножества: четыре
таблицы и одно правило — «активных записей не больше вместимости сессии».
Схема повторяет схему из db/schema.sql по смыслу, но без типов СУБД.

Запуск:  python mcp/make_mock_db.py [путь к campus.db]
"""
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

DDL = """
DROP TABLE IF EXISTS ticket;
DROP TABLE IF EXISTS seat_offer;
DROP TABLE IF EXISTS registration;
DROP TABLE IF EXISTS session;
DROP TABLE IF EXISTS event;
DROP TABLE IF EXISTS app_user;

CREATE TABLE app_user (
    id          TEXT PRIMARY KEY,
    full_name   TEXT NOT NULL,
    email       TEXT,
    study_group TEXT,
    role        TEXT NOT NULL DEFAULT 'Студент'
);

CREATE TABLE event (
    id            TEXT PRIMARY KEY,
    title         TEXT NOT NULL,
    description   TEXT,
    category_code TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'Опубликовано'
);

CREATE TABLE session (
    id         TEXT PRIMARY KEY,
    event_id   TEXT NOT NULL REFERENCES event(id),
    starts_at  TEXT NOT NULL,
    building   TEXT,
    room       TEXT,
    capacity   INTEGER NOT NULL CHECK (capacity >= 1),
    taken      INTEGER NOT NULL DEFAULT 0 CHECK (taken >= 0 AND taken <= capacity)
);

CREATE TABLE registration (
    id                TEXT PRIMARY KEY,
    session_id        TEXT NOT NULL REFERENCES session(id),
    user_id           TEXT NOT NULL REFERENCES app_user(id),
    status            TEXT NOT NULL DEFAULT 'Записан',
    waitlist_position INTEGER,
    created_at        TEXT NOT NULL,
    cancelled_at      TEXT,
    attended_at       TEXT
);

CREATE UNIQUE INDEX ux_registration_active
    ON registration (session_id, user_id) WHERE status <> 'Отменено';

CREATE TABLE seat_offer (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL REFERENCES session(id),
    registration_id TEXT NOT NULL REFERENCES registration(id),
    issued_at       TEXT NOT NULL,
    expires_at      TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'Выдано'
);

CREATE TABLE ticket (
    id              TEXT PRIMARY KEY,
    registration_id TEXT NOT NULL UNIQUE REFERENCES registration(id),
    qr_payload      TEXT NOT NULL UNIQUE,
    status          TEXT NOT NULL DEFAULT 'Действителен',
    issued_at       TEXT NOT NULL,
    used_at         TEXT
);
"""


def main(path: str) -> None:
    con = sqlite3.connect(path)
    con.executescript(DDL)

    now = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)

    users = [
        ("u-0001", "Иванов Иван Иванович", "ivanov@bsu.by", "4 курс, 1 группа", "Студент"),
        ("u-0002", "Петрова Анна Сергеевна", "petrova@bsu.by", "3 курс, 2 группа", "Студент"),
        ("u-0003", "Сидоров Павел Олегович", "sidorov@bsu.by", "4 курс, 1 группа", "Организатор"),
        ("u-0004", "Лукашевич Егор Дмитриевич", "lukashev@bsu.by", "2 курс, 3 группа", "Студент"),
        ("u-0005", "Ковалёв Артём Игоревич", "kovalev@bsu.by", "1 курс, 4 группа", "Студент"),
        ("u-0006", "Морозова Дарья Павловна", "morozova@bsu.by", "3 курс, 1 группа", "Студент"),
    ]
    con.executemany("INSERT INTO app_user VALUES (?,?,?,?,?)", users)

    events = [
        ("e-0001", "Хакатон FPMI-2026", "Сорок восемь часов на прототип учебного сервиса", "it", "Опубликовано"),
        ("e-0002", "Турнир по волейболу", "Смешанные команды по шесть человек", "sport", "Опубликовано"),
        ("e-0003", "Лекция «Архитектура C4 на практике»", "Разбор уровней C4", "it", "На модерации"),
    ]
    con.executemany("INSERT INTO event VALUES (?,?,?,?,?)", events)

    sessions = [
        ("s-0001", "e-0001", (now + timedelta(days=12)).isoformat(), "Главный корпус", "ауд. 721", 3, 0),
        ("s-0002", "e-0001", (now + timedelta(days=13)).isoformat(), "Главный корпус", "Коворкинг", 40, 0),
        ("s-0003", "e-0002", (now + timedelta(days=17)).isoformat(), "Спорткомплекс", "Зал 2", 20, 0),
    ]
    con.executemany("INSERT INTO session VALUES (?,?,?,?,?,?,?)", sessions)

    regs = [
        ("r-0001", "s-0001", "u-0001", "Записан", None, now.isoformat(), None, None),
        ("r-0002", "s-0001", "u-0002", "Записан", None, now.isoformat(), None, None),
        ("r-0003", "s-0001", "u-0004", "В листе ожидания", 1, now.isoformat(), None, None),
    ]
    con.executemany("INSERT INTO registration VALUES (?,?,?,?,?,?,?,?)", regs)
    con.execute("UPDATE session SET taken = 2 WHERE id = 's-0001'")

    tickets = [
        ("t-0001", "r-0001", "r-0001|s-0001|2026-11-08T12:00:00Z", "Действителен", now.isoformat(), None),
        ("t-0002", "r-0002", "r-0002|s-0001|2026-11-08T12:00:00Z", "Действителен", now.isoformat(), None),
        ("t-0003", "r-0003", "r-0003|s-0001|2026-11-08T12:00:00Z", "Отозван", now.isoformat(), None),
    ]
    con.executemany("INSERT INTO ticket VALUES (?,?,?,?,?,?)", tickets)

    con.commit()
    con.close()
    print(f"создана mock-база: {path}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "campus.db")
    main(target)

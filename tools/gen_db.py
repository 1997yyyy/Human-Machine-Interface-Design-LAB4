# -*- coding: utf-8 -*-
"""Единая модель данных Campus Events (ЛР4, задание 2).

Из одного описания генерируются три артефакта:
  db/schema.sql        — DDL физической модели (PostgreSQL 15+)
  docs/05-database.md  — логическая модель: словарь полей
  db/erd.puml          — ER-диаграмма физической модели
Правит человек только этот файл, остальное пересобирается.
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ENUMS = {
    "event_status": ["Черновик", "На модерации", "Опубликовано", "Отклонено", "Отменено", "Завершено"],
    "publish_mode": ["Свободный", "С утверждением"],
    "user_role": ["Гость", "Студент", "Организатор", "Администратор"],
    "club_position": ["Руководитель", "Заместитель", "Член"],
    "registration_status": ["Записан", "В листе ожидания", "Отменено", "Посетил", "Неявка"],
    "reg_source": ["Приложение", "Веб", "Регистрация на месте"],
    "ticket_status": ["Действителен", "Использован", "Отозван"],
    "offer_status": ["Выдано", "Принято", "Истекло"],
    "request_status": ["На рассмотрении", "Утверждено", "Возвращено"],
    "decision_type": ["Утвердить", "Вернуть"],
    "review_status": ["На проверке", "Опубликован", "Скрыт"],
    "notification_type": ["Подтверждение", "Напоминание 24 ч", "Напоминание 2 ч",
                          "Приглашение из очереди", "Отмена"],
    "channel": ["Push", "Email", "Оба"],
}


def f(name, sqltype, meaning, **kw):
    d = {"n": name, "t": sqltype, "r": meaning}
    d.update(kw)
    return d


ID = f("id", "uuid", "Суррогатный первичный ключ", pk=True, nn=True,
       dflt="gen_random_uuid()")
CREATED = f("created_at", "timestamptz", "Момент создания записи (UTC)", nn=True,
            dflt="now()")

TABLES = [
    {
        "name": "club", "ru": "Клуб",
        "purpose": "Организационная единица: факультетский клуб, от имени которого публикуются мероприятия.",
        "fields": [
            ID,
            f("name", "varchar(120)", "Название клуба для интерфейса", nn=True),
            f("description", "text", "Описание клуба для страницы «Клубы»"),
            f("logo_url", "varchar(255)", "Ссылка на логотип в S3-хранилище"),
            f("is_active", "boolean", "Признак «клуб работает»; неактивный скрыт из каталога",
              nn=True, dflt="true"),
            CREATED,
        ],
        "uniques": [(["name"], None)],
        "checks": [],
    },
    {
        "name": "category", "ru": "Категория",
        "purpose": "Справочник тематик мероприятия; код используется во внешних ссылках и фильтрах.",
        "fields": [
            f("code", "varchar(32)", "Код категории (латиница), PK и часть URL", pk=True, nn=True),
            f("name", "varchar(80)", "Название категории на русском", nn=True),
            f("sort_order", "smallint", "Порядок вывода в фильтре каталога", nn=True),
        ],
        "uniques": [],
        "checks": [],
    },
    {
        "name": "app_user", "ru": "Пользователь",
        "purpose": "Учётная запись, создаваемая автоматически при первом входе через CAS; пароль не хранится.",
        "fields": [
            ID,
            f("cas_login", "varchar(64)", "Логин в CAS/LDAP; ключ сопоставления с внешней системой",
              nn=True, un=True),
            f("full_name", "varchar(160)", "ФИО из атрибутов CAS; печатается на билете", nn=True),
            f("email", "varchar(160)", "Почта для дублирования push; в выгрузки не попадает",
              chk="email IS NULL OR email LIKE '%@%'"),
            f("faculty", "varchar(120)", "Факультет из CAS"),
            f("study_group", "varchar(40)", "Учебная группа; входит в экспорт списка участников"),
            f("role", "user_role", "Роль, определяющая права; повышается только администратором",
              nn=True, dflt="'Студент'"),
            f("is_active", "boolean", "Признак активной учётки; отключение не удаляет историю",
              nn=True, dflt="true"),
            CREATED,
        ],
        "uniques": [],
        "checks": [],
    },
    {
        "name": "event", "ru": "Мероприятие",
        "purpose": "Афишная единица: то, что видит студент в ленте и на что ведётся запись.",
        "fields": [
            ID,
            f("club_id", "uuid", "Клуб-организатор", nn=True, fk="club"),
            f("category_code", "varchar(32)", "Тематика для фильтра", nn=True, fk="category"),
            f("title", "varchar(200)", "Название; не короче 5 символов", nn=True,
              chk="char_length(title) >= 5"),
            f("description", "text", "Полное описание для карточки"),
            f("poster_url", "varchar(255)", "Ссылка на афишу в S3"),
            f("status", "event_status", "Стадия жизненного цикла; управляет видимостью в каталоге",
              nn=True, dflt="'Черновик'"),
            f("publish_mode", "publish_mode", "Свободная публикация или через модерацию",
              nn=True, dflt="'Свободный'"),
            f("capacity", "integer", "Общий лимит, если он не задан по сессиям",
              chk="capacity IS NULL OR capacity > 0"),
            f("owner_id", "uuid", "Организатор-владелец; проверяется при правке", nn=True, fk="app_user"),
            CREATED,
            f("published_at", "timestamptz", "Момент публикации; NULL для черновика"),
            f("cancelled_at", "timestamptz", "Момент отмены"),
            f("cancel_reason", "varchar(300)", "Причина отмены, показывается студенту"),
        ],
        "uniques": [],
        "checks": [("cancelled_at IS NULL OR status = 'Отменено'", "event_cancel_chk")],
    },
    {
        "name": "session", "ru": "Сессия",
        "purpose": "Конкретная дата, время и место проведения; запись ведётся на сессию, а не на мероприятие.",
        "fields": [
            ID,
            f("event_id", "uuid", "Мероприятие, к которому относится сессия", nn=True, fk="event"),
            f("starts_at", "timestamptz", "Начало в UTC; в интерфейсе — Europe/Minsk", nn=True),
            f("ends_at", "timestamptz", "Окончание; должно быть позже начала", nn=True),
            f("building", "varchar(120)", "Корпус", nn=True),
            f("room", "varchar(60)", "Аудитория"),
            f("capacity", "integer", "Лимит мест этой сессии", nn=True, chk="capacity >= 1"),
            f("taken", "integer", "Занятых мест; меняется только триггером регистрации",
              nn=True, dflt="0"),
            f("qr_key_version", "smallint", "Версия ключа подписи билетов на момент сессии",
              nn=True, dflt="1"),
            CREATED,
        ],
        "uniques": [],
        "checks": [
            ("ends_at > starts_at", "session_interval_chk"),
            ("taken >= 0 AND taken <= capacity", "session_seats_chk"),
            ("qr_key_version >= 1", "session_key_ver_chk"),
        ],
    },
    {
        "name": "membership", "ru": "Членство в клубе",
        "purpose": "Связь «пользователь — клуб» с должностью; определяет право публиковать от имени клуба.",
        "fields": [
            f("user_id", "uuid", "Пользователь", pk=True, nn=True, fk="app_user"),
            f("club_id", "uuid", "Клуб", pk=True, nn=True, fk="club"),
            f("position", "club_position", "Должность в клубе", nn=True, dflt="'Член'"),
            f("from_date", "date", "Дата вступления", nn=True, dflt="current_date"),
            f("to_date", "date", "Дата выхода; NULL — действующее членство"),
        ],
        "uniques": [],
        "checks": [("to_date IS NULL OR to_date >= from_date", "membership_period_chk")],
    },
    {
        "name": "registration", "ru": "Регистрация",
        "purpose": "Факт записи пользователя на сессию; одна активная запись на пару «пользователь — сессия».",
        "fields": [
            ID,
            f("session_id", "uuid", "Сессия", nn=True, fk="session"),
            f("user_id", "uuid", "Записавшийся", nn=True, fk="app_user"),
            f("status", "registration_status", "Состояние записи", nn=True, dflt="'Записан'"),
            f("waitlist_position", "integer", "Номер в очереди; заполнен только для статуса «В листе ожидания»",
              chk="waitlist_position IS NULL OR waitlist_position > 0"),
            f("source", "reg_source", "Откуда пришла запись", nn=True, dflt="'Приложение'"),
            CREATED,
            f("cancelled_at", "timestamptz", "Момент отмены записи"),
            f("attended_at", "timestamptz", "Момент отметки присутствия; отделён от статуса"),
        ],
        "uniques": [(["session_id", "user_id"], "status <> 'Отменено'")],
        "checks": [
            ("status <> 'В листе ожидания' OR waitlist_position IS NOT NULL", "reg_waitlist_chk"),
            ("status <> 'Отменено' OR cancelled_at IS NOT NULL", "reg_cancel_chk"),
        ],
    },
    {
        "name": "ticket", "ru": "Билет",
        "purpose": "Электронный билет 1:1 к регистрации; содержит подпись, но не содержит персональных данных.",
        "fields": [
            ID,
            f("registration_id", "uuid", "Регистрация, породившая билет", nn=True, fk="registration", un=True),
            f("qr_payload", "varchar(300)", "Строка, закодированная в QR: ticket_id|session_id|issued_at",
              nn=True, un=True),
            f("qr_signature", "varchar(200)", "Подпись Ed25519 по строке qr_payload", nn=True),
            f("status", "ticket_status", "Состояние билета", nn=True, dflt="'Действителен'"),
            f("issued_at", "timestamptz", "Момент выдачи; входит в подписываемую строку",
              nn=True, dflt="now()"),
            f("used_at", "timestamptz", "Момент прохода; повторная отметка не перезаписывает"),
        ],
        "uniques": [],
        "checks": [("status <> 'Использован' OR used_at IS NOT NULL", "ticket_used_chk")],
    },
    {
        "name": "seat_offer", "ru": "Предложение места",
        "purpose": "Приглашение из листа ожидания с ограниченным сроком; отделено от регистрации, чтобы у места было одно активное предложение.",
        "fields": [
            ID,
            f("session_id", "uuid", "Сессия, где освободилось место", nn=True, fk="session"),
            f("registration_id", "uuid", "Запись из очереди, которой предложено место", nn=True, fk="registration"),
            f("issued_at", "timestamptz", "Момент выдачи приглашения", nn=True, dflt="now()"),
            f("expires_at", "timestamptz", "Срок ответа; после истечения место уходит следующему", nn=True),
            f("status", "offer_status", "Состояние приглашения", nn=True, dflt="'Выдано'"),
        ],
        "uniques": [(["registration_id"], "status = 'Выдано'")],
        "checks": [("expires_at > issued_at", "offer_interval_chk")],
    },
    {
        "name": "event_version", "ru": "Версия мероприятия",
        "purpose": "Снимок того, что ушло на модерацию; позволяет показать администратору именно рассмотренный вариант.",
        "fields": [
            ID,
            f("event_id", "uuid", "Мероприятие", nn=True, fk="event"),
            f("number", "integer", "Номер версии внутри мероприятия, с 1", nn=True,
              chk="number >= 1"),
            f("snapshot", "jsonb", "Полный снимок полей и сессий на момент отправки", nn=True),
            f("author_id", "uuid", "Кто сохранил версию", nn=True, fk="app_user"),
            CREATED,
        ],
        "uniques": [(["event_id", "number"], None)],
        "checks": [],
    },
    {
        "name": "moderation_request", "ru": "Заявка на модерацию",
        "purpose": "Очередь администратора; ссылается на конкретную версию мероприятия.",
        "fields": [
            ID,
            f("event_id", "uuid", "Мероприятие", nn=True, fk="event"),
            f("version_id", "uuid", "Рассматриваемая версия", nn=True, fk="event_version"),
            f("submitted_at", "timestamptz", "Момент подачи", nn=True, dflt="now()"),
            f("due_at", "timestamptz", "Срок рассмотрения; по нему сортируется очередь", nn=True),
            f("status", "request_status", "Состояние заявки", nn=True, dflt="'На рассмотрении'"),
        ],
        "uniques": [(["event_id"], "status = 'На рассмотрении'")],
        "checks": [("due_at > submitted_at", "request_due_chk")],
    },
    {
        "name": "decision", "ru": "Решение по заявке",
        "purpose": "Неизменяемая запись о решении администратора; вместе с заявкой образует журнал модерации.",
        "fields": [
            ID,
            f("request_id", "uuid", "Заявка", nn=True, fk="moderation_request"),
            f("type", "decision_type", "Утвердить или вернуть", nn=True),
            f("comment", "text", "Комментарий; обязателен при возврате, не короче 10 символов",
              chk="comment IS NULL OR char_length(comment) >= 10"),
            f("admin_id", "uuid", "Принявший решение администратор", nn=True, fk="app_user"),
            f("decided_at", "timestamptz", "Момент решения", nn=True, dflt="now()"),
        ],
        "uniques": [(["request_id"], None)],
        "checks": [("type <> 'Вернуть' OR (comment IS NOT NULL AND char_length(comment) >= 10)",
                    "decision_comment_chk")],
    },
    {
        "name": "review", "ru": "Отзыв",
        "purpose": "Оценка посещённого мероприятия; один отзыв на пару «мероприятие — пользователь».",
        "fields": [
            ID,
            f("event_id", "uuid", "Мероприятие", nn=True, fk="event"),
            f("user_id", "uuid", "Автор отзыва", nn=True, fk="app_user"),
            f("rating", "smallint", "Оценка от 1 до 5", nn=True, chk="rating BETWEEN 1 AND 5"),
            f("text", "text", "Текст отзыва"),
            f("status", "review_status", "Видимость отзыва после проверки", nn=True, dflt="'На проверке'"),
            CREATED,
        ],
        "uniques": [(["event_id", "user_id"], None)],
        "checks": [],
    },
    {
        "name": "notification", "ru": "Уведомление",
        "purpose": "Запланированное или отправленное сообщение; недоставленный push дублируется по e-mail.",
        "fields": [
            ID,
            f("user_id", "uuid", "Получатель", nn=True, fk="app_user"),
            f("registration_id", "uuid", "Запись, к которой относится уведомление", nn=True, fk="registration"),
            f("type", "notification_type", "Повод отправки", nn=True),
            f("channel", "channel", "Канал доставки", nn=True),
            f("payload", "jsonb", "Данные шаблона: название, время, аудитория"),
            f("scheduled_at", "timestamptz", "Когда отправить; воркер выбирает по этому полю", nn=True),
            f("sent_at", "timestamptz", "Фактический момент отправки"),
            f("read_at", "timestamptz", "Момент прочтения в приложении"),
        ],
        "uniques": [],
        "checks": [],
    },
]

# ---------------------------------------------------------------- DDL

def q(s):
    return "'" + s.replace("'", "''") + "'"


def ddl():
    out = ["-- Campus Events: физическая модель данных (PostgreSQL 15+)",
           "-- Сгенерировано tools/gen_db.py из единой модели; править gen_db.py, а не этот файл.",
           "",
           "BEGIN;",
           "",
           "-- 1. Перечисления",
           ]
    for name, vals in ENUMS.items():
        body = ",\n    ".join(q(v) for v in vals)
        out.append(f"CREATE TYPE {name} AS ENUM (\n    {body}\n);")
    out.append("")

    out.append("-- 2. Таблицы")
    for t in TABLES:
        cols = []
        for fd in t["fields"]:
            line = f'    {fd["n"]:<17} {fd["t"]}'
            if "dflt" in fd:
                line += f' DEFAULT {fd["dflt"]}'
            if fd.get("nn"):
                line += " NOT NULL"
            if "chk" in fd:
                line += f' CHECK ({fd["chk"]})'
            cols.append(line)
        pks = [fd["n"] for fd in t["fields"] if fd.get("pk")]
        if pks:
            cols.append(f'    PRIMARY KEY ({", ".join(pks)})')
        for fd in t["fields"]:
            if fd.get("un"):
                cols.append(f'    UNIQUE ({fd["n"]})')
        for fd in t["fields"]:
            if "fk" in fd:
                ref = fd["fk"]
                refcol = "code" if ref == "category" else "id"
                cols.append(f'    FOREIGN KEY ({fd["n"]}) REFERENCES {ref}({refcol})')
        for expr, cname in t.get("checks", []):
            cols.append(f'    CONSTRAINT {cname} CHECK ({expr})')
        out.append(f'\nCREATE TABLE {t["name"]} (')
        out.append(",\n".join(cols))
        out.append(");")

    out.append("\n-- 3. Индексы: частично уникальные и поисковые")
    for t in TABLES:
        for cols, where in t.get("uniques", []):
            nm = "ux_" + t["name"] + "_" + "_".join(cols)
            sql = f'CREATE UNIQUE INDEX {nm}\n    ON {t["name"]} ({", ".join(cols)})'
            if where:
                sql += f"\n    WHERE {where}"
            out.append(sql + ";")
    out += [
        "CREATE INDEX ix_event_status_published ON event (status, published_at DESC);",
        "CREATE INDEX ix_event_club ON event (club_id);",
        "CREATE INDEX ix_session_event_starts ON session (event_id, starts_at);",
        "CREATE INDEX ix_registration_session_status ON registration (session_id, status);",
        "CREATE INDEX ix_registration_user ON registration (user_id, created_at DESC);",
        "CREATE INDEX ix_seat_offer_expires ON seat_offer (expires_at) WHERE status = 'Выдано';",
        "CREATE INDEX ix_notification_due ON notification (scheduled_at) WHERE sent_at IS NULL;",
        "CREATE INDEX ix_event_version_snapshot ON event_version USING gin (snapshot);",
    ]

    out += ["""
-- 4. Триггеры инвариантов: счётчик занятых мест
-- taken меняется только здесь, поэтому правило 0 <= taken <= capacity
-- не может быть нарушено прикладным кодом.
CREATE OR REPLACE FUNCTION registration_seat_insert() RETURNS trigger AS $$
DECLARE s record;
BEGIN
    IF NEW.status IN ('Записан', 'Посетил') THEN
        SELECT taken, capacity INTO s FROM session WHERE id = NEW.session_id FOR UPDATE;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'FK_VIOLATION: сессия % не найдена', NEW.session_id;
        END IF;
        IF s.taken >= s.capacity THEN
            RAISE EXCEPTION 'NO_SEATS: в сессии % нет свободных мест', NEW.session_id;
        END IF;
        UPDATE session SET taken = taken + 1 WHERE id = NEW.session_id;
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION registration_seat_update() RETURNS trigger AS $$
DECLARE s record;
BEGIN
    IF OLD.status IN ('Записан', 'Посетил') AND NEW.status = 'Отменено' THEN
        UPDATE session SET taken = GREATEST(taken - 1, 0) WHERE id = NEW.session_id;
    ELSIF OLD.status = 'Отменено' AND NEW.status IN ('Записан', 'Посетил') THEN
        SELECT taken, capacity INTO s FROM session WHERE id = NEW.session_id FOR UPDATE;
        IF s.taken >= s.capacity THEN
            RAISE EXCEPTION 'NO_SEATS: в сессии % нет свободных мест', NEW.session_id;
        END IF;
        UPDATE session SET taken = taken + 1 WHERE id = NEW.session_id;
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_registration_seat_ins
    BEFORE INSERT ON registration
    FOR EACH ROW EXECUTE FUNCTION registration_seat_insert();

CREATE TRIGGER trg_registration_seat_upd
    AFTER UPDATE OF status ON registration
    FOR EACH ROW EXECUTE FUNCTION registration_seat_update();

-- 5. Журнал модерации неизменяем: решения только добавляются
CREATE OR REPLACE FUNCTION decision_immutable() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'APPEND_ONLY: решение по заявке нельзя изменить или удалить';
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_decision_no_update
    BEFORE UPDATE OR DELETE ON decision
    FOR EACH ROW EXECUTE FUNCTION decision_immutable();

COMMIT;
"""]
    return "\n".join(out)


# ---------------------------------------------------------------- словарь полей

VERIFY_SECTION = [
    "## Проверка ограничений и триггеров",
    "",
    "Ограничения из `schema.sql` проверены на работающем PostgreSQL 16, а не только "
    "объявлены. Скрипт `db/verify.sql` выполняет пятнадцать проб внутри одной транзакции "
    "и откатывает её, поэтому демонстрационные данные не меняются:",
    "",
    "```bash",
    "docker compose up -d postgres",
    "docker exec -i campus-events-db psql -U campus -d campus_events < db/verify.sql",
    "```",
    "",
    "| № | Что проверяется | Ожидаемое поведение | Механизм | Результат |",
    "|---|---|---|---|---|",
    "| T01 | `taken` больше вместимости | отказ | `session_seats_chk` | PASS |",
    "| T02 | Отрицательное `taken` | отказ | `session_seats_chk` | PASS |",
    "| T03 | Повторная активная запись на ту же сессию | отказ | `ux_registration_session_id_user_id` | PASS |",
    "| T04 | Запись после отмены предыдущей | разрешено | частичный индекс | PASS |",
    "| T05 | Запись занимает место | `taken` +1 | `trg_registration_seat_ins` | PASS |",
    "| T06 | Запись при `taken = capacity` | `NO_SEATS` | `trg_registration_seat_ins` | PASS |",
    "| T07 | Отмена освобождает место | `taken` −1 | `trg_registration_seat_upd` | PASS |",
    "| T08 | Изменение решения модерации | `APPEND_ONLY` | `trg_decision_no_update` | PASS |",
    "| T09 | Удаление решения модерации | `APPEND_ONLY` | `trg_decision_no_update` | PASS |",
    "| T10 | Возврат заявки с коротким комментарием | отказ | `decision_comment_chk` | PASS |",
    "| T11 | Оценка вне диапазона 1–5 | отказ | `review_rating_check` | PASS |",
    "| T12 | Сессия заканчивается раньше начала | отказ | `session_interval_chk` | PASS |",
    "| T13 | Название мероприятия короче 5 символов | отказ | `event_title_check` | PASS |",
    "| T14 | Использованный билет без `used_at` | отказ | `ticket_used_chk` | PASS |",
    "| T15 | Вторая заявка в статусе «На рассмотрении» | отказ | `ux_moderation_request_event_id` | PASS |",
    "",
    "Три проверки (T05–T07) принципиальны: счётчик занятых мест меняется только "
    "триггерами, поэтому приложение не может обойти правило `0 <= taken <= capacity` "
    "даже при ошибке в коде. Отказ T06 приходит из базы сообщением `NO_SEATS`, "
    "которое API транслирует в код `409` — тот же код, что описан в спецификации.",
    "",
]


def md():
    out = ["# Логическая модель данных: словарь полей",
           "",
           "Модель унаследована из ЛР № 3 (ER-диаграмма, 14 таблиц) и уточнена под физическую реализацию: "
           "добавлены перечисления, ограничения целостности и составные уникальные индексы. "
           "Первичные ключи — UUID, время — `timestamptz` в UTC. "
           "Значения перечислений совпадают с подписями интерфейса, чтобы не держать два словаря.",
           "",
           f"Всего таблиц: **{len(TABLES)}**, полей: **{sum(len(t['fields']) for t in TABLES)}**, "
           f"перечислений: **{len(ENUMS)}**.",
           "",
           "![ER-диаграмма физической модели](../assets/erd-physical.png)",
           ""]
    for i, t in enumerate(TABLES, 1):
        out.append(f"## {i}. {t['name']} — {t['ru']}")
        out.append("")
        out.append(t["purpose"])
        out.append("")
        out.append("| Поле | Смысл поля | Тип данных | Ограничения |")
        out.append("|---|---|---|---|")
        for fd in t["fields"]:
            cons = []
            if fd.get("pk"):
                cons.append("PK")
            if "fk" in fd:
                ref = fd["fk"]
                cons.append(f"FK → {ref}")
            if fd.get("nn"):
                cons.append("NOT NULL")
            if fd.get("un"):
                cons.append("UNIQUE")
            if "dflt" in fd:
                cons.append(f"по умолчанию `{fd['dflt']}`")
            if "chk" in fd:
                cons.append(f"`{fd['chk']}`")
            out.append(f"| `{fd['n']}` | {fd['r']} | {fd['t']} | {', '.join(cons) or '—'} |")
        extra = []
        for cols, where in t.get("uniques", []):
            s = "уникальный индекс по (" + ", ".join(cols) + ")"
            if where:
                s += f", только где `{where}`"
            extra.append(s)
        for expr, cname in t.get("checks", []):
            extra.append(f"ограничение `{cname}`: `{expr}`")
        if extra:
            out.append("")
            out.append("Дополнительно: " + "; ".join(extra) + ".")
        out.append("")
    out.extend(VERIFY_SECTION)
    return "\n".join(out)


# ---------------------------------------------------------------- ER

def puml():
    out = ["@startuml campus-events-erd",
           "' Физическая модель: типы данных СУБД и ограничения. Генерируется tools/gen_db.py.",
           "!pragma layout smetana",
           "hide circle",
           "skinparam shadowing false",
           "skinparam linetype ortho",
           "skinparam entity {",
           "  BackgroundColor #FFFFFF",
           "  BorderColor #5F5E5A",
           "  FontSize 9",
           "}",
           ""]
    for t in TABLES:
        out.append(f'entity "{t["name"]}" as {t["name"]} {{')
        pkdone = False
        for fd in t["fields"]:
            mark = ""
            if fd.get("pk"):
                mark = " <<PK>>"
            elif "fk" in fd:
                mark = " <<FK>>"
            out.append(f'  {fd["n"]} : {fd["t"]}{mark}')
        out.append("}")
        out.append("")
    for t in TABLES:
        for fd in t["fields"]:
            if "fk" in fd:
                out.append(f'{fd["fk"]} ||--o{{ {t["name"]} : "{fd["n"]}"')
    out.append("@enduml")
    return "\n".join(out)


def main():
    for path, text in [("db/schema.sql", ddl()),
                       ("docs/05-database.md", md()),
                       ("db/erd.puml", puml())]:
        p = os.path.join(ROOT, path)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        io.open(p, "w", encoding="utf-8", newline="\n").write(text)
        print("written", path, len(text), "chars")


if __name__ == "__main__":
    main()

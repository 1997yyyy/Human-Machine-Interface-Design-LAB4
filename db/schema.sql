-- Campus Events: физическая модель данных (PostgreSQL 15+)
-- Сгенерировано tools/gen_db.py из единой модели; править gen_db.py, а не этот файл.

BEGIN;

-- 1. Перечисления
CREATE TYPE event_status AS ENUM (
    'Черновик',
    'На модерации',
    'Опубликовано',
    'Отклонено',
    'Отменено',
    'Завершено'
);
CREATE TYPE publish_mode AS ENUM (
    'Свободный',
    'С утверждением'
);
CREATE TYPE user_role AS ENUM (
    'Гость',
    'Студент',
    'Организатор',
    'Администратор'
);
CREATE TYPE club_position AS ENUM (
    'Руководитель',
    'Заместитель',
    'Член'
);
CREATE TYPE registration_status AS ENUM (
    'Записан',
    'В листе ожидания',
    'Отменено',
    'Посетил',
    'Неявка'
);
CREATE TYPE reg_source AS ENUM (
    'Приложение',
    'Веб',
    'Регистрация на месте'
);
CREATE TYPE ticket_status AS ENUM (
    'Действителен',
    'Использован',
    'Отозван'
);
CREATE TYPE offer_status AS ENUM (
    'Выдано',
    'Принято',
    'Истекло'
);
CREATE TYPE request_status AS ENUM (
    'На рассмотрении',
    'Утверждено',
    'Возвращено'
);
CREATE TYPE decision_type AS ENUM (
    'Утвердить',
    'Вернуть'
);
CREATE TYPE review_status AS ENUM (
    'На проверке',
    'Опубликован',
    'Скрыт'
);
CREATE TYPE notification_type AS ENUM (
    'Подтверждение',
    'Напоминание 24 ч',
    'Напоминание 2 ч',
    'Приглашение из очереди',
    'Отмена'
);
CREATE TYPE channel AS ENUM (
    'Push',
    'Email',
    'Оба'
);

-- 2. Таблицы

CREATE TABLE club (
    id                uuid DEFAULT gen_random_uuid() NOT NULL,
    name              varchar(120) NOT NULL,
    description       text,
    logo_url          varchar(255),
    is_active         boolean DEFAULT true NOT NULL,
    created_at        timestamptz DEFAULT now() NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE category (
    code              varchar(32) NOT NULL,
    name              varchar(80) NOT NULL,
    sort_order        smallint NOT NULL,
    PRIMARY KEY (code)
);

CREATE TABLE app_user (
    id                uuid DEFAULT gen_random_uuid() NOT NULL,
    cas_login         varchar(64) NOT NULL,
    full_name         varchar(160) NOT NULL,
    email             varchar(160) CHECK (email IS NULL OR email LIKE '%@%'),
    faculty           varchar(120),
    study_group       varchar(40),
    role              user_role DEFAULT 'Студент' NOT NULL,
    is_active         boolean DEFAULT true NOT NULL,
    created_at        timestamptz DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (cas_login)
);

CREATE TABLE event (
    id                uuid DEFAULT gen_random_uuid() NOT NULL,
    club_id           uuid NOT NULL,
    category_code     varchar(32) NOT NULL,
    title             varchar(200) NOT NULL CHECK (char_length(title) >= 5),
    description       text,
    poster_url        varchar(255),
    status            event_status DEFAULT 'Черновик' NOT NULL,
    publish_mode      publish_mode DEFAULT 'Свободный' NOT NULL,
    capacity          integer CHECK (capacity IS NULL OR capacity > 0),
    owner_id          uuid NOT NULL,
    created_at        timestamptz DEFAULT now() NOT NULL,
    published_at      timestamptz,
    cancelled_at      timestamptz,
    cancel_reason     varchar(300),
    PRIMARY KEY (id),
    FOREIGN KEY (club_id) REFERENCES club(id),
    FOREIGN KEY (category_code) REFERENCES category(code),
    FOREIGN KEY (owner_id) REFERENCES app_user(id),
    CONSTRAINT event_cancel_chk CHECK (cancelled_at IS NULL OR status = 'Отменено')
);

CREATE TABLE session (
    id                uuid DEFAULT gen_random_uuid() NOT NULL,
    event_id          uuid NOT NULL,
    starts_at         timestamptz NOT NULL,
    ends_at           timestamptz NOT NULL,
    building          varchar(120) NOT NULL,
    room              varchar(60),
    capacity          integer NOT NULL CHECK (capacity >= 1),
    taken             integer DEFAULT 0 NOT NULL,
    qr_key_version    smallint DEFAULT 1 NOT NULL,
    created_at        timestamptz DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (event_id) REFERENCES event(id),
    CONSTRAINT session_interval_chk CHECK (ends_at > starts_at),
    CONSTRAINT session_seats_chk CHECK (taken >= 0 AND taken <= capacity),
    CONSTRAINT session_key_ver_chk CHECK (qr_key_version >= 1)
);

CREATE TABLE membership (
    user_id           uuid NOT NULL,
    club_id           uuid NOT NULL,
    position          club_position DEFAULT 'Член' NOT NULL,
    from_date         date DEFAULT current_date NOT NULL,
    to_date           date,
    PRIMARY KEY (user_id, club_id),
    FOREIGN KEY (user_id) REFERENCES app_user(id),
    FOREIGN KEY (club_id) REFERENCES club(id),
    CONSTRAINT membership_period_chk CHECK (to_date IS NULL OR to_date >= from_date)
);

CREATE TABLE registration (
    id                uuid DEFAULT gen_random_uuid() NOT NULL,
    session_id        uuid NOT NULL,
    user_id           uuid NOT NULL,
    status            registration_status DEFAULT 'Записан' NOT NULL,
    waitlist_position integer CHECK (waitlist_position IS NULL OR waitlist_position > 0),
    source            reg_source DEFAULT 'Приложение' NOT NULL,
    created_at        timestamptz DEFAULT now() NOT NULL,
    cancelled_at      timestamptz,
    attended_at       timestamptz,
    PRIMARY KEY (id),
    FOREIGN KEY (session_id) REFERENCES session(id),
    FOREIGN KEY (user_id) REFERENCES app_user(id),
    CONSTRAINT reg_waitlist_chk CHECK (status <> 'В листе ожидания' OR waitlist_position IS NOT NULL),
    CONSTRAINT reg_cancel_chk CHECK (status <> 'Отменено' OR cancelled_at IS NOT NULL)
);

CREATE TABLE ticket (
    id                uuid DEFAULT gen_random_uuid() NOT NULL,
    registration_id   uuid NOT NULL,
    qr_payload        varchar(300) NOT NULL,
    qr_signature      varchar(200) NOT NULL,
    status            ticket_status DEFAULT 'Действителен' NOT NULL,
    issued_at         timestamptz DEFAULT now() NOT NULL,
    used_at           timestamptz,
    PRIMARY KEY (id),
    UNIQUE (registration_id),
    UNIQUE (qr_payload),
    FOREIGN KEY (registration_id) REFERENCES registration(id),
    CONSTRAINT ticket_used_chk CHECK (status <> 'Использован' OR used_at IS NOT NULL)
);

CREATE TABLE seat_offer (
    id                uuid DEFAULT gen_random_uuid() NOT NULL,
    session_id        uuid NOT NULL,
    registration_id   uuid NOT NULL,
    issued_at         timestamptz DEFAULT now() NOT NULL,
    expires_at        timestamptz NOT NULL,
    status            offer_status DEFAULT 'Выдано' NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (session_id) REFERENCES session(id),
    FOREIGN KEY (registration_id) REFERENCES registration(id),
    CONSTRAINT offer_interval_chk CHECK (expires_at > issued_at)
);

CREATE TABLE event_version (
    id                uuid DEFAULT gen_random_uuid() NOT NULL,
    event_id          uuid NOT NULL,
    number            integer NOT NULL CHECK (number >= 1),
    snapshot          jsonb NOT NULL,
    author_id         uuid NOT NULL,
    created_at        timestamptz DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (event_id) REFERENCES event(id),
    FOREIGN KEY (author_id) REFERENCES app_user(id)
);

CREATE TABLE moderation_request (
    id                uuid DEFAULT gen_random_uuid() NOT NULL,
    event_id          uuid NOT NULL,
    version_id        uuid NOT NULL,
    submitted_at      timestamptz DEFAULT now() NOT NULL,
    due_at            timestamptz NOT NULL,
    status            request_status DEFAULT 'На рассмотрении' NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (event_id) REFERENCES event(id),
    FOREIGN KEY (version_id) REFERENCES event_version(id),
    CONSTRAINT request_due_chk CHECK (due_at > submitted_at)
);

CREATE TABLE decision (
    id                uuid DEFAULT gen_random_uuid() NOT NULL,
    request_id        uuid NOT NULL,
    type              decision_type NOT NULL,
    comment           text CHECK (comment IS NULL OR char_length(comment) >= 10),
    admin_id          uuid NOT NULL,
    decided_at        timestamptz DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (request_id) REFERENCES moderation_request(id),
    FOREIGN KEY (admin_id) REFERENCES app_user(id),
    CONSTRAINT decision_comment_chk CHECK (type <> 'Вернуть' OR (comment IS NOT NULL AND char_length(comment) >= 10))
);

CREATE TABLE review (
    id                uuid DEFAULT gen_random_uuid() NOT NULL,
    event_id          uuid NOT NULL,
    user_id           uuid NOT NULL,
    rating            smallint NOT NULL CHECK (rating BETWEEN 1 AND 5),
    text              text,
    status            review_status DEFAULT 'На проверке' NOT NULL,
    created_at        timestamptz DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (event_id) REFERENCES event(id),
    FOREIGN KEY (user_id) REFERENCES app_user(id)
);

CREATE TABLE notification (
    id                uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id           uuid NOT NULL,
    registration_id   uuid NOT NULL,
    type              notification_type NOT NULL,
    channel           channel NOT NULL,
    payload           jsonb,
    scheduled_at      timestamptz NOT NULL,
    sent_at           timestamptz,
    read_at           timestamptz,
    PRIMARY KEY (id),
    FOREIGN KEY (user_id) REFERENCES app_user(id),
    FOREIGN KEY (registration_id) REFERENCES registration(id)
);

-- 3. Индексы: частично уникальные и поисковые
CREATE UNIQUE INDEX ux_club_name
    ON club (name);
CREATE UNIQUE INDEX ux_registration_session_id_user_id
    ON registration (session_id, user_id)
    WHERE status <> 'Отменено';
CREATE UNIQUE INDEX ux_seat_offer_registration_id
    ON seat_offer (registration_id)
    WHERE status = 'Выдано';
CREATE UNIQUE INDEX ux_event_version_event_id_number
    ON event_version (event_id, number);
CREATE UNIQUE INDEX ux_moderation_request_event_id
    ON moderation_request (event_id)
    WHERE status = 'На рассмотрении';
CREATE UNIQUE INDEX ux_decision_request_id
    ON decision (request_id);
CREATE UNIQUE INDEX ux_review_event_id_user_id
    ON review (event_id, user_id);
CREATE INDEX ix_event_status_published ON event (status, published_at DESC);
CREATE INDEX ix_event_club ON event (club_id);
CREATE INDEX ix_session_event_starts ON session (event_id, starts_at);
CREATE INDEX ix_registration_session_status ON registration (session_id, status);
CREATE INDEX ix_registration_user ON registration (user_id, created_at DESC);
CREATE INDEX ix_seat_offer_expires ON seat_offer (expires_at) WHERE status = 'Выдано';
CREATE INDEX ix_notification_due ON notification (scheduled_at) WHERE sent_at IS NULL;
CREATE INDEX ix_event_version_snapshot ON event_version USING gin (snapshot);

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

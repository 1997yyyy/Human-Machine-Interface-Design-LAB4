-- =====================================================================
--  Проверка ограничений и триггеров схемы campus_events
--  Запуск:  docker exec -i campus-events-db psql -U campus -d campus_events -f /dev/stdin < db/verify.sql
--  либо:    psql -U campus -d campus_events -f db/verify.sql
--
--  Все проверки выполняются внутри одной транзакции, которая в конце
--  откатывается, поэтому демонстрационные данные не меняются.
--  Негативные проверки ждут нарушения ограничения: если исключения
--  не произошло, печатается FAIL.
-- =====================================================================

\set ON_ERROR_STOP off
BEGIN;

-- ---------------------------------------------------------------------
-- T01. Инвариант 0 <= taken <= capacity: превышение отклоняется
-- ---------------------------------------------------------------------
DO $$
BEGIN
    BEGIN
        UPDATE session SET taken = capacity + 1
         WHERE id = 'c3000000-0000-4000-8000-000000000001';
        RAISE NOTICE 'T01 FAIL  превышение capacity принято';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'T01 PASS  taken > capacity отклонено (session_seats_chk)';
    END;
END $$;

-- ---------------------------------------------------------------------
-- T02. Отрицательное число занятых мест отклоняется
-- ---------------------------------------------------------------------
DO $$
BEGIN
    BEGIN
        UPDATE session SET taken = -1
         WHERE id = 'c3000000-0000-4000-8000-000000000001';
        RAISE NOTICE 'T02 FAIL  отрицательное taken принято';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'T02 PASS  taken < 0 отклонено (session_seats_chk)';
    END;
END $$;

-- ---------------------------------------------------------------------
-- T03. Повторная активная запись того же пользователя на ту же сессию
--      запрещена частично уникальным индексом
-- ---------------------------------------------------------------------
DO $$
BEGIN
    BEGIN
        INSERT INTO registration (session_id, user_id, status)
        VALUES ('c3000000-0000-4000-8000-000000000001',
                '11111111-1111-4111-8111-111111111111', 'Записан');
        RAISE NOTICE 'T03 FAIL  вторая активная запись принята';
    EXCEPTION WHEN unique_violation THEN
        RAISE NOTICE 'T03 PASS  дубль активной записи отклонён (ux_registration_session_id_user_id)';
    END;
END $$;

-- ---------------------------------------------------------------------
-- T04. Но после отмены повторная запись разрешена (индекс частичный)
-- ---------------------------------------------------------------------
DO $$
BEGIN
    BEGIN
        INSERT INTO registration (id, session_id, user_id, status)
        VALUES ('e5000000-0000-4000-8000-0000000000fe',
                'c3000000-0000-4000-8000-000000000002',
                '11111111-1111-4111-8111-111111111111', 'Записан');
        RAISE NOTICE 'T04 PASS  запись после отмены разрешена';
    EXCEPTION WHEN others THEN
        RAISE NOTICE 'T04 FAIL  запись после отмены отклонена: %', SQLERRM;
    END;
END $$;

-- ---------------------------------------------------------------------
-- T05. Триггер увеличивает счётчик занятых мест при записи
-- ---------------------------------------------------------------------
DO $$
DECLARE
    before_taken integer;
    after_taken  integer;
BEGIN
    SELECT taken INTO before_taken
      FROM session WHERE id = 'c3000000-0000-4000-8000-000000000001';

    INSERT INTO registration (id, session_id, user_id, status)
    VALUES ('e5000000-0000-4000-8000-0000000000ff',
            'c3000000-0000-4000-8000-000000000001',
            '11111111-1111-4111-8111-111111111114', 'Записан');

    SELECT taken INTO after_taken
      FROM session WHERE id = 'c3000000-0000-4000-8000-000000000001';

    IF after_taken = before_taken + 1 THEN
        RAISE NOTICE 'T05 PASS  taken % -> % (trg_registration_seat_ins)',
                     before_taken, after_taken;
    ELSE
        RAISE NOTICE 'T05 FAIL  taken % -> %', before_taken, after_taken;
    END IF;
END $$;

-- ---------------------------------------------------------------------
-- T06. Запись на заполненную сессию отклоняется триггером, а не приложением
--      (после T05 в сессии ровно capacity = 3 занятых места)
-- ---------------------------------------------------------------------
DO $$
BEGIN
    BEGIN
        INSERT INTO registration (session_id, user_id, status)
        VALUES ('c3000000-0000-4000-8000-000000000001',
                '11111111-1111-4111-8111-111111111113', 'Записан');
        RAISE NOTICE 'T06 FAIL  запись без свободных мест принята';
    EXCEPTION WHEN others THEN
        IF SQLERRM LIKE 'NO_SEATS%' THEN
            RAISE NOTICE 'T06 PASS  запись при taken = capacity отклонена: %', SQLERRM;
        ELSE
            RAISE NOTICE 'T06 FAIL  неожиданная ошибка: %', SQLERRM;
        END IF;
    END;
END $$;

-- ---------------------------------------------------------------------
-- T07. Отмена записи возвращает место
-- ---------------------------------------------------------------------
DO $$
DECLARE
    before_taken integer;
    after_taken  integer;
BEGIN
    SELECT taken INTO before_taken
      FROM session WHERE id = 'c3000000-0000-4000-8000-000000000001';

    UPDATE registration
       SET status = 'Отменено', cancelled_at = now()
     WHERE id = 'e5000000-0000-4000-8000-0000000000ff';

    SELECT taken INTO after_taken
      FROM session WHERE id = 'c3000000-0000-4000-8000-000000000001';

    IF after_taken = before_taken - 1 THEN
        RAISE NOTICE 'T07 PASS  taken % -> % при отмене (trg_registration_seat_upd)',
                     before_taken, after_taken;
    ELSE
        RAISE NOTICE 'T07 FAIL  taken % -> %', before_taken, after_taken;
    END IF;
END $$;

-- ---------------------------------------------------------------------
-- T08. Журнал решений по модерации неизменяем: UPDATE запрещён
-- ---------------------------------------------------------------------
DO $$
BEGIN
    BEGIN
        UPDATE decision SET comment = 'Переписано задним числом'
         WHERE id = '29000000-0000-4000-8000-000000000001';
        RAISE NOTICE 'T08 FAIL  изменение решения принято';
    EXCEPTION WHEN others THEN
        IF SQLERRM LIKE 'APPEND_ONLY%' THEN
            RAISE NOTICE 'T08 PASS  UPDATE решения отклонён (trg_decision_no_update)';
        ELSE
            RAISE NOTICE 'T08 FAIL  неожиданная ошибка: %', SQLERRM;
        END IF;
    END;
END $$;

-- ---------------------------------------------------------------------
-- T09. Журнал решений неизменяем и на удаление
-- ---------------------------------------------------------------------
DO $$
BEGIN
    BEGIN
        DELETE FROM decision WHERE id = '29000000-0000-4000-8000-000000000001';
        RAISE NOTICE 'T09 FAIL  удаление решения принято';
    EXCEPTION WHEN others THEN
        IF SQLERRM LIKE 'APPEND_ONLY%' THEN
            RAISE NOTICE 'T09 PASS  DELETE решения отклонён (trg_decision_no_update)';
        ELSE
            RAISE NOTICE 'T09 FAIL  неожиданная ошибка: %', SQLERRM;
        END IF;
    END;
END $$;

-- ---------------------------------------------------------------------
-- T10. Возврат заявки без содержательного комментария невозможен
-- ---------------------------------------------------------------------
DO $$
BEGIN
    BEGIN
        INSERT INTO decision (request_id, type, comment, admin_id)
        VALUES ('18000000-0000-4000-8000-000000000002', 'Вернуть',
                'Коротко', '11111111-1111-4111-8111-111111111114');
        RAISE NOTICE 'T10 FAIL  возврат без комментария принят';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'T10 PASS  возврат с комментарием короче 10 символов отклонён (decision_comment_chk)';
    END;
END $$;

-- ---------------------------------------------------------------------
-- T11. Оценка вне диапазона 1..5 отклоняется
-- ---------------------------------------------------------------------
DO $$
BEGIN
    BEGIN
        UPDATE review SET rating = 6;
        RAISE NOTICE 'T11 FAIL  оценка 6 принята';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'T11 PASS  rating = 6 отклонён (review_rating_check)';
    END;
END $$;

-- ---------------------------------------------------------------------
-- T12. Сессия не может закончиться раньше, чем начаться
-- ---------------------------------------------------------------------
DO $$
BEGIN
    BEGIN
        UPDATE session
           SET ends_at = starts_at - interval '1 hour'
         WHERE id = 'c3000000-0000-4000-8000-000000000001';
        RAISE NOTICE 'T12 FAIL  обратный интервал принят';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'T12 PASS  ends_at <= starts_at отклонено (session_interval_chk)';
    END;
END $$;

-- ---------------------------------------------------------------------
-- T13. Слишком короткое название мероприятия отклоняется
-- ---------------------------------------------------------------------
DO $$
BEGIN
    BEGIN
        UPDATE event SET title = 'Лек'
         WHERE id = 'b2000000-0000-4000-8000-000000000001';
        RAISE NOTICE 'T13 FAIL  название из 3 символов принято';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'T13 PASS  название короче 5 символов отклонено (event_title_check)';
    END;
END $$;

-- ---------------------------------------------------------------------
-- T14. Билет не может быть использован без времени использования
-- ---------------------------------------------------------------------
DO $$
BEGIN
    BEGIN
        UPDATE ticket SET status = 'Использован', used_at = NULL
         WHERE id = 'f6000000-0000-4000-8000-000000000001';
        RAISE NOTICE 'T14 FAIL  использованный билет без used_at принят';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'T14 PASS  использованный билет без used_at отклонён (ticket_used_chk)';
    END;
END $$;

-- ---------------------------------------------------------------------
-- T15. У мероприятия не может быть двух заявок в статусе «На рассмотрении»
-- ---------------------------------------------------------------------
DO $$
BEGIN
    BEGIN
        INSERT INTO moderation_request (event_id, version_id, due_at)
        VALUES ('b2000000-0000-4000-8000-000000000002',
                'd4000000-0000-4000-8000-000000000002', now() + interval '2 days');
        RAISE NOTICE 'T15 FAIL  вторая заявка на рассмотрении принята';
    EXCEPTION WHEN unique_violation THEN
        RAISE NOTICE 'T15 PASS  вторая заявка на рассмотрении отклонена (ux_moderation_request_event_id)';
    END;
END $$;

ROLLBACK;

\echo ''
\echo 'Транзакция откатана: данные остались в исходном состоянии.'

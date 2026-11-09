# -*- coding: utf-8 -*-
"""Сборка отчёта по лабораторной работе № 4 в формат .docx.

Запуск: python tools/gen_report.py
Результат: report/Отчет_ЛР4_Zeng_Yaoxin.docx
"""
import os
import json
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import (WD_ALIGN_PARAGRAPH, WD_BREAK,
                            WD_TAB_ALIGNMENT, WD_TAB_LEADER)
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE, 'report')
OUT = os.path.join(OUT_DIR, 'Отчет_ЛР4_Zeng_Yaoxin.docx')
os.makedirs(OUT_DIR, exist_ok=True)

FONT = 'Times New Roman'
ALIGN = {'just': WD_ALIGN_PARAGRAPH.JUSTIFY, 'center': WD_ALIGN_PARAGRAPH.CENTER,
         'left': WD_ALIGN_PARAGRAPH.LEFT, 'right': WD_ALIGN_PARAGRAPH.RIGHT}

doc = Document()

# ---------- страница и базовый стиль ----------
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.left_margin, sec.right_margin = Cm(3), Cm(1.5)
sec.top_margin, sec.bottom_margin = Cm(2), Cm(2)
sec.different_first_page_header_footer = True

normal = doc.styles['Normal']
normal.font.name = FONT
normal.font.size = Pt(14)
normal.element.rPr.rFonts.set(qn('w:eastAsia'), FONT)
npf = normal.paragraph_format
npf.line_spacing = 1.5
npf.space_before = Pt(0)
npf.space_after = Pt(0)
npf.first_line_indent = Cm(1.25)
npf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

h1s = doc.styles['Heading 1']
h1s.font.name = FONT
h1s.font.size = Pt(14)
h1s.font.bold = True
h1s.font.color.rgb = RGBColor(0, 0, 0)
h1s.element.rPr.rFonts.set(qn('w:eastAsia'), FONT)
h1s.paragraph_format.space_before = Pt(12)
h1s.paragraph_format.space_after = Pt(6)
h1s.paragraph_format.first_line_indent = Cm(0)
h1s.paragraph_format.line_spacing = 1.5
h1s.paragraph_format.keep_with_next = True
h1s.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT


def p(text='', size=14, bold=False, italic=False, align='just', indent=1.25,
      before=0, after=0, line=1.5, keep_next=False):
    par = doc.add_paragraph()
    pf = par.paragraph_format
    pf.first_line_indent = Cm(indent)
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    pf.alignment = ALIGN[align]
    if keep_next:
        pf.keep_with_next = True
    if text:
        r = par.add_run(text)
        r.font.name = FONT
        r.font.size = Pt(size)
        r.bold = bold
        r.italic = italic
    return par


def h1(text):
    return doc.add_paragraph(text, style='Heading 1')


def fig(name, caption, width=None, height=None):
    path = os.path.join(BASE, 'assets', name)
    kw = {}
    if width:
        kw['width'] = Cm(width)
    if height:
        kw['height'] = Cm(height)
    doc.add_picture(path, **kw)
    par = doc.paragraphs[-1]
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.first_line_indent = Cm(0)
    par.paragraph_format.space_before = Pt(6)
    par.paragraph_format.space_after = Pt(0)
    par.paragraph_format.line_spacing = 1.0
    par.paragraph_format.keep_with_next = True
    p(caption, size=12, align='center', indent=0, before=2, after=10, line=1.0).paragraph_format.keep_with_next = False


def shade(cell, color='EDEDED'):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color)
    tcPr.append(shd)


def table(caption, headers, rows, widths, font=10, align_col=None, indent_left=0,
          keep_together=True):
    if caption:
        cap = p(caption, size=12, align='left', indent=0, before=10, after=3, line=1.0)
        cap.paragraph_format.keep_with_next = True
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    tblPr = t._tbl.tblPr
    layout = OxmlElement('w:tblLayout')
    layout.set(qn('w:type'), 'fixed')
    tblPr.append(layout)

    align_col = align_col or ['left'] * len(headers)
    hdr = t.rows[0]
    trPr = hdr._tr.get_or_add_trPr()
    trPr.append(OxmlElement('w:tblHeader'))
    trPr.append(OxmlElement('w:cantSplit'))
    for i, htext in enumerate(headers):
        cell = hdr.cells[i]
        cell.width = Cm(widths[i])
        cell.text = ''
        par = cell.paragraphs[0]
        par.paragraph_format.first_line_indent = Cm(0)
        par.paragraph_format.line_spacing = 1.0
        par.paragraph_format.space_before = Pt(1)
        par.paragraph_format.space_after = Pt(1)
        par.alignment = ALIGN['center']
        r = par.add_run(htext)
        r.font.name = FONT
        r.font.size = Pt(font)
        r.bold = True
        shade(cell)

    for row in rows:
        cells = t.add_row().cells
        t.rows[-1]._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
        for i, val in enumerate(row):
            cell = cells[i]
            cell.width = Cm(widths[i])
            cell.text = ''
            par = cell.paragraphs[0]
            par.paragraph_format.first_line_indent = Cm(0)
            par.paragraph_format.line_spacing = 1.0
            par.paragraph_format.space_before = Pt(1)
            par.paragraph_format.space_after = Pt(1)
            par.alignment = ALIGN[align_col[i]]
            r = par.add_run(str(val))
            r.font.name = FONT
            r.font.size = Pt(font)
    if keep_together:
        for row in t.rows[:-1]:
            for cell in row.cells:
                for par in cell.paragraphs:
                    par.paragraph_format.keep_with_next = True
    p('', size=6, indent=0, line=1.0)
    return t


def page_break():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def add_page_numbers():
    footer = sec.footer
    par = footer.paragraphs[0]
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = par.add_run()
    run.font.name = FONT
    run.font.size = Pt(12)
    fld = OxmlElement('w:fldSimple')
    fld.set(qn('w:instr'), 'PAGE')
    inner = OxmlElement('w:r')
    rpr = OxmlElement('w:rPr')
    rfonts = OxmlElement('w:rFonts')
    rfonts.set(qn('w:ascii'), FONT)
    rfonts.set(qn('w:hAnsi'), FONT)
    rpr.append(rfonts)
    sz = OxmlElement('w:sz')
    sz.set(qn('w:val'), '24')
    rpr.append(sz)
    inner.append(rpr)
    t = OxmlElement('w:t')
    t.text = '1'
    inner.append(t)
    fld.append(inner)
    par._p.append(fld)


add_page_numbers()

# ======================= ТИТУЛЬНЫЙ ЛИСТ =======================
for line in ('МИНИСТЕРСТВО ОБРАЗОВАНИЯ РЕСПУБЛИКИ БЕЛАРУСЬ',
             'БЕЛОРУССКИЙ ГОСУДАРСТВЕННЫЙ УНИВЕРСИТЕТ',
             'Факультет прикладной математики и информатики',
             'Кафедра технологий программирования'):
    p(line, size=13, align='center', indent=0, line=1.15)

for _ in range(3):
    p('', indent=0, line=1.5)

p('ОТЧЕТ', size=20, bold=True, align='center', indent=0, line=1.0)
p('по лабораторной работе № 4', size=14, align='center', indent=0, before=6, line=1.15)
p('по курсу «Проектирование человеко-машинных интерфейсов»',
  size=14, align='center', indent=0, line=1.15)
p('Стили интеграции программных систем и проектирование API',
  size=15, bold=True, align='center', indent=0, before=14, line=1.15)
p('Вариант: подсистема записи на мероприятия университетских клубов (Campus Events), группа 13',
  size=12, italic=True, align='center', indent=0, before=8, line=1.15)

for _ in range(4):
    p('', indent=0, line=1.5)

p('Выполнил: студент 13 группы', size=13, align='left', indent=8.5, line=1.15)
p('Zeng Yaoxin', size=13, align='left', indent=9.6, line=1.15)
p('', indent=0, line=1.0)
p('Проверила: ст. преподаватель', size=13, align='left', indent=8.5, line=1.15)
p('Давидовская М.И.', size=13, align='left', indent=9.6, line=1.15)

for _ in range(5):
    p('', indent=0, line=1.5)

p('Минск, 2026', size=13, align='center', indent=0, line=1.0)
page_break()

# ======================= СОДЕРЖАНИЕ =======================
p('СОДЕРЖАНИЕ', size=14, bold=True, align='center', indent=0, after=10, line=1.15)
toc = [
    '1  Цель работы и состав выполненных работ',
    '2  Объект проектирования и действующие лица',
    '3  Задание 1. Модель требований и реестр вариантов использования',
    '4  Задание 2. Логическая и физическая модели базы данных',
    '5  Задание 3. Маршруты и конечные точки API',
    '6  Задание 4. Спецификация OpenAPI и тестирование на Mock-сервере',
    '7  Задание 5. MCP-сервер (выполнено дополнительно)',
    '8  Организация работы над проектом и документирование',
    '9  Выводы',
    'Список использованных источников',
]
TOC_PAGES = {}
_toc_json = os.path.join(OUT_DIR, '_toc.json')
if os.path.exists(_toc_json):
    TOC_PAGES = json.load(open(_toc_json, encoding='utf-8'))

for i, item in enumerate(toc, start=1):
    par = doc.add_paragraph()
    pf = par.paragraph_format
    pf.first_line_indent = Cm(0)
    pf.line_spacing = 1.5
    pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf.tab_stops.add_tab_stop(Cm(16.4), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
    r = par.add_run(item)
    r.font.name = FONT
    r.font.size = Pt(13)
    page_no = TOC_PAGES.get(str(i))
    r2 = par.add_run('\t' + (str(page_no) if page_no else ''))
    r2.font.name = FONT
    r2.font.size = Pt(13)
page_break()

# ======================= 1 =======================
h1('1  Цель работы и состав выполненных работ')
p('Цель работы — получить навыки проектирования и документирования API; проектирования, '
  'документирования и интеграции агентных систем на основе протокола MCP; создания окружения '
  'на основе технологии контейнеризации Docker.')
p('Объектом проектирования является подсистема записи на мероприятия университетских клубов '
  '(Campus Events). Модель требований и архитектура системы разработаны в лабораторной работе № 3, '
  'поэтому настоящая работа опирается на её результаты: требования уточнены под API, спроектированы '
  'логическая и физическая модели базы данных, маршруты и конечные точки, создана спецификация '
  'OpenAPI 3.0.3 и выполнено её тестирование на Mock-сервере.')
p('Согласно критериям оценивания, для группы 13 обязательными являются задания 1–4; задание 5 '
  '(MCP-сервер) выполнено дополнительно. Работа индивидуальная: все материалы размещены в открытом '
  'репозитории GitHub, продублированы в вики и на сайте GitHub Pages.')
table('Таблица 1 — Состав выполненных работ',
      ['Задание', 'Результат', 'Файлы в репозитории', 'Страница вики'],
      [['1. Модель требований и реестр вариантов использования',
        '20 вариантов использования, 4 действующих лица, диаграмма Use case, текстовые сценарии',
        'docs/02-requirements.md', 'Функциональные требования'],
       ['2. Логическая и физическая модели базы данных',
        '14 таблиц, 13 перечислений, DDL, ER-диаграмма, 15 проверок ограничений',
        'db/schema.sql, db/verify.sql', 'Схема базы данных'],
       ['3. Маршруты и конечные точки API',
        '25 маршрутов, 29 операций, 28 строк соответствия «вариант использования — HTTP-метод»',
        'api/openapi.yaml', 'API проекта'],
       ['4. Спецификация и тестирование API',
        'OpenAPI 3.0.3 (28 схем), Mock-сервер, 8 сценариев проверки, снимки ответов в Bruno',
        'api/, api/mock/', 'API проекта'],
       ['5. MCP-сервер (дополнительно)',
        '3 инструмента, 2 ресурса, 1 шаблон промпта, проверка в MCP Inspector',
        'mcp/', 'MCP-сервер']],
      widths=[4.4, 5.6, 3.6, 2.9], font=9,
      align_col=['left', 'left', 'left', 'left'])

# ======================= 2 =======================
h1('2  Объект проектирования и действующие лица')
p('Система автоматизирует запись студентов и сотрудников на мероприятия, которые проводят '
  'университетские клубы: хакатоны, лекции, спортивные турниры, экскурсии. Основные сущности — клуб, '
  'мероприятие, сессия (конкретные дата, время и место проведения), регистрация, билет с QR-кодом, '
  'отзыв.')
p('Выделены четыре действующих лица. Гость просматривает афишу и карточки мероприятий без '
  'авторизации. Участник записывается на сессию, отменяет запись, показывает билет и оставляет отзыв. '
  'Организатор создаёт мероприятия и сессии, видит список участников и выгружает его. Администратор '
  'модерирует публикации, управляет клубами и назначает роли. Вход выполняется через университетский '
  'CAS: тикет обменивается на JWT, дальнейшие запросы авторизуются заголовком Authorization.')
p('Ключевые ограничения предметной области, определившие проектные решения: количество мест на '
  'сессии ограничено, и переполнение невозможно ни при параллельных запросах, ни при отменах; '
  'использованный билет нельзя погасить повторно; принятое решение по заявке на модерацию не '
  'изменяется.')

# ======================= 3 =======================
h1('3  Задание 1. Модель требований и реестр вариантов использования')
p('Требования лабораторной работы № 3 дополнены до уровня, достаточного для проектирования API, и '
  'описаны трёхуровневой моделью «Действующее лицо → User Story → Use Case». Реестр содержит '
  '20 вариантов использования (UC-01 … UC-23), сгруппированных по функциональным областям: афиша и '
  'поиск, запись и билеты, работа организатора, модерация и администрирование, уведомления.')
p('Диаграмма вариантов использования (рисунок 1) построена в PlantUML и содержит четыре актора и '
  'пять смысловых разделов: регистрация, профиль, организация мероприятий, модерация и аналитика, '
  'каталог и поиск. Исходный код диаграммы хранится в репозитории рядом со скриптом сборки, поэтому '
  'изображение пересобирается одной командой при изменении требований.')
fig('use-cases.png', 'Рисунок 1 — Диаграмма вариантов использования: подсистема записи на мероприятия',
    width=13.4)
p('Для каждого варианта использования в реестре указан основной поток — конечные точки API, которые '
  'его реализуют, и исключительные ситуации с кодами ошибок. Фрагмент реестра приведён в таблице 2; '
  'полный реестр размещён на странице «Функциональные требования» в вики проекта и на сайте '
  'GitHub Pages.')
table('Таблица 2 — Реестр вариантов использования (фрагмент)',
      ['Вариант использования', 'Основной поток', 'Исключительные ситуации'],
      [['UC-01 Просмотреть афишу',
        'GET /events с фильтрами и постраничной выдачей; карточки с датой, клубом и числом свободных мест',
        'пустая выдача → 200, items: [] и подсказка снять фильтры'],
       ['UC-06 Отменить запись',
        'DELETE /registrations/{id}; место возвращается в фонд сессии, билет гасится',
        'билет уже отмечен → 409 TICKET_USED; чужая запись → 403 FORBIDDEN'],
       ['UC-09 Показать билет',
        'GET /tickets, GET /tickets/{id}; QR-код рисуется на клиенте из qr_payload',
        'билет отозван → 409 TICKET_USED'],
       ['UC-11 Создать мероприятие',
        'POST /events → черновик с сессиями и вместимостью',
        'название короче 3 символов → 422 TITLE_TOO_SHORT; сессия в прошлом → 422 SESSION_IN_PAST'],
       ['UC-12 Отправить на публикацию',
        'POST /events/{id}/submit; создаётся версия карточки и заявка на модерацию',
        'нет ни одной сессии → 422; заявка уже на рассмотрении → 409'],
       ['UC-15 Экспортировать список участников',
        'GET /sessions/{sid}/export → CSV или XLSX',
        'пустой список → 200 с файлом, содержащим только заголовок'],
       ['UC-23 Назначить роль',
        'PATCH /users/{id}/role; изменение попадает в журнал',
        'отзыв последнего администратора → 409; нет прав → 403 ROLE_REQUIRED']],
      widths=[3.9, 8.0, 4.6], font=9,
      align_col=['left', 'left', 'left'])
p('Текстовые сценарии оформлены для вариантов UC-05, UC-07/08, UC-13 и UC-17 — тех, где логика '
  'нетривиальна (лист ожидания, пакетная отметка присутствия, модерация); для каждого указаны '
  'предусловия, основной поток, альтернативы и постусловия. Остальные 15 вариантов описаны таблицей '
  '«шаг — действие — результат»: для линейных сценариев подробная форма избыточна.')

# ======================= 4 =======================
h1('4  Задание 2. Логическая и физическая модели базы данных')
p('Логическая модель уточнена: для каждой из 14 сущностей указаны первичный ключ, внешние ключи и '
  'кардинальность связей (таблица 3). Преобладают связи «один ко многим»: клуб → мероприятия, '
  'мероприятие → сессии, сессия → регистрации, регистрация → билет. Связь «многие ко многим» между '
  'пользователем и клубом разрешена через таблицу membership, которая хранит роль и дату вступления.')
table('Таблица 3 — Сущности базы данных',
      ['Таблица', 'Назначение'],
      [['club', 'Клуб: объединение организаторов, проводит мероприятия'],
       ['category', 'Справочник тематик для афиши и фильтров'],
       ['app_user', 'Учётная запись: роль, контакты, признак активности'],
       ['event', 'Мероприятие: карточка в афише, статус публикации'],
       ['session', 'Сессия: дата, время, место, вместимость; единица записи'],
       ['membership', 'Членство пользователя в клубе с ролью'],
       ['registration', 'Регистрация пользователя на сессию'],
       ['ticket', 'Билет: QR-код и отметка присутствия'],
       ['seat_offer', 'Предложение места из листа ожидания'],
       ['event_version', 'Снимок карточки мероприятия для модерации'],
       ['moderation_request', 'Заявка на модерацию: очередь проверки'],
       ['decision', 'Решение модератора по заявке, неизменяемое'],
       ['review', 'Отзыв: оценка 1–5 и текст после посещения'],
       ['notification', 'Уведомление: письмо или напоминание о событии']],
      widths=[4.2, 12.3], font=9,
      align_col=['left', 'left'])
p('Физическая модель реализована для PostgreSQL 16: 14 таблиц, 13 перечислений, 103 поля, три '
  'триггера и семь частичных уникальных индексов. Первичные ключи — UUID, время хранится в timestamptz '
  'в UTC, значения перечислений совпадают с подписями интерфейса, чтобы не поддерживать два словаря.')
p('Целостность обеспечена средствами СУБД, а не кодом приложения: триггеры на таблице registration '
  'пересчитывают занятые места при вставке и обновлении и не позволяют записать больше вместимости, '
  'триггер trg_decision_no_update запрещает изменять уже принятое решение. Частичные уникальные '
  'индексы не дают одному пользователю дважды записаться на одну сессию и дважды оставить отзыв о '
  'мероприятии.')
p('DDL и демонстрационные данные (34 строки) загружаются автоматически при старте контейнера '
  'PostgreSQL, поэтому развёртывание схемы сводится к одной команде. Для проверки ограничений написан '
  'сценарий db/verify.sql из 15 атакующих запросов: он выполняется на реальной СУБД и завершается '
  'откатом транзакции. Все 15 проверок пройдены — переполнение сессии, повторная запись, двойная '
  'отметка билета, изменение решения и нарушение диапазона оценки блокируются базой.')
fig('erd-physical.png', 'Рисунок 2 — ER-диаграмма физической модели базы данных', width=11.6)

# ======================= 5 =======================
h1('5  Задание 3. Маршруты и конечные точки API')
p('Спроектировано 25 маршрутов и 29 операций. Коллекции ресурсов именуются во множественном числе, '
  'вложенность не превышает двух уровней, действия, не сводимые к CRUD, оформлены как подресурсы: '
  'POST /events/{id}/submit, POST /sessions/{sid}/waitlist, POST /tickets/{id}/check-in. Полный '
  'перечень приведён в таблице 4.')
routes = [
    ('GET', '/events', 'Афиша с фильтрами и постраничной выдачей'),
    ('POST', '/events', 'Создать мероприятие (черновик)'),
    ('GET', '/events/{id}', 'Карточка мероприятия с сессиями'),
    ('PATCH', '/events/{id}', 'Изменить мероприятие'),
    ('POST', '/events/{id}/submit', 'Отправить мероприятие на публикацию'),
    ('GET', '/events/{id}/report', 'Сводка по мероприятию'),
    ('GET', '/search', 'Поиск по названию и описанию'),
    ('GET', '/categories', 'Справочник категорий'),
    ('GET', '/clubs', 'Список клубов'),
    ('POST', '/clubs', 'Создать клуб'),
    ('PATCH', '/clubs/{id}', 'Изменить или закрыть клуб'),
    ('POST', '/auth/cas/callback', 'Обмен тикета CAS на токен доступа'),
    ('GET', '/me', 'Текущий пользователь, его роль и клубы'),
    ('GET', '/notifications/settings', 'Настройки каналов уведомлений'),
    ('PUT', '/notifications/settings', 'Изменить каналы уведомлений'),
    ('PATCH', '/users/{id}/role', 'Назначить роль пользователю'),
    ('POST', '/sessions/{sid}/registrations', 'Записаться на сессию'),
    ('DELETE', '/registrations/{id}', 'Отменить запись'),
    ('POST', '/sessions/{sid}/waitlist', 'Встать в лист ожидания'),
    ('POST', '/seat-offers/{id}/accept', 'Принять предложенное место'),
    ('GET', '/tickets', 'Мои билеты'),
    ('GET', '/tickets/{id}', 'Билет с данными для QR-кода'),
    ('POST', '/tickets/{id}/check-in', 'Отметить присутствие по билету'),
    ('POST', '/checkins/batch', 'Пакетная отметка после работы без сети'),
    ('GET', '/sessions/{sid}/participants', 'Список участников сессии'),
    ('GET', '/sessions/{sid}/export', 'Выгрузка списка участников'),
    ('POST', '/reviews', 'Оставить отзыв о посещённом мероприятии'),
    ('GET', '/moderation/requests', 'Очередь заявок на модерацию'),
    ('POST', '/moderation/requests/{id}/decision', 'Принять решение по заявке'),
]
table('Таблица 4 — Маршруты и конечные точки API',
      ['Метод', 'Маршрут', 'Назначение'],
      [[m, r, s] for m, r, s in routes],
      widths=[2.0, 8.2, 6.3], font=9,
      align_col=['center', 'left', 'left'], keep_together=False)
p('Каждый вариант использования сопоставлен с HTTP-методом и маршрутом — всего 28 строк '
  'соответствия, они опубликованы на странице «API проекта» в вики. Такой реестр позволяет проверить '
  'в обе стороны: ни одно требование не осталось без конечной точки, и у каждой конечной точки есть '
  'основание в требованиях.')
p('Единый формат ошибки — объект из четырёх полей: code (машиночитаемый код, например NO_SEATS или '
  'TICKET_USED), message (текст для пользователя на русском языке), field (поле, не прошедшее '
  'проверку, или null) и traceId (идентификатор запроса для поиска в журналах). Коды ответов '
  'используются по назначению: 201 при создании, 204 при удалении, 401 при отсутствии или истечении '
  'токена, 403 при недостатке прав, 409 при конфликте состояния, 422 при ошибке валидации, 429 при '
  'превышении лимита запросов.')

# ======================= 6 =======================
h1('6  Задание 4. Спецификация OpenAPI и тестирование на Mock-сервере')
p('Спецификация оформлена в формате OpenAPI 3.0.3: 28 схем компонентов, описание безопасности '
  '(Bearer JWT), общие ответы и параметры пагинации. Для каждого POST- и PUT-запроса определены тело, '
  'обязательные поля, ограничения и полный набор статусов с пояснением смысла. Спецификация проходит '
  'проверку валидатором openapi-spec-validator без ошибок и предупреждений.')
p('Тестирование выполнено на Mock-сервере Prism 5, развёрнутом локально. Prism отдаёт ответ, '
  'описанный в контракте, а конкретный код запрашивается заголовком Prefer: code=<код>, поэтому '
  'проверка не зависит от случайной генерации данных и воспроизводится у любого проверяющего. Прогон '
  'из восьми сценариев (таблица 5) выполняется скриптом api/mock/smoke.py; результат — 8 из 8 PASS, '
  'полный протокол с телами запросов и ответов сохранён в репозитории.')
table('Таблица 5 — Сценарии проверки на Mock-сервере',
      ['Сценарий', 'Запрос', 'Код', 'Итог'],
      [['Афиша: успешный список', 'GET /events?size=2&page=1', '200', 'PASS'],
       ['Создание мероприятия: черновик принят', 'POST /events', '201', 'PASS'],
       ['Запись на сессию: место есть', 'POST /sessions/{sid}/registrations', '201', 'PASS'],
       ['Запись на сессию: свободных мест нет', 'POST /sessions/{sid}/registrations', '409', 'PASS'],
       ['Запись без токена', 'POST /sessions/{sid}/registrations', '401', 'PASS'],
       ['Список заявок модерации: чужая организация', 'GET /moderation/requests', '403', 'PASS'],
       ['Создание мероприятия: поле не прошло проверку', 'POST /events', '422', 'PASS'],
       ['Афиша: превышен лимит запросов', 'GET /events', '429', 'PASS']],
      widths=[7.2, 5.6, 1.7, 2.0], font=9,
      align_col=['left', 'left', 'center', 'center'])
p('Дополнительно контракт проверен в графическом клиенте Bruno: импортирована коллекция из восьми '
  'запросов, три ответа приведены на рисунках 3–5. Ответ 201 подтверждает приём черновика '
  'мероприятия, ответ 409 NO_SEATS — что на сессии не осталось свободных мест, ответ 403 — что '
  'очередь модерации недоступна пользователю без нужной роли.')
p('Побочный результат прогона: Mock-сервер выявил дефект контракта. Общий компонент ответа 422 '
  'возвращал пример «комментарий короче 10 символов» для всех пятнадцати операций, включая создание '
  'мероприятия. Пример перенесён в операцию решения по заявке, а общий компонент теперь отдаёт '
  'VALIDATION_FAILED с полем title. Это показывает, что проверка на Mock-сервере работает не только '
  'как демонстрация, но и как ревью контракта.')
fig('mock/bruno-201-created.png', 'Рисунок 3 — Проверка POST /events: ответ 201 Created', width=12.4)
fig('mock/bruno-409-no-seats.png',
    'Рисунок 4 — Проверка записи на сессию: ответ 409, свободных мест нет', width=12.4)
fig('mock/bruno-403-not-owner.png',
    'Рисунок 5 — Проверка очереди модерации: ответ 403, недостаточно прав', width=12.4)

# ======================= 7 =======================
h1('7  Задание 5. MCP-сервер (выполнено дополнительно)')
p('Для группы 13 задание 5 не является обязательным; MCP-сервер реализован как MVP на MCP Python SDK '
  'и демонстрирует, как AI-ассистент работает с подсистемой через три инструмента: create_registration '
  '(запись на сессию), cancel_registration (отмена записи) и check_in_ticket (отметка присутствия по '
  'QR-коду).')
p('Данные ассистент читает через два ресурса: catalog://events — каталог ближайших мероприятий со '
  'свободными местами, и шаблонный ресурс registrations://user/{user_id} — записи конкретного '
  'пользователя. Для типового сценария подготовлен шаблон промпта registration_help, задающий порядок '
  'действий: прочитать каталог, уточнить сессию у пользователя, вызвать инструмент.')
p('Главный принцип — правила проверяет сервер, а не модель: аргументы инструментов валидируются по '
  'JSON-схеме, вместимость считает база данных, повторная отметка билета идемпотентна и возвращает '
  'already_marked вместо ошибки, отмена использованного билета запрещена.')
fig('mcp/inspector-web.png', 'Рисунок 6 — MCP Inspector: инструменты сервера и результат вызова',
    width=15.2)
p('Сервер проверен официальным MCP Inspector (рисунок 6): получены списки инструментов, ресурсов и '
  'промптов, выполнены вызовы create_registration, check_in_ticket (дважды, для проверки '
  'идемпотентности) и вызов с несуществующей сессией, который вернул NOT_FOUND. Протокол проверки в '
  'режиме командной строки сохранён в репозитории, дополнительно 10 сценариев покрыты скриптом '
  'test_mcp.py. Инструкция по развёртыванию и примеры запросов от лица пользователя оформлены в '
  'mcp/README.md и на странице «MCP-сервер» в вики.')

# ======================= 8 =======================
h1('8  Организация работы над проектом и документирование')
p('Проект ведётся в GitHub Projects: четыре колонки To do / In progress / To check / Done, одна '
  'задача — один issue с критерием приёмки. На рисунке 7 показано состояние доски на момент сдачи. '
  'Работа индивидуальная, поэтому коммиты идут в ветку main небольшими шагами «одна задача — один '
  'коммит»; для доработок создаются отдельные ветки.')
fig('projects-board.png', 'Рисунок 7 — Доска проекта в GitHub Projects', width=15.2)
p('Документация построена по требованиям методических указаний. README содержит разделы Project Name, '
  'Description, Installation, Sub modules, Usage и Contributing. Вики состоит из восьми страниц — '
  'семи обязательных и страницы MCP-сервера. Сайт GitHub Pages повторяет структуру вики; '
  'дополнительно на нём опубликованы читаемые HTML-версии спецификации API и DDL, поскольку GitHub '
  'отдаёт файлы .yaml и .sql без указания кодировки, из-за чего кириллица в них отображается '
  'некорректно.')
p('Репозиторий проекта: https://github.com/1997yyyy/Human-Machine-Interface-Design-LAB4. '
  'Сайт проекта: https://1997yyyy.github.io/Human-Machine-Interface-Design-LAB4/', align='left')

# ======================= 9 =======================
h1('9  Выводы')
p('1. Требования лабораторной работы № 3 доведены до уровня, пригодного для проектирования API: '
  '20 вариантов использования, четыре действующих лица, диаграмма Use case и текстовые сценарии.')
p('2. Спроектированы логическая и физическая модели данных. Целостность обеспечена средствами '
  'PostgreSQL, а не кодом приложения, и подтверждена 15 проверками на реальной СУБД.')
p('3. Спроектированы 25 маршрутов и 29 операций REST API; каждый вариант использования сопоставлен с '
  'конечной точкой, определён единый формат ошибок.')
p('4. Создана и проверена спецификация OpenAPI 3.0.3. Тестирование на Mock-сервере (8 из 8) выявило '
  'дефект контракта, который был устранён.')
p('5. Реализован MCP-сервер с тремя инструментами, двумя ресурсами и шаблоном промпта; работа '
  'проверена официальным MCP Inspector.')
p('6. Освоены GitHub Projects, вики и GitHub Pages как средства ведения и документирования проекта.')

# ======================= ИСТОЧНИКИ =======================
h1('Список использованных источников')
sources = [
    '1. Давидовская М.И. Проектирование человеко-машинных интерфейсов: метод. указания к лаб. '
    'работе № 4. — Минск: БГУ, 2026. — 16 с.',
    '2. Проектирование REST API на примере интернет-магазина // GetAnalyst.',
    '3. Пример проектирования REST API библиотеки // GetAnalyst.',
    '4. Материалы по REST API, Postman и Swagger // GetAnalyst.',
    '5. OpenAPI Specification 3.0.3: https://spec.openapis.org/oas/v3.0.3',
    '6. SwaggerHub Documentation: https://support.smartbear.com/swaggerhub/docs/',
    '7. Bruno Documentation. Mock Servers: https://docs.usebruno.com/',
    '8. Model Context Protocol: https://modelcontextprotocol.io/',
    '9. GitHub Docs: boards, wikis, Pages: https://docs.github.com/',
]
for s in sources:
    p(s, size=12, indent=1.25, line=1.0, align='left')

doc.save(OUT)
print('saved:', OUT)

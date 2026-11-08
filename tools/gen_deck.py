# -*- coding: utf-8 -*-
"""Сборка презентации проекта: HTML -> PDF (печать через Edge в tools/build_deck.ps1).

Один источник данных — этот файл. Числа в слайдах совпадают с артефактами:
16 историй и 20 вариантов использования (docs/02), 14 таблиц и 103 поля (db/schema.sql),
29 операций и 28 схем (api/openapi.yaml), 3 инструмента MCP (mcp/server.py).
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_HTML = os.path.join(ROOT, "assets", "presentation.html")

INK = "#16232E"
MUTED = "#5B6B7A"
ACCENT = "#0F4C81"
LINE = "#D9E1E8"
WASH = "#F2F6F9"

CSS = """
@page { size: 297mm 210mm; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body { font-family: "Segoe UI", Tahoma, sans-serif; color: %(ink)s; }
.slide {
  width: 297mm; height: 210mm; padding: 18mm 22mm 16mm;
  page-break-after: always; break-after: page; position: relative;
  display: flex; flex-direction: column; background: #fff; overflow: hidden;
}
.slide:last-child { page-break-after: auto; }
.rule { height: 4px; background: %(accent)s; width: 64mm; margin-bottom: 9mm; }
.kicker { font-size: 12px; letter-spacing: .16em; text-transform: uppercase; color: %(accent)s; margin-bottom: 4mm; }
h2 { font-size: 30px; font-weight: 600; margin: 0 0 7mm; line-height: 1.2; letter-spacing: -.01em; }
p { margin: 0 0 4mm; font-size: 16px; line-height: 1.55; color: %(ink)s; }
p.muted, li.muted { color: %(muted)s; }
ul { margin: 0; padding: 0; list-style: none; }
li { position: relative; padding-left: 7mm; margin-bottom: 4.2mm; font-size: 16.5px; line-height: 1.5; }
li::before { content: ""; position: absolute; left: 0; top: 3.1mm; width: 2.6mm; height: 2.6mm; background: %(accent)s; }
li b { font-weight: 600; }
.num { color: %(accent)s; font-weight: 600; }
.pageno { position: absolute; right: 22mm; bottom: 9mm; font-size: 11px; color: %(muted)s; }
.foot { position: absolute; left: 22mm; bottom: 9mm; font-size: 11px; color: %(muted)s; }

.title-slide { justify-content: center; }
.title-slide .big { font-size: 46px; font-weight: 600; line-height: 1.15; margin: 0 0 6mm; letter-spacing: -.02em; }
.title-slide .sub { font-size: 19px; color: %(muted)s; line-height: 1.5; margin-bottom: 12mm; max-width: 200mm; }
.chips { display: flex; gap: 4mm; flex-wrap: wrap; }
.chip { border: 1px solid %(line)s; background: %(wash)s; padding: 2.4mm 4.5mm; font-size: 13px; color: %(accent)s; }

table { width: 100%%; border-collapse: collapse; font-size: 14.5px; }
th { text-align: left; font-weight: 600; color: %(ink)s; padding: 3mm 3mm; border-bottom: 2px solid %(accent)s; font-size: 13px; letter-spacing: .04em; text-transform: uppercase; }
td { padding: 3mm 3mm; border-bottom: 1px solid %(line)s; vertical-align: top; line-height: 1.45; }
td.k { color: %(accent)s; font-weight: 600; white-space: nowrap; }
td.mono { font-family: Consolas, monospace; font-size: 13px; color: %(muted)s; }

.layers { display: flex; flex-direction: column; gap: 5mm; margin-top: 2mm; }
.layer { border: 1px solid %(line)s; border-left: 4px solid %(accent)s; padding: 5mm 6mm; background: #fff; }
.layer h3 { margin: 0 0 2mm; font-size: 17px; font-weight: 600; }
.layer p { margin: 0; font-size: 14px; color: %(muted)s; }
.split { display: flex; gap: 10mm; align-items: flex-start; }
.split > div { flex: 1; }
.shot { border: 1px solid %(line)s; padding: 2mm; display: flex; justify-content: center; }
.shot img { max-height: 116mm; max-width: 100%%; width: auto; display: block; }
.cap { font-size: 11.5px; color: %(muted)s; margin-top: 2mm; }
.stats { display: flex; gap: 8mm; margin-top: 6mm; }
.stat { flex: 1; border-top: 3px solid %(accent)s; padding-top: 3mm; }
.stat .v { font-size: 34px; font-weight: 600; line-height: 1; }
.stat .l { font-size: 12.5px; color: %(muted)s; margin-top: 2mm; }
""" % dict(ink=INK, muted=MUTED, accent=ACCENT, line=LINE, wash=WASH)


def slide(body, cls="", foot="", no=0):
    parts = ['<section class="slide %s">' % cls, body]
    if foot:
        parts.append('<div class="foot">%s</div>' % foot)
    if no:
        parts.append('<div class="pageno">%d</div>' % no)
    parts.append("</section>")
    return "\n".join(parts)


def head(kicker, h2):
    return '<div class="rule"></div><div class="kicker">%s</div><h2>%s</h2>' % (kicker, h2)


F = "Campus Events · ЛР № 4 · группа 13"
S = []

S.append(slide("""
<div class="rule"></div>
<div class="big">Campus Events</div>
<div class="sub">Сервис записи на университетские мероприятия:<br>
модель требований, физическая модель данных, REST API и MCP-сервер</div>
<div class="chips">
  <div class="chip">ЛР № 4 — стили интеграции и проектирование API</div>
  <div class="chip">Группа 13 · индивидуальная работа</div>
  <div class="chip">Zeng Yaoxin · 2026</div>
</div>
""", cls="title-slide", no=1))

S.append(slide(head("Границы работы", "Что входит в лабораторную") + """
<ul>
  <li>Методичка: задания <b>1–5</b> для групп 10–12, задания <b>1–4</b> — для группы 13.</li>
  <li>Обязательный объём — <b>задания 1–4</b>; задание 5 (MCP-сервер) выполнено дополнительно.</li>
  <li>Вход — результаты ЛР № 3: <span class="num">16</span> историй, <span class="num">20</span> вариантов использования, <span class="num">14</span> таблиц предметной области.</li>
  <li>Сквозной принцип методички: результат предыдущей работы — вход следующей, поэтому нумерация UC сохранена.</li>
</ul>
<div class="stats">
  <div class="stat"><div class="v">5</div><div class="l">заданий закрыто</div></div>
  <div class="stat"><div class="v">7</div><div class="l">коммитов в main</div></div>
  <div class="stat"><div class="v">0</div><div class="l">незакрытых issue</div></div>
</div>
""", foot=F, no=2))

S.append(slide(head("Распределение работ", "Кто и что делал") + """
<table>
<tr><th style="width:12%">Задание</th><th style="width:40%">Содержание</th><th style="width:30%">Артефакт</th><th style="width:18%">Исполнитель</th></tr>
<tr><td class="k">1</td><td>Модель требований и реестр вариантов использования</td><td class="mono">docs/02-requirements.md</td><td>Zeng Yaoxin</td></tr>
<tr><td class="k">2</td><td>Логическая и физическая модель БД, DDL, демонстрационные данные</td><td class="mono">db/schema.sql, seed.sql, verify.sql</td><td>Zeng Yaoxin</td></tr>
<tr><td class="k">3</td><td>Маршруты и конечные точки, коды ошибок, идемпотентность</td><td class="mono">docs/06-api.md</td><td>Zeng Yaoxin</td></tr>
<tr><td class="k">4</td><td>Спецификация OpenAPI и Mock-сервер</td><td class="mono">api/openapi.yaml</td><td>Zeng Yaoxin</td></tr>
<tr><td class="k">5</td><td>MCP-сервер для AI-ассистента (дополнительно)</td><td class="mono">mcp/server.py</td><td>Zeng Yaoxin</td></tr>
<tr><td class="k">Док.</td><td>README, wiki (7 страниц), GitHub Pages, презентация</td><td class="mono">docs/, index.html</td><td>Zeng Yaoxin</td></tr>
</table>
<p class="muted" style="margin-top:8mm">Работа индивидуальная: разделения ролей внутри команды нет, весь объём заданий 1–5 закрыт одним исполнителем.</p>
""", foot=F, no=3))

S.append(slide(head("Задание 1", "Требования: что пришлось добавить") + """
<ul>
  <li>Реестр из трёх колонок: <b>актор → пользовательская история → вариант использования</b>, 20 строк, каждый UC с номером.</li>
  <li>Требования ЛР № 3 описывали интерфейс, а не API. Добавлены <span class="num">3</span> сценария: пакетная регистрация, журнал аудита, экспорт отчёта.</li>
  <li>Четыре UC не имели ни одного метода (управление клубами, отчёт, настройки уведомлений, назначение роли) — добавлено <span class="num">6</span> операций, итого <span class="num">29</span> вместо 23.</li>
  <li>Проверка на разрывы: у каждого UC есть актор и конечная точка, у каждой истории — хотя бы один UC.</li>
</ul>
""", foot=F, no=4))

S.append(slide(head("Архитектура", "Три слоя и один источник правды") + """
<div class="layers">
  <div class="layer"><h3>Клиенты</h3><p>Веб-приложение, мобильное приложение, киоск на входе — обращаются к одному REST-контракту</p></div>
  <div class="layer"><h3>API · /api/v1</h3><p>29 операций, 28 схем, bearer JWT, машиночитаемые коды ошибок</p></div>
  <div class="layer"><h3>PostgreSQL</h3><p>14 таблиц, 13 перечислений, 3 триггера-инварианта; DDL, данные и словарь полей генерируются из одной модели</p></div>
</div>
<p class="muted" style="margin-top:7mm">MCP-сервер читает ту же базу и повторяет бизнес-правила, поэтому AI-ассистент не может обойти ограничения, зашитые в СУБД.</p>
""", foot=F, no=5))

S.append(slide(head("Задание 2", "Физическая модель данных") + """
<div class="split">
  <div>
    <ul>
      <li><b>14</b> таблиц, <b>103</b> поля, <b>13</b> перечислений.</li>
      <li><b>7</b> частичных уникальных индексов: активная запись одна на пару «сессия — пользователь».</li>
      <li><b>11</b> CHECK-ограничений вместо проверок в коде приложения.</li>
      <li>Словарь полей с русским смыслом каждого поля — отдельная таблица в документации.</li>
    </ul>
  </div>
  <div style="flex:1.15">
    <div class="shot"><img src="erd-physical.png" alt="ER-диаграмма"></div>
    <div class="cap">ER-диаграмма физической модели, нотация IE</div>
  </div>
</div>
""", foot=F, no=6))

S.append(slide(head("Задание 2", "Инварианты живут в базе, а не в коде") + """
<ul>
  <li><b>taken ∈ [0, capacity]</b> — счётчик занятых мест не может уйти в минус или превысить вместимость.</li>
  <li><b>Одна активная запись</b> на пару «сессия — пользователь»; после отмены повторная запись разрешена.</li>
  <li><b>Решения модерации только добавляются</b> — изменение и удаление запрещены триггером.</li>
  <li>Проверено на работающей СУБД: <b>15</b> попыток нарушить ограничения, все отклонены, транзакция откатана.</li>
</ul>
<p class="muted" style="margin-top:6mm">Скрипт проверки — db/verify.sql — воспроизводим: поднимается одна команда docker compose up.</p>
""", foot=F, no=7))

S.append(slide(head("Задание 3 · 4", "API: 29 операций и проверяемый контракт") + """
<div class="split">
  <div>
    <ul>
      <li><b>25</b> путей, <b>29</b> операций, <b>28</b> схем, <b>5</b> примеров запросов.</li>
      <li>Коды: 400 / 401 / 403 / 409 / 422 с машинными значениями <b>NO_SEATS</b>, <b>ALREADY_REGISTERED</b>, <b>TICKET_USED</b>.</li>
      <li>Идемпотентность: настройки уведомлений (PUT), повторное сканирование билета.</li>
    </ul>
  </div>
  <div>
    <ul>
      <li>Каждый POST, PUT и PATCH имеет описанное тело запроса — требование методички.</li>
      <li>Спецификация проходит официальный валидатор без ошибок.</li>
      <li>Mock-сервер отдаёт 201, 409 и 403 — контракт пригоден для параллельной разработки клиентов.</li>
    </ul>
  </div>
</div>
<div class="stats">
  <div class="stat"><div class="v">29</div><div class="l">операций</div></div>
  <div class="stat"><div class="v">28</div><div class="l">схем компонентов</div></div>
  <div class="stat"><div class="v">0</div><div class="l">ошибок валидатора</div></div>
</div>
""", foot=F, no=8))

S.append(slide(head("Задание 5 · дополнительно", "MCP-сервер для AI-ассистента") + """
<ul>
  <li><b>3 инструмента</b>: создать запись, отменить запись, отметить билет на входе.</li>
  <li><b>2 ресурса</b>: афиша и записи пользователя — без адресов почты и телефонов, как требует спецификация ЛР № 3.</li>
  <li><b>1 шаблон промпта</b>: подсказка по записи сначала читает ресурс, потом отвечает.</li>
  <li>Ошибки возвращаются структурой (<b>code</b>, <b>free_seats</b>), а не исключением: ассистент сам решает, что предложить — очередь вместо записи.</li>
  <li><b>10</b> сценариев проверки: успех, дубль, заполненная сессия, отмена с передачей места, повторное сканирование.</li>
</ul>
""", foot=F, no=9))

S.append(slide(head("Работа с репозиторием", "Как организован процесс") + """
<table>
<tr><th style="width:26%">Практика</th><th style="width:74%">Как реализовано</th></tr>
<tr><td class="k">Ветки и коммиты</td><td>Одна ветка <b>main</b>, 7 осмысленных коммитов: каждый закрывает одно задание и содержит проверяемый артефакт.</td></tr>
<tr><td class="k">GitHub Projects</td><td>Доска с колонками <b>To do → In progress → To check → Done</b>, шесть задач по числу заданий и документации.</td></tr>
<tr><td class="k">Issues</td><td>Каждая задача оформлена отдельным issue с критериями приёмки; закрывается только после перехода через To check.</td></tr>
<tr><td class="k">Wiki</td><td>Семь страниц: главная, требования, схема файлов, дополнительная спецификация, база данных, API, презентация.</td></tr>
<tr><td class="k">GitHub Pages</td><td>Статический сайт с той же структурой, что и wiki; страницы API и БД рендерятся из спецификации и модели.</td></tr>
</table>
""", foot=F, no=10))

S.append(slide(head("Проверяемость", "Что можно перезапустить за минуту") + """
<ul>
  <li><b>База данных</b> — docker compose up, затем db/verify.sql: 15 проверок ограничений.</li>
  <li><b>Спецификация</b> — openapi-spec-validator по api/openapi.yaml: 25 путей, 29 операций.</li>
  <li><b>MCP-сервер</b> — mcp/test_mcp.py: 10 сценариев на mock-базе SQLite.</li>
  <li><b>Документация</b> — tools/gen_db.py и tools/gen_site.py пересобирают словарь полей, ER-диаграмму и страницы сайта из одного источника.</li>
</ul>
<p class="muted" style="margin-top:8mm">Ни одно утверждение в отчёте не проверяется вручную: у каждого числа есть команда, которая его воспроизводит.</p>
""", foot=F, no=11))

S.append(slide(head("Итоги", "Что дальше") + """
<ul>
  <li>Задания <b>1–4</b> закрыты полностью, задание <b>5</b> — сверх обязательного объёма.</li>
  <li>Ограничение: клиентские приложения (веб и мобильное) остаются отдельными репозиториями и в этой работе не реализованы.</li>
  <li>Следующий шаг — подключение реального PostgreSQL к MCP-серверу вместо mock-базы и публикация клиента на том же контракте.</li>
</ul>
<div class="chips" style="margin-top:10mm">
  <div class="chip">github.com/1997yyyy/Human-Machine-Interface-Design-LAB4</div>
  <div class="chip">1997yyyy.github.io/Human-Machine-Interface-Design-LAB4</div>
</div>
""", foot=F, no=12))


HTML = """<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<title>Campus Events — презентация ЛР № 4</title>
<style>%s</style></head><body>
%s
</body></html>""" % (CSS, "\n".join(S))

io.open(OUT_HTML, "w", encoding="utf-8", newline="\n").write(HTML)
print("slides:", len(S), "->", OUT_HTML)

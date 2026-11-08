# -*- coding: utf-8 -*-
"""Статические страницы для GitHub Pages: api/index.html и db/index.html.

Зачем это нужно. GitHub Pages отдаёт .yaml и .sql без параметра charset
(Content-Type: text/yaml, application/sql), поэтому браузер угадывает кодировку
по системной локали и кириллица превращается в мусор. Заголовки на Pages задать
нельзя, поэтому рядом с исходниками генерируются HTML-страницы с явным
<meta charset="utf-8">: их и показываем посетителю, а сами файлы остаются
ссылкой «скачать оригинал».

Запуск:  python tools/gen_site.py
"""
import html
import io
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import gen_db  # noqa: E402  — единая модель данных для страницы БД

CSS = """
  :root{
    --bg:#fbfbf9; --card:#ffffff; --ink:#1b1b19; --muted:#6b6b66;
    --line:#e2e1da; --accent:#0f6e56; --accent-soft:#e1f5ee;
    --get:#0f6e56; --post:#1f5fa8; --put:#8a5a00; --patch:#7a3fa0; --delete:#a33a2c;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);
       font:16px/1.65 -apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
  .wrap{max-width:880px;margin:0 auto;padding:56px 24px 80px}
  header{border-bottom:1px solid var(--line);padding-bottom:28px;margin-bottom:28px}
  .eyebrow{font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}
  h1{font-size:32px;line-height:1.2;margin:10px 0 12px;font-weight:600}
  .lead{color:var(--muted);margin:0;max-width:64ch}
  .stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:28px 0 10px}
  .stat{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
  .stat b{display:block;font-size:26px;font-weight:600;line-height:1.1}
  .stat span{font-size:13px;color:var(--muted)}
  h2{font-size:15px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);
     margin:44px 0 14px;font-weight:500}
  a{color:var(--accent)}
  code{background:#f1efe8;padding:1px 5px;border-radius:4px;font-size:13px}
  .op{background:var(--card);border:1px solid var(--line);border-radius:12px;
      padding:16px 20px;margin-bottom:10px}
  .op .head{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:6px}
  .m{font:600 11px/1 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.06em;
     color:#fff;padding:5px 8px;border-radius:5px}
  .m.get{background:var(--get)} .m.post{background:var(--post)} .m.put{background:var(--put)}
  .m.patch{background:var(--patch)} .m.delete{background:var(--delete)}
  .op .path{font:600 15px/1.3 ui-monospace,SFMono-Regular,Menlo,monospace}
  .op .sum{margin:0 0 4px;font-weight:600}
  .op .desc{margin:0;color:var(--muted);font-size:14px}
  .op .oid{font-size:12px;color:var(--muted)}
  table{width:100%;border-collapse:collapse;font-size:14px;background:var(--card);
        border:1px solid var(--line);border-radius:12px;overflow:hidden;margin:10px 0 0}
  th,td{text-align:left;padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:top}
  th{background:var(--accent-soft);font-weight:600;font-size:13px}
  tr:last-child td{border-bottom:none}
  .req{color:#a33a2c;font-size:12px}
  details{background:var(--card);border:1px solid var(--line);border-radius:12px;
          padding:12px 18px;margin-bottom:8px}
  details>summary{cursor:pointer;font-weight:600;font-size:15px}
  details[open]>summary{margin-bottom:8px}
  pre{background:#1f1f1d;color:#e9e6dc;padding:16px 18px;border-radius:12px;overflow:auto;
      font:12.5px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace}
  .methods{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
  footer{margin-top:52px;padding-top:20px;border-top:1px solid var(--line);
         color:var(--muted);font-size:13px}
  @media(max-width:640px){.stats{grid-template-columns:repeat(2,1fr)}h1{font-size:26px}}
"""


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def page(title, eyebrow, lead, body, stats=None):
    st = ""
    if stats:
        cells = "".join(f'<div class="stat"><b>{v}</b><span>{esc(k)}</span></div>'
                        for v, k in stats)
        st = f'<div class="stats">{cells}</div>'
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="eyebrow">{esc(eyebrow)}</div>
    <h1>{esc(title)}</h1>
    <p class="lead">{lead}</p>
  </header>
  {st}
  {body}
  <footer>
    <a href="../index.html">← На главную</a> ·
    <a href="https://github.com/1997yyyy/Human-Machine-Interface-Design-LAB4">Репозиторий</a> ·
    ПЧМИ, лабораторная работа № 4, группа 13
  </footer>
</div>
</body>
</html>
"""


# ------------------------------------------------------------ типы OpenAPI

def type_label(sch):
    if not sch:
        return "—"
    if "$ref" in sch:
        return sch["$ref"].rsplit("/", 1)[-1]
    t = sch.get("type", "")
    if t == "array":
        return "array&lt;" + type_label(sch.get("items", {})) + "&gt;"
    if "enum" in sch:
        return "enum"
    return (t + (" · " + sch["format"] if sch.get("format") else "")) or "—"


def merge_all_of(sch, spec):
    """Схема может быть allOf из $ref и inline-объекта — собираем свойства в один список."""
    props, required = {}, []
    for part in sch.get("allOf", [sch]):
        if "$ref" in part:
            name = part["$ref"].rsplit("/", 1)[-1]
            target = spec["components"]["schemas"].get(name, {})
            p, r = merge_all_of(target, spec)
            props.update(p)
            required += r
        else:
            props.update(part.get("properties", {}))
            required += part.get("required", [])
    return props, required


def schema_table(sch, spec):
    props, required = merge_all_of(sch, spec)
    if not props:
        t = type_label(sch)
        enum = sch.get("enum")
        extra = ""
        if enum:
            extra = "<br><span class='req'>" + " · ".join(esc(e) for e in enum) + "</span>"
        return f"<p class='desc'>Тип: <code>{t}</code>{extra}</p>"
    rows = []
    for name, p in props.items():
        mark = '<span class="req">*</span>' if name in required else ""
        note = p.get("description", "")
        extra = []
        if p.get("enum"):
            extra.append("значения: " + ", ".join(f"<code>{esc(e)}</code>" for e in p["enum"][:8]))
        for k in ("minLength", "maxLength", "minimum", "maximum", "pattern"):
            if k in p:
                extra.append(f"{k}={esc(p[k])}")
        if p.get("example") is not None:
            extra.append("пример: <code>" + esc(p["example"]) + "</code>")
        if extra:
            note = (note + " " if note else "") + "<span class='oid'>" + "; ".join(extra) + "</span>"
        rows.append(f"<tr><td><code>{esc(name)}</code>{mark}</td>"
                    f"<td>{type_label(p)}</td><td>{note or '—'}</td></tr>")
    return ("<table><tr><th>Поле</th><th>Тип</th><th>Смысл</th></tr>"
            + "".join(rows) + "</table>")


def ref_name(sch):
    return sch.get("$ref", "").rsplit("/", 1)[-1] if sch else ""


def deref(obj, spec):
    """$ref вида #/components/<раздел>/<Имя> раскрывается один раз."""
    seen = 0
    while isinstance(obj, dict) and "$ref" in obj and seen < 5:
        parts = obj["$ref"].split("/")           # ['#','components','parameters','EventId']
        obj = spec["components"][parts[-2]][parts[-1]]
        seen += 1
    return obj


# ------------------------------------------------------------------ api page

def build_api():
    spec = yaml.safe_load(io.open(os.path.join(ROOT, "api", "openapi.yaml"),
                                  encoding="utf-8"))
    paths = spec["paths"]
    ops = [(m, p, o) for p, item in paths.items()
           for m, o in item.items() if m in ("get", "post", "put", "patch", "delete")]
    schemas = spec["components"]["schemas"]

    by_tag = {}
    for m, p, o in ops:
        tag = (o.get("tags") or ["Прочее"])[0]
        by_tag.setdefault(tag, []).append((m, p, o))
    order = [t["name"] for t in spec.get("tags", [])] + \
            [t for t in by_tag if t not in {x["name"] for x in spec.get("tags", [])}]

    out = []
    out.append('<h2>Точки входа</h2><div class="op">')
    for s in spec.get("servers", []):
        out.append(f'<div style="margin-bottom:6px"><code>{esc(s["url"])}</code> '
                   f'<span class="oid">— {esc(s.get("description", ""))}</span></div>')
    sec = spec["components"].get("securitySchemes", {})
    for k, v in sec.items():
        out.append(f'<div class="oid">Аутентификация <code>{esc(k)}</code>: '
                   f'{esc(v.get("scheme", ""))} {esc(v.get("bearerFormat", ""))}. '
                   f'{esc(v.get("description", ""))}</div>')
    out.append("</div>")

    for tag in order:
        if tag not in by_tag:
            continue
        out.append(f"<h2>{esc(tag)}</h2>")
        for m, p, o in by_tag[tag]:
            out.append("<div class='op'>")
            out.append("<div class='head'>"
                       f"<span class='m {m}'>{m.upper()}</span>"
                       f"<span class='path'>{esc(p)}</span></div>")
            if o.get("summary"):
                out.append(f"<p class='sum'>{esc(o['summary'])}</p>")
            if o.get("description"):
                out.append(f"<p class='desc'>{esc(o['description'])}</p>")
            oid = o.get("operationId", "")
            auth = "без токена" if o.get("security") == [] else "Bearer JWT"
            out.append(f"<p class='oid'>{esc(oid)} · {auth}</p>")

            params = [deref(x, spec) for x in o.get("parameters", [])]
            if params:
                rows = []
                for pr in params:
                    sch = pr.get("schema", {})
                    req = '<span class="req">обязателен</span>' if pr.get("required") else "нет"
                    rows.append(f"<tr><td><code>{esc(pr['name'])}</code></td>"
                                f"<td>{esc(pr.get('in', ''))}</td><td>{type_label(sch)}</td>"
                                f"<td>{req}</td><td>{esc(pr.get('description', '')) or '—'}</td></tr>")
                out.append("<table><tr><th>Параметр</th><th>Где</th><th>Тип</th>"
                           "<th>Обязателен</th><th>Смысл</th></tr>" + "".join(rows) + "</table>")

            rb = o.get("requestBody")
            if rb:
                for ctype, media in rb.get("content", {}).items():
                    sch = media.get("schema", {})
                    name = ref_name(sch)
                    head = f"<p class='oid'>Тело запроса <code>{esc(ctype)}</code>"
                    if name:
                        head += f" → <a href='#{esc(name)}'><code>{esc(name)}</code></a>"
                    head += " · обязателен</p>" if rb.get("required") else " · необязателен</p>"
                    out.append(head)
                    out.append(schema_table(sch, spec))
                    if media.get("example") is not None:
                        out.append("<details><summary>Пример запроса</summary><pre>"
                                   + esc(yaml.safe_dump(media["example"], allow_unicode=True,
                                                        sort_keys=False))
                                   + "</pre></details>")

            resp = o.get("responses", {})
            rows = []
            for code, r in resp.items():
                r = deref(r, spec)
                content = r.get("content", {})
                ref = ""
                if content:
                    media = next(iter(content.values()))
                    ref = ref_name(media.get("schema", {}))
                rows.append(f"<tr><td><code>{esc(code)}</code></td>"
                            f"<td>{esc(r.get('description', ''))}</td>"
                            f"<td>{('<a href=#%s><code>%s</code></a>' % (esc(ref), esc(ref))) if ref else '—'}</td></tr>")
            if rows:
                out.append("<table><tr><th>Код</th><th>Смысл</th><th>Схема ответа</th></tr>"
                           + "".join(rows) + "</table>")
            out.append("</div>")

    out.append("<h2>Схемы данных ({} шт.)</h2>".format(len(schemas)))
    for name, sch in schemas.items():
        body = schema_table(sch, spec)
        if "$ref" in sch or sch.get("allOf"):
            parts = []
            for part in sch.get("allOf", [sch]):
                if "$ref" in part:
                    n = ref_name(part)
                    parts.append(f"наследует <a href='#{esc(n)}'><code>{esc(n)}</code></a>")
            if parts:
                body = "<p class='oid'>" + "; ".join(parts) + "</p>" + body
        out.append(f"<details id='{esc(name)}'><summary>{esc(name)}</summary>{body}</details>")

    stats = [(len(paths), "путей"), (len(ops), "операций"),
             (len(schemas), "схем данных"), (len(by_tag), "разделов")]
    body = ('<p class="oid">Страница собрана из <code>api/openapi.yaml</code> '
            f'скриптом <code>tools/gen_site.py</code>: <a href="openapi.yaml">скачать оригинал (YAML)</a>. '
            'Файл отдаётся без <code>charset</code>, поэтому в браузере исходник выглядит '
            'искажённо — читать спецификацию нужно здесь.</p>'
            + "\n".join(out))
    html_doc = page("Спецификация API — Campus Events",
                    "ПЧМИ · ЛР № 4 · задание 4 · OpenAPI 3.0.3",
                    "Афиша студенческих мероприятий БГУ: 29 операций, сгруппированных "
                    "по ролям. Каждая операция показывает параметры, тело запроса со "
                    "ссылкой на схему и коды ответов.", body, stats)
    p = os.path.join(ROOT, "api", "index.html")
    io.open(p, "w", encoding="utf-8", newline="\n").write(html_doc)
    return len(ops), len(schemas)


# ------------------------------------------------------------------- db page

def build_db():
    tables = gen_db.TABLES
    enums = gen_db.ENUMS

    rows = []
    for i, t in enumerate(tables, 1):
        fields = t["fields"]
        pk = next((f["n"] for f in fields if f.get("pk")), "—")
        fk = sum(1 for f in fields if f.get("fk"))
        purpose = t.get("purpose", "")
        ru = t.get("ru", "")
        note = (f"<b>{esc(ru)}</b><br>" if ru else "") + esc(purpose)
        rows.append(f"<tr><td>{i}</td><td><code>{esc(t['name'])}</code></td>"
                    f"<td>{note}</td><td>{len(fields)}</td><td><code>{esc(pk)}</code></td>"
                    f"<td>{fk or '—'}</td></tr>")
    tbl = ("<table><tr><th>№</th><th>Таблица</th><th>Назначение</th><th>Полей</th>"
           "<th>Первичный ключ</th><th>Внешних ключей</th></tr>" + "".join(rows) + "</table>")

    erows = []
    for name, vals in enums.items():
        erows.append(f"<tr><td><code>{esc(name)}</code></td><td>{len(vals)}</td>"
                     f"<td>{' · '.join(esc(v) for v in vals)}</td></tr>")
    en = ("<table><tr><th>Перечисление</th><th>Значений</th><th>Допустимые значения</th></tr>"
          + "".join(erows) + "</table>")

    sql = io.open(os.path.join(ROOT, "db", "schema.sql"), encoding="utf-8").read()
    pre = "<pre>" + esc(sql) + "</pre>"
    seed = io.open(os.path.join(ROOT, "db", "seed.sql"), encoding="utf-8").read()
    pre_seed = "<pre>" + esc(seed) + "</pre>"

    nfields = sum(len(t["fields"]) for t in tables)
    stats = [(len(tables), "таблиц"), (len(enums), "перечислений"),
             (nfields, "полей"), (sql.count("CREATE TRIGGER"), "триггера")]
    body = (
        '<p class="oid">Исходники отдаются без <code>charset</code>, поэтому в браузере '
        'они выглядят искажённо. Ниже — та же схема в читаемом виде: '
        '<a href="schema.sql">schema.sql</a>, <a href="seed.sql">seed.sql</a>.</p>'
        '<h2>Состав модели</h2>' + tbl
        + "<h2>Перечисления</h2>" + en
        + '<h2>DDL (db/schema.sql)</h2>' + pre
        + '<h2>Демонстрационные данные (db/seed.sql)</h2>' + pre_seed
    )
    html_doc = page("Физическая модель базы данных — Campus Events",
                    "ПЧМИ · ЛР № 4 · задание 2 · PostgreSQL 16",
                    "14 таблиц, 13 перечислений, 103 поля, 3 триггера-инварианта. "
                    "Ограничения проверены на работающей СУБД скриптом db/verify.sql — "
                    "15 проверок, все пройдены.", body, stats)
    p = os.path.join(ROOT, "db", "index.html")
    io.open(p, "w", encoding="utf-8", newline="\n").write(html_doc)
    return nfields


def main():
    n_ops, n_sch = build_api()
    n_fields = build_db()
    print(f"api/index.html: {n_ops} операций, {n_sch} схем")
    print(f"db/index.html: {n_fields} полей")


if __name__ == "__main__":
    main()

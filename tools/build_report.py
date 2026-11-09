# -*- coding: utf-8 -*-
"""Сборка отчёта: docx -> PDF -> номера страниц для содержания -> docx -> PDF.

Требуется установленный Microsoft Word (экспорт PDF через COM).
Запуск: python tools/build_report.py
"""
import json
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCX = os.path.join(BASE, 'report', 'Отчет_ЛР4_Zeng_Yaoxin.docx')
PDF = os.path.join(BASE, 'report', 'Отчет_ЛР4_Zeng_Yaoxin.pdf')
TOC = os.path.join(BASE, 'report', '_toc.json')

MARKERS = [
    'Цель работы и состав выполненных работ',
    'Объект проектирования и действующие лица',
    'Задание 1. Модель требований и реестр',
    'Задание 2. Логическая и физическая модели',
    'Задание 3. Маршруты и конечные точки',
    'Задание 4. Спецификация OpenAPI',
    'Задание 5. MCP-сервер',
    'Организация работы над проектом и документирование',
    'Выводы',
    'Список использованных источников',
]


def gen():
    subprocess.run([sys.executable, os.path.join(BASE, 'tools', 'gen_report.py')], check=True)


def to_pdf():
    import win32com.client as win32
    app = win32.DispatchEx('Word.Application')
    app.Visible = False
    app.DisplayAlerts = 0
    doc = app.Documents.Open(DOCX)
    try:
        doc.Fields.Update()
        doc.ExportAsFixedFormat(PDF, 17)
        return doc.ComputeStatistics(2)
    finally:
        doc.Close(0)
        app.Quit()


def toc_pages():
    import pymupdf
    doc = pymupdf.open(PDF)
    pages = [' '.join(p.get_text().split()) for p in doc]
    res = {}
    for i, marker in enumerate(MARKERS, start=1):
        res[str(i)] = None
        for idx in range(2, len(pages)):
            if marker in pages[idx]:
                res[str(i)] = idx + 1
                break
    return res


def preview():
    import pymupdf
    out = os.path.join(BASE, 'report', '_preview')
    os.makedirs(out, exist_ok=True)
    doc = pymupdf.open(PDF)
    for i, page in enumerate(doc):
        page.get_pixmap(dpi=95).save(os.path.join(out, 'p%02d.png' % (i + 1)))
    return doc.page_count


if __name__ == '__main__':
    gen()
    n1 = to_pdf()
    pages = toc_pages()
    json.dump(pages, open(TOC, 'w', encoding='utf-8'), ensure_ascii=False)
    gen()
    n2 = to_pdf()
    print('pages: pass1=%d, pass2=%d' % (n1, n2))
    print('toc:', pages)
    print('preview pages:', preview())

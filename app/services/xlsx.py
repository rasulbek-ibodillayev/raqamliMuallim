"""Oddiy .xlsx o'qish va yozish (faqat standart kutubxona: zipfile + XML).

Savollarni Excel orqali import qilish uchun yetarli: birinchi varaq, matn va son kataklari.
Formulalar, birlashtirilgan kataklar va formatlash e'tiborga olinmaydi.
"""
from __future__ import annotations

import io
import re
import zipfile
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
MAX_BYTES = 5 * 1024 * 1024        # yuklanadigan fayl hajmi
MAX_UNZIPPED = 50 * 1024 * 1024    # «zip bomba»dan himoya
MAX_ROWS = 2000


class XlsxError(ValueError):
    pass


def _col_index(ref: str) -> int:
    """'C7' → 2 (0 dan)."""
    letters = re.match(r"[A-Z]+", ref).group(0)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _col_letter(i: int) -> str:
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def read_rows(data: bytes) -> list[list[str]]:
    """Birinchi varaqning qatorlari (har katak — matn, bo'sh katak — '')."""
    if len(data) > MAX_BYTES:
        raise XlsxError("Fayl 5 MB dan katta")
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise XlsxError("Fayl .xlsx formatida emas") from None
    if sum(i.file_size for i in z.infolist()) > MAX_UNZIPPED:
        raise XlsxError("Fayl juda katta")
    names = set(z.namelist())
    try:
        shared = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall("m:si", NS):
                shared.append("".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")))
        sheet = _first_sheet(z, names)
        root = ET.fromstring(z.read(sheet))
    except (KeyError, ET.ParseError):
        raise XlsxError("Excel faylini o‘qib bo‘lmadi") from None
    rows = []
    for row in root.iter(f"{{{NS['m']}}}row"):
        cells: dict[int, str] = {}
        for c in row.findall("m:c", NS):
            ref, kind = c.get("r", ""), c.get("t")
            if kind == "inlineStr":
                val = "".join(t.text or "" for t in c.iter(f"{{{NS['m']}}}t"))
            else:
                v = c.find("m:v", NS)
                val = v.text if v is not None and v.text is not None else ""
                if kind == "s" and val.isdigit() and int(val) < len(shared):
                    val = shared[int(val)]
                elif kind is None and re.fullmatch(r"-?\d+\.0+", val):
                    val = val.split(".")[0]     # 45.0 → 45
            idx = _col_index(ref) if ref else len(cells)
            cells[idx] = val.strip()
        if cells:
            width = max(cells) + 1
            rows.append([cells.get(i, "") for i in range(width)])
        if len(rows) > MAX_ROWS + 1:
            raise XlsxError(f"Bir faylda ko‘pi bilan {MAX_ROWS} ta savol bo‘lsin")
    return rows


def _first_sheet(z: zipfile.ZipFile, names: set[str]) -> str:
    if "xl/workbook.xml" in names and "xl/_rels/workbook.xml.rels" in names:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        first = wb.find("m:sheets/m:sheet", NS)
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        if first is not None:
            rid = first.get(f"{{{NS['r']}}}id")
            for rel in rels:
                if rel.get("Id") == rid:
                    target = rel.get("Target", "").lstrip("/")
                    path = target if target.startswith("xl/") else "xl/" + target
                    if path in names:
                        return path
    return "xl/worksheets/sheet1.xml"


def write(rows: list[list[str]], sheet_name: str = "Savollar", widths: list[int] | None = None) -> bytes:
    """Qatorlar → .xlsx (birinchi qator qalin sarlavha, matnlar inlineStr)."""
    def cell(r, c, v):
        ref = f"{_col_letter(c)}{r + 1}"
        style = ' s="1"' if r == 0 else ""
        return (f'<c r="{ref}" t="inlineStr"{style}><is><t xml:space="preserve">{escape(str(v))}</t></is></c>'
                if v != "" else "")
    cols = "".join(f'<col min="{i + 1}" max="{i + 1}" width="{w}" customWidth="1"/>' for i, w in enumerate(widths or []))
    body = "".join(f'<row r="{r + 1}">' + "".join(cell(r, c, v) for c, v in enumerate(row)) + "</row>"
                   for r, row in enumerate(rows))
    sheet = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             f'<worksheet xmlns="{NS["m"]}"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" '
             'activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
             + (f"<cols>{cols}</cols>" if cols else "") + f"<sheetData>{body}</sheetData></worksheet>")
    files = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            '</Types>',
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>',
        "xl/workbook.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<workbook xmlns="{NS["m"]}" xmlns:r="{NS["r"]}"><sheets>'
            f'<sheet name="{escape(sheet_name)}" sheetId="1" r:id="rId1"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '</Relationships>',
        "xl/styles.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<styleSheet xmlns="{NS["m"]}">'
            '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
            '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
            '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
            '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>'
            '</styleSheet>',
        "xl/worksheets/sheet1.xml": sheet,
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in files.items():
            z.writestr(name, text)
    return buf.getvalue()

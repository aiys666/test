# -*- coding: utf-8 -*-
"""
把 Presto 结果写回 Excel 副本（不覆盖原文件）。

做法: 把 .xlsx 当 zip, 只替换目标 worksheet 的
      <dimension> / <sheetData> / <autoFilter ref>, 其余原样保留。
      - 文本用 inlineStr, 不碰 sharedStrings.xml
      - 每个数据行的列样式, 沿用原表首个数据行(第2行)对应列的 s
      - 日期写成 Excel 序列号(1900 日期系统)
      - 透视缓存不修改(整列范围本就覆盖全部行)
"""
import datetime
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _xlsx import idx_to_col  # noqa: E402

EPOCH = datetime.date(1899, 12, 30)          # Excel 1900 日期系统原点

# ---- 列类型判定：按表头名 ----
DATE_COLS = {"ltv_month", "ltv_month_d", "ltv_week", "ltv_week_d", "ltv_date"}
TEXT_COLS = {
    "app_channel_name", "app_channel_name_d",
    "product_name", "product_name_d",
    "app_version", "app_version_d",
    "channel_category", "channel_category_d",
    "register_media_source", "register_media_source_d",
    "is_low_amount_flag", "is_low_amount_flag_d",
}


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def parse_date(v):
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, datetime.date):
        return v
    s = str(v).strip()[:10]
    for sep in ("-", "/"):
        p = s.split(sep)
        if len(p) == 3:
            return datetime.date(int(p[0]), int(p[1]), int(p[2]))
    raise ValueError(f"无法解析日期: {v!r}")


def cell(ref, style, name, val):
    """生成一个单元格 XML。val 为 None/NaN 时空单元格。"""
    if val is None:
        return ""
    if isinstance(val, float) and val != val:      # NaN
        return ""
    if isinstance(val, str) and val.strip() == "":
        return ""
    if name in DATE_COLS:
        d = parse_date(val)
        return f'<c r="{ref}" s="{style}"><v>{(d - EPOCH).days}</v></c>'
    if name in TEXT_COLS:
        return f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{esc(val)}</t></is></c>'
    # 数值
    try:
        f = float(val)
    except (TypeError, ValueError):
        return f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{esc(val)}</t></is></c>'
    if f == int(f) and abs(f) < 1e15:
        return f'<c r="{ref}" s="{style}"><v>{int(f)}</v></c>'
    return f'<c r="{ref}" s="{style}"><v>{f!r}</v></c>'


def col_styles(sheet_xml):
    """从原表第1行(表头)与第2行(首个数据行)提取每列的样式索引。"""
    hdr, dat = {}, {}
    for row_no, target in ((1, hdr), (2, dat)):
        m = re.search(r'<row r="%d"[^>]*>(.*?)</row>' % row_no, sheet_xml, re.S)
        if not m:
            continue
        for c in re.finditer(r'<c r="([A-Z]+)\d+"(?: s="(\d+)")?', m.group(1)):
            col, s = c.group(1), c.group(2)
            n = 0
            for ch in col:
                n = n * 26 + (ord(ch) - 64)
            target[n] = int(s) if s else 0
    return hdr, dat


def row_attrs(sheet_xml):
    """取第2行的行级属性(如 ' s="1" customFormat="1"')，供新数据行复用。"""
    m = re.search(r'<row r="2"([^>]*)>', sheet_xml)
    if not m:
        return ""
    a = dict(re.findall(r'(\w[\w:]*)="([^"]*)"', m.group(1)))
    a.pop("r", None)
    a.pop("spans", None)
    return "".join(f' {k}="{v}"' for k, v in a.items())


def build_sheetdata(df, hdr_style, dat_style, rattr, ncols):
    """由 DataFrame 生成 <sheetData> 片段。"""
    names = list(df.columns)
    parts = []

    # 表头
    cells = []
    for i, nm in enumerate(names, 1):
        s = hdr_style.get(i) or hdr_style.get(1) or 1
        cells.append(f'<c r="{idx_to_col(i)}1" s="{s}" t="inlineStr">'
                     f'<is><t xml:space="preserve">{esc(nm)}</t></is></c>')
    parts.append(f'<row r="1" spans="1:{ncols}">' + "".join(cells) + "</row>")

    # 数据
    col_default = dat_style.get(1) or 1
    for k, rec in enumerate(df.itertuples(index=False), start=2):
        cells = []
        for i, (nm, val) in enumerate(zip(names, rec), 1):
            s = dat_style.get(i, col_default)
            cells.append(cell(f"{idx_to_col(i)}{k}", s, nm, val))
        parts.append(f'<row r="{k}"{rattr} spans="1:{ncols}">' + "".join(cells) + "</row>")

    return "<sheetData>" + "".join(parts) + "</sheetData>"


def write_sheet(src_xlsx, dst_xlsx, sheet_to_xml, df_map):
    """把 df_map{sheet名: DataFrame} 写入 dst_xlsx 的对应 worksheet。"""
    if not os.path.exists(dst_xlsx):
        import shutil
        shutil.copy2(src_xlsx, dst_xlsx)

    zin = zipfile.ZipFile(src_xlsx)
    zout = zipfile.ZipFile(dst_xlsx, "w", zipfile.ZIP_DEFLATED)

    patched = {}
    for sheet, xmlpath in sheet_to_xml.items():
        df = df_map[sheet]
        x = zin.read(xmlpath).decode("utf-8")
        hdr_s, dat_s = col_styles(x)
        rattr = row_attrs(x)
        ncols = len(df.columns)
        last = idx_to_col(ncols)
        nrows = len(df) + 1

        body = build_sheetdata(df, hdr_s, dat_s, rattr, ncols)
        x = re.sub(r"<dimension[^>]*/>", f'<dimension ref="A1:{last}{nrows}"/>', x, count=1)
        x = re.sub(r"<sheetData>.*</sheetData>", lambda _m: body, x, count=1, flags=re.S)
        x = re.sub(r'(<autoFilter ref=")[^"]*(")', lambda m: m.group(1) + f"A1:{last}{nrows}" + m.group(2), x, count=1)
        patched[xmlpath] = x.encode("utf-8")
        print(f"  {sheet:<14s} → {xmlpath}  {nrows-1} 行 × {ncols} 列  "
              f"(原 {idx_to_col(len(hdr_s))})")

    for item in zin.infolist():
        data = patched.get(item.filename)
        zout.writestr(item, data if data is not None else zin.read(item.filename))
    zout.close()
    zin.close()
    print(f"  ✓ 已写出 {os.path.basename(dst_xlsx)}")

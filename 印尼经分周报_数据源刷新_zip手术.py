# -*- coding: utf-8 -*-
"""
印尼经分周报 数据源 zip 手术核心模块
=====================================
只替换 3 个数据源 sheet(进件/投放/复贷) 的 <sheetData> 数据行，
并在 4 个 pivotCacheDefinition 中加入 refreshOnLoad="1"，其余内容(条件格式/
切片器/透视表定义/公式/样式)原样保留。

用法(供外部脚本调用):
    from _zip_surgery import refresh_data_sources
    refresh_data_sources(template_path, out_path, data_map, log=print)

data_map: {
  "数据源（进件）": DataFrame(43列),
  "投放数据源":     DataFrame(12列),
  "复贷数据源":     DataFrame(70列),
}
"""
import zipfile
import re
import io
from datetime import datetime, date

# sheet 名 -> (sheetN.xml, 列数)；文件编号通过 _map_sheet_files() 动态解析
TARGET_SHEETS = {
    "数据源（进件）": 43,
    "投放数据源": 12,
    "复贷数据源": 71,  # 2026-08-18 复贷表新增 issue_cnt_from_app 列 (70->71)
}
CACHE_FILES = [
    "xl/pivotCache/pivotCacheDefinition1.xml",
    "xl/pivotCache/pivotCacheDefinition2.xml",
    "xl/pivotCache/pivotCacheDefinition3.xml",
    "xl/pivotCache/pivotCacheDefinition4.xml",
]


def _map_sheet_files(zin):
    """动态解析 sheet 名 -> sheetN.xml 文件路径（基于 workbook.xml + rels）"""
    wbxml = zin.read("xl/workbook.xml").decode("utf-8", errors="replace")
    sheets = re.findall(r'<sheet[^>]*name="([^"]+)"[^>]*r:id="(rId\d+)"', wbxml)
    rels = zin.read("xl/_rels/workbook.xml.rels").decode("utf-8", errors="replace")
    rid_map = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="worksheets/(sheet\d+\.xml)"', rels))
    out = {}
    for name, rid in sheets:
        if rid in rid_map:
            out[name] = "xl/worksheets/" + rid_map[rid]
    return out

_EPOCH = datetime(1899, 12, 30)


def excel_serial(value):
    """日期/时间 -> Excel 序列号"""
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime(value.year, value.month, value.day)
    else:
        raise TypeError(f"not a date: {value!r}")
    delta = dt - _EPOCH
    return delta.days + delta.seconds / 86400.0


def parse_value(v):
    """把 pandas 单元格值转成 (kind, xml_fragment)
    kind: 'n' 数值 | 's' inlineStr 文本 | 'empty'
    日期字符串/对象 -> 数值(Excel序列号)
    """
    if v is None:
        return "empty", ""
    if isinstance(v, bool):
        return "n", str(int(v))
    if isinstance(v, (int, float)):
        return "n", repr(float(v)) if isinstance(v, float) else str(v)
    if isinstance(v, (datetime, date)):
        return "n", repr(excel_serial(v))
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return "empty", ""
        # 日期字符串
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                dt = datetime.strptime(s, fmt)
                return "n", repr(excel_serial(dt))
            except ValueError:
                continue
        # 数字字符串 -> 数值
        try:
            f = float(s)
            return "n", repr(f)
        except ValueError:
            pass
        # 文本
        esc = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return "s", esc
    return "s", str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_data_rows(df, col_styles):
    """生成数据行 XML（从第2行起）。col_styles: {col_index(1-based): s属性 or None}
    注意：必须用 enumerate 生成连续行号——DataFrame 经 pd.concat 分页拼接后
    index 每页从 0 重复，直接取 index 会导致行号错乱、数据互相覆盖。
    """
    rows = []
    ncols = df.shape[1]
    for offset, (_, row) in enumerate(df.iterrows()):
        r = offset + 2  # 数据从第2行开始，行号必须连续
        cells = []
        for ci in range(ncols):
            col_letter = _col_letter(ci)
            kind, frag = parse_value(row.iloc[ci])
            if kind == "empty":
                continue
            s = col_styles.get(ci + 1)
            s_attr = f' s="{s}"' if s else ""
            if kind == "n":
                cells.append(f'<c r="{col_letter}{r}"{s_attr}><v>{frag}</v></c>')
            else:
                cells.append(f'<c r="{col_letter}{r}"{s_attr} t="inlineStr"><is><t xml:space="preserve">{frag}</t></is></c>')
        rows.append(f'<row r="{r}" spans="1:{ncols}">' + "".join(cells) + "</row>")
    return "".join(rows)


def _col_letter(idx):
    """0-based -> 列字母 (A, B, ..., Z, AA...)"""
    letters = ""
    idx += 1
    while idx:
        idx, rem = divmod(idx - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def build_header_row(df, orig_row1_xml, old_ncols, new_ncols):
    """用 DataFrame 列名生成新表头行（当查询列数 > 模板列数时调用）。
    orig_row1_xml: 原表头行 XML；old_ncols: 原列数；new_ncols: 新列数。
    样式沿用原表头单元格的 s 属性（通常 s=2 深蓝底白字）。
    """
    # 从原表头提取每列样式 s（默认 s=2）
    styles = {}
    for cm in re.finditer(r'<c r="([A-Z]+)1"([^>]*)>', orig_row1_xml):
        letter = cm.group(1)
        attrs = cm.group(2)
        sm = re.search(r's="(\d+)"', attrs)
        ci = 0
        for ch in letter:
            ci = ci * 26 + (ord(ch) - 64)
        if sm:
            styles[ci] = sm.group(1)
    # 生成新表头
    cells = []
    for ci in range(new_ncols):
        letter = _col_letter(ci)
        s = styles.get(ci + 1, "2")
        # 列名可能含特殊字符，需 XML 转义
        name = str(df.columns[ci])
        esc = name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        cells.append(f'<c r="{letter}1" s="{s}" t="inlineStr"><is><t xml:space="preserve">{esc}</t></is></c>')
    return f'<row r="1" spans="1:{new_ncols}">' + "".join(cells) + "</row>"


def extract_row1_styles(sheet_xml, ncols):
    """从原 XML 的数据行(优先 row2，退化 row1)提取样式映射: {col_index: s}
    数据行日期列带 s=3(日期格式)，套用后新数据保持日期显示与透视表行为一致。
    """
    styles = {}
    for target in (2, 3, 1):
        m = re.search(rf'<row r="{target}"[^>]*>(.*?)</row>', sheet_xml, re.S)
        if not m:
            continue
        found = False
        for cm in re.finditer(r'<c r="([A-Z]+)\d+"([^>]*)>', m.group(1)):
            col_letter = cm.group(1)
            attrs = cm.group(2)
            sm = re.search(r's="(\d+)"', attrs)
            ci = sum((ord(ch) - 64) * (26 ** (len(col_letter) - 1 - k)) for k, ch in enumerate(col_letter))
            if sm:
                styles[ci] = sm.group(1)
                found = True
        if found:
            break
    return styles


def refresh_data_sources(template_path, out_path, data_map, log=print,
                         target_sheets=None, cache_files=None):
    """替换模板中指定数据源 sheet 的数据，并让透视表打开时自动刷新。

    参数:
        template_path: 模板 xlsx 路径
        out_path:      输出 xlsx 路径
        data_map:      {sheet名: DataFrame}，DataFrame 列数需与模板 sheet 一致
        log:           日志函数
        target_sheets: {sheet名: 列数}，默认用模块级 TARGET_SHEETS（可按国家/场景覆盖）
        cache_files:   需要加 refreshOnLoad 的 pivotCache 文件列表，默认用 CACHE_FILES
    """
    if target_sheets is None:
        target_sheets = TARGET_SHEETS
    if cache_files is None:
        cache_files = CACHE_FILES

    # 1. 读取原 zip 所有条目
    zin = zipfile.ZipFile(template_path, "r")
    items = {}
    for info in zin.infolist():
        items[info.filename] = (info, zin.read(info.filename))
    sheet_files = _map_sheet_files(zin)
    zin.close()

    # 2b. 若某数据源 DataFrame 列数比模板表头列数多，先扩展引用它的 pivotCache 范围
    #     （必须在替换数据前用原始模板表头判断，替换后表头已变成新列数）
    for sheet_name, df in data_map.items():
        fname = sheet_files.get(sheet_name)
        if fname is None:
            continue
        actual_ncols = df.shape[1]
        info0, raw0 = items[fname]
        xml0 = raw0.decode("utf-8")
        m_row1 = re.search(r'<row r="1"[^>]*>.*?</row>', xml0, re.S)
        tpl_hdr = len(re.findall(r'<c r=', m_row1.group(0))) if m_row1 else target_sheets.get(sheet_name, actual_ncols)
        if actual_ncols <= tpl_hdr:
            continue
        old_letter = _col_letter(tpl_hdr - 1)   # 模板最后一列字母（如 BR=70列）
        new_letter = _col_letter(actual_ncols - 1)  # 新最后一列（如 BS=71列）
        for fname_c in cache_files:
            if fname_c not in items:
                continue
            info_c, raw_c = items[fname_c]
            cxml = raw_c.decode("utf-8")
            old_ref = f'A1:{old_letter}1048576'
            new_ref = f'A1:{new_letter}1048576'
            if f'"{old_ref}"' in cxml and f'sheet="{sheet_name}"' in cxml:
                cxml = cxml.replace(f'"{old_ref}"', f'"{new_ref}"')
                items[fname_c] = (info_c, cxml.encode("utf-8"))
                log(f"  [i] cache 范围已扩展: {sheet_name} {old_ref} -> {new_ref}")

    # 2c. 替换数据源 sheet 的 sheetData
    for sheet_name, ncols in target_sheets.items():
        fname = sheet_files.get(sheet_name)
        if fname is None:
            log(f"  [!] 模板中找不到 sheet: {sheet_name}")
            continue
        if sheet_name not in data_map:
            log(f"  [!] 缺 {sheet_name} 数据，跳过")
            continue
        df = data_map[sheet_name]
        info, raw = items[fname]
        xml = raw.decode("utf-8")

        # 实际列数以 DataFrame 为准（查询可能比模板多列，如复贷新增 issue_cnt_from_app）
        actual_ncols = df.shape[1]
        if actual_ncols != ncols:
            log(f"  [i] {sheet_name}: DataFrame {actual_ncols} 列 != 配置 {ncols} 列，按实际列数处理")

        # 提取原数据行样式（按实际列数上限截取）
        row1_styles = extract_row1_styles(xml, actual_ncols)
        new_rows = build_data_rows(df, row1_styles)
        total_rows = 1 + len(df)  # 含表头

        # 更新 dimension（按实际列数）
        xml_new = re.sub(r'<dimension ref="[^"]*"',
                         f'<dimension ref="A1:{_col_letter(actual_ncols-1)}{total_rows}"', xml, count=1)
        # 替换 sheetData: 保留 <sheetData> 开头和 </sheetData> 结尾，中间只留表头行
        m_open = re.search(r"<sheetData>", xml_new)
        m_close = re.search(r"</sheetData>", xml_new)
        if not m_open or not m_close:
            raise RuntimeError(f"{fname}: 找不到 sheetData 边界")
        # 取原表头行；若 DataFrame 列数比模板表头列数多，用 DataFrame 列名生成新表头
        m_row1 = re.search(r'<row r="1"[^>]*>.*?</row>', xml_new, re.S)
        head_row = ""
        template_header_cols = 0
        if m_row1:
            # 数模板表头实际列数（模板可能比配置少，如复贷模板 70 列、配置/查询 71 列）
            template_header_cols = len(re.findall(r'<c r=', m_row1.group(0)))
            if actual_ncols <= template_header_cols:
                head_row = m_row1.group(0)
            else:
                head_row = build_header_row(df, m_row1.group(0), template_header_cols, actual_ncols)
                log(f"  [i] {sheet_name}: 表头已按查询列名扩展为 {actual_ncols} 列 (模板原 {template_header_cols} 列)")
        new_sheet = (
            xml_new[: m_open.end()]
            + head_row
            + new_rows
            + xml_new[m_close.start():]
        )
        items[fname] = (info, new_sheet.encode("utf-8"))
        log(f"  [OK] {sheet_name}: {len(df)} 行 x {actual_ncols} 列 -> {fname}")

    # 3. 给 pivotCacheDefinition 加 refreshOnLoad="1"
    for fname in cache_files:
        if fname not in items:
            continue
        info, raw = items[fname]
        xml = raw.decode("utf-8")
        if 'refreshOnLoad="1"' in xml:
            log(f"  [=] {fname} 已有 refreshOnLoad")
            continue
        # 在 <pivotCacheDefinition ...> 开始标签中插入属性
        xml_new = re.sub(
            r'<pivotCacheDefinition([^>]*?)/?>',
            lambda m: m.group(0).replace(m.group(1), m.group(1) + ' refreshOnLoad="1"', 1)
            if 'refreshOnLoad' not in m.group(1) else m.group(0),
            xml,
            count=1,
        )
        items[fname] = (info, xml_new.encode("utf-8"))
        log(f"  [OK] {fname} +refreshOnLoad")

    # 4. 写新 zip
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for fname, (info, data) in items.items():
            zout.writestr(info, data)
    log(f"  [DONE] 输出: {out_path}")


if __name__ == "__main__":
    import pandas as pd
    # mock 数据测试
    test_map = {
        "数据源（进件）": pd.DataFrame({"a": [1, 2], "b": ["x", "y"]}),
        "投放数据源": pd.DataFrame({"a": [1.5], "b": ["2026-06-17"]}),
        "复贷数据源": pd.DataFrame({"a": [1], "b": [2]}),
    }
    print("模块加载成功")

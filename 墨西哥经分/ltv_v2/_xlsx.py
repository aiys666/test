# -*- coding: utf-8 -*-
"""
LTV v2 交付用的 xlsx 读写工具。

背景: 目标工作簿含数据透视缓存, openpyxl 打开会抛
      TypeError: Nested.from_tree() missing 1 required positional argument
      因此必须把 .xlsx 当 zip 处理, 直接改 worksheet XML。

关键约束: 透视表缓存按【列顺序索引】引用字段。
      因此绝不能插入/重排列 —— 新列只能追加在区间末尾。
"""
import os
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NSR = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def col_to_idx(ref):
    """'AB12' -> 27 (1-based 列号)"""
    m = re.match(r"([A-Z]+)", ref)
    n = 0
    for ch in m.group(1):
        n = n * 26 + (ord(ch) - 64)
    return n


def idx_to_col(n):
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


class Workbook:
    """只读探针 + 定向写回。"""

    def __init__(self, path):
        self.path = path
        self.zf = zipfile.ZipFile(path)
        self.shared = self._shared_strings()
        self.sheets = self._sheet_map()

    def _shared_strings(self):
        try:
            root = ET.fromstring(self.zf.read("xl/sharedStrings.xml"))
        except KeyError:
            return []
        out = []
        for si in root.findall(f"{NS}si"):
            out.append("".join(t.text or "" for t in si.iter(f"{NS}t")))
        return out

    def _sheet_map(self):
        """{sheet 名: 'xl/worksheets/sheetN.xml'}"""
        wb = ET.fromstring(self.zf.read("xl/workbook.xml"))
        rels = ET.fromstring(self.zf.read("xl/_rels/workbook.xml.rels"))
        rid2t = {r.get("Id"): r.get("Target") for r in rels}
        out = {}
        for sh in wb.find(f"{NS}sheets"):
            tgt = rid2t[sh.get(f"{NSR}id")]
            if not tgt.startswith("xl/"):
                tgt = "xl/" + tgt.lstrip("/")
            out[sh.get("name")] = tgt
        return out

    def header(self, sheet, row=1):
        """返回该行所有单元格的值（按列号展开，含空单元格的 None）。"""
        path = self.sheets[sheet]
        root = ET.fromstring(self.zf.read(path))
        cells = {}
        for c in root.iter(f"{NS}c"):
            ref = c.get("r")
            r = int(re.sub(r"[A-Z]", "", ref))
            if r != row:
                continue
            v = c.find(f"{NS}v")
            if v is None:
                val = None
            elif c.get("t") == "s":
                val = self.shared[int(v.text)]
            else:
                val = v.text
            cells[col_to_idx(ref)] = val
        if not cells:
            return []
        return [cells.get(i) for i in range(1, max(cells) + 1)]

    def dims(self, sheet):
        """返回 (最大行, 最大列)，读 worksheet 的 dimension。"""
        root = ET.fromstring(self.zf.read(self.sheets[sheet]))
        d = root.find(f"{NS}dimension")
        ref = d.get("ref") if d is not None else ""
        m = re.match(r"([A-Z]+)(\d+):([A-Z]+)(\d+)", ref or "")
        if not m:
            return None, None
        return int(m.group(4)), col_to_idx(m.group(3))

    def row_count(self, sheet):
        """数据行数（不含表头）。"""
        n, _ = self.dims(sheet)
        return (n - 1) if n else 0

    def close(self):
        self.zf.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


if __name__ == "__main__":
    import sys
    with Workbook(sys.argv[1]) as wb:
        print("工作表数:", len(wb.sheets))
        for name in sys.argv[2:]:
            if name not in wb.sheets:
                print(f"\n!! 没有名为 {name} 的工作表")
                continue
            n, c = wb.dims(name)
            hdr = wb.header(name)
            print(f"\n=== {name} ===  {idx_to_col(c)}1 结尾 / {n} 行 (数据 {n-1} 行) / {len(hdr)} 列")
            for i, h in enumerate(hdr, 1):
                print(f"  {idx_to_col(i):>3s} {h}")

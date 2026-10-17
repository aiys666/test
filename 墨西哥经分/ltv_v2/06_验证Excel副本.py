# -*- coding: utf-8 -*-
"""验证写出的 Excel 副本: 维度/行数/表头/首末行/日期序列号。

不依赖 openpyxl（这些工作簿 openpyxl 打不开），直接按 zip+XML 读。
用法:
    python 06_验证Excel副本.py            # 月版 + 周版
    python 06_验证Excel副本.py m
"""
import datetime
import os
import re
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _xlsx import Workbook, idx_to_col   # noqa: E402

BASE = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\墨西哥风险"
EPOCH = datetime.date(1899, 12, 30)

FILES = {
    "m": ("墨西哥LTV更新_20260927_v2.xlsx",
          {"数据源-首贷": 36, "数据源-复贷": 68}),
    "w": ("墨西哥LTV更新_20260927 - 小金额-周_v2.xlsx",
          {"数据源-首贷": 36, "数据源-复贷": 69}),
}


def col_letter(n):
    return idx_to_col(n)


def parse_row(seg):
    """把 <row ...>...</row> 解析成 {列字母: 值字符串}。"""
    out = {}
    for m in re.finditer(
            r'<c r="([A-Z]+)\d+"([^>]*?)(?:/>|>(.*?)</c>)', seg, re.S):
        ref, attrs, body = m.group(1), m.group(2), m.group(3) or ""
        if body == "":
            out[ref] = None
            continue
        if 't="inlineStr"' in attrs:
            tm = re.search(r"<t[^>]*>(.*?)</t>", body, re.S)
            out[ref] = tm.group(1) if tm else ""
        elif 't="s"' in attrs:
            vm = re.search(r"<v>(\d+)</v>", body)
            out[ref] = ("SHARED#" + vm.group(1)) if vm else ""
        else:
            vm = re.search(r"<v>([^<]*)</v>", body)
            out[ref] = vm.group(1) if vm else ""
    return out


def rows_of(data, want):
    """从 worksheet XML 串里取指定行号, 返回 {行号: {列: 值}}。"""
    got = {}
    tgt = set(want)
    for m in re.finditer(r'<row r="(\d+)"[^>]*>(.*?)</row>', data, re.S):
        r = int(m.group(1))
        if r in tgt:
            got[r] = parse_row(m.group(2))
    return got


def check(key):
    fn, sheets = FILES[key]
    path = os.path.join(BASE, fn)
    print("=" * 78)
    print(f"{fn}")
    print("=" * 78)
    if not os.path.exists(path):
        print("  !! 文件不存在")
        return False

    wb = Workbook(path)
    ss = wb.shared
    ok = True
    for sheet, ncol in sheets.items():
        xml = wb.sheets.get(sheet)
        print(f"\n--- 【{sheet}】 {xml}")
        if not xml:
            print("  !! 找不到该 sheet")
            ok = False
            continue
        dim = wb.dims(sheet)
        print(f"  dimension : {dim}")
        data = wb.zf.read(xml).decode("utf-8", "replace")
        er = re.findall(r'<row r="(\d+)"', data)
        last = max(int(x) for x in er) if er else 0
        got = rows_of(data, {1, 2, last})
        nonempty = 0
        for m in re.finditer(r'<row r="(\d+)"[^>]*>(.*?)</row>', data, re.S):
            if int(m.group(1)) == 1:
                continue
            if parse_row(m.group(2)):
                nonempty += 1

        hdr = got.get(1, {})
        names = []
        for i in range(1, ncol + 1):
            L = col_letter(i)
            v = hdr.get(L)
            if v and v.startswith("SHARED#"):
                v = ss[int(v.split("#")[1])]
            names.append(f"{L}={v}")
        print(f"  表头({ncol}列): " + " | ".join(names))

        r2 = got.get(2, {})
        print(f"  首行数据: " + " | ".join(
            f"{col_letter(i)}={r2.get(col_letter(i))}" for i in range(1, min(ncol, 12) + 1)))
        # 日期列序列号换算
        for cand in ("A", "B", "C", "D", "E"):
            v = r2.get(cand)
            if v and re.match(r"^\d{5}$", v):
                print(f"    {cand} 序列号 {v} → {EPOCH + datetime.timedelta(days=int(v))}")
        rl = got.get(last, {})
        print(f"  末行(r{last}): " + " | ".join(
            f"{col_letter(i)}={rl.get(col_letter(i))}" for i in range(1, min(ncol, 8) + 1)))
        print(f"  末列 = {col_letter(ncol)}  数据行数 = {nonempty}")
        if nonempty == 0:
            ok = False
    wb.close()
    return ok


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "mw"
    res = [check(k) for k in ("m", "w") if k in which]
    print("\n" + ("全部通过" if all(res) else "有异常"))
    return 0 if all(res) else 1


if __name__ == "__main__":
    sys.exit(main())

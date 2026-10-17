# -*- coding: utf-8 -*-
"""从 V6-1分析0923 - 副本 (2).xlsx 内部 XML 提取数据透视表计算字段公式"""
import sys, io, zipfile, re, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

XLSX = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\墨西哥风险\V6-1分析0923 - 副本 (2).xlsx"

z = zipfile.ZipFile(XLSX)
names = z.namelist()

print("=== 含 pivot 的文件 ===")
for n in names:
    if 'pivot' in n.lower():
        info = z.getinfo(n)
        print(f"{n}  ({info.file_size} bytes)")

print("\n=== pivotCacheDefinition 里的字段与公式 ===")
for n in names:
    if 'pivotCacheDefinition' in n:
        try:
            data = z.read(n).decode('utf-8', errors='replace')
        except Exception as e:
            print(f"[skip {n}] {e}")
            continue
        # 计算字段
        cfs = re.findall(r'<calculatedField[^>]*>.*?</calculatedField>', data, re.S)
        if cfs:
            print(f"\n--- {n} : calculatedField ---")
            for cf in cfs:
                name = re.search(r'name="([^"]+)"', cf)
                formula = re.search(r'<formula>(.*?)</formula>', cf, re.S)
                print(f"  name={name.group(1) if name else '?'}")
                print(f"  formula={formula.group(1) if formula else '?'}")
        # 普通字段
        flds = re.findall(r'<cacheField[^>]*name="([^"]+)"', data)
        if flds:
            print(f"\n--- {n} : cacheField names ({len(flds)}) ---")
            print("  " + ", ".join(flds))

print("\n=== pivotTableDefinition 里的 dataField（值字段）公式 ===")
for n in names:
    if 'pivotTable' in n and n.endswith('.xml'):
        data = z.read(n).decode('utf-8', errors='replace')
        dfs = re.findall(r'<dataField[^>]*name="([^"]+)"[^>]*>.*?</dataField>', data, re.S)
        if dfs:
            print(f"\n--- {n} ---")
            for d in dfs:
                print("  " + d[:200])
        # 也抓 formula
        for m in re.finditer(r'<dataField name="([^"]+)".*?<formula>(.*?)</formula>', data, re.S):
            print(f"  dataField={m.group(1)}  formula={m.group(2)}")

z.close()
print("\nDone.")

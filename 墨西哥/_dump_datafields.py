# -*- coding: utf-8 -*-
import zipfile, re, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
z = zipfile.ZipFile(r'E:\岳松个人文件\嘉银工作内容的整理\01工作内容\墨西哥风险\V6-1分析0923 - 副本 (2).xlsx')
for i in [1, 2]:
    d = z.read(f'xl/pivotTables/pivotTable{i}.xml').decode('utf-8', 'replace')
    names = re.findall(r'<dataField name="([^"]+)"', d)
    print(f'=== pivotTable{i}: {len(names)} dataFields ===')
    for j, n in enumerate(names):
        print(f'  {j:2d}  {n}')
    # 抓每个dataField的fld编号
    flds = re.findall(r'<dataField name="([^"]+)" fld="(\d+)"', d)
    print('  --- name -> fld ---')
    for n, f in flds:
        print(f'    fld={f}  {n}')
z.close()

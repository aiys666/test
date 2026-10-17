# -*- coding: utf-8 -*-
import zipfile, re, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
z = zipfile.ZipFile(r'E:\岳松个人文件\嘉银工作内容的整理\01工作内容\墨西哥风险\V6-1分析0923 - 副本 (2).xlsx')

d = z.read('xl/pivotCache/pivotCacheDefinition2.xml').decode('utf-8', 'replace')
fields = re.findall(r'<cacheField name="([^"]+)"', d)
print('cacheDefinition2 字段总数:', len(fields))

# dataField 的 fld -> 字段名映射
fld_map = {}
for n in ['pivotTable1', 'pivotTable2']:
    t = z.read(f'xl/pivotTables/{n}.xml').decode('utf-8', 'replace')
    flds = re.findall(r'<dataField name="([^"]+)" fld="(\d+)"', t)
    for name, f in flds:
        fi = int(f)
        fld_map.setdefault(fi, set()).add(name.strip())

print('\n=== 出账系列及其基础字段（fld->cacheDefinition2字段名）===')
for fi in sorted(fld_map):
    if fi < len(fields):
        print(f'  fld={fi}  cacheField={fields[fi]:28s}  dataField={sorted(fld_map[fi])}')
    else:
        print(f'  fld={fi}  (越界)  dataField={sorted(fld_map[fi])}')

z.close()

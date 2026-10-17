# -*- coding: utf-8 -*-
import zipfile, re, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
z = zipfile.ZipFile(r'E:\岳松个人文件\嘉银工作内容的整理\01工作内容\墨西哥风险\V6-1分析0923 - 副本 (2).xlsx')

# cacheField 索引 -> name
d = z.read('xl/pivotCache/pivotCacheDefinition1.xml').decode('utf-8', 'replace')
# 完整cacheField标签（可能跨行，用finditer找开始标签到/>
fields = re.findall(r'<cacheField name="([^"]+)"', d)
print('cacheField 总数:', len(fields))
print('\n=== 完整索引表 ===')
for i, n in enumerate(fields):
    print(f'{i:3d}  {n}')

z.close()

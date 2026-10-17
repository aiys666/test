import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

path = r'e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\22.墨西哥逾期率效果排查.sql'
sql = open(path, encoding='utf-8').read()

# 去掉整行注释
lines = [l for l in sql.splitlines() if not l.strip().startswith('--')]
sql2 = '\n'.join(lines)

# 按分号拆分语句
stmts = [s.strip() for s in sql2.split(';') if s.strip()]

pq = PrestoQuery()
pq.login()

for i, s in enumerate(stmts):
    first = s.split()[0].upper()
    if first in ('DROP', 'CREATE', 'INSERT'):
        print(f'=== 语句 {i}: {first} 开始 ===')
        ok, msg = pq.execute(s, wait_sec=3, timeout=1200)
        print(f'    -> ok={ok} msg={msg}')
    else:
        print(f'=== 语句 {i}: {first} 跳过 ===')

print('全部完成')

import sys, json, base64
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

path = r'e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\23.墨西哥逾期率效果排查_GROUPINGSETS.sql'
sql = open(path, encoding='utf-8').read()
lines = [l for l in sql.splitlines() if not l.strip().startswith('--')]
sql2 = '\n'.join(lines)
stmts = [s.strip() for s in sql2.split(';') if s.strip()]

# 找到第 4 条（batch2 的 INSERT，索引3对应文件里第二个 INSERT）
inserts = [s for s in stmts if s.split()[0].upper() == 'INSERT']
print('INSERT 条数:', len(inserts))
print('各条长度:', [len(s) for s in inserts])

pq = PrestoQuery()
pq.login()

# 诊断最短的一条 INSERT（batch4, 14维）
s = min(inserts, key=len)
print('诊断最短 INSERT, 长度:', len(s))

r = pq.sess.post(
    f"{pq.base}/dataworks-development/adhoc/querySql",
    headers=pq.headers,
    data=json.dumps({
        "sql": base64.b64encode(s.encode()).decode(),
        "engine": "PRESTO", "headRowNum": 54, "queryType": "Data",
        "dependStatus": 1, "windowId": 16, "varList": []
    }),
    timeout=(10, 180), verify=False
)
print('HTTP状态码:', r.status_code)
print('原始返回前1000字符:')
print(r.text[:1000])

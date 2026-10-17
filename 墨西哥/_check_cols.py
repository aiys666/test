import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
pq.login()

df = pq.query("SELECT column_name FROM information_schema.columns WHERE table_schema='mx' AND table_name='yj_test_table_250225'")
print(df.to_string())

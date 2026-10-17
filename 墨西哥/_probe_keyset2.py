# -*- coding: utf-8 -*-
"""测试 keyset 数字比较 & 单日行数"""
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
print("登录:", pq.login())

# keyset 数字比较（不带引号）
df2 = pq.query("""
select camera_id from ods.s02_loan
where release_time >= timestamp '2026-05-01' and state in (1,2)
and camera_id > 1620000419566695
order by camera_id limit 9999
""", wait_sec=1)
if isinstance(df2, str):
    print("keyset数字比较失败:", df2)
else:
    print("keyset数字 行数:", len(df2), "首:", df2.iloc[0]['camera_id'], "尾:", df2.iloc[-1]['camera_id'])

# 单日行数（放款/计划/明细）
for name, sql in [
    ("放款单日", """select count(*) c from ods.s02_loan where release_time >= timestamp '2026-05-01' and release_time < timestamp '2026-05-02' and state in (1,2)"""),
    ("计划单日", """select count(*) c from ods.s02_loan_repayment rp join ods.s02_loan l on l.camera_id=rp.camera_id where l.release_time >= timestamp '2026-05-01' and l.release_time < timestamp '2026-05-02' and l.state in (1,2)"""),
    ("明细单日", """select count(*) c from ods.s02_loan_repayment_detail rd join ods.s02_loan l on l.camera_id=rd.camera_id where l.release_time >= timestamp '2026-05-01' and l.release_time < timestamp '2026-05-02' and l.state in (1,2)"""),
]:
    d = pq.query(sql, wait_sec=1)
    print(name, d.to_dict('records') if not isinstance(d, str) else d)

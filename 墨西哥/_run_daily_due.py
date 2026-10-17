# -*- coding: utf-8 -*-
"""补跑 daily_due 分组（复用已建好的订单级表，避免重扫底表）。"""
import sys, os
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

OUT = os.path.join(r'E:\岳松个人文件\嘉银工作内容的整理\code\墨西哥', '_cache', 'sqlagg')
ORDER_TABLE = "mx.yuesong_asset_order"

METRICS = """
count(*) n_loan,
sum(contract_amount) contract_amount,
sum(should_sum) should_sum,
sum(fact_all) fact_all,
sum(unpaid_all) unpaid_all
"""

pq = PrestoQuery()
print("login", pq.login())
df = pq.query(f"""
select release_date, is_due, {METRICS}
from {ORDER_TABLE}
group by 1, 2
order by 1, 2
""")
if isinstance(df, str):
    print("FAIL", df)
else:
    p = os.path.join(OUT, 'daily_due.csv')
    df.to_csv(p, index=False)
    print(f"{len(df)} 行 -> {p}")
    print(df.head(10).to_string(index=False))

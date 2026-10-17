# -*- coding: utf-8 -*-
"""第二轮修正: 查funnel表字段名后重跑"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None); pd.set_option('display.width', 420)

def q(sql, tag="", show=150):
    print("="*130); print(tag)
    r = pq.query(sql)
    if isinstance(r, str): print("[ERR]", r[:1500]); return None
    if r is None or len(r)==0: print("[空]"); return None
    print(r.to_string() if len(r)<=show else r.head(show).to_string())
    print(f"[rows={len(r)}]"); return r

# F0: funnel表字段名排查
q("""
select column_name from information_schema.columns
where table_schema='mx' and table_name='wxs_application_funnel'
  and (column_name like '%amount%' or column_name like '%product%' or column_name like '%issue%' or column_name like '%loan%' or column_name like '%channel%' or column_name like '%media%' or column_name like '%source%')
order by 1
""", "F0 funnel表 金额/产品/渠道相关字段")

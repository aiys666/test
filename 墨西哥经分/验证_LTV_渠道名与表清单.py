# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery()
pq.login()
print("登录成功")

def run(sql, desc):
    print("\n" + "="*70)
    print(desc)
    print("="*70)
    r = pq.query(sql)
    if isinstance(r, pd.DataFrame):
        print(r.to_string())
    else:
        print("RESULT:", r)
    return r

# 所有 LTV 相关表
run("""
select table_name from information_schema.tables
where table_schema = 'mx' and table_name like 'ys_%ltv%'
order by table_name
""", "mx schema 下所有 LTV 相关表")

# 渠道名 group by
run("""
select reloan_app_channel_name, count(*) as row_cnt, sum(double_cnt) as dc
from mx.ys_dl_ltv_double_loan_group
group by 1
order by 3 desc
""", "新group表 复贷渠道名分布")

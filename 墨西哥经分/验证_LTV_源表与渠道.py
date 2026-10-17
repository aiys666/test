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

# 源表当前总量
run("""
select is_reloan, count(*) as row_cnt, count(distinct camera_id) as biz_cnt, sum(contract_amount) as amt
from mx.wxs_application_funnel
where if_issue = 1
group by 1
""", "源表 wxs_application_funnel 当前总量(按首复贷)")

# 复贷渠道分布（避开 count distinct 组合，用简单聚合）
run("""
select reloan_app_channel_name, sum(double_cnt) as dc, sum(contract_amount) as amt
from mx.ys_dl_ltv_double_loan_group
group by 1
order by 2 desc
limit 20
""", "新group表 复贷渠道名 top20")

# 复贷渠道id分布
run("""
select reloan_app_channel_d, sum(double_cnt) as dc
from mx.ys_dl_ltv_double_loan_group
group by 1
order by 2 desc
limit 20
""", "新group表 复贷渠道id top20")

# 明细表复贷渠道 vs group表是否一致
run("""
select count(distinct reloan_app_channel_name) as detail_channel_name_cnt
from mx.ys_dl_ltv_double_loan_0511
""", "明细表复贷渠道名去重数")

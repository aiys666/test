# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 400)
pd.set_option('display.max_colwidth', 40)

def q(sql, tag=""):
    print("="*110)
    print(tag)
    r = pq.query(sql)
    if isinstance(r, str):
        print("[ERR]", r[:600]); return None
    if r is None or len(r)==0:
        print("[空]"); return None
    print(r.to_string())
    print(f"[rows={len(r)}]")
    return r

# 0) funnel表是否有 apply_time；yj表 app_time vs 需求里的 apply_time 关系
df = pq.query("show columns from mx.wxs_application_funnel", wait_sec=2)
names = [str(x) for x in df['Column']]
for k in ['apply_time','app_time','app_date','release_time','if_issue','is_reloan','temp_grant_amount']:
    print(k, "存在" if k in names else "❌不存在", end=" | ")
print()
print("funnel 列数:", len(names))

# yj表里 app_time 和 apply_time 是否同源: 看 strategy_test_flag 非空的行, 其 app_date 分布
q("""
select temp_credit_amount_strategy_test_flag, 
  min(date(app_time)) min_app, max(date(app_time)) max_app,
  count(*) cnt
from mx.yj_test_table_250225
where temp_credit_amount_strategy_test_flag is not null
  and app_time >= cast('2026-08-01 00:00:00.000' as timestamp)
group by 1 order by 1
""", "Q0 strategy_test_flag 非空的 app_time 范围(yj表)")

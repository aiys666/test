# -*- coding: utf-8 -*-
"""第三轮: 在线临额细节指标核对(yj表) — strategy_test_flag / issue_tag / 使用临额均值件数总额 / fd_use_creditamount_score_v1&type"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 400)
pd.set_option('display.max_colwidth', 50)

def q(sql, tag="", show=60):
    print("="*120)
    print(tag)
    r = pq.query(sql)
    if isinstance(r, str):
        print("[ERR]", r[:800]); return None
    if r is None or len(r) == 0:
        print("[空数据]"); return None
    print(r.head(show).to_string() if len(r) > show else r.to_string())
    print(f"[rows={len(r)}]")
    return r

# 0) yj表字段存在性
df = pq.query("show columns from mx.yj_test_table_250225", wait_sec=2)
names = [str(x) for x in df['Column']]
for k in ['apply_time','app_time','app_date','release_time','temp_grant_amount','temp_credit_amount_issue_tag',
          'fd_use_creditamount_score_v1','fd_use_creditamount_type','credit_no','app_group_sha256','if_issue','is_reloan']:
    print(k, "存在" if k in names else "❌不存在", end=" | ")
print()
print("yj 列数:", len(names))

# 1) apply_time 与 app_time 是否同一天(yj表)
q("""
select
  count(*) cnt,
  count_if(date(apply_time) = date(app_time)) same_day,
  count_if(date(apply_time) != date(app_time)) diff_day,
  count_if(apply_time is null) apply_null,
  count_if(app_time is null) app_null
from mx.yj_test_table_250225
where app_time >= cast('2026-08-01 00:00:00.000' as timestamp)
""", "Q1 apply_time vs app_time 同日性(yj表, 8/1后)")

# 2) strategy_test_flag 分桶(按 apply_time 窗口, 与SQL一致)
q("""
select
  case when date(apply_time) >= date'2026-09-03' then 'A_9.3后(>0.3->V5_2)'
       when date(apply_time) >= date'2026-08-10' and date(apply_time) < date'2026-09-03' then 'B_8.10~9.3(>0.7->V5_2)'
       else 'C_8.10前(null)' end as win,
  temp_credit_amount_strategy_test_flag,
  count(*) cnt,
  count(distinct mid) mids
from mx.yj_test_table_250225
where app_time >= cast('2026-08-01 00:00:00.000' as timestamp)
group by 1,2 order by 1,2
""", "Q2 strategy_test_flag 分桶(apply_time窗口)")

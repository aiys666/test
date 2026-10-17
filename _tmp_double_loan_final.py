# -*- coding: utf-8 -*-
"""复贷最终查询NULL分布诊断: 拆分小查询 + 重试 + 输出UTF-8文件。"""
import sys, io, time
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

OUT = io.StringIO()
def log(*a):
    s = " ".join(str(x) for x in a)
    print(s); OUT.write(s + "\n")

def run(pq, sql, tag, tries=3):
    for i in range(tries):
        try:
            df = pq.query(sql, wait_sec=5)
            if isinstance(df, str):
                log(f"[{tag}] 尝试{i+1} FAILED:", df[:200])
                time.sleep(3); continue
            return df
        except Exception as e:
            log(f"[{tag}] 尝试{i+1} 异常:", repr(e)[:200])
            time.sleep(3)
    return None

# Q1: double_group 在 (month,wob,channel,grade) 粒度下是否有多行(loan_period拆分)
Q1 = """
select split_cnt as rows_per_combo, count(*) as combos
from (
  select ltv_month_d, wob_d, app_channel_name_d, new_grade_level_d, count(*) as split_cnt
  from mx.ys_dl_ltv_double_loan_group
  group by 1,2,3,4
) t
group by 1 order by 1
"""

# Q2: 最终网格规模 + limit安全
Q2 = """
with frst as (
  select ltv_month, app_channel_name, new_grade_level, count(distinct mid) as frs_cnt
  from mx.ys_dl_ltv_first_loan_0511 group by 1,2,3
)
select count(*) as cohorts, max(wob_d) as max_wob,
       count(*) * (max(wob_d)+1) as grid_rows,
       count(distinct ltv_month) as months
from (select ltv_month, app_channel_name, new_grade_level from mx.ys_dl_ltv_first_loan_0511 group by 1,2,3) c
cross join (select max(wob_d) as wob_d from mx.ys_dl_ltv_double_loan_group) w
"""

# Q3: 最终网格中, 有多少 (month,channel,grade,wob) combo 有double数据但frs_cnt应为null
#     逻辑: rnk>1 的double行 (同combo被loan_period拆分后第2+行) → join frst_loan需rnk=1 → null
Q3 = """
with frst as (
  select ltv_month, app_channel_name, new_grade_level, count(distinct mid) as frs_cnt
  from mx.ys_dl_ltv_first_loan_0511 group by 1,2,3
),
dg as (
  select ltv_month_d, app_channel_name_d, new_grade_level_d, wob_d, count(*) as rows_per_combo
  from mx.ys_dl_ltv_double_loan_group group by 1,2,3,4
)
select
  count(*) as total_dg_combos,
  count(case when rows_per_combo >= 2 then 1 end) as combos_with_multi,
  sum(case when rows_per_combo >= 2 then rows_per_combo - 1 else 0 end) as extra_rows_beyond_rnk1
from dg
"""

def main():
    pq = PrestoQuery(); pq.login(); log("login ok")
    for tag, sql in [("Q1 double_group按combo行数分布", Q1),
                     ("Q2 网格规模", Q2),
                     ("Q3 rnk>1导致的null数", Q3)]:
        df = run(pq, sql, tag)
        if df is None:
            log(f"  {tag}: 全部失败"); continue
        log(f"\n=== {tag} ===")
        log(df.to_string(index=False))

    with open(r"E:\岳松个人文件\嘉银工作内容的整理\code\_tmp_double_loan_final_out.txt", "w", encoding="utf-8") as f:
        f.write(OUT.getvalue())
    log("\n[已写入 _tmp_double_loan_final_out.txt]")

if __name__ == "__main__":
    main()

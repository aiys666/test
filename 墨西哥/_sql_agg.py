# -*- coding: utf-8 -*-
"""每日放款资产统计 —— SQL 端聚合版（Presto 下推，只下载聚合结果）。

步骤：
  1) 建订单级聚合表 mx.yuesong_asset_order（一次扫描三张底表）
  2) 对聚合表做多个轻量 GROUP BY，只下载聚合后的少量结果

口径（全部金额口径，对齐《01墨西哥风险宽表新口径.sql》）：
  - 放款范围: release_time in [2026-05-01, 2026-09-30), state in (1,2)
  - 应还 = should_capital + should_interest（repayment 按订单聚合）
  - 实还(广义, 已还) = fact_capital + fact_interest + subtract_capital + subtract_interest + coupon_amount
  - 未还(广义) = 应还 - 实还(广义)
  - 到期日 due_date = max(should_time)；已到期 is_due = due_date <= 2026-09-30
  - 时点字段（直接字段名，非分箱；只对现金实还 fact_capital+fact_interest 切分）：
      repay_pre3_cum(到期前>=3天累计) / repay_d3 / repay_d2 / repay_d1 / repay_d0 / repay_after_due(到期后)
  - 逾期窗累计现金实还: t0(<=到期日)/t1(+1)/t3(+3)/t7(+7)
  - 逾期未还金额 t{N}_overdue = max(应还 - (窗内现金实还 + 全部减免优惠), 0)，未到期记 0
  - 金额分箱 amount_bin: (0,200](200,500](500,1000](1000,2000](2000,3000](3000,4000](4000,5000] 5000+
  - 期限: loan_cycle 原始值(7/14/21/28/45)
  - 验证等式(本金口径): contract_amount = fact_capital + subtract_capital + unpaid_capital
输出: _cache/sqlagg/*.csv
"""
import sys, os, time
import pandas as pd
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE, '_cache', 'sqlagg')
os.makedirs(OUT_DIR, exist_ok=True)

OBS = "date '2026-09-30'"
D0 = "timestamp '2026-05-01 00:00:00'"
D1 = "timestamp '2026-09-30 00:00:00'"
ORDER_TABLE = "mx.yuesong_asset_order"

CREATE_SQL = f"""
create table {ORDER_TABLE} as
with loan as (
  select camera_id, date(release_time) release_date, loan_cycle,
         contract_amount, amount, haircut_amount, interest
  from ods.s02_loan
  where release_time >= {D0} and release_time < {D1} and state in (1,2)
),
should as (
  select rp.camera_id,
         sum(rp.should_capital) should_capital,
         sum(rp.should_interest) should_interest,
         sum(rp.should_capital) + sum(rp.should_interest) should_sum,
         max(rp.should_time) due_date,
         sum(rp.subtract_capital) subtract_capital,
         sum(rp.subtract_interest) subtract_interest,
         sum(rp.coupon_amount) coupon_amount
  from ods.s02_loan_repayment rp
  join loan l on l.camera_id = rp.camera_id
  group by rp.camera_id
),
fact as (
  select rd.camera_id,
         sum(rd.fact_capital) fact_capital,
         sum(rd.fact_interest) fact_interest
  from ods.s02_loan_repayment_detail rd
  join loan l on l.camera_id = rd.camera_id
  group by rd.camera_id
),
factwin as (
  select rd.camera_id,
         sum(case when date_diff('day', date(rd.fact_time), date(s.due_date)) >= 3 then rd.fact_capital + rd.fact_interest else 0 end) repay_pre3_cum,
         sum(case when date_diff('day', date(rd.fact_time), date(s.due_date)) >= 4 then rd.fact_capital + rd.fact_interest else 0 end) repay_pre4_cum,
         sum(case when date_diff('day', date(rd.fact_time), date(s.due_date)) >= 5 then rd.fact_capital + rd.fact_interest else 0 end) repay_pre5_cum,
         sum(case when date_diff('day', date(rd.fact_time), date(s.due_date)) >= 6 then rd.fact_capital + rd.fact_interest else 0 end) repay_pre6_cum,
         sum(case when date_diff('day', date(rd.fact_time), date(s.due_date)) >= 7 then rd.fact_capital + rd.fact_interest else 0 end) repay_pre7_cum,
         sum(case when date_diff('day', date(rd.fact_time), date(s.due_date)) = 3 then rd.fact_capital + rd.fact_interest else 0 end) repay_d3,
         sum(case when date_diff('day', date(rd.fact_time), date(s.due_date)) = 2 then rd.fact_capital + rd.fact_interest else 0 end) repay_d2,
         sum(case when date_diff('day', date(rd.fact_time), date(s.due_date)) = 1 then rd.fact_capital + rd.fact_interest else 0 end) repay_d1,
         sum(case when date_diff('day', date(rd.fact_time), date(s.due_date)) = 0 then rd.fact_capital + rd.fact_interest else 0 end) repay_d0,
         sum(case when date_diff('day', date(rd.fact_time), date(s.due_date)) < 0 then rd.fact_capital + rd.fact_interest else 0 end) repay_after_due,
         sum(case when date(rd.fact_time) <= date(s.due_date) then rd.fact_capital + rd.fact_interest else 0 end) t0_fact,
         sum(case when date(rd.fact_time) <= date_add('day', 1, date(s.due_date)) then rd.fact_capital + rd.fact_interest else 0 end) t1_fact,
         sum(case when date(rd.fact_time) <= date_add('day', 3, date(s.due_date)) then rd.fact_capital + rd.fact_interest else 0 end) t3_fact,
         sum(case when date(rd.fact_time) <= date_add('day', 7, date(s.due_date)) then rd.fact_capital + rd.fact_interest else 0 end) t7_fact,
         sum(case when date_diff('day', l.release_date, date(rd.fact_time)) = 0 then rd.fact_capital + rd.fact_interest else 0 end) repay_rel_d0,
         sum(case when date_diff('day', l.release_date, date(rd.fact_time)) = 1 then rd.fact_capital + rd.fact_interest else 0 end) repay_rel_d1,
         sum(case when date_diff('day', l.release_date, date(rd.fact_time)) = 2 then rd.fact_capital + rd.fact_interest else 0 end) repay_rel_d2,
         sum(case when date_diff('day', l.release_date, date(rd.fact_time)) = 3 then rd.fact_capital + rd.fact_interest else 0 end) repay_rel_d3,
         sum(case when date_diff('day', l.release_date, date(rd.fact_time)) = 7 then rd.fact_capital + rd.fact_interest else 0 end) repay_rel_d7,
         sum(case when date_diff('day', l.release_date, date(rd.fact_time)) = 14 then rd.fact_capital + rd.fact_interest else 0 end) repay_rel_d14,
         sum(case when date_diff('day', l.release_date, date(rd.fact_time)) = 21 then rd.fact_capital + rd.fact_interest else 0 end) repay_rel_d21,
         sum(case when date_diff('day', l.release_date, date(rd.fact_time)) = 28 then rd.fact_capital + rd.fact_interest else 0 end) repay_rel_d28,
         sum(case when date_diff('day', l.release_date, date(rd.fact_time)) >= 3 then rd.fact_capital + rd.fact_interest else 0 end) repay_rel_d3p
  from ods.s02_loan_repayment_detail rd
  join loan l on l.camera_id = rd.camera_id
  join should s on s.camera_id = rd.camera_id
  group by rd.camera_id
)
select
  l.camera_id, l.release_date, l.loan_cycle,
  case when l.loan_cycle in (7,14,21,28,45) then cast(l.loan_cycle as bigint) else 99 end loan_cycle_bin,
  l.contract_amount, l.amount, l.haircut_amount, l.interest,
  case when l.contract_amount <= 200 then 1
       when l.contract_amount <= 500 then 2
       when l.contract_amount <= 1000 then 3
       when l.contract_amount <= 2000 then 4
       when l.contract_amount <= 3000 then 5
       when l.contract_amount <= 4000 then 6
       when l.contract_amount <= 5000 then 7
       else 8 end amount_bin,
  coalesce(s.should_capital,0) should_capital,
  coalesce(s.should_interest,0) should_interest,
  coalesce(s.should_sum,0) should_sum,
  s.due_date,
  coalesce(s.subtract_capital,0) subtract_capital,
  coalesce(s.subtract_interest,0) subtract_interest,
  coalesce(s.coupon_amount,0) coupon_amount,
  coalesce(f.fact_capital,0) fact_capital,
  coalesce(f.fact_interest,0) fact_interest,
  coalesce(f.fact_capital,0) + coalesce(f.fact_interest,0) fact_cash,
  coalesce(s.subtract_capital,0) + coalesce(s.subtract_interest,0) + coalesce(s.coupon_amount,0) redu_all,
  coalesce(f.fact_capital,0) + coalesce(f.fact_interest,0)
    + coalesce(s.subtract_capital,0) + coalesce(s.subtract_interest,0) + coalesce(s.coupon_amount,0) fact_all,
  coalesce(s.should_sum,0) - (coalesce(f.fact_capital,0) + coalesce(f.fact_interest,0)
    + coalesce(s.subtract_capital,0) + coalesce(s.subtract_interest,0) + coalesce(s.coupon_amount,0)) unpaid_all,
  coalesce(s.should_capital,0) - (coalesce(f.fact_capital,0) + coalesce(s.subtract_capital,0)) unpaid_capital,
  case when s.due_date is not null and date(s.due_date) <= {OBS} then 1 else 0 end is_due,
  coalesce(w.repay_pre3_cum,0) repay_pre3_cum,
  coalesce(w.repay_pre4_cum,0) repay_pre4_cum,
  coalesce(w.repay_pre5_cum,0) repay_pre5_cum,
  coalesce(w.repay_pre6_cum,0) repay_pre6_cum,
  coalesce(w.repay_pre7_cum,0) repay_pre7_cum,
  coalesce(w.repay_d3,0) repay_d3,
  coalesce(w.repay_d2,0) repay_d2,
  coalesce(w.repay_d1,0) repay_d1,
  coalesce(w.repay_d0,0) repay_d0,
  coalesce(w.repay_after_due,0) repay_after_due,
  coalesce(w.t0_fact,0) t0_fact,
  coalesce(w.t1_fact,0) t1_fact,
  coalesce(w.t3_fact,0) t3_fact,
  coalesce(w.t7_fact,0) t7_fact,
  coalesce(w.repay_rel_d0,0) repay_rel_d0,
  coalesce(w.repay_rel_d1,0) repay_rel_d1,
  coalesce(w.repay_rel_d2,0) repay_rel_d2,
  coalesce(w.repay_rel_d3,0) repay_rel_d3,
  coalesce(w.repay_rel_d7,0) repay_rel_d7,
  coalesce(w.repay_rel_d14,0) repay_rel_d14,
  coalesce(w.repay_rel_d21,0) repay_rel_d21,
  coalesce(w.repay_rel_d28,0) repay_rel_d28,
  coalesce(w.repay_rel_d3p,0) repay_rel_d3p
from loan l
left join should s on l.camera_id = s.camera_id
left join fact f on l.camera_id = f.camera_id
left join factwin w on l.camera_id = w.camera_id
"""

METRICS = """
count(*) n_loan,
sum(contract_amount) contract_amount,
sum(amount) amount,
sum(haircut_amount) haircut_amount,
sum(interest) interest,
sum(should_capital) should_capital,
sum(should_interest) should_interest,
sum(should_sum) should_sum,
sum(fact_capital) fact_capital,
sum(fact_interest) fact_interest,
sum(subtract_capital) subtract_capital,
sum(subtract_interest) subtract_interest,
sum(coupon_amount) coupon_amount,
sum(fact_cash) fact_cash,
sum(redu_all) redu_all,
sum(fact_all) fact_all,
sum(unpaid_all) unpaid_all,
sum(unpaid_capital) unpaid_capital,
sum(is_due) n_due,
sum(1 - is_due) n_not_due,
sum(repay_pre3_cum) repay_pre3_cum,
sum(repay_pre4_cum) repay_pre4_cum,
sum(repay_pre5_cum) repay_pre5_cum,
sum(repay_pre6_cum) repay_pre6_cum,
sum(repay_pre7_cum) repay_pre7_cum,
sum(repay_d3) repay_d3,
sum(repay_d2) repay_d2,
sum(repay_d1) repay_d1,
sum(repay_d0) repay_d0,
sum(repay_after_due) repay_after_due,
sum(repay_rel_d0) repay_rel_d0,
sum(repay_rel_d1) repay_rel_d1,
sum(repay_rel_d2) repay_rel_d2,
sum(repay_rel_d3) repay_rel_d3,
sum(repay_rel_d7) repay_rel_d7,
sum(repay_rel_d14) repay_rel_d14,
sum(repay_rel_d21) repay_rel_d21,
sum(repay_rel_d28) repay_rel_d28,
sum(repay_rel_d3p) repay_rel_d3p,
sum(greatest(should_sum - (t0_fact + redu_all), 0) * is_due) t0_overdue,
sum(greatest(should_sum - (t1_fact + redu_all), 0) * is_due) t1_overdue,
sum(greatest(should_sum - (t3_fact + redu_all), 0) * is_due) t3_overdue,
sum(greatest(should_sum - (t7_fact + redu_all), 0) * is_due) t7_overdue
"""

def agg_sql(group_cols, order_cols=None):
    cols = ", ".join(group_cols)
    gb = ", ".join(str(i + 1) for i in range(len(group_cols)))
    ob = ", ".join(str(i + 1) for i in range(len(order_cols or group_cols)))
    return f"""
select {cols},
{METRICS}
from {ORDER_TABLE}
group by {gb}
order by {ob}
"""

GROUPS = [
    ("daily", ["release_date"]),
    ("daily_due", ["release_date", "is_due"]),
    ("daily_amt", ["release_date", "amount_bin"]),
    ("daily_cycle", ["release_date", "loan_cycle_bin"]),
    ("box_amt", ["amount_bin"]),
    ("box_cycle", ["loan_cycle_bin"]),
    ("box_cross", ["loan_cycle_bin", "amount_bin"]),
]

DAYOFF_SQL = f"""
select date(l.release_time) release_date,
  cast(least(greatest(date_diff('day', date(l.release_time), date(rd.fact_time)), 0), 28) as bigint) day_bucket,
  sum(rd.fact_capital + rd.fact_interest) fact_amt
from ods.s02_loan_repayment_detail rd
join ods.s02_loan l on l.camera_id = rd.camera_id
where l.release_time >= {D0} and l.release_time < {D1}
  and l.state in (1,2)
group by 1, 2
order by 1, 2
"""


def main():
    pq = PrestoQuery()
    print("登录:", pq.login(), flush=True)

    # 1. 建订单级聚合表
    print("drop 旧表...", flush=True)
    r = pq.execute(f"drop table if exists {ORDER_TABLE}", wait_sec=2)
    print("drop:", r, flush=True)
    if isinstance(r, tuple) and r[0] is False:
        print("drop 失败，终止", flush=True)
        return

    print("建订单级聚合表（扫描三张底表，预计几分钟）...", flush=True)
    r = pq.execute(CREATE_SQL, wait_sec=3, timeout=1200)
    print("create:", r, flush=True)
    if isinstance(r, tuple) and r[0] is False:
        print("create 失败，终止", flush=True)
        return

    # 2. 校验
    df = pq.query(f"select count(*) n, count(distinct camera_id) n_ord, min(release_date) mn, max(release_date) mx from {ORDER_TABLE}", wait_sec=2)
    if isinstance(df, str):
        print("校验失败:", df, flush=True)
        return
    print("订单级表:", df.to_string(index=False), flush=True)

    # 3. 下载聚合结果
    for name, gcols in GROUPS:
        sql = agg_sql(gcols)
        df = pq.query(sql, wait_sec=2)
        if isinstance(df, str):
            print(f"[{name}] 失败: {df}", flush=True)
            continue
        path = os.path.join(OUT_DIR, f"{name}.csv")
        df.to_csv(path, index=False)
        print(f"[{name}] {len(df)} 行 -> {path}", flush=True)

    # 4. 全局汇总
    t = pq.query(f"select {METRICS} from {ORDER_TABLE}", wait_sec=2)
    if isinstance(t, str):
        print("[total] 失败:", t, flush=True)
    else:
        t.to_csv(os.path.join(OUT_DIR, "total.csv"), index=False)
        print(f"[total] 1 行 -> total.csv", flush=True)

    # 5. 放款日相对还款
    d = pq.query(DAYOFF_SQL, wait_sec=3)
    if isinstance(d, str):
        print("[dayoff] 失败:", d, flush=True)
    else:
        d.to_csv(os.path.join(OUT_DIR, "dayoff.csv"), index=False)
        print(f"[dayoff] {len(d)} 行 -> dayoff.csv", flush=True)

    print("DONE", flush=True)


if __name__ == "__main__":
    main()

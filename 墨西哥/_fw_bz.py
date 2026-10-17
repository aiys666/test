# -*- coding: utf-8 -*-
"""B系列: 复现同事《临额风险影响分析20260909.xlsx》的 rawdata 与 by是否发放临额 交叉表。
- 维度: 评级v5_3 × 发放临额issue_tag × 策略strategy_flag × app_month × if_0811 × 是否使用临额if_used_templimit
- vintage 风险: t1d0$/#、t1d3$/#、t2d3$/#、t3d3$/#（window1..3, t0=逾期0天口径, t3=逾期3天口径）
- yj 快照覆盖 8/14-10/09; 用 8/19-10/06 完整窗; if_0811 窗口内恒=1(数据均在8/11后)
"""
import sys, io, time, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 500)
OUT = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_fw_data"

def q(sql, name, tag=""):
    print("=" * 100); print(tag or name, flush=True)
    for i in range(8):
        try:
            r = pq.query(sql)
        except Exception:
            print(f"[conn retry {i+1}]"); time.sleep(10)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]")
            r.to_csv(os.path.join(OUT, name + ".csv"), index=False, encoding='utf-8-sig')
            return r
        print(f"[retry {i+1}] {r[:200]}"); time.sleep(10)
        try: pq.login()
        except Exception: pass
    print(f"[FAIL] {name}"); return None

for _ in range(8):
    try:
        pq = PrestoQuery(); pq.login(); break
    except Exception:
        print("[login retry]"); time.sleep(12)

# vintage 指标构造: t0口径(window n) 与 t3口径(window n)
def rate_amt(w):  # $ 金额口径
    return (f"round(sum(if(t{w}_should_amt_1>0,t{w}_overdue_amount_1,null))/"
            f"nullif(sum(if(t{w}_should_amt_1>0,t{w}_should_amt_1,null)),0)*100,4)")
def rate_cnt_ovd(w):
    return (f"round(sum(if(t{w}_should_amt_1>0,is_{w}_overdue_1,0))/"
            f"nullif(sum(if(t{w}_should_amt_1>0,1,0)),0)*100,4)")
# 金额口径用窗口序号参数化的写法
# w 传数字符串('0'/'3'), n 传窗口序号
def amt_n(w, n):
    return (f"round(sum(if(t{w}_should_amt_{n}>0,t{w}_overdue_amount_{n},null))/"
            f"nullif(sum(if(t{w}_should_amt_{n}>0,t{w}_should_amt_{n},null)),0)*100,4)")
def cnt_n(w, n):
    # 坏账笔数口径与金额口径一致: 该窗口已成熟且逾期金额>0
    return (f"round(sum(if(t{w}_should_amt_{n}>0 and t{w}_overdue_amount_{n}>0,1,0))/"
            f"nullif(sum(if(t{w}_should_amt_{n}>0,1,0)),0)*100,4)")

BASE_J = """
select
  cast(android_oldcust_maincreditlevel_charge_v5_3 as integer) as grade,
  cast(temp_credit_amount_issue_tag as integer) as issue_tag,
  temp_credit_amount_strategy_test_flag as strategy_flag,
  app_month,
  if(app_date >= date'2026-08-11',1,0) as if_0811,
  if(temp_grant_amount>0,1,0) as if_used_templimit,
  count(*) as biz_cnt,
  count(distinct mid) as mid_cnt,
  round(sum(if(if_in_sx=1,credit_amount,null)),1) as credit_amount,
  round(sum(contract_amount),1) as contract_amount,
  {a10} as t1d0_amt, {a13} as t1d3_amt,
  {a23} as t2d3_amt, {a33} as t3d3_amt
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and app_date >= date'2026-08-19' and app_date < date'2026-10-06'
group by 1,2,3,4,5,6
""".format(a10=amt_n('0',1), a13=amt_n('3',1), a23=amt_n('3',2), a33=amt_n('3',3))

# B1: 明细 rawdata（复现同事 rawdata sheet 结构）
q(BASE_J, "B1_rawdata_repro", "B1 rawdata 复现(评级×issue×strategy×月×if0811×used)")

# B2: 汇总交叉「by是否发放临额」——按 评级 × issue_tag × if_used_templimit 汇总
q("""
with t as (
  select android_oldcust_maincreditlevel_charge_v5_3 as gg,
    temp_credit_amount_issue_tag as issue_tag,
    if(temp_grant_amount>0,1,0) as if_used_templimit,
    contract_amount, if(if_in_sx=1,credit_amount,null) as credit_amount,
    if(t3_should_amt_1>0,t3_overdue_amount_1,null) as od1, if(t3_should_amt_1>0,t3_should_amt_1,null) as sh1,
    if(t3_should_amt_2>0,t3_overdue_amount_2,null) as od2, if(t3_should_amt_2>0,t3_should_amt_2,null) as sh2
  from mx.yj_test_table_250225
  where is_reloan='old' and if_issue=1 and app_date >= date'2026-08-19' and app_date < date'2026-10-06'
)
select gg as grade, issue_tag, if_used_templimit,
  count(*) as biz_cnt, round(sum(contract_amount),0) as contract_amount, round(sum(credit_amount),0) as credit_amount,
  round(sum(od1)/nullif(sum(sh1),0)*100,2) as t1d3_amt,
  round(sum(od2)/nullif(sum(sh2),0)*100,2) as t2d3_amt
from t
group by 1,2,3 order by 1,2,3
""", "B2_by_issue_used", "B2 评级×发放临额×是否使用临额")

# B3: 头/中/尾分组（1-5 / 6-13）用/不用临额对比
q(f"""
select case when gc.gg <= 5 then '头部(1-5)' else '中尾(6-13)' end as grp_head,
  gc.issue_tag, gc.if_used_templimit,
  sum(gc.biz_cnt) as biz_cnt, sum(gc.contract_amount) as contract_amount,
  round(sum(gc.od3_1)/nullif(sum(gc.sh3_1),0)*100,2) as t1d3_amt
from (
  select android_oldcust_maincreditlevel_charge_v5_3 as gg, temp_credit_amount_issue_tag as issue_tag,
    if(temp_grant_amount>0,1,0) as if_used_templimit, 1 as biz_cnt,
    contract_amount, if(t3_should_amt_1>0,t3_overdue_amount_1,null) as od3_1,
    if(t3_should_amt_1>0,t3_should_amt_1,null) as sh3_1
  from mx.yj_test_table_250225
  where is_reloan='old' and if_issue=1 and app_date >= date'2026-08-19' and app_date < date'2026-10-06'
) gc
group by 1,2,3 order by 1,2,3
""", "B3_headtail", "B3 头/中尾 × 发放×使用临额")

print("B DONE")

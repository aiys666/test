# -*- coding: utf-8 -*-
"""H系列: V5_2/V5_3 用信决策矩阵(评级档×score_v1 -> fd_use_creditamount_type 1~4)
E5 矩阵实证校验(按hash组当期执行策略) / E6 客户级type迁徙 / E7 单元风险格
矩阵来源: 决策表导出(用户2026-10-11提供), 行=android_oldCust_mainCreditLevel_charge,
列=fd_use_creditamount_score_v1分档, 值=fd_use_creditamount_type(1优~4差)"""
import sys, io, time, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 460)
OUT = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_fw_data"
pq = None

def q(sql, name, tag="", retry=8):
    print("="*120); print(tag or name, flush=True)
    for i in range(retry):
        try:
            r = pq.query(sql)
        except Exception:
            print(f"[conn retry {i+1}]", flush=True); time.sleep(10)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r)==0: print("[空]", flush=True); return None
            print(r.to_string()); print(f"[rows={len(r)}]", flush=True)
            r.to_csv(os.path.join(OUT, name+".csv"), index=False, encoding='utf-8-sig')
            return r
        print(f"[retry {i+1}] {r[:200]}", flush=True); time.sleep(10)
        try: pq.login()
        except Exception: pass
    print(f"[FAIL] {name}", flush=True)
    return None

# ---------- 矩阵构造 ----------
V52 = {1:(1,1,2,2,3), 2:(1,1,2,2,3), 3:(1,1,2,3,3), 4:(1,2,2,3,3),
       5:(2,2,2,3,3), 6:(2,2,2,4,4), 7:(2,2,3,4,4)}
V53 = {1:(1,1,1,1,1), 2:(1,1,1,1,2), 3:(1,1,2,2,2), 4:(1,1,2,2,2),
       5:(1,1,2,2,3), 6:(1,1,2,2,3), 7:(1,1,2,2,3), 8:(2,2,2,2,3),
       9:(2,2,3,3,4), 10:(2,2,3,3,4)}
FOUR = (4,4,4,4,4)  # grade 8-13(V52)/11-13(V53), >=14, null

def matrix(gcol, scol, vec, top_open):
    """返回SQL表达式: (评级, score) -> type 1-4; score null -> null; grade null -> 4
    紧凑写法(数组按评分档下标取值), 单矩阵约0.6K字符, 便于完整落SQL依据页;
    与决策表逐项等价: 评级整数, when链从13向下兜底"""
    band = (f"case when {scol} >= 5 then 0 when {scol} >= 3 then 1 "
            f"when {scol} >= 1 then 2 when {scol} >= 0 then 3 else 4 end")
    lines = ["case", f"when {scol} is null then null",
             f"when {gcol} is null then 4 else case",
             f"when {gcol} >= 14 then 4"]
    for gg in range(13, 0, -1):
        v = vec.get(gg, FOUR)
        lines.append(f"when {gcol} >= {gg} then element_at(array[{','.join(map(str, v))}], ({band})+1)")
    lines.append("end end")
    return " ".join(lines)

G52 = "cast(android_oldcust_maincreditlevel_charge_v5_2 as double)"
G53 = "cast(android_oldcust_maincreditlevel_charge_v5_3 as double)"
SC  = "cast(fd_use_creditamount_score_v1 as double)"
P52 = matrix(G52, SC, V52, 7)
P53 = matrix(G53, SC, V53, 10)

T0 = "sum(if(t0_should_amt_1>0,t0_overdue_amount_1,null))/nullif(sum(if(t0_should_amt_1>0,t0_should_amt_1,null)),0)*100"
T0B = "sum(od_amt)/nullif(sum(sh_amt),0)*100"
HASH = "from_base(substr(to_hex(sha256(to_utf8('20260811'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000"
GRP = f"""case when {HASH} > 0.7 then 'A_v52_always'
       when {HASH} > 0.3 then 'B_switchback'
       else 'C_v53_always' end"""
PHASE = """case when date(app_time) < date'2026-09-03' then 'P1_v53'
       else 'P2_cutback' end"""

BASE = f"""
select {PHASE} as phase, {GRP} as grp,
  {G52} as g52, {G53} as g53, {SC} as sc,
  cast(fd_use_creditamount_type as integer) as act_type,
  {P52} as pred52, {P53} as pred53,
  real_issue_amount, credit_amount, temp_grant_amount,
  temp_credit_amount_issue_tag as itag, biz_id,
  if(t0_should_amt_1>0,t0_overdue_amount_1,null) as od_amt,
  if(t0_should_amt_1>0,t0_should_amt_1,null) as sh_amt
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old'
  and app_date >= date'2026-08-19' and app_date < date'2026-09-22'
  and temp_credit_amount_strategy_test_flag is not null
"""

# ============ E5: 矩阵实证校验 (各hash组当期执行策略下 预测type vs 实际type) ============
E5_SQL = f"""
with b as ({BASE})
select phase, grp, count(*) as cnt,
  sum(if(sc is null,1,0)) as score_null_cnt,
  sum(if(g52 is null,1,0)) as g52_null_cnt,
  sum(if(g53 is null,1,0)) as g53_null_cnt,
  sum(if(expected = act_type,1,0)) as match_cnt,
  round(sum(if(expected = act_type,1,0))*100.0/count(*),2) as match_pct
from (
  select *, case
    when phase='P1_v53' and grp in ('B_switchback','C_v53_always') then pred53
    when phase='P1_v53' then pred52
    when phase='P2_cutback' and grp='C_v53_always' then pred53
    else pred52 end as expected
  from b
) x
group by 1,2 order by 1,2
"""

# ============ E5b: 失配明细 (评级×score档×预测×实际) ============
E5B_SQL = f"""
with b as ({BASE})
select phase, grp,
  case when g53 is null then 'null' when g53>=14 then 'g14p'
       else 'g'||cast(cast(g53 as integer) as varchar) end as grade53,
  case when sc is null then 's_null' when sc>=5 then 's5p' when sc>=3 then 's3_5'
       when sc>=1 then 's1_3' when sc>=0 then 's0_1' else 'sn0' end as score_band,
  pred52, pred53, act_type, count(*) as cnt
from (
  select *, case
    when phase='P1_v53' and grp in ('B_switchback','C_v53_always') then pred53
    when phase='P1_v53' then pred52
    when phase='P2_cutback' and grp='C_v53_always' then pred53
    else pred52 end as expected
  from b
) x
where expected <> act_type or sc is null
group by 1,2,3,4,5,6,7 order by 1,2,8 desc
"""

# ============ E6: 客户级 type 迁徙 (V5_2矩阵 -> V5_3矩阵, 与实际执行组无关) ============
E6_SQL = f"""
with b as (
  select {G52} as g52, {G53} as g53, {SC} as sc, {P52} as pred52, {P53} as pred53,
    real_issue_amount, temp_grant_amount, temp_credit_amount_issue_tag as itag, biz_id,
    if(t0_should_amt_1>0,t0_overdue_amount_1,null) as od_amt,
    if(t0_should_amt_1>0,t0_should_amt_1,null) as sh_amt
  from mx.yj_test_table_250225
  where if_issue=1 and is_reloan='old'
    and app_date >= date'2026-08-19' and app_date < date'2026-10-06'
    and temp_credit_amount_strategy_test_flag is not null
)
select pred52 as type_v52, pred53 as type_v53,
  count(*) as cnt,
  round({T0B},2) as t0_rate,
  round(avg(real_issue_amount),0) as issue_avg,
  sum(if(itag=1,1,0)) as tag1_cnt,
  round(sum(temp_grant_amount/1000.0),0) as temp_use_k,
  round(avg(g53),2) as grade53_avg,
  round(avg(sc),2) as score_avg
from b
group by 1,2 order by 1,2
"""

# ============ E7: 单元风险格 (C组实走V5_3 / A组实走V5_2) ============
E7_SQL = f"""
with b as ({BASE})
select src,
  case when gg is null then 'g_null' when gg>=14 then 'g14p' else 'g'||cast(cast(gg as integer) as varchar) end as grade,
  case when sc is null then 's_null' when sc>=5 then 's5p(>=5)' when sc>=3 then 's3_5'
       when sc>=1 then 's1_3' when sc>=0 then 's0_1' else 'sn0(<0)' end as score_band,
  pred, count(*) as cnt,
  round({T0B},2) as t0_rate,
  round(avg(real_issue_amount),0) as issue_avg,
  sum(if(itag=1,1,0)) as tag1_cnt
from (
  select 'C_V5_3实走' as src, g53 as gg, sc, pred53 as pred,
         real_issue_amount, itag, od_amt, sh_amt from b where grp='C_v53_always'
  union all
  select 'A_V5_2实走' as src, g52 as gg, sc, pred52 as pred,
         real_issue_amount, itag, od_amt, sh_amt from b where grp='A_v52_always'
) u
group by 1,2,3,4 order by 1,2,3
"""

# 供Excel脚本把SQL依据页中的宏展开为可直接复跑的完整SQL
def expand_doc(s):
    for k, v in [("{BASE}", BASE), ("{T0B}", T0B), ("{G52}", G52), ("{G53}", G53),
                 ("{SC}", SC), ("{P52}", P52), ("{P53}", P53),
                 ("{PHASE}", PHASE), ("{GRP}", GRP), ("{HASH}", HASH), ("{T0}", T0)]:
        s = s.replace(k, v)
    return s

if __name__ == "__main__":
    for _i in range(8):
        try:
            pq = PrestoQuery(); pq.login(); break
        except Exception:
            print("[login retry]", flush=True); time.sleep(12)
    q(E5_SQL, "E5_matrix_validate", "E5 V5_2/V5_3决策矩阵实证校验(预测type命中率)")
    q(E5B_SQL, "E5b_mismatch", "E5b 矩阵失配明细")
    q(E6_SQL, "E6_type_migration", "E6 V5_2->V5_3 客户级type迁徙(反事实)")
    q(E7_SQL, "E7_cell_risk", "E7 评级×score 单元风险(C实走V5_3 vs A实走V5_2)")
    print("H DONE", flush=True)

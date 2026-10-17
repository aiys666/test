# -*- coding: utf-8 -*-
"""全维度贡献分解(Excel口径) + 临额发放/使用统计
口径: mx.yj_test_table_250225, is_t3_window_1=1, if_issue=1, app_time 进件周,
      1t0总额% = sum(t0_overdue_amount_1)/sum(t0_should_amt_1)
窗口: 8/3周 vs 8/10周
分解: 率效应=(r2-r1)*w1, 结构效应=(w2-w1)*r1, 交叉=(r2-r1)*(w2-w1)
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 300)

def q(sql, tag="", show=60):
    print("="*120)
    print(tag)
    r = pq.query(sql)
    if isinstance(r, str):
        print("[ERR]", r[:800]); return None
    print(r.head(show).to_string() if len(r) > show else r.to_string())
    print(f"[rows={len(r)}]")
    return r

W1, W2 = '2026-08-03', '2026-08-10'

def decomp(df, dimcol, tag, min_shd=0):
    """df: 列 wk(dimcol 已含), shd, ovd, cnt → 输出贡献分解表"""
    d = df.copy()
    d['wk'] = d['wk'].astype(str).str[:10]
    for c in ['shd', 'ovd', 'cnt']:
        d[c] = pd.to_numeric(d[c], errors='coerce').fillna(0)
    agg = d.groupby(['wk', dimcol], as_index=False)[['shd', 'ovd', 'cnt']].sum()
    p1 = agg[agg.wk == W1].set_index(dimcol)
    p2 = agg[agg.wk == W2].set_index(dimcol)
    dims = sorted(set(p1.index) | set(p2.index))
    p1 = p1.reindex(dims).fillna(0); p2 = p2.reindex(dims).fillna(0)
    tot1 = p1.shd.sum(); tot2 = p2.shd.sum()
    r1 = p1.ovd / p1.shd; r2 = p2.ovd / p2.shd
    w1 = p1.shd / tot1; w2 = p2.shd / tot2
    R1 = p1.ovd.sum() / tot1; R2 = p2.ovd.sum() / tot2
    out = pd.DataFrame({
        '组': dims,
        'r1%': (r1*100).round(2), 'r2%': (r2*100).round(2), 'Δ率pp': ((r2-r1)*100).round(2),
        'w1%': (w1*100).round(1), 'w2%': (w2*100).round(1), 'Δ份额pp': ((w2-w1)*100).round(1),
        '率效应pp': ((r2-r1)*w1*100).round(2),
        '结构效应pp': ((w2-w1)*r1*100).round(2),
        '交叉pp': ((r2-r1)*(w2-w1)*100).round(2),
    })
    out['贡献合计pp'] = (out['率效应pp']+out['结构效应pp']+out['交叉pp']).round(2)
    out['cnt1'] = p1.cnt.astype(int).values; out['cnt2'] = p2.cnt.astype(int).values
    out = out[out[['cnt1','cnt2']].sum(axis=1) >= 30]  # 过滤小样本
    out = out.sort_values('贡献合计pp', ascending=False)
    print("\n" + "#"*100)
    print(f"【{tag}】整体 {R1*100:.2f}% → {R2*100:.2f}%  (Δ {(R2-R1)*100:+.2f}pp)")
    print("#"*100)
    print(out.to_string(index=False))
    print(f"校验-率效应合计: {out['率效应pp'].sum():+.2f} | 结构合计: {out['结构效应pp'].sum():+.2f} | 交叉合计: {out['交叉pp'].sum():+.2f} | 总Δ: {(R2-R1)*100:+.2f}")
    return out

BASE_WHERE = """y.is_t3_window_1=1 and y.if_issue=1
  and y.app_time >= cast('2026-08-03 00:00:00.000' as timestamp)
  and y.app_time <  cast('2026-08-17 00:00:00.000' as timestamp)"""

# ============ Q1: 首贷 vs 复贷 ============
r1 = q(f"""
select date_trunc('week', date(y.app_time)) as wk, y.is_reloan as dim,
  sum(y.t0_should_amt_1) shd, sum(y.t0_overdue_amount_1) ovd, sum(y.if_issue) cnt
from mx.yj_test_table_250225 y
where {BASE_WHERE}
group by 1,2
""", "Q1 首贷vs复贷 原始")
if r1 is not None: decomp(r1, 'dim', '第一层: 首贷 vs 复贷')

# ============ Q2: 复贷内 临额类型 ============
r2 = q(f"""
with tmp_evt as (
  select mid, change_event_type, create_time
  from ods_view_presto.s05_user_creditlimit_change_record
  where limit_type='TEMP' and change_event_type in ('C010','C013','C015')
),
evt_last as (
  select biz_id, change_event_type,
    row_number() over (partition by biz_id order by create_time desc) as rn
  from (
    select y.biz_id, e.change_event_type, e.create_time
    from mx.yj_test_table_250225 y
    join tmp_evt e on y.mid = e.mid and e.create_time <= y.release_time
    where {BASE_WHERE} and y.is_reloan='old'
  ) x
)
select date_trunc('week', date(y.app_time)) as wk,
  case
    when el.change_event_type='C010' then '在线临额C010'
    when el.change_event_type in ('C013','C015') then '离线临额C013_15'
    else '无临额' end as dim,
  sum(y.t0_should_amt_1) shd, sum(y.t0_overdue_amount_1) ovd, sum(y.if_issue) cnt
from mx.yj_test_table_250225 y
left join evt_last el on y.biz_id = el.biz_id and el.rn=1
where {BASE_WHERE} and y.is_reloan='old'
group by 1,2
""", "Q2 复贷内临额类型 原始")
if r2 is not None: decomp(r2, 'dim', '第二层(复贷内): 在线 vs 离线 vs 无临额')

# ============ Q3: 复贷内 评级分档 ============
r3 = q(f"""
select date_trunc('week', date(y.app_time)) as wk,
  case when y.android_oldcust_maincreditlevel_charge_v5_3 is null then 'null'
       when y.android_oldcust_maincreditlevel_charge_v5_3<=2 then '1-2'
       when y.android_oldcust_maincreditlevel_charge_v5_3<=5 then '3-5'
       when y.android_oldcust_maincreditlevel_charge_v5_3<=7 then '6-7'
       when y.android_oldcust_maincreditlevel_charge_v5_3<=10 then '8-10'
       when y.android_oldcust_maincreditlevel_charge_v5_3<=12 then '11-12'
       else '13+' end as dim,
  sum(y.t0_should_amt_1) shd, sum(y.t0_overdue_amount_1) ovd, sum(y.if_issue) cnt
from mx.yj_test_table_250225 y
where {BASE_WHERE} and y.is_reloan='old'
group by 1,2
""", "Q3 复贷内评级分档 原始")
if r3 is not None:
    d3 = decomp(r3, 'dim', '第三层(复贷内): 评级分档 v5_3')
    if d3 is not None:
        mid6612 = d3[d3['组'].isin(['6-7','8-10','11-12'])]['贡献合计pp'].sum()
        print(f"\n>>> 评级6-12合计贡献: {mid6612:+.2f}pp")

# ============ Q4: 复贷内 产品期限 loan_cycle ============
r4 = q(f"""
select date_trunc('week', date(y.app_time)) as wk, cast(y.loan_cycle as varchar) as dim,
  sum(y.t0_should_amt_1) shd, sum(y.t0_overdue_amount_1) ovd, sum(y.if_issue) cnt
from mx.yj_test_table_250225 y
where {BASE_WHERE} and y.is_reloan='old'
group by 1,2
""", "Q4 复贷内产品期限 原始")
if r4 is not None: decomp(r4, 'dim', '第四层(复贷内): 产品期限 loan_cycle')

# ============ Q5: 复贷内 产品 product_name_new ============
r5 = q(f"""
select date_trunc('week', date(y.app_time)) as wk, y.product_name_new as dim,
  sum(y.t0_should_amt_1) shd, sum(y.t0_overdue_amount_1) ovd, sum(y.if_issue) cnt
from mx.yj_test_table_250225 y
where {BASE_WHERE} and y.is_reloan='old'
group by 1,2
""", "Q5 复贷内产品名 原始")
if r5 is not None: decomp(r5, 'dim', '第四层(复贷内): 产品 product_name_new')

# ============ Q6: 首贷内 产品期限 ============
r6 = q(f"""
select date_trunc('week', date(y.app_time)) as wk, cast(y.loan_cycle as varchar) as dim,
  sum(y.t0_should_amt_1) shd, sum(y.t0_overdue_amount_1) ovd, sum(y.if_issue) cnt
from mx.yj_test_table_250225 y
where {BASE_WHERE} and y.is_reloan='first'
group by 1,2
""", "Q6 首贷内产品期限 原始")
if r6 is not None: decomp(r6, 'dim', '补充(首贷内): 产品期限 loan_cycle')

# ============ Q7: 临额使用统计(按周) ============
q("""
select date_trunc('week', date(create_time)) as wk, limit_type,
  count(*) freeze_cnt, count(distinct mid) mids,
  round(sum(risk_credit_limit),0) freeze_amt
from ods_view_presto.s05_user_creditlimit_used_detail
where change_action='FREEZE_LIMIT'
  and create_time >= cast('2026-06-01 00:00:00' as timestamp)
group by 1,2 order by 1,2
""", "Q7a 临额/主额 使用(冻结)金额按周")

# ============ Q8: 在线临额 C010 按周 ============
q("""
select date_trunc('week', date(create_time)) as wk,
  count(*) c010_cnt, count(distinct mid) mids
from ods_view_presto.s05_user_creditlimit_change_record
where limit_type='TEMP' and change_event_type='C010'
  and create_time >= cast('2026-06-01 00:00:00' as timestamp)
group by 1 order by 1
""", "Q8 在线临额C010事件按周")

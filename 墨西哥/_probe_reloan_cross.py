# -*- coding: utf-8 -*-
"""复贷内二级分解: 临额类型 × 评级档 / × 产品期限
回答: 在线/离线临额的率涨中, 多少是评级6-12带来, 多少是期限/产品带来
口径: yj 表(仅复贷), is_t3_window_1=1, if_issue=1, app_time 进件, 总额1t0
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 300)

def q(sql, tag="", show=80):
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

W1, W2 = '2026-08-03', '2026-08-10'
BASE = """y.is_t3_window_1=1 and y.if_issue=1
  and y.app_time >= cast('2026-08-03 00:00:00.000' as timestamp)
  and y.app_time <  cast('2026-08-17 00:00:00.000' as timestamp)
  and y.is_reloan='old'"""

# 临额打标(复贷内)
EVT = f"""
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
    where {BASE}
  ) x
)"""

def decomp(df, dimcol, tag):
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
    r1 = (p1.ovd / p1.shd.replace(0, float('nan'))).fillna(0)
    r2 = (p2.ovd / p2.shd.replace(0, float('nan'))).fillna(0)
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
    out = out[out[['cnt1','cnt2']].sum(axis=1) >= 30].sort_values('贡献合计pp', ascending=False)
    print("\n" + "#"*100)
    print(f"【{tag}】整体 {R1*100:.2f}% → {R2*100:.2f}%  (Δ {(R2-R1)*100:+.2f}pp)")
    print("#"*100)
    print(out.to_string(index=False))
    return out

# ============ Q1: 临额类型 × 评级档 ============
r1 = q(f"""
{EVT}
select date_trunc('week', date(y.app_time)) as wk,
  case when el.change_event_type='C010' then '在线'
    when el.change_event_type in ('C013','C015') then '离线'
    else '无临额' end as tl,
  case when y.android_oldcust_maincreditlevel_charge_v5_3 is null then '评级null'
       when y.android_oldcust_maincreditlevel_charge_v5_3<=5 then '评级1-5'
       when y.android_oldcust_maincreditlevel_charge_v5_3<=12 then '评级6-12'
       else '评级13+' end as lvl,
  sum(y.t0_should_amt_1) shd, sum(y.t0_overdue_amount_1) ovd, sum(y.if_issue) cnt
from mx.yj_test_table_250225 y
left join evt_last el on y.biz_id = el.biz_id and el.rn=1
where {BASE}
group by 1,2,3 order by 1,2,3
""", "Q1 临额类型×评级档 原始")

# ============ Q2: 临额类型 × 产品期限 ============
r2 = q(f"""
{EVT}
select date_trunc('week', date(y.app_time)) as wk,
  case when el.change_event_type='C010' then '在线'
    when el.change_event_type in ('C013','C015') then '离线'
    else '无临额' end as tl,
  cast(y.loan_cycle as varchar) as cyc,
  sum(y.t0_should_amt_1) shd, sum(y.t0_overdue_amount_1) ovd, sum(y.if_issue) cnt
from mx.yj_test_table_250225 y
left join evt_last el on y.biz_id = el.biz_id and el.rn=1
where {BASE}
group by 1,2,3 order by 1,2,3
""", "Q2 临额类型×产品期限 原始")

# ============ 每个临额类型内部的 评级 分解 ============
if r1 is not None:
    r1 = r1.copy()
    r1['tl_lvl'] = r1['tl'] + '|' + r1['lvl']
    # 只做 在线 和 离线 各自内部
    for tl in ['在线', '离线']:
        sub = r1[r1['tl'] == tl].copy()
        sub['dim'] = sub['tl_lvl']
        decomp(sub, 'dim', f'{tl}临额内部: 评级档分解')

# ============ 每个临额类型内部的 期限 分解 ============
if r2 is not None:
    r2 = r2.copy()
    r2['tl_cyc'] = r2['tl'] + '|' + r2['cyc'] + '天'
    for tl in ['在线', '离线']:
        sub = r2[r2['tl'] == tl].copy()
        sub['dim'] = sub['tl_cyc']
        decomp(sub, 'dim', f'{tl}临额内部: 期限分解')

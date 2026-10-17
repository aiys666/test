# -*- coding: utf-8 -*-
"""修正: funnel 四组全局分解(is_reloan='new') + 首贷内期限"""
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
    if r is None or len(r) == 0:
        print("[空数据]"); return None
    print(r.head(show).to_string() if len(r) > show else r.to_string())
    print(f"[rows={len(r)}]")
    return r

W1, W2 = '2026-08-03', '2026-08-10'

def decomp(df, dimcol, tag):
    d = df.copy()
    d['wk'] = d['wk'].astype(str).str[:10]
    for c in ['shd', 'ovd', 'cnt']:
        d[c] = pd.to_numeric(d[c], errors='coerce').fillna(0)
    if len(d) == 0:
        print(f"[{tag}] 空数据, 跳过"); return None
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
    print(f"校验: 率{out['率效应pp'].sum():+.2f} 结构{out['结构效应pp'].sum():+.2f} 交叉{out['交叉pp'].sum():+.2f} | 总Δ {(R2-R1)*100:+.2f}")
    return out

FW = """f.if_issue=1
  and f.app_time >= cast('2026-08-03 00:00:00.000' as timestamp)
  and f.app_time <  cast('2026-08-17 00:00:00.000' as timestamp)"""

# ============ 全局四组分解(修正 new) ============
r1 = q(f"""
with tmp_evt as (
  select mid, change_event_type, create_time
  from ods_view_presto.s05_user_creditlimit_change_record
  where limit_type='TEMP' and change_event_type in ('C010','C013','C015')
),
evt_last as (
  select biz_id, change_event_type,
    row_number() over (partition by biz_id order by create_time desc) as rn
  from (
    select f.biz_id, e.change_event_type, e.create_time
    from mx.wxs_application_funnel f
    join tmp_evt e on f.mid = e.mid and e.create_time <= f.release_time
    where {FW} and f.is_reloan='old'
  ) x
)
select date_trunc('week', date(f.app_time)) as wk,
  case when f.is_reloan='new' then '1_首贷'
    when el.change_event_type='C010' then '2_复贷-在线临额'
    when el.change_event_type in ('C013','C015') then '3_复贷-离线临额'
    else '4_复贷-无临额' end as dim,
  sum(f.t0_should_amt_1) shd, sum(f.t0_overdue_amount_1) ovd, sum(f.if_issue) cnt
from mx.wxs_application_funnel f
left join evt_last el on f.biz_id = el.biz_id and el.rn=1
where {FW}
group by 1,2
""", "全局四组(修正) 原始")
if r1 is not None: decomp(r1, 'dim', '全局四组: 首贷/复贷在线/复贷离线/复贷无临额')

# ============ 首贷内期限 ============
r2 = q(f"""
select date_trunc('week', date(f.app_time)) as wk, cast(f.loan_cycle as varchar) as dim,
  sum(f.t0_should_amt_1) shd, sum(f.t0_overdue_amount_1) ovd, sum(f.if_issue) cnt
from mx.wxs_application_funnel f
where {FW} and f.is_reloan='new'
group by 1,2
""", "首贷内期限")
if r2 is not None: decomp(r2, 'dim', '首贷内: 期限')

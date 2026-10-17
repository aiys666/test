# -*- coding: utf-8 -*-
"""补充: funnel 表 首贷vs复贷分解(含首贷) + 临额使用统计"""
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
    r1 = p1.ovd / p1.shd.replace(0, float('nan')); r2 = p2.ovd / p2.shd.replace(0, float('nan'))
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

# Q1b: funnel 首贷 vs 复贷
r1 = q(f"""
select date_trunc('week', date(f.app_time)) as wk, f.is_reloan as dim,
  sum(f.t0_should_amt_1) shd, sum(f.t0_overdue_amount_1) ovd, sum(f.if_issue) cnt
from mx.wxs_application_funnel f
where {FW}
group by 1,2
""", "Q1b funnel 首贷vs复贷")
if r1 is not None: decomp(r1, 'dim', '第一层(funnel全量): 首贷 vs 复贷')

# Q2b: funnel 首贷内 期限
r2 = q(f"""
select date_trunc('week', date(f.app_time)) as wk, cast(f.loan_cycle as varchar) as dim,
  sum(f.t0_should_amt_1) shd, sum(f.t0_overdue_amount_1) ovd, sum(f.if_issue) cnt
from mx.wxs_application_funnel f
where {FW} and f.is_reloan='first'
group by 1,2
""", "Q2b 首贷内期限")
if r2 is not None: decomp(r2, 'dim', '第二层(首贷内): 期限')

# Q3b: funnel 复贷内期限(对照yj口径)
r3 = q(f"""
select date_trunc('week', date(f.app_time)) as wk, cast(f.loan_cycle as varchar) as dim,
  sum(f.t0_should_amt_1) shd, sum(f.t0_overdue_amount_1) ovd, sum(f.if_issue) cnt
from mx.wxs_application_funnel f
where {FW} and f.is_reloan='old'
group by 1,2
""", "Q3b 复贷内期限(funnel)")
if r3 is not None: decomp(r3, 'dim', '对照(funnel复贷内): 期限')

# Q7: 临额/主额 使用(冻结)金额按周
q("""
select date_trunc('week', date(create_time)) as wk, limit_type,
  count(*) freeze_cnt, count(distinct mid) mids,
  round(sum(risk_credit_limit),0) freeze_amt
from ods_view_presto.s05_user_creditlimit_used_detail
where change_action='FREEZE_LIMIT'
  and create_time >= cast('2026-06-01 00:00:00' as timestamp)
group by 1,2 order by 1,2
""", "Q7 临额/主额 使用(冻结)按周")

# Q8: 在线临额C010事件按周
q("""
select date_trunc('week', date(create_time)) as wk,
  count(*) c010_cnt, count(distinct mid) mids
from ods_view_presto.s05_user_creditlimit_change_record
where limit_type='TEMP' and change_event_type='C010'
  and create_time >= cast('2026-06-01 00:00:00' as timestamp)
group by 1 order by 1
""", "Q8 在线临额C010按周")

# Q9: 离线临额实际发放(C013/C015)按周
q("""
select date_trunc('week', date(create_time)) as wk, change_event_type,
  count(*) cnt, count(distinct mid) mids,
  round(sum(change_total_grantamount),0) amt
from ods_view_presto.s05_user_creditlimit_change_record
where limit_type='TEMP' and change_event_type in ('C013','C015')
  and create_time >= cast('2026-06-01 00:00:00' as timestamp)
group by 1,2 order by 1,2
""", "Q9 离线临额发放(C013/C015)按周")

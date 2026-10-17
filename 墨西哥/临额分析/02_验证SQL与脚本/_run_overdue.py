# -*- coding: utf-8 -*-
"""临额逾期率分析: 笔数逾期率/金额逾期率, 分1T0/2T0/3T0/4T0/4T7/TR, 拆临额影响
   金额逾期率 = (逾期笔数*逾期件均)/(总笔数*整体件均) = sum(逾期金额)/sum(合同额)
   拆临额: 有临额vs无临额的逾期件均对比
"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 620)

def q(sql, tag):
    print("=" * 120); print(tag, flush=True)
    for i in range(6):
        try: r = pq.query(sql)
        except Exception:
            print(f"[conn retry {i+1}]"); time.sleep(6)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0: print("[空]"); print(); return None
            print(r.to_string()); print(f"[rows={len(r)}]\n", flush=True); return r
        print(f"[retry {i+1}] {str(r)[:300]}"); time.sleep(6)
        try: pq.login()
        except Exception: pass
    print(f"[FAIL] {tag}\n"); return None

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: print("[login retry]"); time.sleep(8)

WHERE = """app_time >= timestamp'2026-07-01 00:00:00'
  AND app_time <  timestamp'2026-10-01 00:00:00'
  AND if_issue = 1"""

# ============================================================
# D1: 总体逾期率 (分账龄: 1T0/2T0/3T0/4T0/4T7/TR)
# 笔数逾期率 = 逾期笔数/总笔数
# 金额逾期率 = sum(逾期金额)/sum(合同额)
# ============================================================
d1 = q(f"""
SELECT
  app_month,
  COUNT(*) AS total_cnt,
  round(SUM(contract_amount),0) AS total_contract_amt,
  round(AVG(contract_amount),0) AS avg_contract_amt,
  -- 1T0 第1期T0逾期
  SUM(CASE WHEN t0_overdue_amount_1 > 0 THEN 1 ELSE 0 END) AS ovd_1t0_cnt,
  round(SUM(t0_overdue_amount_1),0) AS ovd_1t0_amt,
  -- 2T0
  SUM(CASE WHEN t0_overdue_amount_2 > 0 THEN 1 ELSE 0 END) AS ovd_2t0_cnt,
  round(SUM(t0_overdue_amount_2),0) AS ovd_2t0_amt,
  -- 3T0
  SUM(CASE WHEN t0_overdue_amount_3 > 0 THEN 1 ELSE 0 END) AS ovd_3t0_cnt,
  round(SUM(t0_overdue_amount_3),0) AS ovd_3t0_amt,
  -- 4T0 (第4期T0)
  SUM(CASE WHEN t0_overdue_amount_4 > 0 THEN 1 ELSE 0 END) AS ovd_4t0_cnt,
  round(SUM(t0_overdue_amount_4),0) AS ovd_4t0_amt,
  -- 4T7 (第4期T7)
  SUM(CASE WHEN t7_overdue_amount_4 > 0 THEN 1 ELSE 0 END) AS ovd_4t7_cnt,
  round(SUM(t7_overdue_amount_4),0) AS ovd_4t7_amt,
  -- TR 总逾期(任一期T0逾期, 金额取各期最大值避免重复计)
  SUM(CASE WHEN t0_overdue_amount_1 > 0 OR t0_overdue_amount_2 > 0 OR t0_overdue_amount_3 > 0 OR t0_overdue_amount_4 > 0 THEN 1 ELSE 0 END) AS ovd_tr_cnt,
  round(SUM(GREATEST(COALESCE(t0_overdue_amount_1,0), COALESCE(t0_overdue_amount_2,0), COALESCE(t0_overdue_amount_3,0), COALESCE(t0_overdue_amount_4,0))),0) AS ovd_tr_amt
FROM mx.report_application_funnel7
WHERE {WHERE}
GROUP BY app_month
ORDER BY app_month
""", "D1 总体逾期率 (分账龄, 放款样本)")

# ============================================================
# D2: 有临额 vs 无临额 逾期率对比 (核心: 临额对逾期的影响)
# ============================================================
d2 = q(f"""
SELECT
  app_month,
  CASE WHEN temp_grant_amount > 0 THEN '有临额' ELSE '无临额' END AS has_temp,
  COUNT(*) AS total_cnt,
  round(SUM(contract_amount),0) AS total_contract_amt,
  round(AVG(contract_amount),0) AS avg_contract_amt,
  -- 1T0
  SUM(CASE WHEN t0_overdue_amount_1 > 0 THEN 1 ELSE 0 END) AS ovd_1t0_cnt,
  round(SUM(t0_overdue_amount_1),0) AS ovd_1t0_amt,
  -- 4T7
  SUM(CASE WHEN t7_overdue_amount_4 > 0 THEN 1 ELSE 0 END) AS ovd_4t7_cnt,
  round(SUM(t7_overdue_amount_4),0) AS ovd_4t7_amt,
  -- TR
  SUM(CASE WHEN t0_overdue_amount_1 > 0 OR t0_overdue_amount_2 > 0 OR t0_overdue_amount_3 > 0 OR t0_overdue_amount_4 > 0 THEN 1 ELSE 0 END) AS ovd_tr_cnt
FROM mx.report_application_funnel7
WHERE {WHERE}
GROUP BY app_month, CASE WHEN temp_grant_amount > 0 THEN '有临额' ELSE '无临额' END
ORDER BY app_month, has_temp
""", "D2 有临额vs无临额 逾期率对比")

# ============================================================
# D3: 逾期件均拆临额影响
# 逾期件均 = 逾期金额/逾期笔数
# 对比: 有临额的逾期件均 vs 无临额的逾期件均
# ============================================================
d3 = q(f"""
SELECT
  app_month,
  CASE WHEN temp_grant_amount > 0 THEN '有临额' ELSE '无临额' END AS has_temp,
  -- 整体件均
  round(AVG(contract_amount),0) AS avg_contract_all,
  -- 1T0逾期件均
  round(SUM(t0_overdue_amount_1)/NULLIF(SUM(CASE WHEN t0_overdue_amount_1 > 0 THEN 1 ELSE 0 END),0),0) AS avg_ovd_1t0,
  -- 有临额的临额件均
  round(AVG(CASE WHEN temp_grant_amount > 0 THEN temp_grant_amount/1000.0 END),0) AS avg_temp_amt,
  -- 有临额的主额件均(合同额-临额)
  round(AVG(CASE WHEN temp_grant_amount > 0 THEN contract_amount - temp_grant_amount/1000.0 END),0) AS avg_main_amt
FROM mx.report_application_funnel7
WHERE {WHERE}
GROUP BY app_month, CASE WHEN temp_grant_amount > 0 THEN '有临额' ELSE '无临额' END
ORDER BY app_month, has_temp
""", "D3 逾期件均拆临额影响 (有临额vs无临额)")

# ============================================================
# D4: 按评级分层的逾期率 (1T0 / TR)
# ============================================================
d4 = q(f"""
SELECT
  app_month,
  android_oldcust_maincreditlevel_charge_v5_3 AS credit_lvl,
  COUNT(*) AS cnt,
  -- 1T0笔数逾期率
  round(100.0*SUM(CASE WHEN t0_overdue_amount_1 > 0 THEN 1 ELSE 0 END)/COUNT(*),2) AS ovd_1t0_cnt_rate,
  -- 1T0金额逾期率
  round(100.0*SUM(t0_overdue_amount_1)/NULLIF(SUM(contract_amount),0),4) AS ovd_1t0_amt_rate,
  -- TR笔数逾期率
  round(100.0*SUM(CASE WHEN t0_overdue_amount_1 > 0 OR t0_overdue_amount_2 > 0 OR t0_overdue_amount_3 > 0 OR t0_overdue_amount_4 > 0 THEN 1 ELSE 0 END)/COUNT(*),2) AS ovd_tr_cnt_rate
FROM mx.darren_jieqing_dt_table
WHERE app_time >= timestamp'2026-07-01 00:00:00'
  AND app_time <  timestamp'2026-09-01 00:00:00'
  AND if_issue = 1
GROUP BY app_month, android_oldcust_maincreditlevel_charge_v5_3
ORDER BY app_month, credit_lvl
""", "D4 按评级v5_3分层的逾期率 (7-8月)")

# ============================================================
# D5: 临额金额大小对逾期率的影响 (分桶)
# ============================================================
d5 = q(f"""
SELECT
  CASE
    WHEN temp_grant_amount = 0 THEN '0_无临额'
    WHEN temp_grant_amount/1000.0 <= 500 THEN '1_<=500'
    WHEN temp_grant_amount/1000.0 <= 1000 THEN '2_500~1k'
    WHEN temp_grant_amount/1000.0 <= 2000 THEN '3_1k~2k'
    ELSE '4_>2k'
  END AS temp_bucket,
  COUNT(*) AS cnt,
  round(100.0*SUM(CASE WHEN t0_overdue_amount_1 > 0 THEN 1 ELSE 0 END)/COUNT(*),2) AS ovd_1t0_cnt_rate,
  round(100.0*SUM(CASE WHEN t0_overdue_amount_1 > 0 OR t0_overdue_amount_2 > 0 OR t0_overdue_amount_3 > 0 OR t0_overdue_amount_4 > 0 THEN 1 ELSE 0 END)/COUNT(*),2) AS ovd_tr_cnt_rate,
  round(AVG(contract_amount),0) AS avg_contract
FROM mx.report_application_funnel7
WHERE {WHERE}
GROUP BY 1
ORDER BY 1
""", "D5 临额金额分桶对逾期率的影响")

# ============================================================
# 计算衍生指标并导出Excel
# ============================================================
def calc_rates(df):
    """计算笔数逾期率和金额逾期率"""
    if df is None: return df
    df = df.copy()
    num_cols = [c for c in df.columns if c not in ('app_month','has_temp','credit_lvl')]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    # 1T0
    df['1T0_笔数逾期率%'] = (df['ovd_1t0_cnt'] / df['total_cnt'] * 100).round(2)
    df['1T0_金额逾期率%'] = (df['ovd_1t0_amt'] / df['total_contract_amt'] * 100).round(4)
    # 2T0
    if 'ovd_2t0_cnt' in df.columns:
        df['2T0_笔数逾期率%'] = (df['ovd_2t0_cnt'] / df['total_cnt'] * 100).round(2)
        df['2T0_金额逾期率%'] = (df['ovd_2t0_amt'] / df['total_contract_amt'] * 100).round(4)
    # 3T0
    if 'ovd_3t0_cnt' in df.columns:
        df['3T0_笔数逾期率%'] = (df['ovd_3t0_cnt'] / df['total_cnt'] * 100).round(2)
        df['3T0_金额逾期率%'] = (df['ovd_3t0_amt'] / df['total_contract_amt'] * 100).round(4)
    # 4T0
    if 'ovd_4t0_cnt' in df.columns:
        df['4T0_笔数逾期率%'] = (df['ovd_4t0_cnt'] / df['total_cnt'] * 100).round(2)
        df['4T0_金额逾期率%'] = (df['ovd_4t0_amt'] / df['total_contract_amt'] * 100).round(4)
    # 4T7
    if 'ovd_4t7_cnt' in df.columns:
        df['4T7_笔数逾期率%'] = (df['ovd_4t7_cnt'] / df['total_cnt'] * 100).round(2)
        df['4T7_金额逾期率%'] = (df['ovd_4t7_amt'] / df['total_contract_amt'] * 100).round(4)
    return df

if d1 is not None:
    d1 = calc_rates(d1)
if d2 is not None:
    d2 = calc_rates(d2)

out = r"E:\岳松个人文件\嘉银工作内容的整理\code\临额逾期率分析_重点结论.xlsx"
with pd.ExcelWriter(out, engine='openpyxl') as w:
    if d1 is not None: d1.to_excel(w, sheet_name='D1_总体逾期率_分账龄', index=False)
    if d2 is not None: d2.to_excel(w, sheet_name='D2_有临额vs无临额', index=False)
    if d3 is not None: d3.to_excel(w, sheet_name='D3_逾期件均拆临额', index=False)
    if d4 is not None: d4.to_excel(w, sheet_name='D4_评级分层逾期率', index=False)
    if d5 is not None: d5.to_excel(w, sheet_name='D5_临额金额分桶逾期率', index=False)

print(f"\n✅ Excel已导出: {out}")
print("DONE-OVERDUE")

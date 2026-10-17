# -*- coding: utf-8 -*-
"""更新Excel: 用最终双字段口径(W1/W2/W3)替换旧的S7/S8/S9错误口径sheet"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

def q(sql, tag):
    print("=" * 100); print(tag, flush=True)
    for i in range(6):
        try: r = pq.query(sql)
        except Exception:
            print(f"[conn retry {i+1}]"); time.sleep(6)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            print(f"[rows={len(r)}]", flush=True); return r
        print(f"[retry {i+1}] {str(r)[:200]}"); time.sleep(6)
        try: pq.login()
        except Exception: pass
    raise RuntimeError(tag)

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)

# W1
w1 = q("""
WITH app AS (
  SELECT mid, biz_id, app_time, app_date, temp_grant_amount
  FROM mx.wxs_application_funnel
  WHERE tenant='yawey' AND is_reloan='old' AND if_issue=1
    AND app_date >= date'2026-09-01' AND app_date < date'2026-10-16'
    AND temp_grant_amount > 0
),
c010_biz AS (
  SELECT DISTINCT external_id FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type='C010' AND create_time >= timestamp'2026-08-25 00:00:00'
),
off AS (
  SELECT mid, off_amt, off_time FROM (
    SELECT cast(mid as bigint) AS mid, change_total_grantamount AS off_amt, create_time AS off_time,
           row_number() OVER (PARTITION BY mid ORDER BY create_time DESC) rn
    FROM ods_view_presto.s05_user_creditlimit_change_record
    WHERE change_event_type IN ('C015','C013')
      AND create_time >= timestamp'2026-04-01 00:00:00'
  ) t WHERE rn=1
),
u AS (
  SELECT a.mid, a.temp_grant_amount/1000.0 AS temp_used, o.off_amt,
         date_diff('day', o.off_time, a.app_time) AS gap_days
  FROM app a
  LEFT JOIN c010_biz c ON cast(a.biz_id as varchar)=c.external_id
  JOIN off o ON cast(a.mid as bigint)=o.mid
  WHERE c.external_id IS NULL
)
SELECT
  CASE
    WHEN gap_days <= 7 THEN '1_离线发放后7天内'
    WHEN gap_days <= 14 THEN '2_8-14天'
    WHEN gap_days <= 30 THEN '3_15-30天'
    ELSE '4_30天以上'
  END AS gap_bucket,
  COUNT(*) AS cnt,
  round(AVG(temp_used),0) AS avg_temp_used,
  round(AVG(off_amt),0) AS avg_offline_grant,
  round(100.0*SUM(CASE WHEN temp_used <= off_amt + 1 THEN 1 ELSE 0 END)/COUNT(*),2) AS used_le_grant_pct
FROM u GROUP BY 1 ORDER BY 1
""", "W1")

FINAL = """
c010 AS (
  SELECT external_id, MAX(change_total_grantamount) AS online_grant
  FROM ods_view_presto.s05_user_creditlimit_change_record
  WHERE change_event_type='C010' AND create_time >= timestamp'2026-04-01 00:00:00'
  GROUP BY external_id
),
off7 AS (
  SELECT mid, app_time, offline_grant FROM (
    SELECT cast(a.mid as bigint) AS mid, a.app_time,
           g.change_total_grantamount AS offline_grant,
           row_number() OVER (PARTITION BY cast(a.mid as bigint), a.app_time ORDER BY g.create_time DESC) rn
    FROM mx.wxs_application_funnel a
    JOIN ods_view_presto.s05_user_creditlimit_change_record g
      ON cast(a.mid as bigint)=cast(g.mid as bigint)
     AND g.change_event_type IN ('C015','C013')
     AND g.create_time <= a.app_time
     AND a.app_time < g.create_time + interval '7' day
    WHERE a.tenant='yawey' AND a.is_reloan='old' AND a.if_issue=1
      AND a.app_date >= date'2026-04-01' AND a.app_date <= date'2026-08-31'
  ) t WHERE rn=1
),
app AS (
  SELECT a.mid, a.biz_id, a.app_time, a.app_date, a.contract_amount,
         a.temp_grant_amount/1000.0 AS temp_used,
         f.is_t0_overdue_1, f.is_t0_overdue_2, f.is_t0_overdue_3, f.is_t0_overdue_4,
         f.t0_overdue_amount_1,
         c.online_grant, o.offline_grant
  FROM mx.wxs_application_funnel a
  JOIN mx.report_application_funnel7 f
    ON cast(a.mid as bigint)=cast(f.mid as bigint) AND a.app_time=f.app_time
  LEFT JOIN c010 c ON cast(a.biz_id as varchar)=c.external_id
  LEFT JOIN off7 o ON cast(a.mid as bigint)=o.mid AND a.app_time=o.app_time
  WHERE a.tenant='yawey' AND a.is_reloan='old' AND a.if_issue=1
    AND a.app_date >= date'2026-04-01' AND a.app_date <= date'2026-08-31'
),
cls AS (
  SELECT *,
    CASE WHEN offline_grant IS NOT NULL THEN '持有离线(7d内)' ELSE '未持有离线' END AS hold_offline,
    CASE
      WHEN temp_used = 0 THEN '0_未使用临额'
      WHEN online_grant IS NOT NULL THEN '1_在线临额使用(C010)'
      ELSE '2_离线临额池使用'
    END AS use_source
  FROM app
)
"""

w2 = q(f"""
WITH {FINAL}
SELECT hold_offline, use_source,
  COUNT(*) AS loan_cnt,
  round(AVG(contract_amount),0) AS avg_contract,
  round(AVG(COALESCE(offline_grant,0)),0) AS avg_offline_grant,
  round(AVG(COALESCE(online_grant,0)),0) AS avg_online_grant,
  round(AVG(temp_used),0) AS avg_temp_used
FROM cls GROUP BY 1, 2 ORDER BY 1, 2
""", "W2")

w3 = q(f"""
WITH {FINAL}
SELECT hold_offline, use_source,
  COUNT(*) AS loan_cnt,
  round(AVG(contract_amount),0) AS avg_contract,
  round(AVG(temp_used),0) AS avg_temp_used,
  round(100.0*AVG(is_t0_overdue_1),2) AS t0_1_rate,
  round(100.0*AVG(is_t0_overdue_2),2) AS t0_2_rate,
  round(100.0*AVG(greatest(is_t0_overdue_1,is_t0_overdue_2,is_t0_overdue_3,is_t0_overdue_4)),2) AS tr_rate,
  round(100.0*SUM(t0_overdue_amount_1)/SUM(contract_amount),2) AS t0_1_amt_rate
FROM cls GROUP BY 1, 2 ORDER BY 1, 2
""", "W3")

# 交叉验证结果表(X1差异说明)
x1 = pd.DataFrame([
    ['官方有标签/我有暴露', '临额', 11193, '一致'],
    ['官方有标签/我有暴露', '临额减息', 616, '一致'],
    ['官方有标签/我有暴露', '减息', 73, '减息组但7天内有其他批次发放'],
    ['官方有标签/我无暴露', '临额', 1233, '申请早于C015实际发放时刻(同日20:00前),官方按自然日0点起算'],
    ['官方有标签/我无暴露', '临额减息', 45, '同上'],
    ['官方有标签/我无暴露', '减息', 1112, '减息组不发临额,无C015事件(口径差异,正确)'],
    ['官方无标签/我有暴露', '-', 2665, 'D+5/D+6边界(官方6自然日 vs 我滚动7天)2336笔 + C013修单329笔'],
    ['双方都无', '-', 40331, '一致'],
], columns=['交叉结果', '实验臂', '申请笔数', '差异原因'])

x2 = pd.DataFrame([
    ['funnel有临额 且 C010按biz对上', 6294, 474.8, 481.6, '在线临额使用,99.7%金额完全相等'],
    ['funnel有临额 但 C010对不上', 5376, 676.3, '-', '其中5344笔=离线C015池使用(91.7%使用额≤离线发放额)'],
    ['funnel无临额 且 C010无', 44961, 0, '-', '一致,未使用临额'],
], columns=['对账结果', '放款笔数', 'funnel临额均额(比索)', 'C010均额(比索)', '说明'])

out = r"E:\岳松个人文件\嘉银工作内容的整理\code\离线临额效果分析_C015口径_重点结论.xlsx"
xls = pd.ExcelFile(out)
existing = {s: pd.read_excel(out, sheet_name=s) for s in xls.sheet_names}
# 旧错误口径sheet删除: S7_真实四分类逾期, S8_持有x使用交叉逾期, S9_标签准确性核对
drop = {'S7_真实四分类逾期', 'S8_持有x使用交叉逾期', 'S9_标签准确性核对'}
with pd.ExcelWriter(out, engine='openpyxl') as w:
    for s, df in existing.items():
        if s in drop: continue
        df.to_excel(w, sheet_name=s, index=False)
    x1.to_excel(w, sheet_name='S10_X1_官方标签对账', index=False)
    x2.to_excel(w, sheet_name='S11_X2_在线临额金额对账', index=False)
    w1.to_excel(w, sheet_name='S12_离线池使用金额验证', index=False)
    w2.to_excel(w, sheet_name='S13_最终双字段分类_金额', index=False)
    w3.to_excel(w, sheet_name='S14_最终双字段分类_逾期', index=False)

print("✅ Excel已更新: 删除3个错误口径sheet, 新增S10-S14")

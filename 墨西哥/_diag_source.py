# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 300)
pd.set_option('display.max_rows', 200)

pq = PrestoQuery()
pq.login()
print("登录成功\n")

def q(tag, sql):
    print(f"\n===== {tag} =====")
    try:
        r = pq.query(sql)
        print(r if isinstance(r, pd.DataFrame) else r)
    except Exception as e:
        print("ERROR:", e)

# 1. 源表全量（无任何过滤）各周总量 —— 验证观察窗与逾期数据是否真实存在
q("源表全量各周总量", """
SELECT app_week,
       COUNT(*) AS row_cnt,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt,
       SUM(if_issue) AS issue_cnt,
       SUM(contract_amount) AS contract_amt
FROM mx.yj_test_table_250225
WHERE app_time >= date'2026-08-03'
GROUP BY 1
ORDER BY 1
""")

# 2. 带 mid 过滤的总量（验证 mid 的影响）
q("带 mid 过滤各周总量", """
SELECT app_week,
       COUNT(*) AS row_cnt,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt
FROM mx.yj_test_table_250225
WHERE app_time >= date'2026-08-03'
  AND mid = 1040160066607324
GROUP BY 1
ORDER BY 1
""")

# 3. is_t0_overdue_1 的取值分布（验证逾期是否真的为0）
q("is_t0_overdue_1 取值分布", """
SELECT is_t0_overdue_1, COUNT(*) AS cnt
FROM mx.yj_test_table_250225
WHERE app_time >= date'2026-08-03'
  AND app_week IN (date'2026-08-03', date'2026-08-10')
GROUP BY 1
ORDER BY 1
""")

# 4. is_t0_window_1 取值分布
q("is_t0_window_1 取值分布", """
SELECT is_t0_window_1, COUNT(*) AS cnt
FROM mx.yj_test_table_250225
WHERE app_time >= date'2026-08-03'
  AND app_week IN (date'2026-08-03', date'2026-08-10')
GROUP BY 1
ORDER BY 1
""")

# 5. model_698_score 维度全量分布（8/3 vs 8/10）
q("model_698_score 全量分布", """
SELECT CAST(model_698_score AS VARCHAR) AS grp,
       app_week,
       SUM(is_t0_window_1) AS billed_cnt,
       SUM(is_t0_overdue_1) AS overdue_cnt,
       SUM(t0_should_amt_1) AS billed_amt,
       SUM(t0_overdue_amount_1) AS overdue_amt
FROM mx.yj_test_table_250225
WHERE app_time >= date'2026-08-03'
  AND app_week IN (date'2026-08-03', date'2026-08-10')
  AND model_698_score IS NOT NULL
GROUP BY 1, 2
ORDER BY 1, 2
""")

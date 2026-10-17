# -*- coding: utf-8 -*-
"""探针：确认产品/期限字段在8月复贷放款上的取值分布。"""
import sys
import pandas as pd
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery

def probe(col):
    return f"""
SELECT
    {col},
    count(*) AS cnt
FROM mx.wxs_application_funnel
WHERE is_reloan = 'old'
  AND if_issue = 1
  AND date_trunc('month', date(release_time)) = DATE '2026-08-01'
GROUP BY 1
ORDER BY cnt DESC
LIMIT 50
"""

if __name__ == "__main__":
    pq = PrestoQuery()
    pq.login()
    pd.set_option("display.max_rows", None)
    pd.set_option("display.width", 200)
    for c in ["product_name", "product_type", "loan_cycle"]:
        print(f"\n===== {c} =====")
        df = pq.query(probe(c), wait_sec=5)
        if isinstance(df, str):
            print(df[:500])
        else:
            print(df.to_string(index=False))

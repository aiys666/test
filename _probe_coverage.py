# -*- coding: utf-8 -*-
"""查主表产品字段头部, 及 new/old 下 y.product_name_new 覆盖"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'e:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
for a in range(4):
    try:
        pq.login()
        break
    except Exception as e:
        print(f'login retry {a}: {e}')
        import time; time.sleep(5 * (a + 1))

sql2 = """
SELECT
    f.is_reloan,
    COUNT(*) AS total,
    COUNT(y.product_name_new) AS y_prod_notnull,
    SUM(CASE WHEN TRIM(COALESCE(y.product_name_new,'')) <> '' THEN 1 ELSE 0 END) AS y_prod_nonempty,
    COUNT(DISTINCT f.product_level) AS n_level,
    COUNT(DISTINCT f.product_name) AS n_name
FROM mx.wxs_application_funnel f
LEFT JOIN mx.yj_test_table_250225 y ON f.biz_id = y.biz_id
WHERE f.if_issue = 1
  AND date(f.release_time) >= DATE '2026-09-01'
  AND date(f.release_time) < DATE '2026-09-08'
GROUP BY 1
"""

sql3 = """
SELECT f.is_reloan, f.product_name, f.product_level, COUNT(*) AS cnt,
       COUNT(y.product_name_new) AS y_prod_notnull
FROM mx.wxs_application_funnel f
LEFT JOIN mx.yj_test_table_250225 y ON f.biz_id = y.biz_id
WHERE f.if_issue = 1
  AND date(f.release_time) >= DATE '2026-09-01'
  AND date(f.release_time) < DATE '2026-09-08'
  AND f.is_reloan = 'new'
GROUP BY 1, 2, 3
ORDER BY 4 DESC
LIMIT 30
"""

sql4 = """
SELECT f.is_reloan, y.product_name_new, f.product_level, COUNT(*) AS cnt
FROM mx.wxs_application_funnel f
LEFT JOIN mx.yj_test_table_250225 y ON f.biz_id = y.biz_id
WHERE f.if_issue = 1
  AND date(f.release_time) >= DATE '2026-09-01'
  AND date(f.release_time) < DATE '2026-09-08'
  AND f.is_reloan = 'old'
GROUP BY 1, 2, 3
ORDER BY 4 DESC
LIMIT 30
"""

for name, sql in [('sql2_new/old覆盖', sql2), ('sql3_首贷f产品字段', sql3), ('sql4_复贷y/f产品字段', sql4)]:
    print('=' * 60)
    print(name)
    try:
        df = pq.query(sql)
        if isinstance(df, str):
            print('ERROR:', df)
        else:
            print(df.to_string())
    except Exception as e:
        print('EXC:', repr(e))

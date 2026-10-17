import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
pq.login()

# 查看 temp_limit_test_flag 在源表的非空情况
r = pq.query("""
SELECT app_week,
       COUNT(*) AS total,
       COUNT(temp_limit_test_flag) AS not_null_cnt,
       COUNT(DISTINCT CAST(temp_limit_test_flag AS VARCHAR)) AS distinct_vals
FROM mx.yj_test_table_250225
WHERE app_time >= date'2026-08-03'
GROUP BY app_week
ORDER BY app_week
""")
print('=== temp_limit_test_flag 非空情况 ===')
print(r.to_string())

# 查看该字段的非空值分布
r2 = pq.query("""
SELECT CAST(temp_limit_test_flag AS VARCHAR) AS v, COUNT(*) AS n
FROM mx.yj_test_table_250225
WHERE app_time >= date'2026-08-03' AND temp_limit_test_flag IS NOT NULL
GROUP BY 1
ORDER BY n DESC
""")
print('=== temp_limit_test_flag 值分布 ===')
print(r2.to_string())

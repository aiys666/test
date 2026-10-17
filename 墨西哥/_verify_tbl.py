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

# 结果表当前总量
q("结果表各周总量", """
SELECT week,
       SUM(billed_cnt) AS billed_cnt,
       SUM(overdue_cnt) AS overdue_cnt,
       SUM(billed_amt) AS billed_amt,
       SUM(overdue_amt) AS overdue_amt
FROM mx.tmp_effect_decomp_all_dims
GROUP BY 1
ORDER BY 1
""")

# 结果表 698模型分 维度明细（验证是否带 mid 旧数据）
q("结果表 698模型分 维度", """
SELECT dim_group, week, billed_cnt, overdue_cnt, billed_amt, overdue_amt
FROM mx.tmp_effect_decomp_all_dims
WHERE dim_name = '698模型分'
ORDER BY dim_group, week
""")

# 结果表 698投票分 维度明细
q("结果表 698投票分 维度", """
SELECT dim_group, week, billed_cnt, overdue_cnt
FROM mx.tmp_effect_decomp_all_dims
WHERE dim_name = '698投票分'
ORDER BY dim_group, week
""")

# 结果表维度数/行数
q("结果表规模", """
SELECT COUNT(*) AS row_cnt,
       COUNT(DISTINCT dim_name) AS dim_cnt,
       COUNT(DISTINCT week) AS week_cnt
FROM mx.tmp_effect_decomp_all_dims
""")

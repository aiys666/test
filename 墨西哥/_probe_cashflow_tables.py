# -*- coding: utf-8 -*-
"""摸清现金流相关表结构：s02_loan / s02_loan_repayment / s02_loan_repayment_detail / s02_loan_postpone_order"""
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
print("登录:", pq.login())

tables = [
    "ods.s02_loan",
    "ods.s02_loan_repayment",
    "ods.s02_loan_repayment_detail",
    "ods.s02_loan_postpone_order",
]

for t in tables:
    print("=" * 80)
    print("TABLE:", t)
    r = pq.query(f"describe {t}")
    if isinstance(r, str):
        print("ERROR:", r)
    else:
        print(r.to_string())

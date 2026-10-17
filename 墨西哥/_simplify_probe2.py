# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import pandas as pd

X = r"E:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\墨西哥_产品评级收益测算_双评级.xlsx"
df = pd.read_excel(X, sheet_name="全期_产品×档")
P = df[df['产品'].notna()].copy()
P = P[P['档位'].astype(str).isin(['产品小计'])]
cols = ['评级体系','产品','放款笔数','复贷客数','放款金额','件均','前收率_税前%','前收率_税后%',
        '后收率_税前%','后收率_税后%','总息费率_税前%','总息费率_税后%','息费税(估)占合同%',
        '加权期限(天)','日息_税后%','日息_税前%','本金逾期率_0%','息费逾期率_0%','TR_0_税前%','TR_0_税后%']
for sys_name in ['V5_3','V6_1']:
    s = P[P['评级体系']==sys_name]
    # B/C/E focus + big products
    sel = s[s['产品'].str.startswith(('B_07_02','C_07_04','E_07','C_07_03','B_07_03','E_07_02'))]
    sel = pd.concat([sel, s.nlargest(8,'放款笔数')]).drop_duplicates('产品').sort_values('放款笔数',ascending=False)
    print(f"\n==== {sys_name} ====")
    print(sel[cols].to_string(index=False, float_format=lambda x: f"{x:.4f}"))

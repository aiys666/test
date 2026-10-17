# -*- coding: utf-8 -*-
"""v11 宽表校验(直接读CSV, 不查Presto)"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
import pandas as pd
import numpy as np

pd.set_option('display.width', 300); pd.set_option('display.max_columns', 80); pd.set_option('display.max_rows', 100)

csv = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\在线临额决策链大宽表_20260901_1015.csv"
df = pd.read_csv(csv, encoding='utf-8-sig', low_memory=False)

# 数值化: 非文本列统一转 numeric(Decimal/str -> float)
_text = {'biz_id','进件日期','进件时刻_app_time','申请时刻_apply_time','实际放款_release_time',
         '离线发放时间','离线批量算额时刻_1504','离线使用时间','在线临额发放时间_model1386',
         '在线临额使用时间_C010','临额冻结时刻_C003','策略分桶_V52_V53','实验组分桶_9月3日后口径',
         '弹窗领取状态','决策是否T+1批处理重跑','离线当时状态','在线是否覆盖离线'}
for c in df.columns:
    if c not in _text:
        df[c] = pd.to_numeric(df[c], errors='coerce')

print("shape:", df.shape)
print("列清单:")
for i, c in enumerate(df.columns): print(i, c)

def sec(t): return f"===== {t} ====="

print(sec("1 行数 & 去重"))
print("rows:", len(df), "uniq biz:", df['biz_id'].nunique())

print(sec("3 主额链条覆盖 & 恒等式"))
print("C002提额命中:", df['申请时主额提额_C002'].notna().sum(),
      " C003预授权命中:", df['申请时主额预授权_C003MAIN'].notna().sum())
print("used_detail MAIN命中:", df['占用主额_used_detail原始'].notna().sum(),
      " 补全后命中:", df['占用主额金额_补全'].notna().sum())
diag = (df['恒等式差额_诊断'].abs() > 0.01).sum()
print("恒等式差额非0笔数:", diag)
print(df['恒等式差额_诊断'].describe())

print(sec("4 公式命中率"))
theo = df['理论发放比例'] * df['算额底数_占用主额floor20']
hit = (theo - df['理论算额_1379_取整前']).abs() <= 0.01
base = df['理论算额_1379_取整前'].notna()
print("1379有值:", base.sum(), " 公式命中:", (hit & base).sum(), " 命中率:", round((hit&base).sum()/base.sum(),5))

print(sec("5 type1 实测比例分布"))
t1 = df[(df['用信临额类型_type_1523']==1) & df['弹窗发放tag_1386'].eq(1) & df['算额底数_占用主额floor20'].gt(0)]
print(t1.groupby(['策略分桶_V52_V53', t1['实测比例_1379除底数'].round(2)]).size())

print(sec("6 弹窗状态分布"))
print(df['弹窗领取状态'].value_counts(dropna=False))

print(sec("15 v11 历史临额占用拆分"))
c010 = df[df['弹窗领取状态']=='已弹窗_本笔在线领取']
print("在线领取笔数:", len(c010), " 历史临额占用金额有值:", df['历史临额占用金额'].notna().sum())
print("历史占用>0.01笔数:", (df['历史临额占用金额']>0.01).sum(),
      " 金额合计:", round(df['历史临额占用金额'].sum(),1))
occ = df[df['历史临额占用金额']>0.01].copy()
print("结清后占用>0.01笔数:", (occ['历史结清后临额占用']>0.01).sum(), " 金额:", round(occ['历史结清后临额占用'].sum(),1))
print("未结清占用>0.01笔数:", (occ['历史未结清临额占用']>0.01).sum(), " 金额:", round(occ['历史未结清临额占用'].sum(),1))
chk = (occ['历史结清后临额占用']+occ['历史未结清临额占用']-occ['历史临额占用金额']).abs()
print("结清后+未结清==历史占用? 偏差>0.05笔数:", (chk>0.05).sum(), " 最大偏差:", round(chk.max(),3))
print("台账还原差额诊断:")
print(df['历史占用台账还原差额_诊断'].describe())
print("|差额|>0.05笔数:", (df['历史占用台账还原差额_诊断'].abs()>0.05).sum())
print("占用笔按周分布(结清后/未结清金额):")
occ['周'] = pd.to_datetime(occ['进件日期']).dt.to_period('W-SUN')
print(occ.groupby('周')[['历史临额占用金额','历史结清后临额占用','历史未结清临额占用']].sum().round(1).to_string())
print("样例笔 1620000465328686:")
print(df[df['biz_id']==1620000465328686][['biz_id','在线临额发放金额_857','在线临额使用金额_C010','历史临额占用金额','历史结清后临额占用','历史未结清临额占用','历史占用台账还原差额_诊断']].to_string())
print("历史占用Top10:")
print(occ.nlargest(10,'历史临额占用金额')[['biz_id','进件日期','在线临额发放金额_857','在线临额使用金额_C010','历史临额占用金额','历史结清后临额占用','历史未结清临额占用','历史占用台账还原差额_诊断']].to_string())
print("DONE-WIDE11")

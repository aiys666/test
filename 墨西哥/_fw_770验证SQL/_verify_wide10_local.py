# -*- coding: utf-8 -*-
"""读已导出的大宽表 CSV 做全量回归(不再查库), 强制数值化"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
import pandas as pd
pd.set_option('display.width', 400); pd.set_option('display.max_columns', 90); pd.set_option('display.max_rows', 120)

p = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\在线临额决策链大宽表_20260901_1015.csv"
df = pd.read_csv(p, dtype=str, encoding='utf-8-sig')
_text = {'biz_id','进件日期','进件时刻_app_time','申请时刻_apply_time','实际放款_release_time',
         '离线发放时间','离线批量算额时刻_1504','离线使用时间','在线临额发放时间_model1386',
         '在线临额使用时间_C010','临额冻结时刻_C003','策略分桶_V52_V53','实验组分桶_9月3日后口径',
         '弹窗领取状态','决策是否T+1批处理重跑','离线当时状态','在线是否覆盖离线'}
for c in df.columns:
    if c not in _text:
        df[c] = pd.to_numeric(df[c].astype(str).str.strip().replace({'':None,'None':None,'nan':None}), errors='coerce')

def sec(t): print("\n" + "="*30, t, "="*30)

sec("1 行数"); print("rows:", len(df), "uniq:", df['biz_id'].nunique())
print("按进件日期行数:"); print(df.groupby('进件日期').size().to_string())

sec("3 主额链条覆盖")
print("C002提额命中:", df['申请时主额提额_C002'].notna().sum(), "C003预授权命中:", df['申请时主额预授权_C003MAIN'].notna().sum())
raw = df['占用主额_used_detail原始']
fill = df['占用主额金额_补全']
print("used_detail MAIN 有行(含全额临额=0):", raw.notna().sum(), " 真延迟(空):", raw.isna().sum())
print("补全后空:", fill.isna().sum())
diag = (df['恒等式差额_诊断'].abs() > 0.01)
print("恒等式差额非0笔数:", diag.sum())
print(df.loc[diag, '恒等式差额_诊断'].describe())

sec("4 公式命中率(补全底数)")
theo = df['理论发放比例'] * df['算额底数_占用主额floor20']
hit = (theo - df['理论算额_1379_取整前']).abs() <= 0.01
base = df['理论算额_1379_取整前'].notna()
print("1379有值:", int(base.sum()), " 命中:", int((hit&base).sum()), " 命中率:", round((hit&base).sum()/base.sum(),5))
print("未命中:")
print(df.loc[base & ~hit, ['biz_id','进件日期','用信临额类型_type_1523','算额底数_占用主额floor20','理论发放比例','理论算额_1379_取整前','策略分桶_V52_V53']].head(20).to_string())

sec("5 type1 实测比例 × flag")
t1 = df[(df['用信临额类型_type_1523']==1) & (df['弹窗发放tag_1386']==1) & (df['算额底数_占用主额floor20']>0)]
print(t1.groupby(['策略分桶_V52_V53', t1['实测比例_1379除底数'].round(3)]).size().to_string())
print("实测比例非0.5/0.6的type1:")
odd = t1[~t1['实测比例_1379除底数'].round(3).isin([0.5,0.6])]
print(odd[['biz_id','进件日期','算额底数_占用主额floor20','实测比例_1379除底数','理论算额_1379_取整前','策略分桶_V52_V53']].to_string())

sec("5b type1 实测比例 × 周(证明非时间趋势)")
w = t1.assign(周=pd.to_datetime(t1['进件日期']).dt.to_period('W-SUN').astype(str))
print(w.groupby(['周', w['实测比例_1379除底数'].round(2)]).size().unstack(fill_value=0).to_string())

sec("6 弹窗状态"); print(df['弹窗领取状态'].value_counts(dropna=False).to_string())
sec("7 T+1重跑"); print(df['决策是否T+1批处理重跑'].value_counts(dropna=False).to_string())
sec("8 hash组 × flag"); print(df.groupby(['实验组分桶_9月3日后口径','策略分桶_V52_V53'], dropna=False).size().to_string())
print("hash覆盖:", df['实验分流hash值'].notna().sum())
sec("9 1067期限额覆盖")
for c in ['7天期支用额_1067','授信有效期天数_1067','单日最大可借额度_1067']:
    print(c, int(df[c].notna().sum()))
sec("10 决策树标签 × type"); print(df.groupby(['用信临额类型_type_1523','决策树标签_tree_label_1379'], dropna=False).size().to_string())
sec("11 间隔分布"); print(df[['间隔_进件到申请_分钟','间隔_申请到放款_分钟','间隔_申请到弹窗决策_秒','间隔_弹窗到领取_秒','间隔_领取到放款_秒']].describe().to_string())
sec("12 评级覆盖")
for c in ['主额评级_V5_2_1500','主额评级_V5_3_1542','主额评级_V6_1_1635']:
    print(c, int(df[c].notna().sum()))
sec("13 gc7d == credit_amount?")
both = df['7天期支用额_1067'].notna() & df['授信额度_credit_amount_1067'].notna()
print("两列都有:", int(both.sum()), " 相等:", int((df.loc[both,'7天期支用额_1067']==df.loc[both,'授信额度_credit_amount_1067']).sum()))
sec("14 主额链覆盖 × 进件日")
cv = df.assign(c2=df['申请时主额提额_C002'].notna(), c3=df['申请时主额预授权_C003MAIN'].notna())
print(cv.groupby('进件日期')[['c2','c3']].mean().round(3).to_string())
print("DONE-LOCAL")

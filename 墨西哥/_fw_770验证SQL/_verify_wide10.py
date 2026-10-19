# -*- coding: utf-8 -*-
"""大宽表 v10 全量回归: 新列命中率 + 旧样例不回退 + 导出 CSV"""
import sys, re, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
import pandas as pd
from mexico_presto import PrestoQuery

pd.set_option('display.width', 300); pd.set_option('display.max_columns', 80); pd.set_option('display.max_rows', 100)

sql_path = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_fw_770验证SQL\11_在线离线临额区分逻辑.sql"
txt = open(sql_path, encoding='utf-8').read()
begin = txt.index("-- <<WIDE_TABLE_SQL_BEGIN>>")
end = txt.index("-- <<WIDE_TABLE_SQL_END>>", begin)
qsql = txt[begin:end]
qsql = qsql[qsql.index("\nwith\n"):].strip().rstrip(';').strip()
assert 'main_change' in qsql and 'exp_hash' in qsql and 'hist_occ_summary' in qsql, "取到的不是大宽表段!"
print("sql chars:", len(qsql), "head:", qsql[:60].replace("\n"," "))

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)

def run_sql(sql, tag):
    for i in range(8):
        try:
            r = pq.query(sql)
            if isinstance(r, str):
                print(f"[{tag} retry {i+1}] {r[:200]}"); time.sleep(8); continue
            return r
        except Exception as e:
            print(f"[{tag} retry {i+1}] {e}"); time.sleep(8)
    print(f"[{tag}] FAILED"); return None

# ★ 网关结果集上限 10000 行 → 按进件日切片(每天 1 片);
#   节点 CTE 窗口填充 ±7 天(进件→申请跨天最长实测 5 天, 决策/评级在 apply 时刻落库);
#   相邻片重叠产生的重复行靠 drop_duplicates(biz_id) 去除
import datetime as dt
parts = []
d = dt.date(2026, 9, 1)
end_all = dt.date(2026, 10, 16)
STEP = 7   # 按周切片(每片约7天*1300行≈9100行, 低于网关1万上限)
hard_lo = dt.date(2026, 8, 31); hard_hi = dt.date(2026, 10, 17)
while d < end_all:
    d1 = min(d + dt.timedelta(days=STEP), end_all)
    ds = lambda x: x.strftime('%Y-%m-%d')
    lo = max(d - dt.timedelta(days=7), hard_lo)
    hi = min(d1 + dt.timedelta(days=8), hard_hi)
    s = (qsql.replace("date'2026-09-01'", f"date'{ds(d)}'")
             .replace("date'2026-10-16'", f"date'{ds(d1)}'")
             .replace("timestamp '2026-08-31'", f"timestamp '{ds(lo)}'")
             .replace("timestamp '2026-10-17'", f"timestamp '{ds(hi)}'"))
    part = run_sql(s, ds(d))
    if part is None: sys.exit(1)
    print(f"{ds(d)}~{ds(d1)} rows:", len(part), flush=True)
    parts.append(part)
    d = d1
df = pd.concat(parts, ignore_index=True).drop_duplicates(subset='biz_id')

# 网关把部分数值列以字符串/Decimal 返回, 统一对非文本列做数值化
_text = {'biz_id','进件日期','进件时刻_app_time','申请时刻_apply_time','实际放款_release_time',
         '离线发放时间','离线批量算额时刻_1504','离线使用时间','在线临额发放时间_model1386',
         '在线临额使用时间_C010','临额冻结时刻_C003','策略分桶_V52_V53','实验组分桶_9月3日后口径',
         '弹窗领取状态','决策是否T+1批处理重跑','离线当时状态','在线是否覆盖离线'}
for c in df.columns:
    if c not in _text and df[c].dtype == object:
        df[c] = pd.to_numeric(df[c], errors='coerce')

print("shape:", df.shape)
print("columns:")
for i, c in enumerate(df.columns): print(i, c)

out = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\在线临额决策链大宽表_20260901_1015.csv"
try:
    df.to_csv(out, index=False, encoding='utf-8-sig')
except PermissionError:
    out = out.replace(".csv", "_v11.csv")
    df.to_csv(out, index=False, encoding='utf-8-sig')
    print("[warn] 旧文件被占用(Excel打开?), 改存:", out)
print("saved:", out)

def sec(t):
    return f"===== {t} ====="

print(sec("1 行数 & 去重"))
print("rows:", len(df), "uniq biz:", df['biz_id'].nunique())

print(sec("2 旧样例不回退"))
samp = df[df['biz_id'].isin(['1620000462179690','1620000480579892','1620000468511585','1620000482769098','1620000462632742','1620000474757589','1620000479377160'])]
cols = ['biz_id','进件日期','授信额度_credit_amount_1067','申请时主额提额_C002','申请时主额预授权_C003MAIN',
        '用信临额类型_type_1523','策略分桶_V52_V53','实验组分桶_9月3日后口径','弹窗发放tag_1386',
        '算额底数_占用主额floor20','理论发放比例','实测比例_1379除底数','理论算额_1379_取整前','决策树标签_tree_label_1379',
        '在线临额发放金额_857','在线临额使用金额_C010','临额最终使用金额','合同金额_放款金额',
        '占用主额_used_detail原始','占用主额金额_补全','恒等式差额_诊断','弹窗领取状态','决策是否T+1批处理重跑']
print(samp[cols].to_string())

print(sec("3 主额链条覆盖"))
print("C002提额命中:", df['申请时主额提额_C002'].notna().sum(), " C003预授权命中:", df['申请时主额预授权_C003MAIN'].notna().sum())
print("used_detail MAIN命中:", df['占用主额_used_detail原始'].notna().sum(),
      " 补全后命中:", df['占用主额金额_补全'].notna().sum())
diag = (df['恒等式差额_诊断'].abs() > 0.01).sum()
print("恒等式差额非0笔数:", diag)
print(df['恒等式差额_诊断'].describe())

print(sec("4 公式命中率(用补全底数)"))
theo = df['理论发放比例'] * df['算额底数_占用主额floor20']
hit = (theo - df['理论算额_1379_取整前']).abs() <= 0.01
base = df['理论算额_1379_取整前'].notna()
print("1379有值:", base.sum(), " 公式命中:", (hit & base).sum(), " 命中率:", round((hit&base).sum()/base.sum(),5))
print("未命中样例:")
print(df.loc[base & ~hit, ['biz_id','用信临额类型_type_1523','算额底数_占用主额floor20','理论发放比例','理论算额_1379_取整前','策略分桶_V52_V53']].head(15).to_string())

print(sec("5 type1 实测比例分布"))
t1 = df[(df['用信临额类型_type_1523']==1) & df['弹窗发放tag_1386'].eq(1) & df['算额底数_占用主额floor20'].gt(0)]
print(t1.groupby(['策略分桶_V52_V53', t1['实测比例_1379除底数'].round(2)]).size())

print(sec("6 弹窗状态分布"))
print(df['弹窗领取状态'].value_counts(dropna=False))

print(sec("7 T+1 重跑分布"))
print(df['决策是否T+1批处理重跑'].value_counts(dropna=False))

print(sec("8 hash实验组 × flag"))
print(df.groupby(['实验组分桶_9月3日后口径','策略分桶_V52_V53'], dropna=False).size().to_string())
print("hash覆盖:", df['实验分流hash值'].notna().sum())

print(sec("9 1067期限额覆盖"))
for c in ['7天期支用额_1067','授信有效期天数_1067','单日最大可借额度_1067']:
    print(c, df[c].notna().sum())

print(sec("10 决策树标签分布"))
print(df.groupby(['用信临额类型_type_1523','决策树标签_tree_label_1379'], dropna=False).size().to_string())

print(sec("11 间隔分布(分钟/秒)"))
print(df[['间隔_进件到申请_分钟','间隔_申请到放款_分钟','间隔_申请到弹窗决策_秒','间隔_弹窗到领取_秒','间隔_领取到放款_秒']].describe().to_string())

print(sec("15 v11 历史临额占用拆分"))
c010 = df[df['弹窗领取状态']=='已弹窗_本笔在线领取']
print("在线领取笔数:", len(c010), " 历史临额占用金额有值:", df['历史临额占用金额'].notna().sum())
print("历史占用>0.01笔数:", (df['历史临额占用金额']>0.01).sum(),
      " 金额合计:", round(df['历史临额占用金额'].sum(),1))
occ = df[df['历史临额占用金额']>0.01]
print("结清后占用>0.01笔数:", (occ['历史结清后临额占用']>0.01).sum(), " 金额:", round(occ['历史结清后临额占用'].sum(),1))
print("未结清占用>0.01笔数:", (occ['历史未结清临额占用']>0.01).sum(), " 金额:", round(occ['历史未结清临额占用'].sum(),1))
chk = (occ['历史结清后临额占用']+occ['历史未结清临额占用']-occ['历史临额占用金额']).abs()
print("结清后+未结清==历史占用? 偏差>0.05笔数:", (chk>0.05).sum(), " 最大偏差:", round(chk.max(),3))
print("台账还原差额诊断:")
print(df['历史占用台账还原差额_诊断'].describe())
print("|差额|>0.05笔数:", (df['历史占用台账还原差额_诊断'].abs()>0.05).sum())
print("占用笔按周分布(结清后/未结清金额):")
w = occ.copy(); w['周'] = pd.to_datetime(w['进件日期']).dt.to_period('W-SUN')
print(w.groupby('周')[['历史临额占用金额','历史结清后临额占用','历史未结清临额占用']].sum().round(1).to_string())
print("样例笔 1620000465328686:")
print(df[df['biz_id']=='1620000465328686'][['biz_id','在线临额发放金额_857','在线临额使用金额_C010','历史临额占用金额','历史结清后临额占用','历史未结清临额占用','历史占用台账还原差额_诊断']].to_string())
print("历史占用Top10:")
print(occ.nlargest(10,'历史临额占用金额')[['biz_id','进件日期','在线临额发放金额_857','在线临额使用金额_C010','历史临额占用金额','历史结清后临额占用','历史未结清临额占用','历史占用台账还原差额_诊断']].to_string())
print("DONE-WIDE10")

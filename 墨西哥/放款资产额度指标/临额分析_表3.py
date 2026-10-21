# -*- coding: utf-8 -*-
"""依托 mx.yj_temp_limit_wide_table_v3 做多维度分析，输出 Excel。"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'e:\岳松个人文件\嘉银工作内容的整理\code')
import pandas as pd
from mexico_presto import PrestoQuery
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

T = 'mx.yj_temp_limit_wide_table_v3'
OUT = os.path.dirname(os.path.abspath(__file__))
q = PrestoQuery(); q.login()

def run(sql):
    r = q.query(sql)
    if isinstance(r, str):
        raise RuntimeError(r[:400])
    return r

NUM_EXCLUDE = ('issue_week','issue_month','used_scenario','grant_scenario',
               'strategy_version','cap_type','product_level','use_bucket','expire_bucket')

def num(df, cols=None):
    for c in (cols if cols is not None else df.columns):
        if c in df.columns and c not in NUM_EXCLUDE:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    return df

print('Q1 总览')
q1 = run(f"""
SELECT used_scenario, grant_scenario,
       COUNT(1) AS n,
       SUM(contract_amount) AS contract_amt,
       AVG(contract_amount) AS avg_contract,
       SUM(main_used_this) AS main_used,
       SUM(offline_used_this) AS offline_used,
       SUM(online_used_this) AS online_used,
       SUM(voucher_limit) AS voucher_amt,
       SUM(CASE WHEN is_contract_capped=1 THEN 1 ELSE 0 END) AS capped_n,
       AVG(temp_share_of_contract) AS temp_share
FROM {T} GROUP BY 1,2 ORDER BY 1,2""")
num(q1, ['n','contract_amt','avg_contract','main_used','offline_used','online_used','voucher_amt','capped_n','temp_share'])
q1['temp_used'] = q1['offline_used'] + q1['online_used']
q1['amt_share'] = q1['contract_amt'] / q1['contract_amt'].sum()
q1['temp_share_of_amt'] = q1['temp_used'] / q1['contract_amt']

print('Q2 供给漏斗（全区间）')
q2 = run(f"""
SELECT COUNT(1) AS n_all,
       SUM(CASE WHEN has_offline_grant=1 THEN 1 ELSE 0 END) AS off_grant_n,
       SUM(offline_grant_amount) AS off_grant_amt,
       SUM(CASE WHEN offline_used_this>0 THEN 1 ELSE 0 END) AS off_used_n,
       SUM(offline_used_this) AS off_used_amt,
       SUM(offline_unused_amount) AS off_unused_amt,
       AVG(CASE WHEN has_offline_grant=1 THEN offline_expire_days END) AS off_avg_expire_days,
       SUM(CASE WHEN has_online_grant=1 THEN 1 ELSE 0 END) AS on_grant_n,
       SUM(online_grant_amount) AS on_grant_amt,
       SUM(CASE WHEN online_used_this>0 THEN 1 ELSE 0 END) AS on_claim_n,
       SUM(online_used_this) AS on_used_amt,
       AVG(CASE WHEN has_online_grant=1 AND online_grant_amount>0 THEN online_use_rate END) AS on_avg_use_rate
FROM {T}""")
num(q2, list(q2.columns))

print('Q2b 供给漏斗（按周）')
q2b = run(f"""
SELECT issue_week,
       COUNT(1) AS n_all,
       SUM(CASE WHEN has_offline_grant=1 THEN 1 ELSE 0 END) AS off_grant_n,
       SUM(offline_grant_amount) AS off_grant_amt,
       SUM(CASE WHEN offline_used_this>0 THEN 1 ELSE 0 END) AS off_used_n,
       SUM(offline_used_this) AS off_used_amt,
       SUM(CASE WHEN has_online_grant=1 THEN 1 ELSE 0 END) AS on_grant_n,
       SUM(online_grant_amount) AS on_grant_amt,
       SUM(CASE WHEN online_used_this>0 THEN 1 ELSE 0 END) AS on_claim_n,
       SUM(online_used_this) AS on_used_amt
FROM {T} GROUP BY 1 ORDER BY 1""")
num(q2b, list(q2b.columns))

print('Q3 额度结构（按产品）')
q3 = run(f"""
SELECT product_level, COUNT(1) AS n,
       SUM(credit_amount) AS main_grant,
       SUM(change_used_grantamount) AS main_hist_used,
       AVG(main_available_amount) AS main_avail_avg,
       SUM(offline_grant_amount) AS off_grant,
       SUM(offline_used_amount) AS off_hist_used,
       AVG(offline_available_amount) AS off_avail_avg,
       SUM(online_grant_amount) AS on_grant,
       SUM(online_used_amount) AS on_hist_used,
       AVG(online_available_amount) AS on_avail_avg,
       AVG(avail_current_logic) AS avail_current_avg,
       AVG(avail_tochange_logic) AS avail_tochange_avg,
       AVG(avail_future_logic) AS avail_future_avg
FROM {T} GROUP BY 1 ORDER BY 2 DESC""")
num(q3, [c for c in q3.columns if c != 'product_level'])

print('Q4 增信效果（评级 × 场景）')
q4 = run(f"""
SELECT v6_1_grade, used_scenario, COUNT(1) AS n,
       AVG(contract_amount) AS avg_contract,
       AVG(main_used_this) AS avg_main,
       AVG(uplift_amount) AS avg_uplift,
       AVG(temp_share_of_contract) AS temp_share,
       AVG(v6_1_level) AS avg_v61
FROM {T} WHERE v6_1_grade IS NOT NULL GROUP BY 1,2 ORDER BY 1,2""")
num(q4, [c for c in q4.columns if c not in ('used_scenario',)])

print('Q5 上限约束（撞顶分类）')
q5 = run(f"""
SELECT cap_type,
       COUNT(1) AS n,
       SUM(contract_amount) AS contract_amt,
       SUM(add_if_cap_50000) AS add_if_50000,
       AVG(main_used_this) AS avg_main_used,
       AVG(credit_amount) AS avg_credit,
       AVG(v6_1_level) AS avg_v61
FROM {T} GROUP BY 1 ORDER BY 1""")
num(q5, [c for c in q5.columns if c != 'cap_type'])
tot = run(f"SELECT COUNT(1) AS n, SUM(add_if_cap_50000) AS add_amt FROM {T}")
tot = num(tot, ['n','add_amt'])

print('Q5b 上限（按周）')
q5b = run(f"""
SELECT issue_week, COUNT(1) AS n,
       SUM(CASE WHEN is_contract_capped=1 THEN 1 ELSE 0 END) AS capped_n,
       SUM(add_if_cap_50000) AS add_if_50000,
       SUM(CASE WHEN cap_type='A' THEN 1 ELSE 0 END) AS capA_n,
       SUM(CASE WHEN cap_type='B' THEN 1 ELSE 0 END) AS capB_n,
       SUM(CASE WHEN cap_type='C' THEN 1 ELSE 0 END) AS capC_n,
       SUM(contract_amount) AS contract_amt
FROM {T} GROUP BY 1 ORDER BY 1""")
num(q5b, list(q5b.columns))
q5b['capped_share'] = q5b['capped_n'] / q5b['n']

print('Q6 风险归因（场景）')
q6 = run(f"""
SELECT used_scenario, COUNT(1) AS n, SUM(contract_amount) AS contract_amt,
       SUM(t0_should_capit_1) AS s1, SUM(t0_overdue_capit_1) AS o1,
       SUM(t0_should_capit_2) AS s2, SUM(t0_overdue_capit_2) AS o2,
       SUM(t0_should_capit_3) AS s3, SUM(t0_overdue_capit_3) AS o3,
       SUM(t0_should_capit_4) AS s4, SUM(t0_overdue_capit_4) AS o4,
       SUM(CASE WHEN is_t7_window_4=1 THEN t7_should_capit_4 ELSE 0 END) AS s47,
       SUM(CASE WHEN is_t7_window_4=1 THEN t7_overdue_capit_4 ELSE 0 END) AS o47,
       SUM(CASE WHEN is_t7_window_4=1 THEN t7_overdue_interest_4 ELSE 0 END) AS oi47,
       SUM(haircut_amount) AS haircut, SUM(should_interest) AS should_interest,
       SUM(CASE WHEN is_t7_window_4=1 THEN 1 ELSE 0 END) AS n_47
FROM {T} GROUP BY 1 ORDER BY 1""")
num(q6, [c for c in q6.columns if c != 'used_scenario'])

print('Q6b 风险（评级 × 场景）')
q6b = run(f"""
SELECT v6_1_grade, used_scenario, COUNT(1) AS n,
       SUM(t0_should_capit_1) AS s1, SUM(t0_overdue_capit_1) AS o1,
       SUM(CASE WHEN is_t7_window_4=1 THEN t7_should_capit_4 ELSE 0 END) AS s47,
       SUM(CASE WHEN is_t7_window_4=1 THEN t7_overdue_capit_4 ELSE 0 END) AS o47,
       SUM(CASE WHEN is_t7_window_4=1 THEN 1 ELSE 0 END) AS n_47
FROM {T} WHERE v6_1_grade IS NOT NULL GROUP BY 1,2 ORDER BY 1,2""")
num(q6b, [c for c in q6b.columns if c != 'used_scenario'])

print('Q6c 风险（周 × 场景）')
q6c = run(f"""
SELECT issue_week, used_scenario, COUNT(1) AS n,
       SUM(t0_should_capit_1) AS s1, SUM(t0_overdue_capit_1) AS o1,
       SUM(CASE WHEN is_t7_window_4=1 THEN 1 ELSE 0 END) AS n_47
FROM {T} GROUP BY 1,2 ORDER BY 1,2""")
num(q6c, [c for c in q6c.columns if c != 'used_scenario'])

print('Q7 资金效率')
q7 = run(f"""
SELECT CASE WHEN offline_use_rate IS NULL THEN 'A 无离线发放'
            WHEN offline_use_rate = 0 THEN 'B 发了没用'
            WHEN offline_use_rate < 0.5 THEN 'C 用了<50%'
            WHEN offline_use_rate < 1 THEN 'D 用了50~99%'
            ELSE 'E 用满100%' END AS use_bucket,
       COUNT(1) AS n, SUM(offline_grant_amount) AS grant_amt,
       SUM(offline_used_this) AS used_amt,
       SUM(offline_unused_amount) AS unused_amt
FROM {T} GROUP BY 1 ORDER BY 1""")
num(q7, ['n','grant_amt','used_amt','unused_amt'])

q7b = run(f"""
SELECT CASE WHEN offline_expire_days IS NULL THEN 'A 无发放'
            WHEN offline_expire_days >= 4 THEN 'B 当天/次日(余4-5天)'
            WHEN offline_expire_days = 3 THEN 'C 余3天'
            WHEN offline_expire_days = 2 THEN 'D 余2天'
            WHEN offline_expire_days = 1 THEN 'E 余1天'
            ELSE 'F 余0天(到期当日)' END AS expire_bucket,
       COUNT(1) AS n,
       SUM(CASE WHEN offline_used_this>0 THEN 1 ELSE 0 END) AS used_n,
       SUM(offline_used_this) AS used_amt
FROM {T} GROUP BY 1 ORDER BY 1""")
num(q7b, ['n','used_n','used_amt'])

print('Q8 策略维度')
q8 = run(f"""
SELECT strategy_version, use_type_1523, COUNT(1) AS n,
       SUM(contract_amount) AS contract_amt,
       SUM(CASE WHEN has_online_grant=1 THEN 1 ELSE 0 END) AS on_grant_n,
       SUM(online_grant_amount) AS on_grant_amt,
       SUM(CASE WHEN online_used_this>0 THEN 1 ELSE 0 END) AS on_claim_n,
       SUM(online_used_this) AS on_used_amt,
       AVG(temp_share_of_contract) AS temp_share,
       SUM(t0_should_capit_1) AS s1, SUM(t0_overdue_capit_1) AS o1,
       SUM(CASE WHEN is_t7_window_4=1 THEN t7_should_capit_4 ELSE 0 END) AS s47,
       SUM(CASE WHEN is_t7_window_4=1 THEN t7_overdue_capit_4 ELSE 0 END) AS o47,
       SUM(CASE WHEN is_t7_window_4=1 THEN 1 ELSE 0 END) AS n_47
FROM {T} WHERE strategy_version IS NOT NULL GROUP BY 1,2 ORDER BY 1,2""")
num(q8, [c for c in q8.columns if c not in ('strategy_version',)])

# ---------- 派生比率 ----------
for df, pairs in [
    (q6, [('i1t0','o1','s1'), ('i2t0','o2','s2'), ('i3t0','o3','s3'), ('i4t0','o4','s4'), ('i4t7','o47','s47')]),
    (q6b, [('i1t0','o1','s1'), ('i4t7','o47','s47')]),
    (q6c, [('i1t0','o1','s1')]),
    (q8, [('i1t0','o1','s1'), ('i4t7','o47','s47')]),
]:
    for name, o, s in pairs:
        df[name] = df.apply(lambda r: r[o] / r[s] if r[s] else None, axis=1)

q1['off_use_rate'] = q1['offline_used'] / q1['contract_amt']
q1['on_use_rate'] = q1['online_used'] / q1['contract_amt']
q2['off_use_rate_by_amt'] = q2['off_used_amt'] / q2['off_grant_amt']
q2['on_claim_rate_by_amt'] = q2['on_used_amt'] / q2['on_grant_amt']
q2['on_claim_rate_by_n'] = q2['on_claim_n'] / q2['on_grant_n']
q2b['off_use_rate'] = q2b['off_used_amt'] / q2b['off_grant_amt']
q2b['on_claim_rate'] = q2b['on_used_amt'] / q2b['on_grant_amt']
q7['use_rate'] = q7.apply(lambda r: r['used_amt'] / r['grant_amt'] if r['grant_amt'] else None, axis=1)
q7b['used_share'] = q7b['used_n'] / q7b['n']
for df in [q8]:
    df['on_grant_share'] = df['on_grant_n'] / df['n']
    df['on_claim_share'] = df['on_claim_n'] / df['n']

# ---------- 写 Excel ----------
XLSX = os.path.join(OUT, '临额分析_表3_20260901起.xlsx')
sheets = [
    ('01_总览_场景', q1),
    ('02_供给漏斗_全区间', q2),
    ('03_供给漏斗_按周', q2b),
    ('04_额度结构_按产品', q3),
    ('05_增信效果_评级场景', q4),
    ('06_上限约束_分类', q5),
    ('07_上限约束_按周', q5b),
    ('08_风险归因_场景', q6),
    ('09_风险归因_评级场景', q6b),
    ('10_风险归因_周场景', q6c),
    ('11_资金效率_使用率', q7),
    ('12_资金效率_有效期', q7b),
    ('13_策略维度_V5', q8),
]
RATE_KEYS = ('rate', 'share', 'i1t0', 'i4t7', 'i2t0', 'i3t0', 'i4t0')
head_fill = PatternFill('solid', fgColor='1F4E78')
head_font = Font(color='FFFFFF', bold=True)
thin = Side(style='thin', color='D9D9D9')
border = Border(left=thin, right=thin, top=thin, bottom=thin)

with pd.ExcelWriter(XLSX, engine='openpyxl') as w:
    for name, df in sheets:
        df.to_excel(w, sheet_name=name, index=False)
    wb = w.book
    for name, df in sheets:
        ws = wb[name]
        for i, c in enumerate(df.columns, 1):
            cell = ws.cell(row=1, column=i)
            cell.fill = head_fill; cell.font = head_font
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            ws.column_dimensions[get_column_letter(i)].width = max(12, min(26, len(str(c)) * 1.6 + 4))
        is_rate = [any(k in str(c) for k in RATE_KEYS) for c in df.columns]
        for j, r in enumerate(df.itertuples(index=False), 2):
            for i, v in enumerate(r, 1):
                cell = ws.cell(row=j, column=i)
                cell.border = border
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    cell.number_format = '0.00%' if is_rate[i-1] else '#,##0'
        ws.freeze_panes = 'A2'
        ws.auto_filter.ref = ws.dimensions

print('\nExcel ->', XLSX)

# ---------- 结论摘要 sheet（插入到最前） ----------
def pct(x, d=2):
    return f'{x*100:.{d}f}%'

sum_rows = [
    ('① 供给漏斗·离线',
     '有离线额度的笔约一半会真用；但额度是按笔重复计数，"金额利用率"不能当兑现率读',
     f"持额 {int(q2.at[0,'off_grant_n'])} 笔（占 {pct(q2.at[0,'off_grant_n']/q2.at[0,'n_all'],1)}），用额 {int(q2.at[0,'off_used_n'])} 笔"
     f"（笔级使用率 {pct(q2.at[0,'off_used_n']/q2.at[0,'off_grant_n'],1)}）；发放计数 {int(q2.at[0,'off_grant_amt']):,} vs 用额 {int(q2.at[0,'off_used_amt']):,}"
     f"（金额比 {pct(q2.at[0,'off_use_rate_by_amt'],1)}，同一批次可被多笔复用，故偏低）；批次口径 S/G≈74.9%",
     '资金效率看批次口径，不看笔级金额比'),
    ('② 供给漏斗·在线',
     '在线以"发了不领"为主：弹窗发放额 903 万，真正领取并到账仅 364 万',
     f"发放 {int(q2.at[0,'on_grant_n'])} 笔（{pct(q2.at[0,'on_grant_n']/q2.at[0,'n_all'],1)}），领取 {int(q2.at[0,'on_claim_n'])} 笔"
     f"（笔级 {pct(q2.at[0,'on_claim_rate_by_n'],1)}），金额兑现 {pct(q2.at[0,'on_claim_rate_by_amt'],1)}",
     '提升领取率比继续扩额更划算'),
    ('③ 额度结构',
     '主额仍是绝对主体（按笔累加 2.89 亿），离线 1,599 万、在线 903 万；不同产品笔均可用差距 3~8 倍',
     '按产品表：D_1_03 笔均 当前/去产品上限/去单日上限 = 6,292/6,905/10,758；B_07_04 为 5,425/5,924/9,254',
     '产品维度差异大于策略维度，优先按产品调参'),
    ('④ 增信效果',
     '同评级内，临额组合同件均显著高于无临额组；离线增幅大于在线',
     'g7 件均 1,113→1,602(离线,+44%)/1,368(在线,+23%)；g8 886→1,159(+31%)/1,127(+27%)；'
     '临额占合同 离线 20~43%、在线 18~25%',
     '含客群选择效应，不能直接读作因果；需同评级内 DID 验证'),
    ('⑤ 上限约束',
     '撞顶 342 笔（0.52%），上限双抬到 5 万可多放 285 万比索（+3.0%）',
     'A 92 笔/85.2 万（纯主额顶格）、B 144 笔/140.8 万（主额+离线合计顶格）、C 106 笔/59.0 万（在线池外已突破）；'
     '周撞顶 29→71 笔、占比 0.39%→0.72%',
     'A+B 才是被 1 万真卡住的；C 属已突破，抬上限是继续放大'),
    ('⑥ 风险归因',
     '全样本临额组 1T0/4T7 均低于无临额；但分评级后：离线在高分段更优，在线在低分段明显更差',
     '全样本 1T0/4T7：none 28.6%/32.0%、offline 24.9%/30.2%、online 26.3%/31.2%；'
     'g3 在线 28.0% vs 无临额 21.2%；g8 离线 35.9% vs 无临额 39.7%',
     '临额本身不是坏账主因，低评级+在线才是；按评级矩阵收紧'),
    ('⑦ 策略维度',
     '同一 type 下 V5_3 坏账显著高于 V5_2，且 type2/3 渗透更高',
     'type2 4T7：V5_2 20.4% vs V5_3 30.2%；type3：26.3% vs 35.9%；type4（不发）35.3% vs 42.5%；'
     'V5_3 type3 弹窗 3,502 笔、领取 2,554 笔',
     '先收紧 V5_3 的 type2/type3，再动上限'),
    ('⑧ 资金效率',
     '离线额度越接近到期，使用率越低；8.3% 的笔完全没用掉',
     '余 4-5 天用 65.1%、余 3 天 51.7%、余 2 天 48.3%、余 1 天 42.0%、到期当日 38.1%；'
     f"完全未用 {int(q7.loc[q7['use_bucket'].str.startswith('B'),'n'].sum())} 笔、未用金额 915 万（笔级口径）",
     '有效期可考虑从 5 天缩短到 3 天，或到期前推送提醒'),
    ('⑨ 口径提示',
     '两处需要留意，避免误读',
     '① 110 笔（0.17%）有离线用额但无 5 天内发放记录（跨窗复用/记录缺失）；'
     '② 10-19 周仅 2,758 笔且离线批次未落完，1T0 未到期，周度趋势只看 08-31~09-28 周',
     '引用周度风险时剔除未成熟周'),
]
sum_df = pd.DataFrame(sum_rows, columns=['分析方向', '结论', '证据（表3口径）', '建议动作'])

from openpyxl import load_workbook
wb2 = load_workbook(XLSX)
ws0 = wb2.create_sheet('00_结论摘要', 0)
ws0.append(list(sum_df.columns))
for i in range(1, 5):
    c = ws0.cell(row=1, column=i)
    c.fill = head_fill; c.font = head_font
    c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
for row in sum_df.itertuples(index=False):
    ws0.append(list(row))
widths = [16, 52, 78, 34]
for i, wd in enumerate(widths, 1):
    ws0.column_dimensions[get_column_letter(i)].width = wd
for r in range(1, ws0.max_row + 1):
    for c in range(1, 5):
        cell = ws0.cell(row=r, column=c)
        cell.alignment = Alignment(vertical='top', wrap_text=True)
        cell.border = border
ws0.freeze_panes = 'A2'
wb2.save(XLSX)
print('摘要 sheet 已写入 ->', XLSX)

print('\n===== 关键数字 =====')
pd.set_option('display.width', 200, 'display.max_columns', 50)
print('\n[总量]', tot.to_string(index=False))
print('\n[场景]');  print(q1.to_string(index=False))
print('\n[漏斗]');  print(q2.to_string(index=False))
print('\n[撞顶]');  print(q5.to_string(index=False))
print('\n[风险]');  print(q6[['used_scenario','n','contract_amt','i1t0','i2t0','i3t0','i4t0','i4t7','n_47']].to_string(index=False))
print('\n[策略]');  print(q8[['strategy_version','use_type_1523','n','on_grant_n','on_claim_n','temp_share','i1t0','i4t7']].to_string(index=False))
print('\n[评级×场景 1T0]')
try:
    print(q6b.pivot_table(index='v6_1_grade', columns='used_scenario', values='i1t0', aggfunc='first').round(4).to_string())
    print('\n[评级×场景 4T7]')
    print(q6b.pivot_table(index='v6_1_grade', columns='used_scenario', values='i4t7', aggfunc='first').round(4).to_string())
    print('\n[评级×场景 笔数]')
    print(q6b.pivot_table(index='v6_1_grade', columns='used_scenario', values='n', aggfunc='sum').to_string())
except Exception as e:
    print('pivot 失败', e)
print('\n[按周撞顶]');  print(q5b.to_string(index=False))
print('\n[资金效率]');  print(q7.to_string(index=False))
print('\n[有效期]');    print(q7b.to_string(index=False))

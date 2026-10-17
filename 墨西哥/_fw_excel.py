# -*- coding: utf-8 -*-
"""组装《额度策略分析框架》Excel: 原始数据 + 派生分析(结构分解/DID) + 图表 + SQL依据"""
import pandas as pd
import numpy as np
import os, glob, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import LineChart, BarChart, Reference
import _fw_h as H

DATA = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_fw_data"
OUT = r"e:\岳松个人文件\嘉银工作内容的整理\01工作内容\墨西哥风险\额度策略分析框架_20261011.xlsx"

def load(name):
    p = os.path.join(DATA, name + ".csv")
    return pd.read_csv(p) if os.path.exists(p) else None

WEEKS = ['w0727','w0803','w0810','w0817','w0824','w0831','w0907','w0914','w0921','w0928','w1005']
WDATE = {'w0727':'2026-07-27','w0803':'2026-08-03','w0810':'2026-08-10','w0817':'2026-08-17',
         'w0824':'2026-08-24','w0831':'2026-08-31','w0907':'2026-09-07','w0914':'2026-09-14',
         'w0921':'2026-09-21','w0928':'2026-09-28','w1005':'2026-10-06'}

# ========== V5_2/V5_3 用信决策矩阵(决策表导出, 用户2026-10-11提供) ==========
SCORE_COLS = ['score≥5.0', '3≤score<5', '1≤score<3', '0≤score<1', 'score<0']
def _vec(mp, g):
    return mp.get(g, (4,4,4,4,4))
def _dnote(dv):
    lo = sum(1 for d in dv if d < 0); hi = sum(1 for d in dv if d > 0)
    if lo and hi: return f"放宽{lo}格/收紧{hi}格"
    if lo: return f"放宽{lo}格(型档变小)"
    if hi: return f"收紧{hi}格(型档变大)"
    return "不变"
mrows = []
mrows.append(['【V5_2 老策略】行=主评级charge_V5_2(1优~14差), 列=用信评分score_v1, 值=fd_use_creditamount_type(1优~4差)'] + ['']*7)
mrows.append(['V5_2', '评级档'] + SCORE_COLS + ['单元说明'])
for g in list(range(1, 14)) + ['≥14', 'null']:
    v = _vec(H.V52, g) if isinstance(g, int) else (4,4,4,4,4)
    mrows.append(['V5_2', str(g)] + list(v) + [''])
mrows.append(['【V5_3 新策略】行=主评级charge_V5_3, 列/值定义同上'] + ['']*7)
mrows.append(['V5_3', '评级档'] + SCORE_COLS + ['单元说明'])
for g in list(range(1, 14)) + ['≥14', 'null']:
    v = _vec(H.V53, g) if isinstance(g, int) else (4,4,4,4,4)
    mrows.append(['V5_3', str(g)] + list(v) + [''])
mrows.append(['【差异 Δ = V5_3 − V5_2】负值=放宽(进更优型档), 正值=收紧'] + ['']*7)
mrows.append(['Δ', '评级档'] + SCORE_COLS + ['单元变化'])
for g in list(range(1, 14)) + ['≥14', 'null']:
    v2 = _vec(H.V52, g) if isinstance(g, int) else (4,4,4,4,4)
    v3 = _vec(H.V53, g) if isinstance(g, int) else (4,4,4,4,4)
    dv = tuple(b - a for a, b in zip(v2, v3))
    mrows.append(['Δ', str(g)] + list(dv) + [_dnote(dv)])
for t in [
  "矩阵来源: 在线用信决策表导出(2026-10-11提供); DOUBLE-0/RESULT_DOUBLE-0是决策表变量类型注解(double/缺省0), 非业务取值",
  "型档含义: fd_use_creditamount_type 1~4, 1最优4最差; type4几乎不发放在线临额(E3实证tag1仅3笔), 仍可支用主额; 型档决定用信审批/临额策略",
  "结构性变化: V5_3把评级8级从全type4放开为2/3, 9-10级从全4放开为2/3/4; 6-7级高分段(score≥3)升入type1; 11级及以上/评级null仍全部type4",
  "实证校验(20表E5): 6个阶段×hash组单元矩阵预测命中率94.2-98.7%, 失配主要为score_v1为空(约1.5%, 矩阵无空分列)",
  "迁徙量化(21表E6): 41.1%放款由V5_2型4迁入V5_3型1-3(加权t0 29.08%), 主路径4→3(15.6k笔/t0 31.35%)、4→2(9.0k/25.96%); 留4→4 19.8k笔t0 42.07%为残留最差池",
  "单元风险(22表E7): V5_2下g8-10全部type4/tag1≈0; V5_3实走下g8 tag1 1293笔(t0 22-35%)、g9 351笔(27-38%)、g10 541笔(g10 s[0,1)达42.27%)为新放开高风险杠杆单元; g8内score≥3段t0 22-27% vs score<0段35%, 评分仍有排序力",
]:
    mrows.append(['说明', t] + ['']*6)
matrix_doc = pd.DataFrame(mrows, columns=['版本', '评级档'] + SCORE_COLS + ['单元说明'])

# ========== 派生: F 四组周度 ==========
fparts = [load(f"F1_grp_{w}") for w in WEEKS]
fparts = [x for x in fparts if x is not None and len(x)]
fall = pd.concat(fparts, ignore_index=True) if fparts else pd.DataFrame()

fwk, fdec, fgrade = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
if len(fall) and {'should_k','od_k'}.issubset(fall.columns):
    g = fall.groupby(['awk','tl_grp'], as_index=False).agg(
        loan_cnt=('loan_cnt','sum'), should_k=('should_k','sum'), od_k=('od_k','sum'),
        issue_sum_k=('issue_sum_k','sum'))
    tot = fall.groupby('awk', as_index=False).agg(t_cnt=('loan_cnt','sum'),
        t_should=('should_k','sum'), t_od=('od_k','sum'))
    g = g.merge(tot, on='awk')
    g['t0_rate'] = (g['od_k']/g['should_k']*100).round(2)
    g['overall_t0'] = (g['t_od']/g['t_should']*100).round(2)
    g['share_loan'] = (g['loan_cnt']/g['t_cnt']*100).round(1)
    g['share_should'] = (g['should_k']/g['t_should']*100).round(1)
    g['wdate'] = g['awk'].map(WDATE)
    wk_cnt = g.groupby('awk')['loan_cnt'].sum()
    # 覆盖率: 与funnel复贷周笔数对账, >=98%为完整周
    _b2 = load("B2_weekly_newold")
    _bench = dict(zip(_b2[_b2['is_reloan']=='old']['app_week'],
                      _b2[_b2['is_reloan']=='old']['loan_cnt'])) if _b2 is not None else {}
    def _cov(w):
        b = _bench.get(WDATE[w])
        return wk_cnt.get(w,0)/b if b else np.nan
    tsh = g.groupby('awk')['t_should'].first()
    def _covlab(w):
        if not tsh.get(w) or np.isnan(tsh.get(w)): return 'partial(t0未成熟)'
        c = _cov(w)
        if np.isnan(c): return 'partial(不足7天)'
        return 'full' if c >= 0.98 else 'partial(%d%%)' % round(c*100)
    g['coverage'] = g['awk'].map(_covlab)
    fwk = g[['wdate','awk','coverage','tl_grp','loan_cnt','share_loan','should_k','share_should',
             'od_k','t0_rate','overall_t0','issue_sum_k']].sort_values(['awk','tl_grp'])
    # 结构分解: 基准=最早完整周(yj快照8/14前缺失; 首个对账>=98%完整周为w0824)
    full_weeks = [w for w in WEEKS
                  if tsh.get(w) and not np.isnan(tsh.get(w))
                  and not np.isnan(_cov(w)) and _cov(w) >= 0.98]
    base = full_weeks[0] if full_weeks else WEEKS[0]
    rows = []
    grps = ['offline','online_tag1','online_tag0','none']
    for wk in full_weeks:
        d0 = fwk[(fwk['awk']==base)].set_index('tl_grp')
        d1 = fwk[fwk['awk']==wk].set_index('tl_grp')
        if len(d0) < 4 or len(d1) < 4: continue
        r0, w0 = d0['t0_rate']/100, d0['share_should']/100
        r1, w1 = d1['t0_rate']/100, d1['share_should']/100
        for grp in grps:
            rows.append({'wdate': WDATE[wk], 'awk': wk, 'tl_grp': grp,
                'rate_effect_pp': round((r1[grp]-r0[grp])*w0[grp]*100,2),
                'mix_effect_pp': round((w1[grp]-w0[grp])*r0[grp]*100,2),
                'interact_pp': round((r1[grp]-r0[grp])*(w1[grp]-w0[grp])*100,2),
                'total_contrib_pp': round(((r1[grp]*w1[grp]-r0[grp]*w0[grp])*100),2)})
    fdec = pd.DataFrame(rows)
    # 离线客群评级档周度
    fo = fall[fall['tl_grp']=='offline'].copy()
    fg = fo.groupby(['awk','grade_grp'], as_index=False).agg(
        loan_cnt=('loan_cnt','sum'), should_k=('should_k','sum'), od_k=('od_k','sum'))
    fg['t0_rate'] = (fg['od_k']/fg['should_k']*100).round(2)
    fg['wdate'] = fg['awk'].map(WDATE)
    fg['coverage'] = fg['awk'].map(_covlab)
    fgrade = fg[['wdate','awk','coverage','grade_grp','loan_cnt','should_k','od_k','t0_rate']].sort_values(['awk','grade_grp'])

# ========== 派生: DID ==========
def did_table(d, val='t0_rate'):
    if d is None: return pd.DataFrame()
    p = d.pivot_table(index='grp', columns='phase', values=val, aggfunc='first')
    p['P1->P2_pp'] = (p.get('P2_cutback')-p.get('P1_v53')).round(2)
    p['P1->P3_pp'] = (p.get('P3_v61')-p.get('P1_v53')).round(2)
    out = p.reset_index()
    extra = []
    if 'A_v52_always' in set(out['grp']) and 'B_switchback' in set(out['grp']):
        a = out.set_index('grp')
        extra.append({'grp':'DID_B-A(P1->P2)',
            'P1_v53': np.nan,'P2_cutback': np.nan,'P3_v61': np.nan,
            'P1->P2_pp': round(a.loc['B_switchback','P1->P2_pp']-a.loc['A_v52_always','P1->P2_pp'],2),
            'P1->P3_pp': round(a.loc['B_switchback','P1->P3_pp']-a.loc['A_v52_always','P1->P3_pp'],2)})
        extra.append({'grp':'DID_C-A(P1->P2)',
            'P1_v53': np.nan,'P2_cutback': np.nan,'P3_v61': np.nan,
            'P1->P2_pp': round(a.loc['C_v53_always','P1->P2_pp']-a.loc['A_v52_always','P1->P2_pp'],2),
            'P1->P3_pp': round(a.loc['C_v53_always','P1->P3_pp']-a.loc['A_v52_always','P1->P3_pp'],2)})
    return pd.concat([out, pd.DataFrame(extra)], ignore_index=True)

d3did = did_table(load("D3_hash_did_all"))
d4did = did_table(load("D4_hash_did_tag1"))

# ========== C1 近期批次 ==========
c1 = load("C1_offline_batch")
c1r = pd.DataFrame()
if c1 is not None:
    c1r = c1[c1['issue_to'] >= '2026-07-01'].sort_values('issue_to')

# ========== 摘要页 ==========
readme = pd.DataFrame({
 "项": ["框架","数据窗口","坏账口径","TR口径","额度使用率口径","通过率口径","临额打标","在线策略阶段","V5_2/V5_3决策矩阵","离线政策证据","DID设计","成熟度","数据校验","脚本"],
 "说明": [
  "7模块: ①额度供给 ②额度使用率+TR盈利 ③在线V5_2/V5_3策略 ④离线准入政策 ⑤风险分层 ⑥客群质量 ⑦性价比+DID因果",
  "进件/放款 2026-07 ~ 2026-10-05; 主表 funnel(全量大盘) + yj_test_table(复贷策略/临额字段) + 离线底表 + change_record",
  "1t0_amt(总额坏账)=t0_overdue_amount_1/t0_should_amt_1含息费; 1t0_capit(本金坏账)=t0_overdue_capit_1/t0_should_capit_1; 1t7息费坏账=t7_overdue_interest_4/t7_should_amt_4",
  "TR=息费率−1T7本金坏账−1T7息费坏账; 息费率=(should_interest后收利息+haircut_amount砍头息)/contract_amount(口径同墨西哥周报); 1T7需4期账龄: 7月成熟、8月部分成熟、9月未成熟仅参考",
  "额度使用率=放款金额/授信额度(util_rate, 此前误称TR已改名); 复贷27-46%分客群, 首贷76-83%批后即借满不可比",
  "通过率=放款笔数/进件笔数; 首贷8.5-9.3%, 复贷60-65%",
  "放款前最近一条limit_type=TEMP事件: C010=在线(再按issue_tag分tag1/tag0), C013/C015=offline, 无=none",
  "P0<8/10; P1 8/10-9/3 V5_3灰度70%; P2 9/3-9/22 切回30%; P3>=9/22 V6_1拒尾+转产线; hash A/B/C三组自然实验",
  "决策表(19表): 行=主评级android_oldCust_mainCreditLevel_charge_V5_2/V5_3(1优~14差), 列=用信评分fd_use_creditamount_score_v1(≥5/3-5/1-3/0-1/<0), 值=fd_use_creditamount_type(1优~4差); E5实证命中率94-99%; V5_3结构性放开g8-10",
  "底表temp_limit_tag批次: 8月有在贷批次近30天1-2天逾期占7-12%, 8/29(0909批次)起归零; 无在贷9/9(0910批次)起归零; 部分标签字段曾被删待回补, 回补后重跑_fw_c.py即可",
  "A=hash>0.7始终V5_2; B=0.3-0.7(P1执行V5_3,P2切回); C<=0.3始终V5_3; DID=ΔB-ΔA / ΔC-ΔA",
  "t0: w0928(9/28-10/4)及之前已成熟; w1005(10/6-9)t0未成熟, 仅看笔数/渗透; t30/1T7: 9月放款未走完, 空白=未成熟, 不可外推",
  "yj_test_table 2026-10-10 05:42快照窗口8/14-10/09(76841行): 8/14-18部分覆盖(34->549/日), 8/19起完整; w0727/w0803缺失, w0810覆盖7%, w0817覆盖92%(周一二缺数), w0824-w0928与funnel周笔数偏差<2%为完整周; 全量大盘趋势用funnel不受影响",
  "_fw_h(决策矩阵校验/type迁徙/单元风险) _fw_b2(B1/A1新口径) _fw_b(大盘) _fw_g/_fw_g3(A/D/F) _fw_e(E1-E4交叉表) _fw_c(C1离线批次) _fw_lc(任务C损失率三因子) _fw_bz(任务B复现同事) mexico_presto.py(连接)"]
})

# ========== SQL 依据 (从已执行脚本提取, 保证与取数一致) ==========
import re
def extract_sql(path):
    txt = open(path, encoding='utf-8').read()
    pat = re.compile(r'q\(\s*f?"""(.*?)"""\s*,\s*f?"([A-Za-z0-9_]+)(?:_\{[a-zA-Z]+\})?"', re.S)
    return {name: sql.strip() for sql, name in pat.findall(txt)}

sql_map = {}
for f in ["_fw_b2.py","_fw_b.py","_fw_c.py","_fw_g.py","_fw_g3.py","_fw_e.py","_fw_bz.py"]:
    p = os.path.join(r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥", f)
    if os.path.exists(p):
        for k, v in extract_sql(p).items():
            sql_map.setdefault(k, (f, v))
# H系列SQL在_fw_h中是已完整展开的模块常量(无宏)
for _k, _v in [("E5_matrix_validate", H.E5_SQL), ("E5b_mismatch", H.E5B_SQL),
               ("E6_type_migration", H.E6_SQL), ("E7_cell_risk", H.E7_SQL)]:
    sql_map.setdefault(_k, ("_fw_h.py", _v.strip()))

# B系列/C系列脚本用变量拼接SQL(正则无法直接抽取), 此处给出完整可复跑字面量
_B1_SQL = """
select
  cast(android_oldcust_maincreditlevel_charge_v5_3 as integer) as grade,
  cast(temp_credit_amount_issue_tag as integer) as issue_tag,
  temp_credit_amount_strategy_test_flag as strategy_flag,
  app_month,
  if(app_date >= date'2026-08-11',1,0) as if_0811,
  if(temp_grant_amount>0,1,0) as if_used_templimit,
  count(*) as biz_cnt, count(distinct mid) as mid_cnt,
  round(sum(if(if_in_sx=1,credit_amount,null)),1) as credit_amount,
  round(sum(contract_amount),1) as contract_amount,
  round(sum(if(t0_should_amt_1>0,t0_overdue_amount_1,null))/nullif(sum(if(t0_should_amt_1>0,t0_should_amt_1,null)),0)*100,4) as t1d0_amt,
  round(sum(if(t3_should_amt_1>0,t3_overdue_amount_1,null))/nullif(sum(if(t3_should_amt_1>0,t3_should_amt_1,null)),0)*100,4) as t1d3_amt,
  round(sum(if(t3_should_amt_2>0,t3_overdue_amount_2,null))/nullif(sum(if(t3_should_amt_2>0,t3_should_amt_2,null)),0)*100,4) as t2d3_amt,
  round(sum(if(t3_should_amt_3>0,t3_overdue_amount_3,null))/nullif(sum(if(t3_should_amt_3>0,t3_should_amt_3,null)),0)*100,4) as t3d3_amt
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1
  and app_date >= date'2026-08-19' and app_date < date'2026-10-06'
group by 1,2,3,4,5,6
"""
sql_map.setdefault("B1_rawdata_repro", ("_fw_bz.py", _B1_SQL.strip()))

_C_BASE = """
with b as (
  select biz_id,
    cast(temp_credit_amount_issue_tag as integer) as issue_tag,
    if(temp_grant_amount>0,1,0) as used,
    case when android_oldcust_maincreditlevel_charge_v5_3 <= 5 then 'head_1_5'
         when android_oldcust_maincreditlevel_charge_v5_3 >= 6 then 'tail_6_13' else 'na' end as ht,
    if(if_in_sx=1, credit_amount, null) as credit_amount,
    contract_amount,
    if(t3_should_amt_1>0 and t3_overdue_amount_1>0,1,0) as bad3,
    if(t0_should_amt_1>0 and t0_overdue_amount_1>0,1,0) as bad0
  from mx.yj_test_table_250225
  where is_reloan='old' and if_issue=1
    and app_date >= date'2026-08-19' and app_date < date'2026-10-06'
)
"""
_C_FAC = """count(*) as n_all, sum({bad}) as n_bad,
  round(sum({bad})*100.0/count(*),2) as F1_hushu_pct,
  round(sum(if({bad}=1,credit_amount,null))/nullif(sum({bad}),0),0) as avg_credit_bad,
  round(sum(credit_amount)/nullif(count(credit_amount),0),0) as avg_credit_all,
  round((sum(if({bad}=1,credit_amount,null))/nullif(sum({bad}),0))/(sum(credit_amount)/nullif(count(credit_amount),0)),4) as F2_limitctrl,
  round(sum(if({bad}=1,contract_amount,0))/nullif(sum(if({bad}=1,credit_amount,null)),0),4) as ur_bad,
  round(sum(contract_amount)/nullif(sum(credit_amount),0),4) as ur_all,
  round((sum(if({bad}=1,contract_amount,0))/nullif(sum(if({bad}=1,credit_amount,null)),0))/(sum(contract_amount)/nullif(sum(credit_amount),0)),4) as F3_usage,
  round(sum(if({bad}=1,contract_amount,0))/nullif(sum(contract_amount),0),4) as loss_direct"""
sql_map.setdefault("C1_loss_issue_used", ("_fw_lc.py", _C_BASE + "\nselect issue_tag, used,\n  " + _C_FAC.format(bad='bad3') + "\nfrom b group by 1,2 order by 1,2"))
sql_map.setdefault("C2_loss_headtail", ("_fw_lc.py", _C_BASE + "\nselect ht, issue_tag, used,\n  " + _C_FAC.format(bad='bad3') + "\nfrom b group by 1,2,3 order by 1,2,3"))
sql_map.setdefault("C3_loss_1t0", ("_fw_lc.py", _C_BASE + "\nselect issue_tag, used,\n  " + _C_FAC.format(bad='bad0') + "\nfrom b group by 1,2 order by 1,2"))

# 宏展开: 把脚本中的SQL宏替换为完整字面量, 保证15表SQL可直接复跑
L_HASH = "from_base(substr(to_hex(sha256(to_utf8('20260811'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000"
L_GRP = ("case when " + L_HASH + " > 0.7 then 'A_v52_always'\n"
         "       when " + L_HASH + " > 0.3 then 'B_switchback'\n"
         "       else 'C_v53_always' end")
L_PHASE = ("case when date(app_time) < date'2026-08-10' then 'P0_pre'\n"
           "       when date(app_time) < date'2026-09-03' then 'P1_v53'\n"
           "       when date(app_time) < date'2026-09-22' then 'P2_cutback'\n"
           "       else 'P3_v61' end")
L_GRADE = ("case when cast(fd_creditlevel_main_v4_2 as double) >= 9 then 'g9p'\n"
           "       when cast(fd_creditlevel_main_v4_2 as double) >= 6 then 'g6_8'\n"
           "       when cast(fd_creditlevel_main_v4_2 as double) >= 1 then 'g1_5'\n"
           "       else 'g_null' end")
L_T0 = "sum(if(t0_should_amt_1>0,t0_overdue_amount_1,null))/nullif(sum(if(t0_should_amt_1>0,t0_should_amt_1,null)),0)*100"
L_T0Y = "sum(if(y.t0_should_amt_1>0,y.t0_overdue_amount_1,null))/nullif(sum(if(y.t0_should_amt_1>0,y.t0_should_amt_1,null)),0)*100"
L_T3 = "sum(if(t3_should_amt_1>0,t3_overdue_amount_1,null))/nullif(sum(if(t3_should_amt_1>0,t3_should_amt_1,null)),0)*100"
def expand_sql(sqltext, week_example=False):
    out = sqltext
    for k, v in [("{GRP}", L_GRP), ("{HASH}", L_HASH), ("{PHASE}", L_PHASE),
                 ("{GRADE}", L_GRADE), ("{T0Y}", L_T0Y), ("{T0}", L_T0), ("{T3}", L_T3)]:
        out = out.replace(k, v)
    if week_example:
        out = ("-- {w0}/{w1}/{wn}为逐周参数, 下例以w0914(9/15-9/22)为准, 其余周仅改3个日期:\n"
               "-- w0727=07-27/08-04, w0803=08-04/08-11, w0810=08-11/08-18, w0817=08-18/08-25, w0824=08-25/09-01,\n"
               "-- w0831=09-01/09-08, w0907=09-08/09-15, w0914=09-15/09-22, w0921=09-22/09-29, w0928=09-29/10-06, w1005=10-06/10-10\n" + out
               ).replace("{w0}", "2026-09-15").replace("{w1}", "2026-09-22").replace("{wn}", "w0914")
    return out

MOD = {
 "B1_monthly_newold": ("模块1/2/7 大盘月度", "mx.wxs_application_funnel", "进件月×首复贷 供给/额度使用率/利息占比/砍头占比/息费率/1t0本金&总额/1t7本金&息费/TR/t30"),
 "B2_weekly_newold": ("模块5 大盘周度", "mx.wxs_application_funnel", "进件周×首复贷 t0/t7/t30"),
 "A1_online_monthly": ("模块1-3 在线月度", "mx.yj_test_table_250225", "在线临额tag1渗透/使用/放款总额/月度t0"),
 "A2_online_phase_flag": ("模块3 在线四阶段", "mx.yj_test_table_250225", "P0-P3×V5_2/V5_3×tag0/tag1"),
 "A3_score_dist": ("模块5 用信评分", "mx.yj_test_table_250225", "fd_use_creditamount score×type"),
 "D1_grade_flag_tag": ("模块5 评级反事实", "mx.yj_test_table_250225", "阶段×评级档×策略×tag"),
 "D2_quality_monthly": ("模块6 客群质量", "mx.yj_test_table_250225", "评级/多头/周期/循环过期月度"),
 "D3_hash_did_all": ("模块7 DID全客户", "mx.yj_test_table_250225", "hash三组×阶段 全客户"),
 "D4_hash_did_tag1": ("模块7 DID_tag1", "mx.yj_test_table_250225", "hash三组×阶段 临额客群"),
 "F1_grp": ("模块3-5 四组打标", "yj join s05_user_creditlimit_change_record", "逐周 offline/online_tag1/tag0/none×评级"),
 "E1_score_grp": ("模块5 评分×四组", "mx.yj_test_table_250225", "score_v1 × tl_grp t0/件均/评级/多头"),
 "E2_score_phase": ("模块5 评分×阶段", "mx.yj_test_table_250225", "score_v1 × P0-P3 分布/t0/临额使用"),
 "E3_type_tempuse": ("模块5 type×临额使用", "mx.yj_test_table_250225", "use_type 1-4 × tag1/tag0 × used/not_used"),
 "E4_score_drift": ("模块5 评分分布漂移", "mx.yj_test_table_250225", "score_v1 × 月 占比/t0/临额漂移"),
 "E5_matrix_validate": ("模块3 决策矩阵校验", "mx.yj_test_table_250225", "阶段×hash组 V5_2/V5_3矩阵预测type命中率"),
 "E5b_mismatch": ("模块3 矩阵失配明细", "mx.yj_test_table_250225", "评级×score档 预测type≠实际type明细"),
 "E6_type_migration": ("模块3 type迁徙反事实", "mx.yj_test_table_250225", "双矩阵客户级type_v52×type_v53迁徙/t0/临额"),
 "E7_cell_risk": ("模块3 矩阵单元风险", "mx.yj_test_table_250225", "C实走V5_3/A实走V5_2 评级×score单元t0/tag1"),
 "C1_offline_batch": ("模块4 离线批次", "mx.yuhan_temp_limit_base_table_his_20260924", "temp_limit_tag批次 准入/评级/金额"),
 "C1_loss_issue_used": ("任务C 损失率三因子", "mx.yj_test_table_250225", "账户biz_id级: 发放临额issue_tag×使用used → F1户数损失率/F2限额控制比/F3额度使用率因子 (坏=1T3)"),
 "C2_loss_headtail": ("任务C 损失率三因子", "mx.yj_test_table_250225", "头1-5/中尾6-13 × 发放×使用 → 三因子 (坏=1T3)"),
 "C3_loss_1t0": ("任务C 损失率三因子", "mx.yj_test_table_250225", "1T0口径对照: 发放临额×使用临额 → 三因子"),
 "B1_rawdata_repro": ("任务B 复现同事", "mx.yj_test_table_250225", "评级v5_3×发放×策略×放款月×if0811×使用 → vintage t1d0$/t1d3$/t2d3$/t3d3$"),
 "B2_by_issue_used": ("任务B 复现同事", "mx.yj_test_table_250225", "评级×发放临额×使用临额 → t1d3$/t2d3$"),
 "B3_headtail": ("任务B 复现同事", "mx.yj_test_table_250225", "头/中尾×发放×使用 → t1d3$ (复现同事by是否发放临额)"),
}
sql_rows = []
for key in ["B1_monthly_newold","B2_weekly_newold","A1_online_monthly","A2_online_phase_flag",
            "A3_score_dist","D1_grade_flag_tag","D2_quality_monthly","D3_hash_did_all","D4_hash_did_tag1",
            "F1_grp","E1_score_grp","E2_score_phase","E3_type_tempuse","E4_score_drift",
            "E5_matrix_validate","E5b_mismatch","E6_type_migration","E7_cell_risk","C1_offline_batch",
            "C1_loss_issue_used","C2_loss_headtail","C3_loss_1t0",
            "B1_rawdata_repro","B2_by_issue_used","B3_headtail"]:
    mod, tbl, desc = MOD[key]
    fn, sqltext = sql_map.get(key, ("", ""))
    if key in ("D3_hash_did_all","D4_hash_did_tag1","A2_online_phase_flag","D1_grade_flag_tag","F1_grp"):
        pre = ("-- 宏已展开为完整SQL; 分组: A=HASH>0.7始终V5_2, B=0.3-0.7切回组(P1执行V5_3/P2切回), C<=0.3始终V5_3\n")
        sqltext = pre + expand_sql(sqltext, week_example=(key=="F1_grp"))
    sql_rows.append({"模块": mod, "输出": key, "说明": desc, "数据源": tbl, "脚本": fn, "SQL": sqltext})
sql_doc = pd.DataFrame(sql_rows)

# ========== 写 Excel ==========
sheets = []
def add(name, df):
    sheets.append((name, df))

# ========== 单位折算: temp_grant_amount/1000=比索(已使用临额, 点弹窗才>0) ==========
# CSV中 avg列已是比索; sum列(raw/1000)是比索总额, /1000 折成千比索
a1 = load("A1_online_monthly")
if a1 is not None:
    a1 = a1.rename(columns={'temp_use_avg_k':'temp_use_avg_p','temp_use_sum_k':'temp_use_sum_k'})
    a1['temp_use_sum_k'] = (a1['temp_use_sum_k']/1000).round(0)
    if 'issue_sum_k' in a1.columns:
        a1['temp_share_issue_pct'] = (a1['temp_use_sum_k']/a1['issue_sum_k']*100).round(1)
a2 = load("A2_online_phase_flag")
if a2 is not None:
    a2 = a2.rename(columns={'temp_use_avg_k':'temp_use_avg_p','temp_use_sum_k':'temp_use_sum_k'})
    a2['temp_use_sum_k'] = (a2['temp_use_sum_k']/1000).round(0)
a3 = load("A3_score_dist")
if a3 is not None:
    a3 = a3.rename(columns={'temp_sum_k':'temp_use_k'})
    a3['temp_use_k'] = (a3['temp_use_k']/1000).round(0)
d1 = load("D1_grade_flag_tag")
if d1 is not None:
    d1 = d1.rename(columns={'temp_sum_k':'temp_use_k'})
    d1['temp_use_k'] = (d1['temp_use_k']/1000).round(0)
d4 = load("D4_hash_did_tag1")
if d4 is not None:
    d4 = d4.rename(columns={'temp_sum_k':'temp_use_k'})
    d4['temp_use_k'] = (d4['temp_use_k']/1000).round(0)
# E5-E7: 决策矩阵校验/type迁徙/单元风险; E2/E4/E6的sum(temp_grant_amount/1000)输出为比索, 再/1000折千比索
e2 = load("E2_score_phase")
if e2 is not None and 'temp_use_k' in e2.columns:
    e2['temp_use_k'] = (e2['temp_use_k']/1000).round(1)
e4 = load("E4_score_drift")
if e4 is not None and 'temp_use_k' in e4.columns:
    e4['temp_use_k'] = (e4['temp_use_k']/1000).round(1)
e5 = load("E5_matrix_validate")
e5b = load("E5b_mismatch")
e6 = load("E6_type_migration")
if e6 is not None:
    e6[["type_v52", "type_v53"]] = e6[["type_v52", "type_v53"]].astype('Int64')
    e6['temp_use_k'] = (e6['temp_use_k']/1000).round(1)
e7 = load("E7_cell_risk")
if e7 is not None:
    e7['pred'] = e7['pred'].astype('Int64')

# ========== C系列: 循环贷损失率三因子拆解 (损失率=F1户数损失率×F2限额控制比×F3额度使用率因子) ==========
c1l = load("C1_loss_issue_used"); c2l = load("C2_loss_headtail"); c3l = load("C3_loss_1t0")
# ========== B系列: 复现同事《临额风险影响分析20260909》 ==========
b1r = load("B1_rawdata_repro"); b2r = load("B2_by_issue_used"); b3r = load("B3_headtail")

C_COLS = ['口径','组别','账户数','坏账户数','F1户数损失率%','平均账户限额','平均坏账限额',
          'F2限额控制比','平均额度使用率','坏账额度使用率','F3额度使用率因子','损失率=三因子%','损失率=直接口径%']
def _issue_lab(it):
    if pd.isna(it): return "无在线tag(离线)"
    return "发放" if int(it) == 1 else "未发放"
def _used_lab(u):
    return "使用" if int(u) == 1 else "未使用"
def _c_rows(df, title, use_ht=False):
    rows = [{'口径': title}]
    if df is None or not len(df): return rows
    for _, r in df.iterrows():
        grp = _issue_lab(r['issue_tag']) + "-" + _used_lab(r['used'])
        if use_ht: grp = str(r['ht']) + '|' + grp
        rows.append({'口径':'', '组别':grp, '账户数':int(r['n_all']), '坏账户数':int(r['n_bad']),
            'F1户数损失率%':float(r['F1_hushu_pct']), '平均账户限额':float(r['avg_credit_all']),
            '平均坏账限额':float(r['avg_credit_bad']), 'F2限额控制比':float(r['F2_limitctrl']),
            '平均额度使用率':float(r['ur_all']), '坏账额度使用率':float(r['ur_bad']),
            'F3额度使用率因子':float(r['F3_usage']), '损失率=三因子%':round(float(r['loss_rate_3factor']), 2),
            '损失率=直接口径%':round(float(r['loss_direct'])*100, 2)})
    return rows

c_rows = [{'口径':'【公式】循环贷损失率 = 户数损失率F1 × 限额控制比F2 × 额度使用率因子F3'},
          {'口径':'   F1=坏账户数/总账户数(准入模型筛人); F2=平均坏账限额/平均账户限额(临时额度最大影响项); F3=坏账额度使用率/平均额度使用率(坏人敢借满)'},
          {'口径':'【样本】账户=biz_id, 复贷放款2026-08-19~10-06; 限额=授信额度credit_amount; 金额$含息费; 坏=该窗口逾期金额>0'},
          {'口径':'【校验】三因子%与直接口径%理论恒等; 有差异的行=部分账户credit_amount为空(主要为无在线授信额度记录、仅走离线临额的"使用"客群), 使F2/F3的均值分母基准不一致; 不影响对照组间横向对比'},
          {'口径':'【对照组1】发放临额: temp_credit_amount_issue_tag; 使用临额: temp_grant_amount>0(点弹窗使用才>0); 无在线tag=离线临额客群'}]
c_rows += _c_rows(c1l, '【表24-1】发放临额 × 使用临额 (坏=1T3 window1, 全样本)', False)
c_rows += _c_rows(c2l, '【表24-2】头(评级1-5) / 中尾(6-13) × 发放×使用 (坏=1T3)', True)
c_rows += _c_rows(c3l, '【表24-3】1T0口径对照 (坏=1T0 window1)', False)
c_doc = pd.DataFrame(c_rows, columns=C_COLS).fillna('')

# 25表: by是否发放临额(复现同事)
B25_COLS = ['分组','是否发放临额','是否使用临额','账户数','合同额','授信额','t1d3坏账率$','t2d3坏账率$']
b25_rows = [{'分组':'【表25-1】头/中尾 × 发放临额 × 使用临额 (复现同事"by是否发放临额"; 风险=t1d3$金额口径, 窗口08-19~10-06)'}]
if b3r is not None:
    for _, r in b3r.iterrows():
        b25_rows.append({'分组':str(r['grp_head']), '是否发放临额':_issue_lab(r['issue_tag']),
            '是否使用临额':_used_lab(r['if_used_templimit']), '账户数':int(r['biz_cnt']),
            '合同额':float(r['contract_amount']), 't1d3坏账率$':float(r['t1d3_amt'])})
b25_rows.append({'分组':'【表25-2】评级v5_3(1优~13差) × 发放 × 使用 (复现同事"rawdata"汇总; t1d3$/t2d3$)'})
if b2r is not None:
    for _, r in b2r.iterrows():
        b25_rows.append({'分组':'评级%s' % int(r['grade']) if pd.notna(r['grade']) else '评级NA',
            '是否发放临额':_issue_lab(r['issue_tag']), '是否使用临额':_used_lab(r['if_used_templimit']),
            '账户数':int(r['biz_cnt']), '合同额':float(r['contract_amount']), '授信额':float(r['credit_amount']),
            't1d3坏账率$':float(r['t1d3_amt']), 't2d3坏账率$':float(r['t2d3_amt'])})
b25_doc = pd.DataFrame(b25_rows, columns=B25_COLS).fillna('')

# 26表: rawdata明细(B1)
b26 = pd.DataFrame()
if b1r is not None:
    b26 = b1r.rename(columns={'grade':'评级v5_3','issue_tag':'是否发放临额','strategy_flag':'策略版本',
        'app_month':'放款月','if_0811':'是否8/11后','if_used_templimit':'是否使用临额','biz_cnt':'账户数','mid_cnt':'客户数',
        'credit_amount':'授信额','contract_amount':'合同额','t1d0_amt':'t1d0坏账率$','t1d3_amt':'t1d3坏账率$',
        't2d3_amt':'t2d3坏账率$','t3d3_amt':'t3d3坏账率$'}).copy()
    b26['是否发放临额'] = b26['是否发放临额'].map(lambda x: _issue_lab(x))
    b26['是否使用临额'] = b26['是否使用临额'].map(lambda x: _used_lab(x))

# ========== B1 列名规范化 (1t0/1t7 口径命名) ==========
b1 = load("B1_monthly_newold")
if b1 is not None:
    b1 = b1.rename(columns={
        'mth':'放款月','is_reloan':'首复贷','app_cnt':'进件','loan_cnt':'放款',
        'pass_rate':'通过率%','credit_avg':'件均授信','issue_avg':'件均放款',
        'issue_sum_k':'放款总额k','credit_sum_k':'授信总额k',
        'util_rate':'额度使用率%','int_rate':'利息占比%(后收/合同)','haircut_rate':'砍头占比%',
        'fee_rate':'息费率%(含砍头)','t0_capit_rate':'1t0_capit本金坏账%','t0_amt_rate':'1t0_amt总额坏账%',
        't7_capit_rate':'1t7_capit本金坏账%','t7_int_rate':'1t7息费坏账%','tr_rate':'TR%',
        't30_rate':'1t30总额坏账%','t30_capit_rate':'1t30_capit本金坏账%',
        'fact_interest_k':'实收利息k','contract_sum_k':'合同总额k'})

# ========== 核心结论 ==========
concl = pd.DataFrame({"模块": [
 "①额度供给","②额度使用率+TR盈利","③在线V5_3扩额下沉","③在线切回P2效果","③分档反事实","③决策矩阵校验","③type迁徙反事实","③新放开单元风险",
 "④离线准入收紧","⑤风险分层","⑤用信评分说明","⑤E1评分x四组","⑤E2评分x阶段","⑤E3_type x临额使用","⑤E4评分分布漂移","⑥客群质量","⑦DID全客户","⑦DID临额桶","⑦结构分解","⑦V6_1拒尾",
 "任务C 损失率三因子","任务C 临额放大机制","任务B 复现同事","任务B rawdata明细",
 "建议1","建议2","建议3","建议4","建议5","建议6","局限"] ,
 "结论与数据依据": [
  "复贷授信总额 7/8/9月=156.4/143.9/163.9百万、放款总额(实放)=51.6/49.0/51.9百万比索(01表); 在线临额实际使用额: 9月4.66百万(占复贷放款额9.0%)、8/14-31窗口2.81百万(占同期放款12.3%, 8月全月因yj快照缺失不可算), 使用者件均589/571比索(03表)",
  "额度使用率(=放款/授信, 此前误称TR已改名): 复贷33.0%/34.1%/31.7%, 首贷76-83%批后即借满不可比; TR=息费率−1T7本金坏账−1T7息费坏账: 复贷7月50.44%(成熟)、8月45.69%(部分成熟)、9月45.00%(未成熟仅参考); 砍头占比复贷5.9-8.9%、首贷8.5-13.9%; 复贷通过率65.2/62.1/60.7%持续下降(01表)",
  "V5_3把临额发给更低评级客群: P1 tag1评级 V5_3=5.01 vs V5_2=3.43; t0 26.41% vs 19.35%; 件均1521 vs 1842(04表)",
  "9/3切回30%后(P2): V5_3 tag1 t0 27.95%(且g9p档升至44.66%), V5_2 tag1仅18.00%; 渗透=放款笔数中发放在线临额(tag1)的占比: 8月30.6%->9月23.9%; tag1客群临额使用率(实际点用/tag1)92.1%->87.4%(03/04表)",
  "P1 V5_3 tag1下沉至g6_8 942笔(t0 32.98%)、g9p 749笔(t0 33.20%); V5_2 tag1集中g1_5 949笔(t0 19.39%), g6_8仅110、g9p仅32(05表)。差距原因=策略设计本身: V5_3目标就是扩额下沉(调低临额审批门槛), V5_2只对优质客群开放; 同评级对照: V5_3的g6_8 tag1 t0 32.98%仍低于同档未发临额的tag0 37.94%, 即模型在下沉客群内仍挑到了相对好的客户",
  "决策矩阵实证(19表矩阵+20表E5): 用决策表(评级charge档×score_v1档→type1-4)逐笔回放, 6个阶段×hash组预测命中率94.2-98.7%(P1/A 98.5%、P1/C 98.2%、P2各组98.1-98.7%, P1/B 94.2%最低); 失配几乎全为score_v1为空(矩阵无空分列, 约1.5%)与零星单笔边界, 证明矩阵即生产真实逻辑, 可用于反事实",
  "客户级type迁徙(21表E6, 8/19-10/05, 6.15万笔): 41.1%(25261笔)在V5_2下为type4、V5_3下升入type1-3=新放开客群, 加权t0 29.08%, 新增加临额使用约2.98百万比索; 主路径4→3 15.6k笔(t0 31.35%)、4→2 9.0k(25.96%)、4→1 0.7k(18.68%), 另3→2 5.5k(21.76%)、2→1 4.1k(15.47%); 留在4→4 19.8k笔t0 42.07%为残留最差池; 升级(档变小)35.7k笔加权t0 26.0%, 降级仅103笔40.3%",
  "新放开单元风险(22表E7): V5_2矩阵下评级8-10全部type4(tag1≈0不发在线临额), V5_3实走(C组)下g8 tag1 1293笔(t0 22.4-35.1%)、g9 351笔(27.7-38.0%)、g10 541笔(s[0,1)单元t0 42.27%/343笔)——高评级档加临额杠杆是V5_3坏账抬升的直接来源; 但g8内score≥3段t0 22-27%显著低于score<0段35%, 评分在下沉档内仍有排序力, 可用score收紧g9-10而非全档关闭",
  "离线底表批次: 8月宽松批近30天1-2天逾期占5.5-11.1%; 有在贷0909批次(8/29发放)起pct_ovd1_2=0、无在贷0910批次(9/9)起=0(11表); offline组周度t0 20-26%为四组最低, 但其中g9p档35-45%(10表)",
  "评级g9p档全组t0 38-47%; 用信评分-2段use_type=4为最大高风险池(9月14328笔, t0 36.44%), 5分段t0 9-17%(13/14表)",
  "fd_use_creditamount_score_v1=1523模型'用信环节评分'(-4~5, 实证越高越优: 5段t0 9-17%、-2段30-39%); fd_use_creditamount_type=1523输出分类1~4(实证type1件均4.4-4.7k且t0 12-20%最优, type4件均最低且t0 30-39%最差); 可继续细化: 评分×四组/×阶段迁徙、type×临额使用交叉、评分分布漂移监控",
  "⑤交叉表E1评分×四组: 同评分内none组坏账最高(-2分38.5%/0分34.9%), 临额组(offline/tag0/tag1)比none低约10pp, 说明临额政策在各评分段内均筛到了相对好客户; 低分段(0/-2分)多头ovd_cnt在none组高达1.6-1.8(15表)",
  "⑤交叉表E2评分×阶段: -2分占比P1 46.8%→P2 48.4%→P3 49.0%缓慢上升(客群结构向低分漂移), 但-2分t0 32.67→32.02→27.94、0分25.73→27.07→22.47普遍在P3(V6_1)下降, 即V6_1拒尾在各评分段都有效(16表)",
  "⑤交叉表E3 type×临额使用: type1-3发临额后t0上升(+4~+9pp, 杠杆放大风险), type4(最大高风险池)发临额后t0反降(34.6→30.9, 件均884→1463, 模型在type4内挑了相对好客户); type4 tag1仅3笔无统计意义(17表)",
  "⑤交叉表E4评分分布漂移(月): -2分占比8月46.5%→9月48.5%(高分段占比下降, 客群评分结构劣化); 5分t0 12.07→14.84上升、-2分32.21→30.98下降, 需持续监控评分分布与各段t0双向漂移(18表)",
  "9月评级结构略改善(g1_5占比51.8->52.5%, g9p 28.7->27.0%), 但外部多头curr_ovd_cnt_all(客户在各借款平台的当前逾期笔数合计, 共债预警变量, 非评分)均值0.319->0.384、当前逾期占比13.2->14.0%恶化(12表)",
  "全客户DID B-A(P1->P2)=+0.10pp≈0: 切回对大盘无因果改善; C-A(P1->P2)=+1.04pp(P1差1.85pp), 始终V5_3比始终V5_2高1-2pp(06表)",
  "tag1桶DID B-A(P1->P2)=-2.68pp, 但同期B桶tag1评级均值4.89->3.48(选择效应), P3 B=3.56/A=3.68时t0 14.37 vs 18.99, 提示切回后新发临额客群质量真实改善(07表)",
  "w0824->w0914大盘t0 28.40->28.32%基本持平: none组应还份额14.2->21.2%贡献结构效应+2.73pp, 抵消online_tag1收缩的合计-1.85pp(率-1.08+结构-0.93+交叉0.16); 即砍临额把高风险长尾挤入无临额组(09表)",
  "9/22 V6_1当周(w0921)大盘t0=23.56%(funnel 23.94互证, -4.8pp), 四组率效应齐降含周度/账龄因素; w0928回弹至25.87%, none组t0 31.1->36.77%, 风险长尾仍在(08/09表)",
  "任务C 循环贷损失率三因子拆解(24表; 账户=biz_id, 复贷放款8/19-10/06, 坏=1T3逾期$>0): 不发未用 F1=28.20%/F2=0.737/F3=1.179→损失率24.50%; 发未用 F1=12.30%/F2=0.661/F3=1.522→12.38%; 不发但用(离线临额) F1=23.80%/F2=0.720/F3=1.037→17.78%; 发且用 F1=23.20%/F2=0.739/F3=1.186→20.33%; 三因子乘积≈直接口径(坏账户合同额/总合同额)校验通过",
  "任务C 临额放大机制: 临额风险不在'变出更多坏账户', 而在放大单户坏账规模——发临额未使用组F1户数损失率最低(12.30%, 模型挑好客户); 一旦使用 F1升至23.20%(使用选择效应)、F2限额控制比0.661→0.739(坏账户人均限额更高)、坏账额度使用率0.302→0.670(敢借满), 双重放大F2×F3; 头部(1-5)发且用损失率15.66%远低于中尾(6-13)27.36%, 支持优质客群发临额、中尾严控上限",
  "任务B 复现同事《临额风险影响分析20260909》(25/26表; 窗口08-19~10-06, vintage t1d0$/t1d3$/t2d3$/t3d3$): 头部(1-5) 不发未用13.77%/发未用10.32%/发且用16.65%(t1d3$); 中尾(6-13) 28.91%/18.56%/27.54%; 与同事结论一致——发放未使用组坏账最低(模型筛选好客户), 使用临额后坏账抬升",
  "任务B rawdata明细(26表): 评级v5_3(1-13) × 是否发放临额 × 策略(V5_2/V5_3) × 放款月 × 是否8/11后 × 是否使用临额 的vintage明细(账户数/客户数/授信额/合同额/t1d0$/t1d3$/t2d3$/t3d3$); 窗口内if_0811恒=1(数据均在8/11后)",
  "在线临额保留g1_5档: tag1 t0 16-20%、件均1781-2051最高, 优质提额",
  "g6_8档减半额度/提高score门槛: tag1 t0 28.5-33%, 风险显著抬升",
  "g9-10档按矩阵单元收紧而非全档停发: V5_3新放开单元g10 s[0,1)t0 42.27%、g9各段27-38%、P2 g9p tag1 44.66%; 但g8/g9的score≥3段t0 22-27%尚可, 建议g10仅保留score≥3且额度减半, g9 score<0段停发在线临额(22表)",
  "离线维持8/29后批次准入标准, 收紧已被批次逾期归零证据验证; offline组整体t0最低可保持供给",
  "风险主战场是无临额长尾(none份额升至24%、t0 37%、多头0.4-0.55): 靠V6_1拒尾+评级准入, 而非收缩临额本身; 同时监测外部多头恶化",
  "临额策略评估核心盯F2限额控制比与F3额度使用率因子(户数损失率F1为辅): 已验证发临额未使用组损失率最低(模型有筛选力), 风险来自使用后的限额放大; 对中尾(6-13)与高评级g8-10已使用临额客群严控临额上限(24表)",
  "缺失的是yj在线复贷宽表(在线策略/四组打标的底表), 不是离线临额: 离线底表(11表)与funnel大盘完整不受影响; yj快照缺w0727/w0803及8/14前, w0817覆盖92%, 四组结论窗口8/18-10/04; 9月t30与1T7/TR未成熟不可外推; 11表部分标签字段曾被删待回补, 回补后重跑_fw_c.py即可; A/B/C随机分组hash口径见23表SQL"]
})

add("00_说明", readme)
add("00A_核心结论", concl)
add("01_大盘月度首复贷", b1)
add("02_大盘周度终损", load("B2_weekly_newold"))
add("03_在线月度发放使用", a1)
add("04_在线四阶段flag_tag", a2)
add("05_评级策略反事实", d1)
add("06_DID全客户", d3did)
add("07_DID_tag1临额客群", d4did)
add("08_四组周度汇总", fwk)
add("09_四组结构分解_pp", fdec)
add("10_离线周度评级档", fgrade)
add("11_离线批次政策证据", c1r)
add("12_客群质量月度", load("D2_quality_monthly"))
add("13_用信评分分布", load("A3_score_dist"))
add("14_四组周度评级明细", fall)
add("15_E1评分x四组", load("E1_score_grp"))
add("16_E2评分x阶段", e2)
add("17_E3_typex临额使用", load("E3_type_tempuse"))
add("18_E4评分分布漂移", e4)
add("19_策略矩阵V5_2vsV5_3", matrix_doc)
add("20_E5矩阵实证校验", e5)
add("21_E6type迁徙反事实", e6)
add("22_E7单元风险格", e7)
add("23_SQL依据", sql_doc)
add("24_损失率三因子拆解", c_doc)
add("25_复现同事_发放临额对比", b25_doc)
add("26_复现同事_rawdata明细", b26)

# 目标文件被Excel占用时自动落_b版本, 避免中断
try:
    with open(OUT, "r+b"):
        pass
except PermissionError:
    OUT = OUT.replace(".xlsx", "_b.xlsx")
    print("[warn] 原文件被占用, 改存:", OUT)

with pd.ExcelWriter(OUT, engine='openpyxl') as xw:
    for name, df in sheets:
        if df is not None and len(df):
            df.to_excel(xw, sheet_name=name[:31], index=False)
    wb = xw.book
    hdr_fill = PatternFill("solid", fgColor="1F4E78")
    hdr_font = Font(color="FFFFFF", bold=True, size=10)
    thin = Border(*[Side(style='thin', color="D9D9D9")]*4)
    for ws in wb.worksheets:
        ws.freeze_panes = "A2"
        for c in ws[1]:
            c.fill = hdr_fill; c.font = hdr_font
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for col in ws.columns:
            w = max((len(str(c.value)) if c.value is not None else 0) for c in col[:200])
            ws.column_dimensions[get_column_letter(col[0].column)].width = min(max(w+2, 9), 48)
    # SQL 依据页专用格式
    if "00A_核心结论" in wb.sheetnames:
        wsc = wb["00A_核心结论"]
        wsc.column_dimensions['A'].width = 20
        wsc.column_dimensions['B'].width = 115
        for row in wsc.iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(vertical="top", wrap_text=True)
    if "23_SQL依据" in wb.sheetnames:
        ws = wb["23_SQL依据"]
        widths = {"A":20,"B":24,"C":34,"D":42,"E":14,"F":130}
        for col, w in widths.items():
            ws.column_dimensions[col].width = w
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(vertical="top", wrap_text=True)
        ws.freeze_panes = "A2"
    # 19表: V5_2/V5_3 决策矩阵专用配色(type 1绿~4红, Δ负=放宽绿/正=收紧红)
    if "19_策略矩阵V5_2vsV5_3" in wb.sheetnames:
        wsm = wb["19_策略矩阵V5_2vsV5_3"]
        palette = {1: "C6EFCE", 2: "E2EFDA", 3: "FFF2CC", 4: "FFC7CE"}
        for r in range(2, wsm.max_row + 1):
            a = wsm.cell(r, 1).value
            if isinstance(a, str) and a.startswith("【"):
                wsm.merge_cells(start_row=r, start_column=1, end_row=r, end_column=8)
                cc = wsm.cell(r, 1)
                cc.font = Font(bold=True, color="1F4E78", size=10)
                cc.fill = PatternFill("solid", fgColor="DDEBF7")
                cc.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
                continue
            if a == "说明":
                wsm.merge_cells(start_row=r, start_column=2, end_row=r, end_column=8)
                for cj in range(1, 9):
                    wsm.cell(r, cj).alignment = Alignment(vertical="top", wrap_text=True)
                wsm.cell(r, 1).font = Font(bold=True, color="7F6000")
                wsm.row_dimensions[r].height = 30
                continue
            for cj in range(3, 8):
                v = wsm.cell(r, cj).value
                if isinstance(v, (int, float)):
                    cell = wsm.cell(r, cj); cell.alignment = Alignment(horizontal="center")
                    if a == "Δ":
                        if v < 0:
                            cell.fill = PatternFill("solid", fgColor="C6EFCE")
                            cell.font = Font(bold=True, color="006100")
                        elif v > 0:
                            cell.fill = PatternFill("solid", fgColor="FFC7CE")
                            cell.font = Font(bold=True, color="9C0006")
                    elif int(v) in palette:
                        cell.fill = PatternFill("solid", fgColor=palette[int(v)])
            if a in ("V5_2", "V5_3", "Δ"):
                wsm.cell(r, 1).font = Font(bold=True)
        for col, w in {"A":10, "B":9, "C":12, "D":12, "E":12, "F":12, "G":11, "H":24}.items():
            wsm.column_dimensions[col].width = w
    # 24/25表: 段落标题行(【...】)加粗高亮 + 列宽
    for sn in ["24_损失率三因子拆解", "25_复现同事_发放临额对比"]:
        if sn in wb.sheetnames:
            w = wb[sn]
            for r in range(2, w.max_row + 1):
                v = w.cell(r, 1).value
                if isinstance(v, str) and v.startswith("【"):
                    w.merge_cells(start_row=r, start_column=1, end_row=r, end_column=w.max_column)
                    c = w.cell(r, 1)
                    c.font = Font(bold=True, color="1F4E78", size=10)
                    c.fill = PatternFill("solid", fgColor="DDEBF7")
                    c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    if "24_损失率三因子拆解" in wb.sheetnames:
        w = wb["24_损失率三因子拆解"]
        for col, wd in {"A":44,"B":28,"C":10,"D":11,"E":14,"F":14,"G":14,"H":13,"I":15,"J":15,"K":17,"L":14,"M":15}.items():
            w.column_dimensions[col].width = wd
    if "25_复现同事_发放临额对比" in wb.sheetnames:
        w = wb["25_复现同事_发放临额对比"]
        for col, wd in {"A":30,"B":14,"C":14,"D":10,"E":15,"F":15,"G":14,"H":14}.items():
            w.column_dimensions[col].width = wd
    # 20表: E5校验下方追加 E5b 失配明细
    if "20_E5矩阵实证校验" in wb.sheetnames and e5b is not None and len(e5b):
        ws5 = wb["20_E5矩阵实证校验"]
        sr = ws5.max_row + 3
        t = ws5.cell(sr, 1, "E5b 失配明细(预测type≠实际type; pred空值=score_v1为空, 决策表无空分列)")
        t.font = Font(bold=True, color="9C0006")
        for j, col in enumerate(e5b.columns, 1):
            cell = ws5.cell(sr+1, j, str(col))
            cell.fill = hdr_fill; cell.font = hdr_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for i, (_, row) in enumerate(e5b.iterrows(), sr+2):
            for j, v in enumerate(row, 1):
                ws5.cell(i, j, None if pd.isna(v) else v)
        ws5.column_dimensions['A'].width = 14
        ws5.column_dimensions['B'].width = 16
    # 图1: 大盘周度 t0 首复贷 (02表, 透视到辅助区)
    ws2 = wb["02_大盘周度终损"]
    b2 = load("B2_weekly_newold")
    if b2 is not None and len(b2):
        pv0 = b2.pivot_table(index='app_week', columns='is_reloan', values='t0_rate', aggfunc='first').reset_index()
        sr0 = ws2.max_row + 3
        for j, col in enumerate(pv0.columns, 1):
            ws2.cell(row=sr0, column=j, value=str(col))
        for i, (_, r) in enumerate(pv0.iterrows(), sr0+1):
            for j, v in enumerate(r, 1):
                ws2.cell(row=i, column=j, value=(None if pd.isna(v) else v))
        ch = LineChart(); ch.title = "大盘周度 t0 坏账率(首贷 vs 复贷)"; ch.height=8; ch.width=20
        data = Reference(ws2, min_col=2, max_col=1+len(pv0.columns)-1, min_row=sr0, max_row=sr0+len(pv0))
        ch.add_data(data, titles_from_data=True)
        cats = Reference(ws2, min_col=1, min_row=sr0+1, max_row=sr0+len(pv0))
        ch.set_categories(cats); ch.y_axis.title='t0%'; ch.x_axis.title='进件周'
        ws2.add_chart(ch, "H2")
    # 图2/3: 四组周度 t0 + 份额
    ws8 = wb["08_四组周度汇总"] if "08_四组周度汇总" in wb.sheetnames else None
    if ws8 is not None and len(fwk) and ws8.max_row > 5:
        ch = LineChart(); ch.title="临额四组周度 t0 坏账率"; ch.height=9; ch.width=22
        # 透视作图数据写到隐藏区
        pv = fwk.pivot_table(index='wdate', columns='tl_grp', values='t0_rate', aggfunc='first').reset_index()
        sr = ws8.max_row + 3
        for j, col in enumerate(pv.columns, 1):
            ws8.cell(row=sr, column=j, value=col)
        for i, (_, r) in enumerate(pv.iterrows(), sr+1):
            for j, v in enumerate(r, 1):
                ws8.cell(row=i, column=j, value=v)
        data = Reference(ws8, min_col=2, max_col=1+len(pv.columns)-1, min_row=sr, max_row=sr+len(pv))
        ch.add_data(data, titles_from_data=True)
        cats = Reference(ws8, min_col=1, min_row=sr+1, max_row=sr+len(pv))
        ch.set_categories(cats); ch.y_axis.title='t0%'
        ws8.add_chart(ch, "M2")
        # 图3: 四组份额堆叠
        ch2 = BarChart(); ch2.type="col"; ch2.grouping="stacked"; ch2.overlap=100
        ch2.title="四组应还金额份额(%)"; ch2.height=9; ch2.width=22
        pv2 = fwk.pivot_table(index='wdate', columns='tl_grp', values='share_should', aggfunc='first').reset_index()
        sr2 = ws8.max_row + len(pv) + 6
        for j, col in enumerate(pv2.columns, 1):
            ws8.cell(row=sr2, column=j, value=col)
        for i, (_, r) in enumerate(pv2.iterrows(), sr2+1):
            for j, v in enumerate(r, 1):
                ws8.cell(row=i, column=j, value=v)
        data2 = Reference(ws8, min_col=2, max_col=1+len(pv2.columns)-1, min_row=sr2, max_row=sr2+len(pv2))
        ch2.add_data(data2, titles_from_data=True)
        cats2 = Reference(ws8, min_col=1, min_row=sr2+1, max_row=sr2+len(pv2))
        ch2.set_categories(cats2); ch2.y_axis.title='share%'
        ws8.add_chart(ch2, "M20")

print("saved:", OUT)
for n, df in sheets:
    print(n, 0 if df is None else len(df))

# -*- coding: utf-8 -*-
"""0903回调效果 & 30%灰度去留 方案测算 (基于已落盘查询结果)"""
import sys, io, pickle
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 420)

d2 = pickle.load(open(r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_v53_results.pkl","rb"))
d3 = pickle.load(open(r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_v53_results2.pkl","rb"))
d4 = pickle.load(open(r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_v53_results3.pkl","rb"))
for d in (d2, d3, d4):
    for k, v in d.items():
        if v is not None:
            for c in v.columns:
                if c not in ('phase','hgrp','stg','score_grp','iwk'):
                    v[c] = pd.to_numeric(v[c], errors='coerce')

def pct(a,b): return round((a-b),2)

print("="*90)
print("【1】DID 一: 全复贷ITT口径(Q5) — B组(与A基线平行,P0差+0.86pp)为最可信实验")
r5 = d3['r5']
def get(df, ph, hg, col):
    x = df[(df.phase==ph)&(df.hgrp==hg)][col]
    return float(x.iloc[0])
P0,P1,P2='P0_0810前','P1_0810-0903(70%)','P2_0903后(切30%)'
for hg in ['A_V5_2锚','B_切换组','C_V5_3锚']:
    r0,r1,r2 = get(r5,P0,hg,'t0_rate'),get(r5,P1,hg,'t0_rate'),get(r5,P2,hg,'t0_rate')
    print(f"  {hg}: P0 {r1 and r0} -> P1 {r1} -> P2 {r2}  (P1->P2 {pct(r2,r1):+}pp)")
did_b_a = pct(get(r5,P2,'B_切换组','t0_rate')-get(r5,P1,'B_切换组','t0_rate'),
              get(r5,P2,'A_V5_2锚','t0_rate')-get(r5,P1,'A_V5_2锚','t0_rate'))
did_b_c = pct(get(r5,P2,'B_切换组','t0_rate')-get(r5,P1,'B_切换组','t0_rate'),
              get(r5,P2,'C_V5_3锚','t0_rate')-get(r5,P1,'C_V5_3锚','t0_rate'))
print(f"  >>> DID(B相对A, 平行对照, 最可信) = {did_b_a:+}pp")
print(f"  >>> DID(B相对C, C基线不平行仅参考) = {did_b_c:+}pp")

print("="*90)
print("【2】DID 二: C010在线临额使用人群口径(Q3a ITT / Q3b 实际使用子群)")
r3a, r3b = d2['r3a'], d2['r3b']
def g2(df, ph, hg, col):
    return float(df[(df.phase==ph)&(df.hgrp==hg)][col].iloc[0])
for nm, df in [('C010全部放款', r3a), ('C010实际使用临额子群', r3b)]:
    db = g2(df,P2,'B_切换组','t0_rate')-g2(df,P1,'B_切换组','t0_rate')
    da = g2(df,P2,'A_V5_2锚','t0_rate')-g2(df,P1,'A_V5_2锚','t0_rate')
    dc = g2(df,P2,'C_V5_3锚','t0_rate')-g2(df,P1,'C_V5_3锚','t0_rate')
    print(f"  {nm}: B变化 {db:+.2f}pp, A变化 {da:+.2f}pp, C变化 {dc:+.2f}pp | DID(B-A)={db-da:+.2f}pp, DID(B-C)={db-dc:+.2f}pp")

print("="*90)
print("【3】P2同期(9/3-9/22,全成熟) V5_2 vs V5_3 方案参数(Q6/Q8)")
r6, r8 = d3['r6'], d3['r8']
print(r6.to_string())
v52 = r6[r6.stg.str.contains('V5_2')].iloc[0]; v53 = r6[r6.stg.str.contains('V5_3')].iloc[0]; tot = r8.iloc[0]
print(f"  坏账率差(V5_3-V5_2) = {v53.t0_rate-v52.t0_rate:+.2f}pp  [注:C组P0基线比A高4.55pp, 含固有差异]")
print(f"  take_rate差 = {v53.take_rate-v52.take_rate:+.2f}pp; 件均差 = {v53.loan_avg-v52.loan_avg:+.0f}比索")
print(f"  临额渗透率: V5_3 {v53.temp_use_pct}% vs V5_2 {v52.temp_use_pct}%")

print("="*90)
print("【4】方案A: 剩余30%(C组)全部切回V5_2 — 按P2窗口(19天)测算")
DAYS=19; WK=7
c_app, c_loan = float(v53.app_cnt), float(v53.loan_cnt)
c_should, c_od, c_amt = float(v53.should_k)*1000, float(v53.od_k)*1000, float(v53.loan_amt_k)*1000
t_should, t_od, t_amt = float(tot.should_k)*1000, float(tot.od_k)*1000, float(tot.loan_amt_k)*1000
# 三档坏账效应假设
eff_hi = float(v53.t0_rate)-float(v52.t0_rate)          # 2.65pp 上界(C vs A+B同期)
eff_mid_did = (g2(r5,P2,'C_V5_3锚','t0_rate')-g2(r5,P1,'C_V5_3锚','t0_rate')) - \
              (g2(r5,P2,'B_切换组','t0_rate')-g2(r5,P1,'B_切换组','t0_rate'))  # DID C-B 下界
eff_mid = 1.0  # 中枢假设1pp
print(f"  C组规模(19天): 进件{c_app:.0f} 放款{c_loan:.0f} 周均放款{c_loan/DAYS*WK:.0f}笔")
print(f"  C组到期应还 {c_should/1000:.0f}k比索, 周均 {c_should/DAYS*WK/1000:.0f}k")
for nm, eff in [('上界(C同期差2.65pp)', eff_hi), ('中枢(1pp)', eff_mid), ('平行DID下界(0.3pp)', 0.3)]:
    od_save_wk = c_should/DAYS*WK * eff/100
    amt_lost_wk = (float(v53.loan_avg)-float(v52.loan_avg)) * c_loan/DAYS*WK
    int_lost_wk = amt_lost_wk*0.22
    big_rate = od_save_wk/(t_should/DAYS*WK)*100
    print(f"  [{nm}] 周减坏账 {od_save_wk/1000:5.1f}k | 大盘1t0%改善 {big_rate:.2f}pp | "
          f"周放款减 {amt_lost_wk/1000:.1f}k({amt_lost_wk/(t_amt/DAYS*WK)*100:.1f}%) | "
          f"利息收入损失~{int_lost_wk/1000:.0f}k | 净收益 {(od_save_wk-int_lost_wk)/1000:+.1f}k/周 "
          f"=> 年化净 {(od_save_wk-int_lost_wk)*52/1000:+.0f}k比索")

print("="*90)
print("【5】评分分层精准方案(Q9 P2) — 各档V5_3 vs V5_2")
r9 = d4['r9']
for sg in ['S1_低分<=0','S2_中分1-3','S3_高分5']:
    a = r9[(r9.stg=='V5_2')&(r9.score_grp==sg)].iloc[0]
    c = r9[(r9.stg=='V5_3')&(r9.score_grp==sg)].iloc[0]
    print(f"  {sg}: V5_2坏{a.t0_rate}%/件均{a.loan_avg}/临额{a.temp_pct}% vs "
          f"V5_3坏{c.t0_rate}%/件均{c.loan_avg}/临额{c.temp_pct}% | 坏账差{c.t0_rate-a.t0_rate:+.2f}pp 件均差{c.loan_avg-a.loan_avg:+.0f}")

print("="*90)
print("【6】当前逾期率水平 & 大盘回落归因")
r4 = d2['r4']
print(r4[['iwk','loan_cnt','mature_cnt','t0_rate']].to_string())
hi = r4[r4.iwk.isin(['2026-08-17','2026-08-24','2026-08-31'])].t0_rate.mean()
lo = r4[r4.iwk.isin(['2026-09-07','2026-09-14','2026-09-21'])].t0_rate.mean()
print(f"  8月高峰三周均值 {hi:.2f}% -> 9月三周均值 {lo:.2f}% = {lo-hi:+.2f}pp")
b_share = g2(r5,P2,'B_切换组','loan_cnt')/float(tot.loan_cnt)*19/19  # B占P2放款比(注:P2=19天)
b_share = float(r5[(r5.phase==P2)&(r5.hgrp=='B_切换组')].loan_cnt.iloc[0])/float(tot.loan_cnt)
print(f"  B组(被回调40%)占P2放款比 {b_share*100:.1f}%; 其ITT坏账效应≈0(DID {did_b_a:+.2f}pp)")
print(f"  >>> 回调对大盘1t0%回落贡献 ≈ {did_b_a*b_share:+.2f}pp (占总回落{(hi-lo):.2f}pp的约{abs(did_b_a*b_share/(lo-hi))*100:.0f}%)")

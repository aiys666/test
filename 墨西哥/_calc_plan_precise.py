# -*- coding: utf-8 -*-
"""精准收缩方案三档敏感性测算
反事实基准: 停发临额后件均 -> V5_2同评级tag0件均(中性) / V5_3同评级tag0件均(悲观即降幅小)
           / 仅减临额均值(保守)
逾期率假设: 不变(B组DID已证临额不影响坏账率) — 坏账减少全部来自件均下降
"""
import sys, io, pickle
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd

d = pickle.load(open(r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_plan_precise.pkl","rb"))
r1, r2, r3 = d['r1'], d['r2'].iloc[0], d['r3'].iloc[0]
for c in r1.columns:
    if c not in ('stg','tag','grade_grp'): r1[c]=pd.to_numeric(r1[c])

def g(stg,tag,gg,col):
    return float(r1[(r1.stg==stg)&(r1.tag==tag)&(r1.grade_grp==gg)][col].iloc[0])

DAYS=19; WK=7; RATE_INT=0.22  # 利率假设22%
# 大盘分母(19天, 单位k比索)
TOT_LOAN, TOT_CREDIT, TOT_SHOULD, TOT_OD = float(r2.loan_k), float(r3.credit_k), float(r2.should_k), float(r2.od_k)
print(f"大盘P2(19天): 放款{TOT_LOAN:.0f}k 授信{TOT_CREDIT:.0f}k 应还{TOT_SHOULD:.0f}k 逾期{TOT_OD:.0f}k 1t0%={float(r2.t0_rate):.2f} TR={float(r3.tr_amt):.2f}%")

def scen(name, cuts):
    """cuts: list of (grade_grp, shrink_ratio, note)"""
    print("="*100); print(f"【{name}】")
    d_loan=d_od=0; n_aff=0
    for gg, ratio, note in cuts:
        n = g('V5_3','tag1',gg,'deal') * ratio
        avg_now = g('V5_3','tag1',gg,'loan_avg')
        avg_cf  = g('V5_2','tag0',gg,'loan_avg')   # 中性反事实: V5_2同档tag0
        avg_cf2 = g('V5_3','tag0',gg,'loan_avg')   # 参考: V5_3同档tag0
        rate    = g('V5_3','tag1',gg,'t0_rate')/100
        dl = n*(avg_now-avg_cf)/1000.0             # k比索/19天
        do = dl*rate
        d_loan+=dl; d_od+=do; n_aff+=n
        print(f"  {gg}({note}): 影响{n:.0f}笔/19天 | 件均{avg_now:.0f}->{avg_cf:.0f}(对照tag0:{avg_cf2:.0f}) | "
              f"放款-{dl:.1f}k | 逾期率{rate*100:.1f}%不变 | 逾期-{do:.1f}k")
    # 汇总(19天->周)
    dl_wk, do_wk = d_loan/DAYS*WK, d_od/DAYS*WK
    int_lost_wk = dl_wk*RATE_INT
    net_wk = do_wk - int_lost_wk
    print(f"  --- 汇总(周均) ---")
    print(f"  放款金额: -{dl_wk:.1f}k/周 = 大盘 {-dl_wk/(TOT_LOAN/DAYS*WK)*100:.2f}%")
    print(f"  逾期金额: -{do_wk:.1f}k/周")
    print(f"  利息损失: -{int_lost_wk:.1f}k/周")
    print(f"  净收益:   {net_wk:+.1f}k/周 = 年化 {net_wk*52/1000:+.1f}M比索")
    # 大盘指标变化
    new_od_rate = (TOT_OD-d_od)/TOT_SHOULD*100
    new_tr = (TOT_LOAN-d_loan)/TOT_CREDIT*100
    print(f"  --- 大盘指标(19天窗口) ---")
    print(f"  复贷1t0%: {float(r2.t0_rate):.2f}% -> {new_od_rate:.2f}%  ({new_od_rate-float(r2.t0_rate):+.2f}pp, 相对{(new_od_rate/float(r2.t0_rate)-1)*100:+.2f}%)")
    print(f"  复贷TR:   {float(r3.tr_amt):.2f}% -> {new_tr:.2f}%  ({new_tr-float(r3.tr_amt):+.3f}pp, 相对{(new_tr/float(r3.tr_amt)-1)*100:+.2f}%)")
    print(f"  复贷放款: {TOT_LOAN:.0f}k -> {TOT_LOAN-d_loan:.0f}k  ({-d_loan/TOT_LOAN*100:+.2f}%)")
    return d_loan, d_od

# S1: 仅停9级以上
scen("S1 停发9级以上临额", [('c_g9p', 1.0, '停发')])
# S2: 停9级 + 6-8级减半
scen("S2 停9级以上 + 6-8级减半", [('c_g9p',1.0,'停发'), ('b_g6_8',0.5,'减半')])
# S3: 停9级 + 6-8级全停
scen("S3 停9级以上 + 6-8级全停", [('c_g9p',1.0,'停发'), ('b_g6_8',1.0,'全停')])

# 对照: 全切V5_2(方案A) — C组tag1全部停发
scen("对照 方案A全切: C组tag1全停", [('a_g1_5',1.0,'全停'),('b_g6_8',1.0,'全停'),('c_g9p',1.0,'全停')])

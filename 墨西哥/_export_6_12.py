# -*- coding: utf-8 -*-
"""6-12级专项排查 Excel: 产品?放松客群?还是其他?"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd, numpy as np
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUT = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥"
XLSX = os.path.join(OUT, "墨西哥6-12级客群风险恶化专项排查.xlsx")

wk_iss = pd.read_pickle(os.path.join(OUT,"_612_wk_issue.pkl"))
wk_app = pd.read_pickle(os.path.join(OUT,"_612_wk_app.pkl"))
lv1 = pd.read_pickle(os.path.join(OUT,"_612_lv1_cmp.pkl"))
allc = pd.read_pickle(os.path.join(OUT,"_612_cmp_all.pkl"))
ss = pd.read_pickle(os.path.join(OUT,"_612_shift.pkl"))

DARK="1F4E79"; HF=Font(name="微软雅黑",size=10,bold=True,color="FFFFFF"); HFL=PatternFill("solid",fgColor=DARK)
TF=Font(name="微软雅黑",size=14,bold=True,color="FFFFFF"); SF=Font(name="微软雅黑",size=12,bold=True,color="1F4E79")
NF=Font(name="微软雅黑",size=10); BF=Font(name="微软雅黑",size=10,bold=True)
RED=PatternFill("solid",fgColor="FFC7CE"); YEL=PatternFill("solid",fgColor="FFEB9C"); GRN=PatternFill("solid",fgColor="C6EFCE")
TFL=PatternFill("solid",fgColor=DARK)
TH=Side(border_style="thin",color="B4B4B4"); BD=Border(left=TH,right=TH,top=TH,bottom=TH)
CEN=Alignment(horizontal="center",vertical="center",wrap_text=True); LFT=Alignment(horizontal="left",vertical="center",wrap_text=True)

def title(ws,t,r=1,span=10):
    ws.merge_cells(start_row=r,start_column=1,end_row=r,end_column=span)
    c=ws.cell(row=r,column=1,value=t); c.fill=TFL; c.font=TF; c.alignment=CEN
    ws.row_dimensions[r].height=28
def section(ws,t,r,span=10):
    ws.merge_cells(start_row=r,start_column=1,end_row=r,end_column=span)
    c=ws.cell(row=r,column=1,value=t); c.font=SF; c.alignment=LFT; ws.row_dimensions[r].height=22

NUM={"issue_cnt","if_app","if_in_sx","if_sx_passed","1t0出账","4t3出账","4t7出账","笔数_b","笔数_c","contract_amount","件均"}
def wdf(ws,df,sr,bad_cols=None,good_bad=True):
    bad_cols=bad_cols or []
    cols=list(df.columns)
    for j,c in enumerate(cols,1):
        x=ws.cell(row=sr,column=j,value=str(c)); x.fill=HFL; x.font=HF; x.alignment=CEN; x.border=BD
    for i,(_,row) in enumerate(df.iterrows(),sr+1):
        for j,c in enumerate(cols,1):
            v=row[c]
            if pd.isna(v): v=None
            x=ws.cell(row=i,column=j,value=v); x.font=NF; x.border=BD
            base=c.split("_")[0]
            if c in NUM or c.endswith("笔数_b") or c.endswith("笔数_c"):
                x.alignment=Alignment(horizontal="right",vertical="center"); x.number_format="#,##0"
            elif isinstance(v,(int,float)):
                x.alignment=Alignment(horizontal="right",vertical="center"); x.number_format="0.00"
            else:
                x.alignment=LFT if j<=2 else CEN
            if c in bad_cols and isinstance(v,(int,float)):
                if good_bad:
                    if v>=6: x.fill=RED
                    elif v>=3: x.fill=YEL
                    elif v<=-3: x.fill=GRN
                else:
                    if v<=7: x.fill=RED
                    elif v<=12: x.fill=YEL
    return sr+len(df)+1
def widths(ws,ws_widths):
    for i,w in enumerate(ws_widths,1): ws.column_dimensions[get_column_letter(i)].width=w

wb=Workbook(); wb.remove(wb.active)

# ── 0 结论 ──
ws=wb.create_sheet("0_排查结论")
title(ws,"6-12级客群风险恶化专项排查：产品？放松客群？还是其他？",1,span=8)
ws.cell(row=2,column=1,value="范围：v5_3主评级 6-12 级（占当期复贷放款 74%，6064/8186）；基期 8/03周 vs 当期 8/10周").font=Font(name="微软雅黑",size=9,italic=True,color="595959")
ws.merge_cells("A2:H2")
blocks=[
 ("假设①：是产品问题吗？","部分是，但不是单一产品事故",
  "产品间结构几乎没变（shift-share 产品结构效应仅 +0.33pp，率效应 +4.58pp）；A/B/C/E 各产品在 6-12 客群内 1t0本金% 全部上升（A +3.25、B +6.25、C_07_03 +5.43、C_07_02 +11.83）。最大单一载体是 C_07_03_00_75（1141→1242笔，1t0 27.36→35.18，+7.82pp，4T7TR 31→18）；产品档 D_1_06 放量46%（149→218笔）且 +11.98pp，需单独核查。"),
 ("假设②：是放松客群/准入放水吗？","否，准入没有放松",
  "8/10周 6-12 客群风险通过率 99.0%→98.8%（基本未变），前置%=100%；24h用信率 70.04→69.13 反而下降；grant_score 全部 S_ge90 无评分下沉；评级分布稳定（7级占比10.95→10.78%、8级23.93→23.43%，10-12合计占比仅+1.27pp，结构效应仅+0.16~0.21pp）。8/17周起风险通过率主动降到92-95%，是风控收紧的滞后响应，不是放松。"),
 ("假设③：那是什么？","同一批客群、同样门槛下的履约表现系统性恶化（率效应≈全部+4.9pp）",
  "6-12 内部所有维度结构效应≈0、率效应4.6~5.05pp——是存量客群还钱能力/意愿变差。高危标签切片被放大：fd_high_pass=1（14.00→39.76，+25.76pp，4T7TR 42.77→1.17 击穿）、历史逾期8-30天（32.38→49.89，+17.51）、25岁以下（+11.97）、当前有逾期ovd_1/ovd_2（+6.45/+8.74）、还款间隔>14天（+7.33）。同时 120h用信率 93.33→96.42（边缘用户更晚才用信=资金链更紧），指向外部现金流/共债/催收环境等系统性因素，而非内部策略。"),
]
r=4
for h,a,b in blocks:
    section(ws,h,r,8); r+=1
    ws.merge_cells(start_row=r,start_column=1,end_row=r,end_column=8)
    c=ws.cell(row=r,column=1,value="判定："+a); c.font=BF; c.alignment=LFT; ws.row_dimensions[r].height=20; r+=1
    ws.merge_cells(start_row=r,start_column=1,end_row=r,end_column=8)
    c=ws.cell(row=r,column=1,value=b); c.font=NF; c.alignment=LFT; ws.row_dimensions[r].height=72; r+=2
section(ws,"6-12 整体大数速览",r,8); r+=1
q=wk_iss[wk_iss.wk.isin(["2026-08-03","2026-08-10","2026-08-17"])][["wk","issue_cnt","contract_amount","1t0本金%","4t3本金%","4t7本金%","4T7TR%"]]
r=wdf(ws,q,r,bad_cols=["1t0本金%","4t3本金%","4t7本金%"])
widths(ws,[12,12,16,10,10,10,10,10])

# ── 1 周度大数 ──
ws=wb.create_sheet("1_6-12周度大数")
title(ws,"6-12级 周度大数（issue放款 + app进件双基准）",span=12)
section(ws,"issue 基准",3,12)
r=wdf(ws,wk_iss[["wk","issue_cnt","contract_amount","1t0本金%","1t3本金%","1t7本金%","4t0本金%","4t3本金%","4t7本金%","4t3息费%","4t7息费%","前砍%","后收%","4t3TR%","4T7TR%","件均"]],4,
      bad_cols=["1t0本金%","4t3本金%","4t7本金%"])
section(ws,"app 基准（放松检验：前置/风险通过率/用信率）",r+1,12)
r=wdf(ws,wk_app[["wk","if_app","issue_cnt","前置%","后置","风险通过率%","24h用信率%","120h用信率%","1t0本金%","4T7TR%"]],r+2,
      bad_cols=["1t0本金%"])
widths(ws,[11]+[10]*14)

# ── 2 结构迁移 ──
ws=wb.create_sheet("2_结构迁移检验")
title(ws,"6-9 vs 10-12：结构迁移只解释 +0.16~0.21pp，主因是各段率自身恶化",span=10)
seg=pd.read_pickle(os.path.join(OUT,"_agg612_评级子段_issue.pkl"))
seg["d"]=pd.to_datetime(seg["d"]); seg["wk"]=(seg["d"]-pd.to_timedelta(seg["d"].dt.weekday,unit="D")).dt.strftime("%Y-%m-%d")
def cm(d):
    d=d.copy()
    d["issue_cnt"]=d["if_issue"]
    d["1t0本金%"]=(d["t0_overdue_capit_1"]/d["t0_should_capit_1"]*100).round(2)
    d["4t3本金%"]=(d["t3_overdue_capit_4"]/d["t3_should_capit_4"]*100).round(2)
    d["4t7本金%"]=(d["t7_overdue_capit_4"]/d["t7_should_capit_4"]*100).round(2)
    return d
sw=cm(seg.groupby(["wk","dim"],as_index=False).sum(numeric_only=True))
piv=sw.pivot(index="wk",columns="dim",values="issue_cnt").fillna(0)
piv["合计"]=piv.sum(axis=1)
for s in ["6-9级","10-12级"]:
    if s in piv: piv[f"{s}占比%"]=(piv[s]/piv["合计"]*100).round(2)
piv=piv.reset_index()
section(ws,"笔数与占比（周）",3,10)
r=wdf(ws,piv[piv.wk>="2026-07-13"],4)
rate=sw.pivot(index="wk",columns="dim",values="1t0本金%").reset_index()
section(ws,"各子段 1t0本金%（率自身在涨）",r+1,10)
r=wdf(ws,rate[rate.wk>="2026-07-13"],r+2,bad_cols=["6-9级","10-12级"])
widths(ws,[12,10,10,10,12,12,10,10,10,10])

# ── 3 评级单级 ──
ws=wb.create_sheet("3_评级单级对比")
title(ws,"评级单级 8/03 vs 8/10：占比稳定，各级坏账率普涨（7级最猛 +8.23）",span=10)
wdf(ws,lv1,3,bad_cols=["1t0_Δ"])
w=ws; w.conditional_formatting  # noop
widths(ws,[6,10,9,10,9,9,9,9,9,10])

# ── 4 内部各维度对比 ──
ws=wb.create_sheet("4_内部各维度对比")
title(ws,"6-12 内部各维度切片 8/03→8/10（全量，按 1t0本金%_Δ 降序）",span=16)
cols=["dim_key","dim","issue_cnt_b","issue_cnt_c","1t0本金%_b","1t0本金%_c","1t0本金%_Δ",
      "4t3本金%_b","4t3本金%_c","4t3本金%_Δ","4t7本金%_Δ","前砍%_Δ","后收%_Δ","4T7TR%_b","4T7TR%_c","4T7TR%_Δ"]
big=allc[allc["issue_cnt_c"]>=50].sort_values("1t0本金%_Δ",ascending=False)
wdf(ws,big[cols],3,bad_cols=["1t0本金%_Δ","4t3本金%_Δ","4t7本金%_Δ"])
ws.freeze_panes="C4"; ws.auto_filter.ref=f"A3:P{len(big)+3}"
widths(ws,[14,20]+[10]*14)

# ── 5 shift-share ──
ws=wb.create_sheet("5_内部shift_share")
title(ws,"6-12 内部 shift-share：全部维度率效应≈+4.6~5.0，结构效应≈0",span=6)
wdf(ws,ss,3)
widths(ws,[16,10,10,8,12,10])

# ── 6 app放松检验(全切片) ──
# 从 pkl 重新算 app 各维度
def load(key,base):
    fp=os.path.join(OUT,f"_agg612_{key}_{base}.pkl")
    if not os.path.exists(fp): return None
    d=pd.read_pickle(fp); d["d"]=pd.to_datetime(d["d"])
    d["wk"]=(d["d"]-pd.to_timedelta(d["d"].dt.weekday,unit="D")).dt.strftime("%Y-%m-%d"); return d
def cm2(d):
    d=d.copy(); d["issue_cnt"]=d["if_issue"]
    def p(n,m): return (n/m*100).round(2)
    d["前置%"]=p(d["if_in_sx"],d["if_app"]); d["风险通过率%"]=(d["前置%"]*(d["issue_cnt"]/d["if_sx_passed"])).round(2)
    d["24h用信率%"]=p(d["if_sx_passed_24h"],d["if_in_sx_24h"]); d["120h用信率%"]=p(d["if_sx_passed_120h"],d["if_in_sx_120h"])
    d["1t0本金%"]=p(d["t0_overdue_capit_1"],d["t0_should_capit_1"])
    return d
appdims=["评级子段","评级单级","grant_score","grant_strategy","fd_high_pass","product_name","product_level",
         "历史最大逾期天","当前逾期笔数","最近还款间隔","app_group","channel_category","loan_cycle","reloan_num"]
rows=[]
for k in appdims:
    d=load(k,"app")
    if d is None: continue
    w=cm2(d.groupby(["wk","dim"],as_index=False).sum(numeric_only=True))
    b=w[w.wk=="2026-08-03"].set_index("dim"); c=w[w.wk=="2026-08-10"].set_index("dim")
    for g in set(b.index)|set(c.index):
        def gv(df,m): return df[m].get(g) if g in df.index else np.nan
        rows.append({"维度":k,"切片":g,"进件_b":gv(b,"if_app"),"进件_c":gv(c,"if_app"),
                     "前置%_b":gv(b,"前置%"),"前置%_c":gv(c,"前置%"),
                     "风险通过率_b":gv(b,"风险通过率%"),"风险通过率_c":gv(c,"风险通过率%"),
                     "24h用信_b":gv(b,"24h用信率%"),"24h用信_c":gv(c,"24h用信率%"),
                     "120h用信_b":gv(b,"120h用信率%"),"120h用信_c":gv(c,"120h用信率%"),
                     "1t0本金_Δ":None if g not in b.index or g not in c.index else round(gv(c,"1t0本金%")-gv(b,"1t0本金%"),2)})
appcmp=pd.DataFrame(rows)
appcmp=appcmp[pd.to_numeric(appcmp["进件_c"],errors="coerce")>=30]
ws=wb.create_sheet("6_app准入放松检验")
title(ws,"app 基准：前置/风险通过率/用信率两周对比（无放松迹象；通过率99→98.8）",span=13)
wdf(ws,appcmp.sort_values(["维度","进件_c"],ascending=[True,False]),3,bad_cols=["1t0本金_Δ"])
ws.freeze_panes="C4"; ws.auto_filter.ref=f"A3:M{len(appcmp)+3}"
widths(ws,[14,18]+[10]*11)

# ── 7 重点切片逐日/逐周 ──
focus=[("fd_high_pass","1.0E0"),("历史最大逾期天","mxovd_8_30"),("product_level","D_1_06"),
       ("product_name","C_07_03_00_75"),("product_name","C_07_02_00_75"),("年龄段","age_lt25"),
       ("contract_amount","L_2k_5k"),("当前逾期笔数","ovd_1")]
def cm3(d):
    d=d.copy(); d["issue_cnt"]=d["if_issue"]
    def p(n,m): return (n/m*100).round(2)
    d["1t0本金%"]=p(d["t0_overdue_capit_1"],d["t0_should_capit_1"])
    d["4t3本金%"]=p(d["t3_overdue_capit_4"],d["t3_should_capit_4"])
    d["4t7本金%"]=p(d["t7_overdue_capit_4"],d["t7_should_capit_4"])
    d["前砍%"]=p(d["haircut_amount"],d["contract_amount"]); d["后收%"]=p(d["should_interest"],d["contract_amount"])
    d["4T7TR%"]=(d["后收%"]+d["前砍%"]-p(d["t7_overdue_interest_4"],d["t7_should_capit_4"])-d["4t7本金%"]).round(2)
    d["件均"]=(d["contract_amount"]/d["issue_cnt"]).round(0)
    return d
ws=wb.create_sheet("7_重点切片逐周")
title(ws,"重点切片逐周表现（高危信号）",span=9)
r=3
for k,g in focus:
    d=load(k,"issue")
    w=cm3(d.groupby(["wk","dim"],as_index=False).sum(numeric_only=True))
    sub=w[w["dim"]==g][["wk","issue_cnt","1t0本金%","4t3本金%","4t7本金%","4T7TR%","件均"]].copy()
    sub.insert(0,"切片",f"{k}={g}")
    section(ws,f"{k} = {g}",r,9)
    r=wdf(ws,sub[sub.wk>="2026-07-13"],r+1,bad_cols=["1t0本金%","4t3本金%","4t7本金%"])+1
widths(ws,[26,11,9,9,9,9,9,9,9])

for s in wb.sheetnames: wb[s].freeze_panes if False else None
wb.save(XLSX)
print("已导出:",XLSX); print("Sheets:",wb.sheetnames)

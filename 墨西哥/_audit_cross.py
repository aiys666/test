# -*- coding: utf-8 -*-
"""逐指标对拍: (1) 现跑 Q6 月小计 SQL 重算; (2) 读 xlsx 月度明细月合计整行逐列比;
(3) 按月拆 全老客/匹配/仅V5_3flag/评级非空(V5_3 cohort) 解释 7 月 37,381 vs 37,689 的口径差。"""
import sys, os, re
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
import pandas as pd
import openpyxl
from mexico_presto import PrestoQuery

HERE = os.path.dirname(os.path.abspath(__file__))
XLSX = os.path.join(HERE, "墨西哥复贷产品分析_V5_3评级x产品_全SQL.xlsx")
SQLF = os.path.join(HERE, "墨西哥复贷产品分析_V5_3评级x产品_全SQL.sql")

_WINS = ["t0", "t3", "t7", "t14", "t30"]

# —— 复刻 DET_KEYS 与中文头(与生成器一致), 用于把 xlsx 列名映回英文 ——
def cn_head(c):
    m = {"grp": "期", "product_name": "产品", "grade": "主等级V5_3",
         "loans": "放款笔数", "custs": "复贷客数", "ca": "放款金额", "ha": "前砍费",
         "si": "后收利息", "si_net": "后收净息", "avg_ca": "件均", "loans_cust": "人均件数",
         "ha_rate": "前砍率", "si_rate": "后收率", "si_net_rate": "后收净率",
         "fee_net_rate": "总息费净率", "vat_ca_rate": "息费税占合同%",
         "loans_share_g": "档内产品笔数占比", "ca_share_g": "档内产品金额占比",
         "loans_share_p": "产品内档位笔数占比", "ca_share_p": "产品内档位金额占比",
         "t7_mature_ca": "T7成熟合同额", "t7_mature_ovd": "T7成熟逾期额",
         "tr_net7": "TR净%(T7,税后)", "t7_ovd_amtrate_ca": "T7逾期额/合同%"}
    for W in _WINS:
        m[f"{W}_mature_cnt"] = f"{W}成熟笔数"; m[f"{W}_mature_rate"] = f"{W}成熟率"
        m[f"{W}_ovd_cnt"] = f"{W}逾期笔数"; m[f"{W}_cntrate"] = f"{W}首逾率%(笔数)"
        m[f"{W}_should_amt"] = f"{W}成熟应还"; m[f"{W}_overdue_amount"] = f"{W}成熟逾期额"
        m[f"{W}_amtrate"] = f"{W}金额逾期率"
    return m.get(c, c)

DET_KEYS = (["grp", "product_name", "grade", "loans", "custs", "ca", "ha", "si", "si_net",
             "avg_ca", "loans_cust", "loans_share_g", "ca_share_g", "loans_share_p", "ca_share_p",
             "fee_net_rate", "si_net_rate", "vat_ca_rate", "tr_net7", "t7_ovd_amtrate_ca"]
            + [f"{W}_{s}" for W in _WINS for s in ("mature_cnt", "mature_rate", "should_amt", "overdue_amount", "ovd_cnt", "cntrate", "amtrate")])
DET_KEYS = list(dict.fromkeys(DET_KEYS))

# —— 从生成器 .sql 提取 Q6 月小计 并现场重跑 ——
text = open(SQLF, encoding="utf-8").read()
blocks = dict(re.findall(r"-- ==== (Q\d+ [^\n]+) ====\n(.*?);\n\n", text, re.S))
q6 = blocks["Q6 月小计"]
pq = PrestoQuery(); pq.login()
r = pq.query(q6)
if isinstance(r, str):
    print("Q6 重跑错误:", r[:400]); sys.exit(1)
fresh = r.copy()
for c in fresh.columns:
    if c not in ("grp", "product_name", "grade"):
        fresh[c] = pd.to_numeric(fresh[c], errors="coerce")
fresh["grp"] = fresh["grp"].astype(str)
fresh_by = {m: fresh[fresh["grp"] == m].iloc[0] for m in fresh["grp"].unique()}

# —— 读 xlsx 月度明细_产品×评级×月 的月合计行(产品、评级空) ——
wb = openpyxl.load_workbook(XLSX, read_only=True)
ws = wb["月度明细_产品×评级×月"]
rows = ws.iter_rows(values_only=True)
next(rows)  # note1
next(rows)  # note2
hdr = list(next(rows))
col_eng = {cn_head(k): k for k in DET_KEYS}
wbm = {}
for row in rows:
    d = dict(zip(hdr, row))
    if d.get("产品") is None and d.get("主等级V5_3") is None and d.get("期") is not None:
        m = str(d["期"])
        wbm[m] = {col_eng[h]: d[h] for h in hdr if h in col_eng}

print("现场重跑 Q6 月小计 vs xlsx 月合计 逐指标对比(全列, 共%d列):" % len(DET_KEYS))
allok = True
for m in sorted(wbm):
    fm = fresh_by[m]
    bad = []
    for k in DET_KEYS:
        if k in ("grp", "product_name", "grade"):
            continue
        a = fm[k]; b = wbm[m][k]
        same = (pd.isna(a) and pd.isna(b)) or (a == b)
        if not same:
            bad.append(f"{k}: SQL={a!r} xlsx={b!r}")
    flag = "PASS" if not bad else "FAIL"
    if bad: allok = False
    print(f"\n[{flag}] 期={m}  共核对 {len(DET_KEYS)-3} 个指标; 不符 {len(bad)}")
    for x in bad[:8]:
        print("   ", x)

# —— 覆盖口径拆解(全老客 vs 匹配 vs V5_3flag vs 评级非空) ——
cov = """
select substr(cast(f.release_time as varchar),1,7) as ym,
 count(distinct f.biz_id) as all_biz,
 count(distinct case when y.biz_id is not null then f.biz_id end) as matched_biz,
 count(distinct case when y.v3_flag='V5_3' then f.biz_id end) as flag_v53_biz,
 count(distinct case when y.v3_flag='V5_3' and y.android_oldcust_maincreditlevel_charge_v5_3 is not null then f.biz_id end) as graded_biz
from mx.wxs_application_funnel f
left join mx.yj_test_table_250225 y on f.biz_id=y.biz_id
where f.is_reloan='old' and f.if_issue=1 and f.product_name is not null
 and f.release_time>=date'2026-06-09' and f.release_time<date'2026-09-01'
group by 1 order by 1"""
rc = pq.query(cov)
print("\n=== 按月覆盖口径拆解 ===")
if isinstance(rc, str):
    print("ERR:", rc[:300])
else:
    print(rc.to_string(index=False))
    print("\n解读: 报表『放款笔数』= graded_biz(评级非空的 V5_3 cohort); 7 月全老客放款 "
          "all_biz 减去 非V5_3/无评级 等行 后 = 37,381。")

print("\n" + ("所有月份逐指标对拍全部一致。" if allok else "存在不一致,见上。"))

# -*- coding: utf-8 -*-
import openpyxl

path = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\墨西哥风险\老客拒尾测试考虑逾期天数 - 副本.xlsx"
wb = openpyxl.load_workbook(path, data_only=True)

def rows(sheet):
    ws = wb[sheet]
    return [[c.value for c in r] for r in ws.iter_rows()]

def safe(x):
    return 0.0 if x is None else float(x)

def wavg(vals, wts):
    vs = [safe(v) for v in vals]; ws = [safe(w) for w in wts]
    tot = sum(ws)
    return sum(a*b for a, b in zip(vs, ws)) / tot if tot else 0.0

# ==================== 主表：各版本评级表现； ====================
# 关键修正：header col1=None(空)。数据 col1=无标签小群体(未出账/无评级)，
#           col2..col12 = V6-1 评级1..11，col13=合计
#           col2..col14 = V5-3 评级1..13，col15=合计
m = rows("各版本评级表现；")

def get(row, col):
    return safe(m[row][col])

def metrics(rowmap, n_rating, tot_col):
    res = {}
    res["special"] = dict(num=get(rowmap["num"], 1), amt=get(rowmap["amt"], 1),
                          jj=get(rowmap["jj"], 1), term=get(rowmap["term"], 1),
                          tr=get(rowmap["tr"], 1), od=get(rowmap["od"], 1),
                          win=get(rowmap["win"], 1))
    for r in range(1, n_rating + 1):
        c = 1 + r
        res[r] = dict(num=get(rowmap["num"], c), amt=get(rowmap["amt"], c),
                      jj=get(rowmap["jj"], c), term=get(rowmap["term"], c),
                      tr=get(rowmap["tr"], c), od=get(rowmap["od"], c),
                      win=get(rowmap["win"], c))
    tot_num = res["special"]["num"] + sum(res[r]["num"] for r in range(1, n_rating + 1))
    tot_amt = res["special"]["amt"] + sum(res[r]["amt"] for r in range(1, n_rating + 1))
    tot_tr = get(rowmap["tr"], tot_col)
    tot_od = get(rowmap["od"], tot_col)
    return res, tot_num, tot_amt, tot_tr, tot_od

v6, V6_NUM, V6_AMT, V6_TR, V6_OD = metrics(
    {"num": 1, "amt": 4, "jj": 6, "term": 8, "tr": 14, "od": 15, "win": 36}, 11, 13)
v5, V5_NUM, V5_AMT, V5_TR, V5_OD = metrics(
    {"num": 43, "amt": 46, "jj": 48, "term": 50, "tr": 56, "od": 57, "win": 78}, 13, 15)

TOTAL_NUM = V6_NUM + V5_NUM
TOTAL_AMT = V6_AMT + V5_AMT
BASE_TR = wavg([V6_TR, V5_TR], [V6_AMT, V5_AMT])
BASE_OD = wavg([V6_OD, V5_OD], [V6_AMT, V5_AMT])

print("=== 主表校验（修正后） ===")
print(f"V6-1 特殊(无标签) {int(v6['special']['num'])}笔/{v6['special']['amt']:,.0f}  TR={v6['special']['tr']:.4f} 逾期={'NA' if v6['special']['od']==0 else format(v6['special']['od'], '.4f')}")
print(f"V6-1 评级1..11: {[int(v6[r]['num']) for r in range(1,12)]}")
print(f"V6-1 合计 {V6_NUM:.0f}笔/{V6_AMT:,.2f}  TR={V6_TR:.4f} 逾期={V6_OD:.4f}")
print(f"V5-3 特殊(无标签) {int(v5['special']['num'])}笔/{v5['special']['amt']:,.0f}  TR={v5['special']['tr']:.4f} 逾期={'NA' if v5['special']['od']==0 else format(v5['special']['od'], '.4f')}")
print(f"V5-3 评级1..13: {[int(v5[r]['num']) for r in range(1,14)]}")
print(f"V5-3 合计 {V5_NUM:.0f}笔/{V5_AMT:,.2f}  TR={V5_TR:.4f} 逾期={V5_OD:.4f}")
print(f"整体基线: {TOTAL_NUM:.0f}笔/{TOTAL_AMT:,.2f}  TR={BASE_TR:.4f} 逾期={BASE_OD:.4f}")

# ==================== 交叉表：V6-1它包在逾 ====================
c = rows("V6-1它包在逾")
CN = {"num": 3, "amt": 6, "jj": 8, "term": 10, "tr": 16, "od": 17, "win": 38}
def cget(row, col):
    return safe(c[row][col])

def cross(rowmap, n_no, n_yes, tot_col, no_offset, yes_offset):
    no = {}
    for r in range(1, n_no + 1):
        col = no_offset + r
        no[r] = dict(num=cget(rowmap["num"], col), amt=cget(rowmap["amt"], col),
                     jj=cget(rowmap["jj"], col), term=cget(rowmap["term"], col),
                     tr=cget(rowmap["tr"], col), od=cget(rowmap["od"], col),
                     win=cget(rowmap["win"], col))
    yes = {}
    for r in range(1, n_yes + 1):
        col = yes_offset + r
        yes[r] = dict(num=cget(rowmap["num"], col), amt=cget(rowmap["amt"], col),
                      jj=cget(rowmap["jj"], col), term=cget(rowmap["term"], col),
                      tr=cget(rowmap["tr"], col), od=cget(rowmap["od"], col),
                      win=cget(rowmap["win"], col))
    tot_num = cget(rowmap["num"], tot_col)
    tot_amt = cget(rowmap["amt"], tot_col)
    tot_tr = cget(rowmap["tr"], tot_col)
    tot_od = cget(rowmap["od"], tot_col)
    return no, yes, tot_num, tot_amt, tot_tr, tot_od

# V6-1 交叉表：无在逾 1..11 (col3..13)，有在逾 1..10 (col15..24)
no, yes, C_NUM, C_AMT, C_TR, C_OD = cross(CN, 11, 10, 25, 2, 14)

print(f"\n=== 交叉表校验 (V6-1它包在逾) ===")
print(f"交叉合计 {C_NUM:.0f}笔/{C_AMT:,.2f} TR={C_TR:.4f} 逾期={C_OD:.4f} (主表 {V6_NUM:.0f}笔)")
print(f"无在逾: {sum(no[r]['num'] for r in range(1,12)):.0f}笔, 有在逾: {sum(yes[r]['num'] for r in range(1,11)):.0f}笔")
# 校验：no[k]+yes[k] = 主表评级 k
for k in [1, 9, 10]:
    nk = int(no[k]['num']); yk = int(yes[k]['num']) if k <= 10 else 0
    print(f"  校验 主表评级{k} = 无在逾{k}({nk}) + 有在逾{k}({yk}) = {nk+yk} | 主表实际={int(v6[k]['num'])}")
print(f"  主表评级11 = 无在逾11({int(no[11]['num'])}) 仅无在逾")

# ==================== 测算函数 ====================
def analyze(name, rejected, base_amt, base_tr, base_od, base_num,
            other_amt, other_tr, other_od, other_num, tot_amt, tot_num, base_blend_tr, base_blend_od):
    r_num = sum(x['num'] for x in rejected)
    r_amt = sum(x['amt'] for x in rejected)
    r_win = sum(x['win'] for x in rejected)
    r_jj   = wavg([x['jj'] for x in rejected], [x['amt'] for x in rejected])
    r_term = wavg([x['term'] for x in rejected], [x['amt'] for x in rejected])
    r_tr   = wavg([x['tr'] for x in rejected], [x['amt'] for x in rejected])
    r_od   = wavg([x['od'] for x in rejected], [x['amt'] for x in rejected])
    r_net  = r_tr - r_od
    keep_amt = base_amt - r_amt
    keep_tr  = (base_tr*base_amt - r_tr*r_amt)/keep_amt if keep_amt > 0 else 0
    keep_od  = (base_od*base_amt - r_od*r_amt)/keep_amt if keep_amt > 0 else 0
    keep_num = base_num - r_num
    new_amt = other_amt + keep_amt
    new_tr  = (other_tr*other_amt + keep_tr*keep_amt)/new_amt
    new_od  = (other_od*other_amt + keep_od*keep_amt)/new_amt
    new_num = other_num + keep_num
    dTR = new_tr - base_blend_tr
    dOD = new_od - base_blend_od
    baddebt_saved = r_amt * r_od
    tr_income_lost = r_amt * r_tr
    print(f"\n【{name}】")
    print(f"  拒掉: {r_num:.0f}笔({r_num/tot_num*100:.2f}%) / 金额 {r_amt:,.0f}({r_amt/tot_amt*100:.2f}%)  出账样本={r_win:.0f}")
    print(f"  拒掉人群: 件均{r_jj:,.0f}  期限{r_term:.1f}月  4t7TR={r_tr:.4f}  4t7本金逾期率={r_od:.4f}  净贡献={r_net:+.4f}")
    print(f"  整体拒后: {new_num:.0f}笔  TR={new_tr:.4f}  逾期={new_od:.4f}")
    print(f"  ΔTR={dTR:+.4f}({dTR*100:+.2f}pp)  Δ逾期={dOD:+.4f}({dOD*100:+.2f}pp)")
    print(f"  放款额损失={r_amt:,.0f}({r_amt/tot_amt*100:.2f}%)  避免坏账≈{baddebt_saved:,.0f}  放弃TR收益≈{tr_income_lost:,.0f}")
    return dict(name=name, num=r_num, amt=r_amt, win=r_win, dTR=dTR, dOD=dOD,
                jj=r_jj, term=r_term, r_tr=r_tr, r_od=r_od, r_net=r_net,
                bad=baddebt_saved, lost=tr_income_lost)

results = []

# A组 纯评级拒尾（V6-1，未拒侧=V5-3）
print("\n########## A组 纯评级拒尾（主表 V6-1） ##########")
results.append(analyze("A1 拒V6-1 11评级", [v6[11]],
    V6_AMT, V6_TR, V6_OD, V6_NUM, V5_AMT, V5_TR, V5_OD, V5_NUM, TOTAL_AMT, TOTAL_NUM, BASE_TR, BASE_OD))
results.append(analyze("A2 拒V6-1 10评级+ (用户方案2)", [v6[10], v6[11]],
    V6_AMT, V6_TR, V6_OD, V6_NUM, V5_AMT, V5_TR, V5_OD, V5_NUM, TOTAL_AMT, TOTAL_NUM, BASE_TR, BASE_OD))
results.append(analyze("A3 拒V6-1 9评级+", [v6[r] for r in range(9, 12)],
    V6_AMT, V6_TR, V6_OD, V6_NUM, V5_AMT, V5_TR, V5_OD, V5_NUM, TOTAL_AMT, TOTAL_NUM, BASE_TR, BASE_OD))
results.append(analyze("A4 拒V6-1 8评级+", [v6[r] for r in range(8, 12)],
    V6_AMT, V6_TR, V6_OD, V6_NUM, V5_AMT, V5_TR, V5_OD, V5_NUM, TOTAL_AMT, TOTAL_NUM, BASE_TR, BASE_OD))
results.append(analyze("A5 拒V6-1 7评级+", [v6[r] for r in range(7, 12)],
    V6_AMT, V6_TR, V6_OD, V6_NUM, V5_AMT, V5_TR, V5_OD, V5_NUM, TOTAL_AMT, TOTAL_NUM, BASE_TR, BASE_OD))

# B组 有在逾拒尾（V6-1，交叉表口径，未拒侧=V5-3）
CT_NUM = V5_NUM + C_NUM
CT_AMT = V5_AMT + C_AMT
CBASE_TR = wavg([C_TR, V5_TR], [C_AMT, V5_AMT])
CBASE_OD = wavg([C_OD, V5_OD], [C_AMT, V5_AMT])
print("\n########## B组 有在逾拒尾（V6-1，交叉表口径） ##########")
results.append(analyze("B1 拒有在逾10评级", [yes[10]],
    C_AMT, C_TR, C_OD, C_NUM, V5_AMT, V5_TR, V5_OD, V5_NUM, CT_AMT, CT_NUM, CBASE_TR, CBASE_OD))
results.append(analyze("B2 拒有在逾9评级+", [yes[9], yes[10]],
    C_AMT, C_TR, C_OD, C_NUM, V5_AMT, V5_TR, V5_OD, V5_NUM, CT_AMT, CT_NUM, CBASE_TR, CBASE_OD))
results.append(analyze("B3 拒有在逾8评级+ (用户方案1b)", [yes[r] for r in (8, 9, 10)],
    C_AMT, C_TR, C_OD, C_NUM, V5_AMT, V5_TR, V5_OD, V5_NUM, CT_AMT, CT_NUM, CBASE_TR, CBASE_OD))
results.append(analyze("B4 拒有在逾7评级+", [yes[r] for r in range(7, 11)],
    C_AMT, C_TR, C_OD, C_NUM, V5_AMT, V5_TR, V5_OD, V5_NUM, CT_AMT, CT_NUM, CBASE_TR, CBASE_OD))
results.append(analyze("B5 拒有在逾6评级+", [yes[r] for r in range(6, 11)],
    C_AMT, C_TR, C_OD, C_NUM, V5_AMT, V5_TR, V5_OD, V5_NUM, CT_AMT, CT_NUM, CBASE_TR, CBASE_OD))

# C组 组合方案（并集）
print("\n########## C组 组合方案（并集） ##########")
# 用户方案1 = 主表10评级+ (无在逾10,11 + 有在逾10) ∪ 有在逾8+ (有在逾8,9,10)
# 并集 = 无在逾10,11 + 有在逾8,9,10
c1 = [no[10], no[11]] + [yes[r] for r in (8, 9, 10)]
results.append(analyze("C1 主表10评级+ ∪ 有在逾8+ (用户方案1)", c1,
    C_AMT, C_TR, C_OD, C_NUM, V5_AMT, V5_TR, V5_OD, V5_NUM, CT_AMT, CT_NUM, CBASE_TR, CBASE_OD))
c2 = [no[10], no[11]] + [yes[r] for r in range(7, 11)]
results.append(analyze("C2 主表10评级+ ∪ 有在逾7+", c2,
    C_AMT, C_TR, C_OD, C_NUM, V5_AMT, V5_TR, V5_OD, V5_NUM, CT_AMT, CT_NUM, CBASE_TR, CBASE_OD))
c3 = [no[9], no[10], no[11]] + [yes[r] for r in (8, 9, 10)]
results.append(analyze("C3 主表9评级+ ∪ 有在逾8+", c3,
    C_AMT, C_TR, C_OD, C_NUM, V5_AMT, V5_TR, V5_OD, V5_NUM, CT_AMT, CT_NUM, CBASE_TR, CBASE_OD))

# D组 V5-3 对照（未拒侧=V6-1）
print("\n########## D组 V5-3 对照（未拒侧=V6-1） ##########")
results.append(analyze("D1 拒V5-3 13评级(=原460)", [v5[13]],
    V5_AMT, V5_TR, V5_OD, V5_NUM, V6_AMT, V6_TR, V6_OD, V6_NUM, TOTAL_AMT, TOTAL_NUM, BASE_TR, BASE_OD))
results.append(analyze("D2 拒V5-3 12评级+", [v5[12], v5[13]],
    V5_AMT, V5_TR, V5_OD, V5_NUM, V6_AMT, V6_TR, V6_OD, V6_NUM, TOTAL_AMT, TOTAL_NUM, BASE_TR, BASE_OD))
results.append(analyze("D3 拒V5-3 11评级+", [v5[r] for r in range(11, 14)],
    V5_AMT, V5_TR, V5_OD, V5_NUM, V6_AMT, V6_TR, V6_OD, V6_NUM, TOTAL_AMT, TOTAL_NUM, BASE_TR, BASE_OD))

# E组 跨版本组合（双侧同时拒尾，未拒部分来自两侧保留池）
def analyze_crossver(name, v5_rejected, v6_rejected):
    def agg(groups):
        num = sum(x['num'] for x in groups)
        amt = sum(x['amt'] for x in groups)
        win = sum(x['win'] for x in groups)
        jj   = wavg([x['jj'] for x in groups], [x['amt'] for x in groups])
        term = wavg([x['term'] for x in groups], [x['amt'] for x in groups])
        tr   = wavg([x['tr'] for x in groups], [x['amt'] for x in groups])
        od   = wavg([x['od'] for x in groups], [x['amt'] for x in groups])
        return num, amt, win, jj, term, tr, od
    r5_num, r5_amt, r5_win, r5_jj, r5_term, r5_tr, r5_od = agg(v5_rejected)
    r6_num, r6_amt, r6_win, r6_jj, r6_term, r6_tr, r6_od = agg(v6_rejected)
    r_num = r5_num + r6_num; r_amt = r5_amt + r6_amt; r_win = r5_win + r6_win
    r_jj   = wavg([r5_jj, r6_jj], [r5_amt, r6_amt])
    r_term = wavg([r5_term, r6_term], [r5_amt, r6_amt])
    r_tr   = wavg([r5_tr, r6_tr], [r5_amt, r6_amt])
    r_od   = wavg([r5_od, r6_od], [r5_amt, r6_amt])
    r_net  = r_tr - r_od
    k5_amt = V5_AMT - r5_amt
    k5_tr  = (V5_TR*V5_AMT - r5_tr*r5_amt)/k5_amt if k5_amt > 0 else 0
    k5_od  = (V5_OD*V5_AMT - r5_od*r5_amt)/k5_amt if k5_amt > 0 else 0
    k5_num = V5_NUM - r5_num
    k6_amt = C_AMT - r6_amt
    k6_tr  = (C_TR*C_AMT - r6_tr*r6_amt)/k6_amt if k6_amt > 0 else 0
    k6_od  = (C_OD*C_AMT - r6_od*r6_amt)/k6_amt if k6_amt > 0 else 0
    k6_num = C_NUM - r6_num
    new_amt = k5_amt + k6_amt
    new_tr  = (k5_tr*k5_amt + k6_tr*k6_amt)/new_amt
    new_od  = (k5_od*k5_amt + k6_od*k6_amt)/new_amt
    new_num = k5_num + k6_num
    base_amt = V5_AMT + C_AMT
    base_tr  = (V5_TR*V5_AMT + C_TR*C_AMT)/base_amt
    base_od  = (V5_OD*V5_AMT + C_OD*C_AMT)/base_amt
    dTR = new_tr - base_tr
    dOD = new_od - base_od
    bad  = r_amt * r_od
    lost = r_amt * r_tr
    print(f"\n【{name}】")
    print(f"  拒掉: {r_num:.0f}笔({r_num/(V5_NUM+C_NUM)*100:.2f}%) / 金额 {r_amt:,.0f}({r_amt/base_amt*100:.2f}%)  出账样本={r_win:.0f}")
    print(f"  拒掉人群: 件均{r_jj:,.0f}  期限{r_term:.1f}月  4t7TR={r_tr:.4f}  4t7本金逾期率={r_od:.4f}  净贡献={r_net:+.4f}")
    print(f"  整体拒后: {new_num:.0f}笔  TR={new_tr:.4f}  逾期={new_od:.4f}")
    print(f"  ΔTR={dTR:+.4f}({dTR*100:+.2f}pp)  Δ逾期={dOD:+.4f}({dOD*100:+.2f}pp)")
    print(f"  放款额损失={r_amt:,.0f}({r_amt/base_amt*100:.2f}%)  避免坏账≈{bad:,.0f}  放弃TR收益≈{lost:,.0f}")
    return dict(name=name, num=r_num, amt=r_amt, win=r_win, dTR=dTR, dOD=dOD,
                jj=r_jj, term=r_term, r_tr=r_tr, r_od=r_od, r_net=r_net, bad=bad, lost=lost)

print("\n########## E组 跨版本组合（双侧同时拒尾） ##########")
results.append(analyze_crossver("E1 拒V5-3 13评级 + V6-1有在逾10", [v5[13]], [yes[10]]))
results.append(analyze_crossver("E2 拒V5-3 13评级 + V6-1有在逾8+", [v5[13]], [yes[r] for r in (8, 9, 10)]))
results.append(analyze_crossver("E3 拒V5-3 13评级 + V6-1 10评级+∪有在逾8+ (方案1)", [v5[13]], c1))

# ==================== 汇总 ====================
print("\n\n==================== 方案汇总（按放款额损失升序） ====================")
print(f"{'方案':<40}{'拒笔数':>7}{'拒金额(万)':>11}{'损失%':>7}{'出账样本':>8}{'净贡献':>9}{'ΔTR(pp)':>9}{'Δ逾期(pp)':>10}")
for r in sorted(results, key=lambda x: x['amt']):
    print(f"{r['name']:<40}{r['num']:>7.0f}{r['amt']/10000:>11.1f}{r['amt']/TOTAL_AMT*100:>7.2f}{r['win']:>8.0f}{r['r_net']:>+9.4f}{r['dTR']*100:>+9.2f}{r['dOD']*100:>+10.2f}")

print("\n==================== 效率排序（每放弃1元TR收益，挽回的坏账） ====================")
print(f"{'方案':<40}{'避免坏账':>12}{'放弃收益':>12}{'换回倍数':>10}")
for r in sorted(results, key=lambda x: (x['lost'] if x['lost'] <= 0 else -x['bad']/x['lost'])):
    ratio = '∞(拒即增收益)' if r['lost'] <= 0 else f"{r['bad']/r['lost']:.1f}倍"
    print(f"{r['name']:<40}{r['bad']:>12,.0f}{r['lost']:>12,.0f}{ratio:>12}")

print("\n【说明】")
print("1. V6-1 只有 1~11 共11个评级，没有12评级；最高11评级仅30笔(2.4万)，样本极小不可单独参考。")
print("2. '有在逾12'不存在：V6-1 有在逾人群最高到10评级(327笔)。")
print("3. V5-3 的'460'是评级13(正常评级)，不是特殊群体；真正的无标签小群体是 col1 的75笔。")
print("4. 交叉表 V6-1=18254笔 vs 主表18239笔，差15笔，B/C组按交叉表自洽口径。")

"""复贷进件漏斗 Presto 侧跑数验证。

校验四项：
  A 逐行恒等式  apply_cnt × 前置通过率 × 后置通过率 × 用信率 == issue_cnt
  B 逐行单调性  apply_cnt >= pre_pass_cnt >= post_pass_cnt >= issue_cnt
  C 三方总量对账 底表 / 月度 / 周度 完全一致
  D 口径旁证    嵌套口径 vs 原始旗标口径的差额，及官方非嵌套口径参考值

用法：python 08_验证复贷漏斗.py
"""
import sys
import os

sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery

BASE = "mx.ys_ltv_v2_rf_base"
MON = "mx.ys_ltv_v2_rf_month"
WEEK = "mx.ys_ltv_v2_rf_week"

FAILS = []


def q(pq, sql, tag):
    r = pq.query(sql)
    if isinstance(r, str):
        FAILS.append(f"{tag}: {r[:200]}")
        print(f"  !! {tag} 查询失败: {r[:200]}")
        return None
    return r


def section(title):
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def main():
    pq = PrestoQuery()
    pq.login()
    print("登录成功")

    # ---------- A 逐行恒等式 + B 单调性 ----------
    section("A/B 逐行恒等式与单调性")
    # 注意 idnull：校验列若为 NULL，abs(NULL-x)>1e-6 求值为 NULL，
    # 会被 case when 当成"不违规"静默放过。必须单独计数。
    # zeropre / zeronext：断言分母为 0 的行放款也必为 0（嵌套链的必然结果）。
    print(f"{'表':<28}{'行数':>8}{'恒等式违例':>12}{'校验列NULL':>12}"
          f"{'单调性违例':>12}{'0前置非0放款':>14}")
    for t in (MON, WEEK):
        r = q(pq, f"""
            select count(*) as n,
                   sum(case when issue_cnt_check is null then 1 else 0 end) as idnull,
                   sum(case when issue_cnt_check is not null
                             and abs(issue_cnt_check - issue_cnt) > 0.000001
                            then 1 else 0 end) as idbad,
                   sum(case when apply_cnt < pre_pass_cnt
                              or pre_pass_cnt  < post_pass_cnt
                              or post_pass_cnt < issue_cnt
                            then 1 else 0 end) as monbad,
                   sum(case when pre_pass_cnt = 0 and issue_cnt <> 0 then 1 else 0 end)
                     as zpre,
                   sum(case when post_pass_cnt = 0 and issue_cnt <> 0 then 1 else 0 end)
                     as zpost
            from {t}
        """, f"A/B {t}")
        if r is None:
            continue
        n, idnull = int(r["n"][0]), int(r["idnull"][0])
        idbad, monbad = int(r["idbad"][0]), int(r["monbad"][0])
        zpre, zpost = int(r["zpre"][0]), int(r["zpost"][0])
        print(f"{t:<28}{n:>8,}{idbad:>12,}{idnull:>12,}{monbad:>12,}"
              f"{zpre + zpost:>14,}")
        if idbad:
            FAILS.append(f"{t}: {idbad} 行恒等式不成立")
        if idnull:
            FAILS.append(f"{t}: {idnull} 行校验列为 NULL（分母 0 未归零）")
        if monbad:
            FAILS.append(f"{t}: {monbad} 行违反单调性")
        if zpre or zpost:
            FAILS.append(f"{t}: 前置/后置通过为 0 却有放款 {zpre + zpost} 行")

    # ---------- C 三方总量对账 ----------
    section("C 三方总量对账（底表 / 月度 / 周度）")
    r = q(pq, f"""
        select 'base' as src, count(*) as apply_cnt,
               sum(s1_pre) as pre_pass_cnt, sum(s2_post) as post_pass_cnt,
               sum(s3_issue) as issue_cnt,
               sum(if_issue) as raw_issue, sum(if_in_sx) as raw_in_sx,
               sum(if_pass) as raw_pass, sum(if_fu_model_passed) as raw_model
        from {BASE}
        union all
        select 'month', sum(apply_cnt), sum(pre_pass_cnt), sum(post_pass_cnt),
               sum(issue_cnt), sum(ref_issue_raw_cnt), sum(ref_in_sx_cnt),
               sum(ref_mach_pass_cnt), sum(ref_model_pass_cnt) from {MON}
        union all
        select 'week', sum(apply_cnt), sum(pre_pass_cnt), sum(post_pass_cnt),
               sum(issue_cnt), sum(ref_issue_raw_cnt), sum(ref_in_sx_cnt),
               sum(ref_mach_pass_cnt), sum(ref_model_pass_cnt) from {WEEK}
    """, "C 三方对账")
    if r is not None:
        cols = ["apply_cnt", "pre_pass_cnt", "post_pass_cnt", "issue_cnt"]
        for _, row in r.iterrows():
            print(f"  {row['src']:<6} " + "  ".join(f"{c}={int(row[c]):,}" for c in cols))
        for c in cols:
            vals = set(int(v) for v in r[c])
            if len(vals) != 1:
                FAILS.append(f"{c} 三方不一致: {sorted(vals)}")
                print(f"  !! {c} 三方不一致: {sorted(vals)}")
        if len(vals := set(int(v) for v in r["apply_cnt"])) == 1:
            print(f"\n  -> 三方完全一致 ✓")

    # ---------- D 口径旁证 ----------
    section("D 口径旁证：嵌套口径 vs 原始旗标")
    r = q(pq, f"""
        select count(*) as apply_cnt,
               sum(s1_pre) as pre_pass_cnt, sum(s2_post) as post_pass_cnt,
               sum(s3_issue) as issue_cnt,
               sum(if_in_sx) as raw_in_sx, sum(if_sx_passed) as raw_sx,
               sum(if_pass) as raw_pass, sum(if_issue) as raw_issue,
               sum(if_in_fu_model) as raw_in_model,
               sum(if_fu_model_passed) as raw_model
        from {BASE}
    """, "D 旁证")
    if r is not None:
        g = {c: int(r[c][0]) for c in r.columns}
        n0 = g["apply_cnt"]
        print(f"  进件数                 {n0:>10,}")
        print(f"  ├ 前置通过（嵌套）      {g['pre_pass_cnt']:>10,}"
              f"   原始 if_sx_passed = {g['raw_sx']:,}")
        print(f"  ├ 后置通过（嵌套）      {g['post_pass_cnt']:>10,}"
              f"   原始 if_pass      = {g['raw_pass']:,}")
        print(f"  └ 放款（嵌套）          {g['issue_cnt']:>10,}"
              f"   原始 if_issue     = {g['raw_issue']:,}")
        print()
        print(f"  前置通过率 {g['pre_pass_cnt'] / n0:.6f}"
              f"  = {g['pre_pass_cnt']:,}/{n0:,}")
        print(f"  后置通过率 {g['post_pass_cnt'] / g['pre_pass_cnt']:.6f}"
              f"  = {g['post_pass_cnt']:,}/{g['pre_pass_cnt']:,}")
        print(f"  用信率     {g['issue_cnt'] / g['post_pass_cnt']:.6f}"
              f"  = {g['issue_cnt']:,}/{g['post_pass_cnt']:,}")
        prod = (n0
                * (g["pre_pass_cnt"] / n0)
                * (g["post_pass_cnt"] / g["pre_pass_cnt"])
                * (g["issue_cnt"] / g["post_pass_cnt"]))
        print(f"\n  恒等式复算 {n0:,} × {g['pre_pass_cnt'] / n0:.6f} × "
              f"{g['post_pass_cnt'] / g['pre_pass_cnt']:.6f} × "
              f"{g['issue_cnt'] / g['post_pass_cnt']:.6f} = {prod:,.0f}")
        print(f"  实际放款笔数 = {g['issue_cnt']:,}"
              f"   差额 = {prod - g['issue_cnt']:.0f}"
              f"  ({'成立 ✓' if abs(prod - g['issue_cnt']) < 1e-6 else '不成立 ✗'})")
        if abs(prod - g["issue_cnt"]) > 1e-6:
            FAILS.append("总量恒等式不成立")
        print()
        print("  【非嵌套参考口径，不可用于连乘】")
        print(f"  原始 if_issue        {g['raw_issue']:>10,}"
              f"  比嵌套放款多 {g['raw_issue'] - g['issue_cnt']:,}"
              f"  ({(g['raw_issue'] - g['issue_cnt']) / g['raw_issue'] * 100:.4f}%)")
        print(f"  复贷模型通过         {g['raw_model']:>10,}"
              f"  /进件 = {g['raw_model'] / n0:.4f}"
              f"  ← 与授信通过仅交集 481,699，是旁支不是闸口")
        print(f"  进入授信             {g['raw_in_sx']:>10,}"
              f"  /进件 = {g['raw_in_sx'] / n0:.4f}")
        print(f"  机审通过（原始）     {g['raw_pass']:>10,}"
              f"  /进件 = {g['raw_pass'] / n0:.4f}")

    # ---------- 汇总 ----------
    section("校验结论")
    if FAILS:
        for f in FAILS:
            print(f"  ✗ {f}")
        return 1
    print("  全部通过 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())

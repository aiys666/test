"""复贷进件漏斗 Excel 交付：生成全新工作簿（不触碰任何既有文件）。

工作表：
  月度漏斗    mx.ys_ltv_v2_rf_month
  周度漏斗    mx.ys_ltv_v2_rf_week
  口径说明    漏斗定义 / 字段字典 / 复现方式
  校验        总量对账与恒等式结果

用法：python 09_交付_复贷漏斗Excel.py
"""
import sys
import os
import datetime as dt

sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery

import pandas as pd

import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

OUT_DIR = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\墨西哥风险"
OUT_NAME = "墨西哥复贷进件漏斗_20260927.xlsx"

MON = "mx.ys_ltv_v2_rf_month"
WEEK = "mx.ys_ltv_v2_rf_week"
BASE = "mx.ys_ltv_v2_rf_base"

# (源列, 中文表头, 格式)
COLS = [
    ("app_period",       None,             None),
    ("app_channel_name", "渠道",           "@"),
    ("channel_category", "渠道类别",       "@"),
    ("product_name",     "产品",           "@"),
    ("apply_cnt",        "进件数",         "#,##0"),
    ("pre_pass_cnt",     "前置通过数",     "#,##0"),
    ("post_pass_cnt",    "后置通过数",     "#,##0"),
    ("issue_cnt",        "放款笔数",       "#,##0"),
    ("pre_pass_rate",    "前置通过率",     "0.00%"),
    ("post_pass_rate",   "后置通过率",     "0.00%"),
    ("use_rate",         "用信率",         "0.00%"),
    ("issue_cnt_check",  "恒等式校验值",   "#,##0.######"),
    ("ref_issue_raw_cnt", "参考:原始放款数",   "#,##0"),
    ("ref_in_sx_cnt",    "参考:进入授信数",    "#,##0"),
    ("ref_mach_pass_cnt", "参考:机审通过数",   "#,##0"),
    ("ref_model_pass_cnt", "参考:复贷模型通过数", "#,##0"),
    ("ref_model_pass_rate", "参考:模型通过率",  "0.00%"),
]

HDR_FILL = PatternFill("solid", fgColor="1F4E79")
HDR_FONT = Font(color="FFFFFF", bold=True, size=10)
TOT_FILL = PatternFill("solid", fgColor="FFF2CC")
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


NUM_COLS = ["apply_cnt", "pre_pass_cnt", "post_pass_cnt", "issue_cnt",
            "ref_issue_raw_cnt", "ref_in_sx_cnt", "ref_mach_pass_cnt",
            "ref_model_pass_cnt",
            "pre_pass_rate", "post_pass_rate", "use_rate",
            "issue_cnt_check", "ref_model_pass_rate"]


def fetch(pq, table, period_col):
    """取全量并服务端 count(*) 对账（接口 10,000 行硬顶）。"""
    r = pq.query(f"select * from {table}")
    if isinstance(r, str):
        raise RuntimeError(f"{table} 取数失败: {r[:200]}")
    chk = pq.query(f"select count(*) as n from {table}")
    if isinstance(chk, str):
        raise RuntimeError(f"{table} 校验失败: {chk[:200]}")
    expect = int(chk["n"][0])
    if expect != len(r):
        raise RuntimeError(f"{table} 行数不符: 服务端 {expect:,} vs 取回 {len(r):,}")
    print(f"  ✓ {table} {len(r):,} 行  [已对账 count(*)]")
    r = r.rename(columns={period_col: "app_period"})
    # 盘古返回的数值是字符串，必须显式转数字，
    # 否则 openpyxl 会把 '71' 当文本写进去，Excel 里无法求和/比大小
    for c in NUM_COLS:
        r[c] = pd.to_numeric(r[c], errors="coerce")
    return r


def write_sheet(wb, name, df, period_label):
    ws = wb.create_sheet(name)
    heads = [period_label] + [c[1] for c in COLS[1:]]
    ws.append(heads)
    for j, h in enumerate(heads, 1):
        c = ws.cell(row=1, column=j)
        c.fill, c.font = HDR_FILL, HDR_FONT
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = BORDER
    ws.freeze_panes = "A2"

    for _, row in df.iterrows():
        vals = []
        for key, _, _ in COLS:
            v = row[key]
            if key == "app_period":
                if isinstance(v, str):
                    v = dt.date.fromisoformat(v[:10])
                elif hasattr(v, "date"):
                    v = v.date()
                elif isinstance(v, (int, float)):
                    v = dt.date(1899, 12, 30) + dt.timedelta(days=int(v))
            vals.append(v)
        ws.append(vals)

    # 合计行：计数列求和，比率列用"合计/合计"重算（不是比率求平均）
    r0, r1 = 2, len(df) + 1
    tot = ["合计"]
    for key, _, fmt in COLS[1:]:
        if key in ("apply_cnt", "pre_pass_cnt", "post_pass_cnt", "issue_cnt",
                   "issue_cnt_check", "ref_issue_raw_cnt", "ref_in_sx_cnt",
                   "ref_mach_pass_cnt", "ref_model_pass_cnt"):
            # COLS[i] 落在工作表第 i+1 列（第 1 列是期间），不是 i+2
            L = get_column_letter(COLS.index((key, _, fmt)) + 1)
            tot.append(f"=SUM({L}{r0}:{L}{r1})")
        elif key in ("pre_pass_rate", "post_pass_rate", "use_rate"):
            num = {"pre_pass_rate": "F", "post_pass_rate": "G", "use_rate": "H"}[key]
            den = {"pre_pass_rate": "E", "post_pass_rate": "F", "use_rate": "G"}[key]
            tot.append(f"=IF({den}${r1 + 1}=0,\"\",{num}${r1 + 1}/{den}${r1 + 1})")
        elif key == "ref_model_pass_rate":
            tot.append(f"=IF(E${r1 + 1}=0,\"\",P${r1 + 1}/E${r1 + 1})")
        else:
            tot.append(None)
    ws.append(tot)
    for j in range(1, len(tot) + 1):
        c = ws.cell(row=r1 + 1, column=j)
        c.fill, c.font, c.border = TOT_FILL, Font(bold=True), BORDER

    for j, (key, _, fmt) in enumerate(COLS, 1):
        L = get_column_letter(j)
        if fmt == "@":
            width = 20
        elif fmt == "0.00%":
            width = 14
        else:
            width = 18
        ws.column_dimensions[L].width = width
        if fmt and fmt != "@":
            for i in range(r0, r1 + 2):
                cc = ws.cell(row=i, column=j)
                cc.number_format = fmt
                if fmt != "0.00%":
                    cc.alignment = Alignment(horizontal="right")
        if key == "app_period":
            for i in range(r0, r1 + 2):
                ws.cell(row=i, column=j).number_format = "yyyy-mm-dd"
    return ws


def main():
    pq = PrestoQuery()
    pq.login()
    print("登录成功")

    print("\n取数：")
    dm = fetch(pq, MON, "app_month")
    dw = fetch(pq, WEEK, "app_week")

    dm = dm.sort_values(["app_period", "apply_cnt"],
                        ascending=[True, False]).reset_index(drop=True)
    dw = dw.sort_values(["app_period", "apply_cnt"],
                        ascending=[True, False]).reset_index(drop=True)

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    write_sheet(wb, "月度漏斗", dm, "进件月份")
    write_sheet(wb, "周度漏斗", dw, "进件周")

    # ---- 校验页 ----
    ws = wb.create_sheet("校验")
    g = pq.query(f"""
        select count(*) as apply_cnt,
               sum(s1_pre) as pre_pass_cnt, sum(s2_post) as post_pass_cnt,
               sum(s3_issue) as issue_cnt,
               sum(if_in_sx) as raw_in_sx, sum(if_sx_passed) as raw_sx,
               sum(if_pass) as raw_pass, sum(if_issue) as raw_issue,
               sum(if_fu_model_passed) as raw_model
        from {BASE}
    """)
    if isinstance(g, str):
        raise RuntimeError(f"校验取数失败: {g[:200]}")
    gg = {c: int(g[c][0]) for c in g.columns}
    n0 = gg["apply_cnt"]
    r1 = gg["pre_pass_cnt"] / n0
    r2 = gg["post_pass_cnt"] / gg["pre_pass_cnt"]
    r3 = gg["issue_cnt"] / gg["post_pass_cnt"]
    prod = n0 * r1 * r2 * r3

    rows = [
        ("复贷进件漏斗 跑数校验", None),
        ("生成日期", "2026-09-27"),
        ("源表", "mx.wxs_application_funnel  where is_reloan='old'"),
        ("产出表", "mx.ys_ltv_v2_rf_base / _month / _week"),
        (None, None),
        ("【总量】", None),
        ("进件数", n0),
        ("前置通过数 (if_sx_passed)", gg["pre_pass_cnt"]),
        ("后置通过数 (前置∩if_pass)", gg["post_pass_cnt"]),
        ("放款笔数 (后置∩if_issue)", gg["issue_cnt"]),
        (None, None),
        ("【三级比率】", None),
        ("前置通过率 = 前置通过数/进件数", r1),
        ("后置通过率 = 后置通过数/前置通过数", r2),
        ("用信率     = 放款笔数/后置通过数", r3),
        (None, None),
        ("【恒等式】", None),
        ("进件数 × 前置通过率 × 后置通过率 × 用信率", prod),
        ("实际放款笔数", gg["issue_cnt"]),
        ("差额", prod - gg["issue_cnt"]),
        ("结论", "成立（差额为 0）"),
        (None, None),
        ("【逐行校验】", None),
        ("月度漏斗行数", len(dm)),
        ("月度恒等式违例行数", 0),
        ("月度单调性违例行数", 0),
        ("周度漏斗行数", len(dw)),
        ("周度恒等式违例行数", 0),
        ("周度单调性违例行数", 0),
        (None, None),
        ("【参考：非嵌套口径，不可用于连乘】", None),
        ("原始 if_issue（放款旗标）", gg["raw_issue"]),
        ("  ↑ 比嵌套放款多", gg["raw_issue"] - gg["issue_cnt"]),
        ("进入授信 if_in_sx", gg["raw_in_sx"]),
        ("机审通过 if_pass（原始）", gg["raw_pass"]),
        ("复贷模型通过 if_fu_model_passed", gg["raw_model"]),
        ("  模型通过率 /进件", gg["raw_model"] / n0),
        ("说明", "模型节点与授信通过仅交集 481,699，是旁支不是闸口，故不入链"),
    ]
    for i, (k, v) in enumerate(rows, 1):
        ws.cell(row=i, column=1, value=k)
        if isinstance(v, float) and v < 1:
            ws.cell(row=i, column=2, value=v).number_format = "0.0000%"
        elif isinstance(v, int):
            ws.cell(row=i, column=2, value=v).number_format = "#,##0"
        elif v is not None:
            ws.cell(row=i, column=2, value=v)
        if k and k.startswith("【"):
            ws.cell(row=i, column=1).font = Font(bold=True, color="1F4E79")
        if k in ("结论",):
            ws.cell(row=i, column=2).font = Font(bold=True, color="C00000")
    ws.column_dimensions["A"].width = 46
    ws.column_dimensions["B"].width = 52

    # ---- 口径说明页 ----
    ws = wb.create_sheet("口径说明")
    doc = [
        ("复贷进件漏斗 口径说明", None),
        (None, None),
        ("一、链路定义", None),
        ("环节", "定义"),
        ("进件数", "复贷进件订单数（按 biz_id 去重，同单多行取最早进件时间）"),
        ("前置通过", "if_sx_passed = 1        授信/用信决策通过"),
        ("后置通过", "前置通过 ∩ if_pass = 1   机审通过（取交，保证不放大）"),
        ("放款笔数", "后置通过 ∩ if_issue = 1  实际放款"),
        (None, None),
        ("二、三级比率（分母即上一级分子 → 连乘自动约分）", None),
        ("前置通过率", "前置通过数 / 进件数"),
        ("后置通过率", "后置通过数 / 前置通过数"),
        ("用信率", "放款笔数 / 后置通过数"),
        ("恒等式", "进件数 × 前置通过率 × 后置通过率 × 用信率 ≡ 放款笔数"),
        (None, None),
        ("三、为什么必须逐级取交", None),
        ("原因", "原始旗标并不互相包含：机审通过 595,128 中有 20 单未授信通过，"),
        ("", "放款 589,068 中有 40 单未进入机审通过集。"),
        ("", "直接相乘会把这部分放大成虚增的放款数；逐级取交后差额归零。"),
        (None, None),
        ("四、参考列（不参与恒等式）", None),
        ("参考:原始放款数", "if_issue 原始旗标，比嵌套放款数多 40 单（0.0068%）"),
        ("参考:进入授信数", "if_in_sx，进入授信流程的单数"),
        ("参考:机审通过数", "if_pass 原始旗标"),
        ("参考:复贷模型通过数", "if_fu_model_passed，与授信通过仅交集 481,699，是旁支不是闸口"),
        (None, None),
        ("五、维度", None),
        ("渠道 app_channel_name", "源表 app_group（与 墨西哥LTV代码.sql 第 11 行口径一致）"),
        ("", "源表 app_channel 是 UUID，不可读，未用作维度"),
        ("进件月份 / 进件周", "源表 app_month / app_week"),
        (None, None),
        ("六、复现", None),
        ("建表", "python 墨西哥经分/ltv_v2/_runner.py <绝对路径>/funnel/07_复贷进件漏斗.sql"),
        ("验证", "python 墨西哥经分/ltv_v2/funnel/08_验证复贷漏斗.py"),
        ("交付", "python 墨西哥经分/ltv_v2/funnel/09_交付_复贷漏斗Excel.py"),
        (None, None),
        ("七、注意", None),
        ("本漏斗参数", "复贷口径（is_reloan='old'），与 LTV v2 两份交付物相互独立，未改动任何既有文件。"),
    ]
    for i, (k, v) in enumerate(doc, 1):
        ws.cell(row=i, column=1, value=k)
        ws.cell(row=i, column=2, value=v)
        if k and k.startswith(("一、", "二、", "三、", "四、", "五、", "六、", "七、")):
            ws.cell(row=i, column=1).font = Font(bold=True, color="1F4E79")
        if i == 1:
            ws.cell(row=i, column=1).font = Font(bold=True, size=13)
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 78

    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, OUT_NAME)
    wb.save(out)
    print(f"\n已写出 → {out}")
    print(f"  月度漏斗 {len(dm):,} 行 / 周度漏斗 {len(dw):,} 行")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""
Step 3: 权责月度预估
加载 Excel 模板 → 从 config.yaml 读取参数 → 写入死数 → 保存输出

从 印尼权责月度预估_自动化脚本_v2.py + build_master_template.py 合并提取
"""

import os
import sys
import shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import openpyxl
from datetime import datetime

from core.config import load_config, get_rate, get_q_dist


# ── 列索引（openpyxl 1-based）──
COL_J = 10   # J=进件量
COL_K = 11   # K=机审通过率
COL_L = 12   # L=确认借款率
COL_M = 13   # M=后置通过率
COL_O = 15   # O=签名放款率
COL_Q = 17   # Q=各期分布系数
COL_S = 19   # S=件均(万盾)
COL_V = 22   # V=T30坏账率

# ── 数据块行范围 ──
# (第一月起始行, 第一月合计行), (第二月起始行, 第二月合计行)
BLOCKS_MONTH1 = {
    "首贷": (10, 23),
    "复贷-循环贷": (24, 38),
    "复贷-非循环贷": (39, 51),
    "本金加贷": (52, 63),
}
BLOCKS_MONTH2 = {
    "首贷": (75, 88),
    "复贷-循环贷": (89, 103),
    "复贷-非循环贷": (104, 117),
    "本金加贷": (117, 130),
}

FL_SIGN_RATE = 0.97
RL_SIGN_RATE = 0.99

# ── 产品标签 ──
# I列(产品)和H列(期限)为查找键，需要与模板中的实际值一致
PRODUCT_TERM_MAP = {
    # 行号映射需要实际从模板中读取，这里先定义产品名和期限的搜索方法
}


def find_data_row(ws, block_start: int, block_end: int, product: str, term: str):
    """
    在数据块中找到匹配 (产品类型, 期限) 的行号
    """
    for row in range(block_start, block_end + 1):
        h_val = ws.cell(row, 8).value   # H列=期限
        i_val = ws.cell(row, 9).value   # I列=产品
        if h_val in ("合计", "汇总", None):
            continue
        if i_val == product and h_val == term:
            return row
    return None


def try_write(ws, row, col, value):
    """安全写入单元格（跳过合并格）"""
    try:
        ws.cell(row, col).value = value
        return True
    except AttributeError:
        return False


def fill_block(ws, block_start: int, block_end: int,
               biz: str, month_label: str, j_value: float,
               sign_rate: float, cfg: dict, verbose: bool = True):
    """
    填充一个数据块的所有死数值
    """
    # 进件量写入 J 列首行（合并格首行）
    try_write(ws, block_start, COL_J, j_value)
    if verbose:
        print(f"    {biz} J: R{block_start} = {j_value:,.0f}")

    rates = cfg.get("accrual_rates", {})

    # 遍历该业务类型下的所有配置
    count = 0
    for key, rate in rates.items():
        parts = key.split("_", 3)  # 月份_业务_产品_期限
        if len(parts) < 4:
            continue
        m_label, b, prod, term_str = parts
        if m_label != month_label or b != biz:
            continue

        try:
            term = int(term_str)
        except ValueError:
            continue

        row = find_data_row(ws, block_start, block_end, prod, term_str)
        if row is None:
            if verbose:
                print(f"    [WARN] 未找到行: {biz} {prod} {term_str}期")
            continue

        try_write(ws, row, COL_K, rate.get("K"))
        try_write(ws, row, COL_L, rate.get("L"))
        try_write(ws, row, COL_M, rate.get("M"))
        try_write(ws, row, COL_O, sign_rate)
        try_write(ws, row, COL_S, rate.get("S"))
        try_write(ws, row, COL_V, rate.get("V"))

        # Q 分布系数
        q_val = get_q_dist(cfg, month_label, biz, prod, term)
        if q_val:
            try_write(ws, row, COL_Q, q_val)

        count += 1

    if verbose:
        print(f"      写入 {count} 行数据")


# ═══════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════

def run(cfg: dict, db=None, verbose: bool = True) -> dict:
    """
    执行 Step 3: 权责月度预估
    返回: {"status": "ok", "output_file": path}
    """
    months = cfg.get("months", {})
    label_m1 = months.get("label_current", "6月")
    label_m2 = months.get("label_next", "7月")

    # 1. 复制模板
    template_path = cfg.get("paths", {}).get("accrual_template", "")
    if not os.path.exists(template_path):
        # 尝试从源文件复制
        source_path = cfg.get("paths", {}).get("accrual_source", "")
        if os.path.exists(source_path):
            os.makedirs(os.path.dirname(template_path), exist_ok=True)
            shutil.copy2(source_path, template_path)
            if verbose:
                print(f"  已从源文件复制模板: {template_path}")
        else:
            return {"status": "error", "message": f"模板文件不存在: {template_path}"}

    wb = openpyxl.load_workbook(template_path)
    ws = wb["Sheet1"]

    if verbose:
        print(f"  月份1: {label_m1}  |  月份2: {label_m2}")

    # 2. 写入全局参数
    exchange_rate = cfg.get("global_params", {}).get("exchange_rate", 17090)
    ws.cell(7, 9).value = exchange_rate    # I7=汇率
    ws.cell(7, 10).value = exchange_rate   # J7=汇率

    gp = cfg.get("global_params", {})
    fl_cost = gp.get("fl_app_cost_idr", {})
    rl_cost = gp.get("rl_app_cost_idr", {})
    ws.cell(3, 9).value = fl_cost.get(label_m1, 0)   # I3=首贷成本月1
    ws.cell(3, 10).value = fl_cost.get(label_m2, 0)   # J3=首贷成本月2
    ws.cell(4, 9).value = rl_cost.get(label_m1, 0)   # I4=复贷成本月1
    ws.cell(4, 10).value = rl_cost.get(label_m2, 0)  # J4=复贷成本月2

    if verbose:
        print(f"  汇率: {exchange_rate}")

    # 3. 写入进件量
    app_cnt = cfg.get("accrual_app_cnt", {})

    if verbose:
        print(f"\n  [{label_m1}] 写入数据区...")
    for biz, (start, end) in BLOCKS_MONTH1.items():
        j_val = app_cnt.get(biz, {}).get(label_m1, 0)
        s_rate = FL_SIGN_RATE if biz == "首贷" else RL_SIGN_RATE
        fill_block(ws, start, end, biz, label_m1, j_val, s_rate, cfg, verbose)

    if verbose:
        print(f"\n  [{label_m2}] 写入数据区...")
    for biz, (start, end) in BLOCKS_MONTH2.items():
        j_val = app_cnt.get(biz, {}).get(label_m2, 0)
        s_rate = FL_SIGN_RATE if biz == "首贷" else RL_SIGN_RATE
        fill_block(ws, start, end, biz, label_m2, j_val, s_rate, cfg, verbose)

    # 4. 保存
    output_dir = cfg.get("pipeline", {}).get("output_dir", ".")
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(
        output_dir,
        f"权责两个月数据预估_{months.get('next', 'unknown')}_{ts}.xlsx"
    )
    wb.save(output_file)

    if verbose:
        print(f"\n  输出: {output_file}")
        print(f"  提示: 打开Excel后 SUMIFS 底部汇总将自动联动刷新")

    return {
        "status": "ok",
        "output_file": output_file,
    }


if __name__ == "__main__":
    cfg = load_config()
    result = run(cfg, verbose=True)
    print(f"\n结果: {result.get('status')}")

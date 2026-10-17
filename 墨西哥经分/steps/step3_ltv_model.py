# -*- coding: utf-8 -*-
"""
Step 3: LTV模型计算
Lifetime Value 模型 - 计算客户生命周期价值
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


def calculate_ltv_model(historical_data):
    """
    计算 LTV (Lifetime Value) 模型
    
    LTV 计算公式:
      LTV = Σ(月均还款额 × 月数 × (1 - 坏账率))
      
    核心指标:
      - 新客CPS ($): 每成功放款成本 (美元)
      - 获客成本 ($): 每客户获取成本
      - 坏账率: 各期累计报案率
      - 月均还款额: 平均月还款金额
      - LTV: 生命周期价值
    
    数据来源:
      - LTV sheet: 历史LTV数据 (Jul,2025 ~ Aug,2026)
      - LTV1 sheet: 预测数据 (含未来月份)
      - 墨西哥经营计划_号7利息累计: 累计报案率
    
    Returns:
        dict: LTV模型数据
    """
    logger.info("开始计算LTV模型...")
    
    ltv_data = {}
    
    # 1. 解析LTV表
    ltv_sheet = historical_data.get('LTV', historical_data.get('ltv_parsed'))
    if ltv_sheet is not None and hasattr(ltv_sheet, 'shape'):
        ltv_data['historical'] = _parse_ltv_historical(ltv_sheet)
        logger.info(f"  LTV历史数据: {len(ltv_data.get('historical', []))} 条")
    
    # 2. 解析LTV预测表
    ltv1_sheet = historical_data.get('LTV1')
    if ltv1_sheet is not None and hasattr(ltv1_sheet, 'shape'):
        ltv_data['forecast'] = _parse_ltv_forecast(ltv1_sheet)
        logger.info(f"  LTV预测数据: {len(ltv_data.get('forecast', []))} 条")
    
    # 3. 解析报案率表
    claim_sheet = historical_data.get('墨西哥经营计划_号7利息累计')
    if claim_sheet is not None and hasattr(claim_sheet, 'shape'):
        ltv_data['claim_rate'] = _parse_claim_rate(claim_sheet)
        logger.info(f"  报案率数据: {len(ltv_data.get('claim_rate', []))} 条")
    
    # 4. 计算综合LTV
    if ltv_data.get('historical'):
        ltv_data['summary'] = _calculate_ltv_summary(ltv_data)
        logger.info(f"  LTV摘要: {ltv_data['summary']}")
    
    logger.info("LTV模型计算完成")
    return ltv_data


def _parse_ltv_historical(df):
    """解析LTV历史表"""
    if df is None or df.empty:
        return []
    
    records = []
    for _, row in df.iterrows():
        record = {
            'month': row.iloc[0] if len(row) > 0 else None,
            'new_cps_usd': row.iloc[2] if len(row) > 2 else None,  # 新客CPS ($)
            'acquisition_cost_usd': row.iloc[3] if len(row) > 3 else None,  # 获客成本 ($)
            'bad_debt_rate': row.iloc[4] if len(row) > 4 else None,  # 坏账率
        }
        if record['month'] is not None:
            records.append(record)
    
    return records


def _parse_ltv_forecast(df):
    """解析LTV预测表"""
    if df is None or df.empty:
        return []
    
    records = []
    for _, row in df.iterrows():
        record = {
            'month': row.iloc[1] if len(row) > 1 else None,  # 月份
            'new_cps_usd': row.iloc[2] if len(row) > 2 else None,
            'acquisition_cost_usd': row.iloc[3] if len(row) > 3 else None,
            'bad_debt_rate': row.iloc[4] if len(row) > 4 else None,
        }
        if record['month'] is not None:
            records.append(record)
    
    return records


def _parse_claim_rate(df):
    """解析累计报案率表"""
    if df is None or df.empty:
        return []
    
    records = []
    for _, row in df.iterrows():
        if pd.notna(row.iloc[0]):
            record = {
                'month': row.iloc[0],
                'claim_m0': row.iloc[2] if len(row) > 2 else None,  # M0报案率
                'claim_m1': row.iloc[3] if len(row) > 3 else None,
                'claim_m3': row.iloc[4] if len(row) > 4 else None,
            }
            records.append(record)
    
    return records


def _calculate_ltv_summary(ltv_data):
    """计算LTV汇总"""
    historical = ltv_data.get('historical', [])
    if not historical:
        return None
    
    # 取最新数据
    latest = historical[-1] if historical else {}
    
    # 安全转换数字
    def safe_float(val):
        if val is None:
            return 0.0
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0
    
    cps = safe_float(latest.get('new_cps_usd', 0))
    bad_rate = safe_float(latest.get('bad_debt_rate', 0))
    
    # LTV估算: CPS / 坏账率 (简化模型)
    if bad_rate > 0 and bad_rate < 1:
        ltv_estimated = cps / bad_rate
    else:
        ltv_estimated = cps * 6  # 默认6个月生命周期
    
    return {
        'month': latest.get('month'),
        'new_cps_usd': round(cps, 2),
        'acquisition_cost_usd': safe_float(latest.get('acquisition_cost_usd')),
        'bad_debt_rate': round(bad_rate, 4),
        'ltv_estimated_usd': round(ltv_estimated, 2),
        'unit': 'USD'
    }


if __name__ == "__main__":
    from step0_data_prep import load_historical_data
    test_file = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\权责分析\墨西哥\墨西哥经营计划_26年6月及7月预估V4.xlsx"
    data = load_historical_data(test_file)
    result = calculate_ltv_model(data)
    print(f"LTV数据: {result}")

# -*- coding: utf-8 -*-
"""
Step 2: 月度预测
基于历史数据生成未来6个月的预测
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


# 墨西哥月度预测配置
FORECAST_CONFIG = {
    'forecast_months': 6,  # 预测未来6个月
    'base_months': 3,     # 用最近3个月平均作为基准
    'growth_rate': {
        # 各指标的增长率假设 (月环比)
        'applicant': 0.05,     # 进件量月增长5%
        'cps': -0.02,          # CPS月降2% (效率提升)
        't3_conversion': 0.01, # T3转化率月提升1%
        'avg_loan': 0.02,      # 客单价月增长2%
    }
}


def generate_monthly_forecast(weekly_data):
    """
    基于历史数据生成月度预测
    
    预测逻辑:
      1. 从历史数据计算最近3个月的平均指标
      2. 应用增长率假设生成未来6个月的预测
      3. 按月汇总输出
    
    Returns:
        list: 每月预测数据
    """
    logger.info("开始生成月度预测...")
    
    # 从周数据汇总月度数据
    monthly_actual = _aggregate_to_monthly(weekly_data)
    
    if not monthly_actual:
        logger.warning("无历史月度数据，使用配置中的默认值")
        monthly_actual = _get_default_monthly()
    
    logger.info(f"历史月度数据: {len(monthly_actual)} 个月")
    
    # 计算基准指标 (最近3个月平均)
    base_metrics = _calculate_base_metrics(monthly_actual)
    logger.info(f"基准指标: {base_metrics}")
    
    # 生成未来预测
    forecast_months = FORECAST_CONFIG['forecast_months']
    growth_config = FORECAST_CONFIG['growth_rate']
    
    # 从最后一个月开始预测
    last_month = monthly_actual[-1] if monthly_actual else _get_default_last_month()
    
    forecasts = []
    current_month = last_month.copy()
    
    for i in range(1, forecast_months + 1):
        forecast = _apply_growth(current_month, growth_config, i)
        forecast['month_index'] = i
        forecast['is_forecast'] = True
        forecasts.append(forecast)
        current_month = forecast
    
    logger.info(f"生成 {len(forecasts)} 个月的预测 (Jul-Dec 2026)")
    
    return forecasts


def _aggregate_to_monthly(monthly_data):
    """
    将月度数据按月汇总
    墨西哥数据已经是月度数据 (KPI sheet)
    """
    if not monthly_data:
        return []
    
    if not isinstance(monthly_data, list):
        return []
    
    if len(monthly_data) == 0:
        return []
    
    first = monthly_data[0]
    if first is None:
        return []
    
    # 如果数据已经有 'month' 字段，已经是月度数据
    if isinstance(first, dict) and 'month' in first:
        return monthly_data
    
    # 否则按 week_date 聚合
    try:
        df = pd.DataFrame(monthly_data)
        if 'week_date' not in df.columns:
            return []
        
        df['month'] = pd.to_datetime(df['week_date']).dt.to_period('M')
        monthly = df.groupby('month').agg({
            'first_loan': 'sum',
            'reloan': 'sum' if 'reloan' in df.columns else 'count'
        }).reset_index()
        
        monthly['month_str'] = monthly['month'].astype(str)
        
        return monthly.to_dict('records')
    except Exception as e:
        print(f"[step2] 聚合月度数据失败: {e}")
        return []


def _calculate_base_metrics(monthly_data):
    """计算基准指标 (最近3个月平均)"""
    if not monthly_data or len(monthly_data) < 3:
        return {
            'applications': 10000,
            'disbursements': 5000,
            'cps': 50,
            't3_conversion': 0.25,
            'avg_loan': 50000
        }
    
    # 筛选有数据的记录
    valid = [r for r in monthly_data if r.get('applications')]
    if len(valid) < 3:
        return {
            'applications': valid[0].get('applications', 10000) if valid else 10000,
            'disbursements': valid[0].get('disbursements', 5000) if valid else 5000,
            'cps': valid[0].get('cps', 50) if valid else 50,
            't3_conversion': 0.25,
            'avg_loan': 50000
        }
    
    recent = valid[-3:]
    
    base = {
        'applications': np.mean([r.get('applications', 0) for r in recent]),
        'disbursements': np.mean([r.get('disbursements', 0) for r in recent]),
        'cps': np.mean([r.get('cps', 0) for r in recent if r.get('cps')]) if any(r.get('cps') for r in recent) else 50,
        'avg_loan': np.mean([r.get('avg_amt_mxn', 0) for r in recent if r.get('avg_amt_mxn')]) if any(r.get('avg_amt_mxn') for r in recent) else 50000,
    }
    
    return base


def _apply_growth(current, growth_config, month_index):
    """应用增长率生成下月预测"""
    forecast = current.copy()
    
    # 月份递增
    if 'month' in forecast:
        month_str = str(forecast['month'])
        # 尝试解析月份
        try:
            if '2025' in month_str:
                year = 2025
                month_num = int(month_str.split('-')[1].split(',')[0].strip() if '-' in month_str else month_str[-2:])
            else:
                month_num = month_index + 6  # 假设从7月开始预测
            new_month = f"Jul-{month_num-5:04d}" if month_num <= 12 else f"Jul-{month_num-5:04d}"
            forecast['month'] = new_month
        except:
            forecast['month'] = f"Month-{month_index}"
    
    # 应用增长率
    growth_factor = month_index
    
    if forecast.get('applications'):
        rate = growth_config.get('applicant', 0.05)
        forecast['applications'] = forecast['applications'] * (1 + rate) ** growth_factor
    
    if forecast.get('disbursements'):
        rate = growth_config.get('applicant', 0.05)
        forecast['disbursements'] = forecast['disbursements'] * (1 + rate) ** growth_factor
    
    if forecast.get('cps'):
        rate = growth_config.get('cps', -0.02)
        forecast['cps'] = max(0, forecast['cps'] * (1 + rate) ** growth_factor)
    
    if forecast.get('avg_amt_mxn'):
        rate = growth_config.get('avg_loan', 0.02)
        forecast['avg_amt_mxn'] = forecast['avg_amt_mxn'] * (1 + rate) ** growth_factor
    
    return forecast


def _get_default_monthly():
    """获取默认月度数据 (当无历史数据时)"""
    return [
        {'month': '2026-01', 'loan_type': '首贷', 'channel': 'BP', 'applications': 8000, 'disbursements': 2000},
        {'month': '2026-02', 'loan_type': '首贷', 'channel': 'BP', 'applications': 8500, 'disbursements': 2200},
        {'month': '2026-03', 'loan_type': '首贷', 'channel': 'BP', 'applications': 9000, 'disbursements': 2400},
    ]


def _get_default_last_month():
    """获取默认最后月数据"""
    return {
        'month': '2026-06',
        'loan_type': '首贷',
        'channel': 'BP',
        'applications': 10000,
        'disbursements': 3000,
        'cps': 50,
        'avg_amt_mxn': 50000
    }


if __name__ == "__main__":
    # 测试
    result = generate_monthly_forecast([])
    print(f"预测了 {len(result)} 个月")
    for r in result:
        print(f"  {r.get('month')}: 进件={r.get('first_loan')}")

# -*- coding: utf-8 -*-
"""
Step 1: 周度指标计算
从历史数据中计算周度经营指标
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def calculate_weekly_metrics(historical_data):
    """
    计算周度/月度经营指标
    
    墨西哥数据主要来源是 Sheet3 (核心KPI，月度数据)
    指标体系:
      - 月度进件量 (首贷/复贷，按渠道BP/HL/ME/MK等)
      - CPI / CPR / CPA / CPS
      - T3转化率 / T10转化率
      - 放款量 / 客单价
      - 逾期率(T0/T3/T7/T30)
    
    Returns:
        list: 每月每渠道的指标数据
    """
    logger.info("开始计算月度经营指标...")
    
    monthly_data = []
    
    # 从 kpi_parsed (Sheet3核心KPI) 获取月度数据
    kpi_data = historical_data.get('kpi_parsed', [])
    
    if kpi_data:
        logger.info(f"从 KPI 数据解析，共 {len(kpi_data)} 条渠道记录")
        
        for record in kpi_data:
            channel_metrics = _parse_kpi_record(record)
            if channel_metrics:
                monthly_data.append(channel_metrics)
                logger.info(
                    f"  {channel_metrics.get('month')}/{channel_metrics.get('loan_type')}/"
                    f"{channel_metrics.get('channel')}: "
                    f"进件={channel_metrics.get('applications')}, "
                    f"放款={channel_metrics.get('disbursements')}, "
                    f"CPS={channel_metrics.get('cps')}"
                )
    
    # 如果有周数据也加上
    weekly_parsed = historical_data.get('weekly_parsed', [])
    if weekly_parsed:
        logger.info(f"从周数据补充，共 {len(weekly_parsed)} 周")
        monthly_data.extend(weekly_parsed)
    
    logger.info(f"月度指标计算完成，共 {len(monthly_data)} 条记录")
    return monthly_data


def _parse_kpi_record(record):
    """解析单条KPI记录 (来自Sheet3)"""
    if not record:
        return None
    
    try:
        channel = record.get('channel', '')
        loan_type = record.get('loan_type', '')
        
        # 跳过无效记录
        if not channel or channel in ['小计', '首复贷']:
            return None
        
        metrics = {
            'month': record.get('month', ''),
            'loan_type': loan_type,          # 首贷 / 复贷
            'channel': channel,               # BP / HL / ME / MK / QP / TC / TG / YW
            'traffic_cost': record.get('traffic_cost'),
            'cpi': record.get('cpi'),
            'cpr': record.get('cpr'),
            'cpa': record.get('cpa'),
            'cps': record.get('cps'),
            't3_first_conversion': record.get('t3_first_conversion'),
            't10_first_conversion': record.get('t10_first_conversion'),
            't3_reloan_conversion': record.get('t3_reloan_conversion'),
            't10_reloan_conversion': record.get('t10_reloan_conversion'),
            'installs': record.get('installs'),
            'registrations': record.get('registrations'),
            'applications': record.get('applications'),
            'credit_approval': record.get('credit_approval'),
            'disbursements': record.get('disbursements'),
            'avg_amt_mxn': record.get('avg_amt_mxn'),
            'avg_amt_usd': record.get('avg_amt_usd'),
            'auto_approve_rate': record.get('auto_approve_rate'),
            'approve_rate': record.get('approve_rate'),
            't2_repay_rate': record.get('t2_repay_rate'),
            't1_repay_rate': record.get('t1_repay_rate'),
            't0_overdue': record.get('t0_overdue'),
            't3_overdue': record.get('t3_overdue'),
            't7_overdue': record.get('t7_overdue'),
            't30_overdue': record.get('t30_overdue'),
        }
        
        return metrics
        
    except Exception as e:
        logger.warning(f"解析KPI记录失败: {e}")
        return None


def get_weekly_summary(weekly_data):
    """获取周度指标摘要"""
    if not weekly_data:
        return {}
    
    df = pd.DataFrame(weekly_data)
    
    summary = {
        'total_weeks': len(df),
        'avg_applicant': df['applicant_cnt'].mean() if 'applicant_cnt' in df.columns else None,
        'avg_cps': df['cps'].mean() if 'cps' in df.columns else None,
        'avg_t3_conversion': df['t3_conversion'].mean() if 't3_conversion' in df.columns else None,
        'max_applicant_week': df['applicant_cnt'].max() if 'applicant_cnt' in df.columns else None,
        'min_applicant_week': df['applicant_cnt'].min() if 'applicant_cnt' in df.columns else None,
    }
    
    return summary


if __name__ == "__main__":
    from step0_data_prep import load_historical_data
    test_file = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\权责分析\墨西哥\墨西哥经营计划_26年6月及7月预估V4.xlsx"
    data = load_historical_data(test_file)
    result = calculate_weekly_metrics(data)
    print(f"计算了 {len(result)} 周的指标")

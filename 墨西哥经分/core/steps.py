# -*- coding: utf-8 -*-
"""
墨西哥经分自动化 - Step 模块初始化
"""
from .step0_data_prep import load_historical_data
from .step1_weekly_metrics import calculate_weekly_metrics
from .step2_monthly_forecast import generate_monthly_forecast
from .step3_ltv_model import calculate_ltv_model
from .step4_template_output import generate_report_template

__all__ = [
    'load_historical_data',
    'calculate_weekly_metrics',
    'generate_monthly_forecast',
    'calculate_ltv_model',
    'generate_report_template'
]

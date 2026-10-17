# -*- coding: utf-8 -*-
"""
Step 0: 数据准备
从墨西哥经营计划 Excel 读取历史数据
"""

import openpyxl
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def load_historical_data(excel_path):
    """
    从 Excel 文件加载墨西哥历史数据
    
    Excel 结构分析:
      - Sheet: 墨西哥经营计划_26年6月及7月预估 (190行 x 42列)
        * 第1行: 月份编号 (31,29,31,30,31,30,31,...)
        * 第2行: Excel日期序列号
        * 第3行: 指标名称 (首贷/复贷)
        * 数据: 从第4行开始，每周一列
      
      - Sheet: 墨西哥经营计划(产品月态) (59行 x 25列)
        * 产品月度数据 (Nov,2025 ~ Jun,2026 x 2)
        * 产品代码: A_07_01_50_00, B_07_03_00_60 等
      
      - Sheet: 墨西哥经营计划_额5期 (129行 x 65列)
        * LTV模型预测数据
        * 列: dt_week, 首贷利息, Jun2025-Aug2026每周数据
      
      - Sheet: Sheet1 (47行 x 13列)
        * 7月产品分布 (6月实际/7月预估)
        * 产品分布: order_type, product_name, loan_cnt, loan_amount_usd
      
      - Sheet: 墨西哥经营计划_额6期 (132行 x 65列)
        * 6月预测版本，与上面类似但包含预测数据
      
      - Sheet: Sheet3 (19行 x 49列)
        * 核心KPI表 (按APR类型: BP/HL/ME/MK)
        * 列: 时间, 名称, APP量, 注册量, CPI, CPR, CPA, CPS
        * T3/T10转化率, 授信, 通过, 放款等49列
      
      - Sheet: 2陈品月态比 (21行 x 12列)
        * 2陈品月度态比
      
      - Sheet: LTV (43行 x 14列)
        * LTV历史数据 (Jul,2025, Aug,2025 ~ 多年)
        * 新客CPS, 获客成本, 坏账率
      
      - Sheet: LTV1 (22行 x 11列)
        * LTV预测数据 (Jul,2025 ~ Feb,2026 实际 + 未来预测)
      
      - Sheet: 墨西哥经营计划_号7利息累计 (34行 x 23列)
        * 累计报案量表
        * dt_mon, 累计报案比例(0~19期)
      
      - Sheet: by月报案累计 (12行 x 10列)
        * 月度累计报案
      
      - Sheet: by月报案累计来源 (1062行 x 9列)
        * 原始报案数据 (2024.4 ~)
      
      - Sheet: 结清预测 (50行 x 9列)
        * 结清预测 (June-Aug 2025)
      
      - Sheet: 墨西哥经营计划_6期 (2) (50行 x 9列)
        * 6期版本
      
      - Sheet: 产品态 (27行 x 14列)
        * 产品月度态 (IOS/Android)
    
    Returns:
        dict: 各 sheet 的数据
    """
    logger.info(f"开始加载 Excel: {excel_path}")
    
    wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
    sheets = wb.sheetnames
    logger.info(f"共 {len(sheets)} 个 Sheet: {sheets}")
    
    data = {}
    
    for sheet_name in sheets:
        try:
            ws = wb[sheet_name]
            logger.info(f"读取 Sheet: {sheet_name} ({ws.max_row}行 x {ws.max_column}列)")
            
            # 读取数据为列表
            rows = []
            for row in ws.iter_rows(values_only=True):
                rows.append(list(row))
            
            # 转换为 DataFrame (去除全空行/列)
            df = _clean_dataframe(rows)
            
            if df is not None and not df.empty:
                data[sheet_name] = df
                logger.info(f"  ✅ {sheet_name}: {len(df)} 行 x {len(df.columns)} 列")
            else:
                logger.warning(f"  ⚠️ {sheet_name}: 数据为空，跳过")
                
        except Exception as e:
            logger.error(f"  ❌ 读取 {sheet_name} 失败: {e}")
    
    wb.close()
    
    # 解析 Sheet3 (核心KPI)
    if 'Sheet3' in data:
        kpi_data = _parse_kpi_sheet(data['Sheet3'])
        data['kpi_parsed'] = kpi_data
        logger.info(f"  ✅ KPI解析完成: {len(kpi_data)} 条记录")
    
    # 解析周数据
    main_sheet_name = [s for s in sheets if '墨西哥经营计划' in s and '额' not in s and '6期' not in s and '7期' not in s and '2' not in s]
    if main_sheet_name:
        weekly = _parse_weekly_data(data.get(main_sheet_name[0]))
        if weekly:
            data['weekly_parsed'] = weekly
            logger.info(f"  ✅ 周数据解析完成: {len(weekly)} 周")
    
    return data


def _clean_dataframe(rows):
    """清理数据：去除空行空列"""
    if not rows:
        return None
    
    import pandas as pd
    
    # 过滤全空行
    non_empty_rows = [row for row in rows if any(v is not None for v in row)]
    if not non_empty_rows:
        return None
    
    # 找出非空列
    max_cols = len(non_empty_rows[0])
    col_mask = [any(row[i] is not None for row in non_empty_rows) for i in range(max_cols)]
    
    # 过滤非空列
    cleaned_rows = []
    for row in non_empty_rows:
        cleaned_row = [row[i] if col_mask[i] else None for i in range(max_cols)]
        cleaned_rows.append(cleaned_row)
    
    df = pd.DataFrame(cleaned_rows)
    
    # 设置列名
    if df.iloc[0].notna().sum() > 0:
        df.columns = df.iloc[0]
        df = df.iloc[1:]
        df = df.reset_index(drop=True)
    
    return df


def _parse_kpi_sheet(df):
    """
    解析 Sheet3 核心KPI表 (19行 x 49列)
    
    结构:
      Row 1: 列头 (月, 首复贷, APP分组, 流量费用, CPI, CPR, CPA, CPS, ...)
      Row 2-9: 复贷数据 (BP, HL, ME, MK, QP, TC, TG, YW)
      Row 10: 首贷标题
      Row 11-18: 首贷数据 (BP, HL, ME, MK, QP, TC, TG, YW)
      Row 19: 小计
    
    关键列:
      Col1: 月 (2026-06)
      Col2: 首复贷 (首贷/复贷)
      Col3: APP分组/渠道 (BP/HL/ME/MK/QP/TC/TG/YW)
      Col5: CPI
      Col6: CPR
      Col7: CPA
      Col8: CPS
      Col9: 首贷T3非风险转化率
      Col10: 首贷T10非风险转化率
      Col11: 复贷T3非风险转化率
      Col12: 复贷T10非风险转化率
      Col13: 安装量
      Col14: 注册量
      Col15: 进件量
      Col16: 授信通过量
      Col17: 放款量
      Col18: 件均(比索)
      Col19: 件均(美元)
      Col20: 实放件均(比索)
      Col21: 安装注册率
      Col22: 机审通过率
      Col23: 机审通过率-剔除额度不足
      Col24: 后置通过率
      Col25: 后置通过率-新
      Col26: 通过率
      Col27: 通过率-新
      Col28: 用信率
      Col29: 合同金额(比索)
      Col30: 合同金额(美元)
      Col31: 实放金额(比索)
      Col32: 应还数
      Col33: 实还金额(比索)
      Col34: 实还金额(美金)
      Col35-39: 逾期率(T-2, T-1, T0, T3, T7)
      Col41: 逾期T30(金额)
      Col42-43: 悲观逾期(1t0, 2t0)
    """
    if df is None or len(df) < 2:
        return []
    
    records = []
    
    # 列名映射 (0-indexed)
    col_map = {
        'month': 0,
        'loan_type': 1,
        'channel': 2,
        'traffic_cost': 3,
        'cpi': 4,
        'cpr': 5,
        'cpa': 6,
        'cps': 7,
        't3_first_conversion': 8,
        't10_first_conversion': 9,
        't3_reloan_conversion': 10,
        't10_reloan_conversion': 11,
        'installs': 12,
        'registrations': 13,
        'applications': 14,
        'credit_approval': 15,
        'disbursements': 16,
        'avg_amt_mxn': 17,
        'avg_amt_usd': 18,
        'actual_avg_mxn': 19,
        'install_reg_rate': 20,
        'auto_approve_rate': 21,
        'auto_approve_rate_net': 22,
        'post_approve_rate': 23,
        'post_approve_rate_new': 24,
        'approve_rate': 25,
        'approve_rate_new': 26,
        'utilization_rate': 27,
        'contract_amt_mxn': 28,
        'contract_amt_usd': 29,
        'actual_amt_mxn': 30,
        'due_amt': 31,
        'actual_repaid_mxn': 32,
        'actual_repaid_usd': 33,
        't2_repay_rate': 34,
        't1_repay_rate': 35,
        't0_overdue': 36,
        't3_overdue': 37,
        't7_overdue': 38,
        't30_reloan_orders': 39,
        't30_overdue': 40,
        'pessimistic_t0_1': 41,
        'pessimistic_t0_2': 42,
    }
    
    rows = []
    for _, row in df.iterrows():
        rows.append([v for v in row])
    
    # Row 1 是列头，跳过; 从 Row 2 开始是数据
    # 识别 首贷/复贷 区域
    for row in rows[1:]:  # 跳过列头
        month = row[col_map['month']]
        loan_type = row[col_map['loan_type']]
        channel = row[col_map['channel']]
        applications = row[col_map['applications']]
        
        if channel and str(channel).strip():  # 有渠道名的行
            record = {
                'month': month,
                'loan_type': loan_type,
                'channel': str(channel).strip(),
                'traffic_cost': row[col_map['traffic_cost']],
                'cpi': row[col_map['cpi']],
                'cpr': row[col_map['cpr']],
                'cpa': row[col_map['cpa']],
                'cps': row[col_map['cps']],
                't3_first_conversion': row[col_map['t3_first_conversion']],
                't10_first_conversion': row[col_map['t10_first_conversion']],
                't3_reloan_conversion': row[col_map['t3_reloan_conversion']],
                't10_reloan_conversion': row[col_map['t10_reloan_conversion']],
                'installs': row[col_map['installs']],
                'registrations': row[col_map['registrations']],
                'applications': applications,
                'credit_approval': row[col_map['credit_approval']],
                'disbursements': row[col_map['disbursements']],
                'avg_amt_mxn': row[col_map['avg_amt_mxn']],
                'avg_amt_usd': row[col_map['avg_amt_usd']],
                'actual_amt_mxn': row[col_map['actual_amt_mxn']],
                'auto_approve_rate': row[col_map['auto_approve_rate']],
                'approve_rate': row[col_map['approve_rate']],
                'actual_repaid_mxn': row[col_map['actual_repaid_mxn']],
                't2_repay_rate': row[col_map['t2_repay_rate']],
                't1_repay_rate': row[col_map['t1_repay_rate']],
                't0_overdue': row[col_map['t0_overdue']],
                't3_overdue': row[col_map['t3_overdue']],
                't7_overdue': row[col_map['t7_overdue']],
                't30_overdue': row[col_map['t30_overdue']],
            }
            records.append(record)
    
    return records


def _parse_weekly_data(df):
    """
    解析周数据表
    返回: List[dict] - 每周一条记录
    """
    if df is None or len(df) < 3:
        return []
    
    records = []
    
    # 找日期行 (第1行是月份编号, 第2行是Excel日期序列号)
    # 从第3行开始是数据
    date_row = None
    for i, row in df.iterrows():
        # 检测是否是日期行 (包含 datetime 对象)
        first_val = row.iloc[0]
        if hasattr(first_val, 'year') or isinstance(first_val, datetime):
            date_row = row.tolist()
            data_row = df.iloc[i + 1].tolist() if i + 1 < len(df) else None
            if data_row:
                records.append({
                    'week_date': first_val,
                    'first_loan': data_row[2] if len(data_row) > 2 else None,
                    'reloan': data_row[3] if len(data_row) > 3 else None
                })
    
    return records


def get_sheet_summary(data):
    """获取各sheet数据摘要"""
    summary = {}
    for sheet_name, df in data.items():
        if hasattr(df, 'shape'):
            summary[sheet_name] = {
                'rows': df.shape[0],
                'cols': df.shape[1],
                'columns': list(df.columns[:10]) if not df.empty else []
            }
    return summary


if __name__ == "__main__":
    import sys
    # 测试: 直接运行
    test_file = r"E:\岳松个人文件\嘉银工作内容的整理\01工作内容\权责分析\墨西哥\墨西哥经营计划_26年6月及7月预估V4.xlsx"
    if Path(test_file).exists():
        data = load_historical_data(test_file)
        print(f"\n加载了 {len(data)} 个数据集")
        for name, df in data.items():
            if hasattr(df, 'shape'):
                print(f"  - {name}: {df.shape}")
    else:
        print(f"测试文件不存在: {test_file}")

# -*- coding: utf-8 -*-
"""
Step 4: Excel模板输出
生成墨西哥权责经分Excel模板
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# Excel样式定义
HEADER_FILL = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
HEADER_FONT = Font(bold=True, color='FFFFFF', size=11)
TITLE_FONT = Font(bold=True, size=14, color='1F4E78')
BORDER = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin')
)


def generate_report_template(all_results, output_dir):
    """
    生成墨西哥权责经分Excel报告模板
    
    Sheet结构 (与印尼pipeline对应):
      1. 封面 - 报告信息
      2. 周度指标 - 周度进件/CPI/CPR/CPA/CPS数据
      3. 月度预测 - Jul-Dec 2026预测数据
      4. LTV模型 - Lifetime Value计算
      5. 成本明细 - 各项成本分解
      6. 经营对比 - 印尼vs墨西哥横向对比
    
    Returns:
        str: 输出文件路径
    """
    logger.info(f"开始生成Excel模板，输出目录: {output_dir}")
    
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # 删除默认sheet
    
    # 1. 封面
    _create_cover_sheet(wb)
    
    # 2. 周度指标
    weekly_data = all_results.get('weekly_data', [])
    _create_weekly_sheet(wb, weekly_data)
    
    # 3. 月度预测
    forecast_data = all_results.get('forecast_data', [])
    _create_forecast_sheet(wb, forecast_data)
    
    # 4. LTV模型
    ltv_data = all_results.get('ltv_data', {})
    _create_ltv_sheet(wb, ltv_data)
    
    # 5. 成本明细
    _create_cost_sheet(wb)
    
    # 6. 印尼对比
    _create_comparison_sheet(wb)
    
    # 保存文件
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = Path(output_dir) / f'墨西哥经分报告_{timestamp}.xlsx'
    
    wb.save(str(output_file))
    logger.info(f"✅ Excel报告已保存: {output_file}")
    
    return str(output_file)


def _create_cover_sheet(wb):
    """创建封面Sheet"""
    ws = wb.create_sheet('封面', 0)
    
    # 标题
    ws['A1'] = '墨西哥经营分析报告'
    ws['A1'].font = Font(bold=True, size=20, color='1F4E78')
    ws.merge_cells('A1:F1')
    
    # 信息
    ws['A3'] = '报告周期'
    ws['B3'] = '2025年6月 - 2026年12月'
    ws['A4'] = '生成日期'
    ws['B4'] = datetime.now().strftime('%Y-%m-%d')
    ws['A5'] = '报告类型'
    ws['B5'] = '墨西哥现金贷业务经营分析'
    ws['A6'] = '包含国家'
    ws['B6'] = '墨西哥 (MX)'
    ws['A7'] = '货币'
    ws['B7'] = 'MXN (墨西哥比索)'
    
    # 样式
    for row in range(3, 8):
        ws[f'A{row}'].font = Font(bold=True)
    
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 30


def _create_weekly_sheet(wb, weekly_data):
    """创建周度/月度指标Sheet"""
    ws = wb.create_sheet('月度KPI')
    
    # 表头 (墨西哥KPI格式)
    headers = ['月份', '首复贷', '渠道', '流量费用', 'CPI', 'CPR', 'CPA', 'CPS',
               'T3转化率', 'T10转化率', '安装量', '注册量', '进件量',
               '授信通过量', '放款量', '件均(比索)', '件均(美元)']
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal='center', wrap_text=True)
        ws.column_dimensions[get_column_letter(col)].width = 14
    
    # 数据行
    if weekly_data and isinstance(weekly_data, list):
        for row_idx, record in enumerate(weekly_data, 2):
            if not isinstance(record, dict):
                continue
            ws.cell(row=row_idx, column=1, value=record.get('month', ''))
            ws.cell(row=row_idx, column=2, value=record.get('loan_type', ''))
            ws.cell(row=row_idx, column=3, value=record.get('channel', ''))
            ws.cell(row=row_idx, column=4, value=record.get('traffic_cost'))
            ws.cell(row=row_idx, column=5, value=record.get('cpi'))
            ws.cell(row=row_idx, column=6, value=record.get('cpr'))
            ws.cell(row=row_idx, column=7, value=record.get('cpa'))
            ws.cell(row=row_idx, column=8, value=record.get('cps'))
            ws.cell(row=row_idx, column=9, value=record.get('t3_first_conversion'))
            ws.cell(row=row_idx, column=10, value=record.get('t10_first_conversion'))
            ws.cell(row=row_idx, column=11, value=record.get('installs'))
            ws.cell(row=row_idx, column=12, value=record.get('registrations'))
            ws.cell(row=row_idx, column=13, value=record.get('applications'))
            ws.cell(row=row_idx, column=14, value=record.get('credit_approval'))
            ws.cell(row=row_idx, column=15, value=record.get('disbursements'))
            ws.cell(row=row_idx, column=16, value=record.get('avg_amt_mxn'))
            ws.cell(row=row_idx, column=17, value=record.get('avg_amt_usd'))
    else:
        ws.cell(row=2, column=1, value='暂无数据 - 请先运行 Step 0-1')
        ws.merge_cells('A2:Q2')
    
    logger.info(f"月度KPI表: {len(weekly_data) if weekly_data and isinstance(weekly_data, list) else 0} 条记录")


def _create_forecast_sheet(wb, forecast_data):
    """创建月度预测Sheet"""
    ws = wb.create_sheet('月度预测')
    
    headers = ['月份', '预测/实际', '首贷进件', '复贷进件', 'CPI', 'CPR', 'CPS', 'T3转化率', '坏账率', 'LTV($)', '备注']
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal='center')
        ws.column_dimensions[get_column_letter(col)].width = 13
    
    if forecast_data and isinstance(forecast_data, list) and len(forecast_data) > 0:
        for row_idx, record in enumerate(forecast_data, 2):
            if not isinstance(record, dict):
                continue
            ws.cell(row=row_idx, column=1, value=record.get('month'))
            ws.cell(row=row_idx, column=2, value='预测' if record.get('is_forecast') else '实际')
            ws.cell(row=row_idx, column=3, value=record.get('applications'))
            ws.cell(row=row_idx, column=4, value=record.get('disbursements'))
            ws.cell(row=row_idx, column=5, value=record.get('cpi'))
            ws.cell(row=row_idx, column=6, value=record.get('cpr'))
            ws.cell(row=row_idx, column=7, value=record.get('cps'))
            ws.cell(row=row_idx, column=8, value=record.get('t3_conversion'))
            ws.cell(row=row_idx, column=9, value=record.get('bad_debt_rate'))
            ws.cell(row=row_idx, column=10, value=record.get('ltv_usd'))
    else:
        # 插入默认预测数据
        default_months = [
            ('Jul,2026', '预测', 11000, 5500),
            ('Aug,2026', '预测', 11500, 5750),
            ('Sep,2026', '预测', 12000, 6000),
            ('Oct,2026', '预测', 12600, 6300),
            ('Nov,2026', '预测', 13200, 6600),
            ('Dec,2026', '预测', 13800, 6900),
        ]
        for row_idx, (month, label, first, reloan) in enumerate(default_months, 2):
            ws.cell(row=row_idx, column=1, value=month)
            ws.cell(row=row_idx, column=2, value=label)
            ws.cell(row=row_idx, column=3, value=first)
            ws.cell(row=row_idx, column=4, value=reloan)
    
    logger.info(f"月度预测表: {len(forecast_data) if forecast_data and isinstance(forecast_data, list) else 0} 个月")


def _create_ltv_sheet(wb, ltv_data):
    """创建LTV模型Sheet"""
    ws = wb.create_sheet('LTV模型')
    
    ws['A1'] = '墨西哥LTV模型'
    ws['A1'].font = TITLE_FONT
    ws.merge_cells('A1:E1')
    
    headers = ['月份', '新客CPS($)', '获客成本($)', '坏账率', 'LTV($)']
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        ws.column_dimensions[get_column_letter(col)].width = 15
    
    # 安全获取 ltv_data
    if not isinstance(ltv_data, dict):
        ws.cell(row=4, column=1, value='LTV数据未加载 (请先运行Step 0-3)')
        ws.merge_cells('A4:E4')
        return
    
    # LTV摘要
    summary = ltv_data.get('summary', {})
    if summary:
        row = 4
        for key, val in summary.items():
            ws.cell(row=row, column=1, value=str(key))
            ws.cell(row=row, column=2, value=val)
            row += 1
    
    # 历史数据
    historical = ltv_data.get('historical', [])
    if historical:
        start_row = 10
        ws.cell(row=start_row, column=1, value='=== 历史数据 ===')
        ws.cell(row=start_row, column=1).font = Font(bold=True)
        for i, record in enumerate(historical[:20], start_row + 1):  # 最多20条
            if not isinstance(record, dict):
                continue
            ws.cell(row=i, column=1, value=record.get('month'))
            ws.cell(row=i, column=2, value=record.get('new_cps_usd'))
            ws.cell(row=i, column=3, value=record.get('acquisition_cost_usd'))
            ws.cell(row=i, column=4, value=record.get('bad_debt_rate'))
            cps = record.get('new_cps_usd', 0) or 0
            bad_rate = record.get('bad_debt_rate', 0) or 0.01
            try:
                ltv = float(cps) / max(float(bad_rate), 0.01)
            except (ValueError, TypeError, ZeroDivisionError):
                ltv = 0
            ws.cell(row=i, column=5, value=round(ltv, 2))
    
    logger.info("LTV模型表创建完成")


def _create_cost_sheet(wb):
    """创建成本明细Sheet"""
    ws = wb.create_sheet('成本明细')
    
    ws['A1'] = '墨西哥成本明细'
    ws['A1'].font = TITLE_FONT
    ws.merge_cells('A1:D1')
    
    headers = ['成本项', '单位', '金额(MXN)', '备注']
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        ws.column_dimensions[get_column_letter(col)].width = 20
    
    # 成本项 (占位，待填)
    cost_items = [
        ('获客成本(CAC)', '元/人', None, '需从数据库计算'),
        ('风控成本', '元/笔', None, '审批系统成本'),
        ('资金成本', '年化%', None, '资金利息'),
        ('催收成本', '元/笔', None, '自营+委外催收'),
        ('运营成本', '元/月', None, '人工+系统'),
        ('技术成本', '元/月', None, '服务器+维护'),
    ]
    
    for row_idx, (item, unit, amount, note) in enumerate(cost_items, 4):
        ws.cell(row=row_idx, column=1, value=item)
        ws.cell(row=row_idx, column=2, value=unit)
        ws.cell(row=row_idx, column=3, value=amount)
        ws.cell(row=row_idx, column=4, value=note)
    
    logger.info("成本明细表创建完成")


def _create_comparison_sheet(wb):
    """创建印尼对比Sheet"""
    ws = wb.create_sheet('印尼对比')
    
    ws['A1'] = '印尼 vs 墨西哥 横向对比'
    ws['A1'].font = TITLE_FONT
    ws.merge_cells('A1:F1')
    
    headers = ['指标', '印尼', '墨西哥', '差异', '差异%', '备注']
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        ws.column_dimensions[get_column_letter(col)].width = 15
    
    comparison_items = [
        ('月均进件量', None, None, None, None, '需从印尼pipeline读取'),
        ('CPI', None, None, None, None, '每注册成本'),
        ('CPS', None, None, None, None, '每放款成本'),
        ('T3转化率', None, None, None, None, '首贷审批通过率'),
        ('坏账率(M3)', None, None, None, None, '3个月逾期率'),
        ('LTV($)', None, None, None, None, '客户生命周期价值'),
        ('月放款量', None, None, None, None, '放款金额'),
    ]
    
    for row_idx, item in enumerate(comparison_items, 4):
        for col_idx, val in enumerate(item, 1):
            ws.cell(row=row_idx, column=col_idx, value=val)
    
    logger.info("印尼对比表创建完成")


if __name__ == "__main__":
    # 测试
    output = generate_report_template({}, r"C:\Users\yuesong\AppData\Local\Temp")
    print(f"测试输出: {output}")

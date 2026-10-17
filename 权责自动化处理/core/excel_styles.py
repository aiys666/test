# -*- coding: utf-8 -*-
"""
经营计划自动化 — Excel 样式常量
所有步骤共用，保持输出 Excel 外观一致
"""

from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# ── 颜色常量 ──
HDR_FILL    = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
SUB_FILL    = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
YLW_FILL    = PatternFill(start_color="FFFF99", end_color="FFFF99", fill_type="solid")
GRN_FILL    = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
ORG_FILL    = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
BLU_FILL    = PatternFill(start_color="DDEEFF", end_color="DDEEFF", fill_type="solid")
RED_FILL    = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
PURPLE_FILL = PatternFill(start_color="7B2C8E", end_color="7B2C8E", fill_type="solid")

WHT_FONT    = Font(bold=True, color="FFFFFF")
BLD_FONT    = Font(bold=True)
BLUE_FONT   = Font(color="0000FF", bold=True)
BLUE_FONT_N = Font(color="0000FF")

# ── 数字格式 ──
PCT_FMT     = '0.00%'
NUM_FMT     = '#,##0'
USD_FMT     = '"$"#,##0.0'
USD_FMT_INT = '"$"#,##0'


def thin_border():
    """细线边框"""
    s = Side(style="thin")
    return Border(left=s, right=s, top=s, bottom=s)


def header_style(ws, row):
    """蓝色表头样式"""
    for cell in ws[row]:
        if cell.value is not None:
            cell.fill = HDR_FILL
            cell.font = WHT_FONT
            cell.alignment = Alignment(horizontal='center')


def set_col_width(ws, widths: dict):
    """批量设置列宽"""
    for col_letter, w in widths.items():
        ws.column_dimensions[col_letter].width = w


def cell_style(cell, font=None, fill=None, alignment=None, number_format=None, border=True):
    """单格样式设置"""
    if font:
        cell.font = font
    if fill:
        cell.fill = fill
    if alignment:
        cell.alignment = alignment
    else:
        cell.alignment = Alignment(horizontal='center', vertical='center')
    if number_format:
        cell.number_format = number_format
    if border:
        cell.border = thin_border()

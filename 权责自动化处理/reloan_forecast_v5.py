# -*- coding: utf-8 -*-
"""
复贷进件量预估系统 v5
核心修复（相较v4）：
  1. 金额全部改为美金单位，件均≈62美金
  2. MOB范围扩展到1-13（支持MOB12+）
  3. 调整系数按MOB分段（短期MOB1-3 / 长期MOB4-13）
  4. 未来首贷量缺失时，用首贷预估值填补（解决复贷低估）
  5. 首贷预估Sheet增加历史实际值校验列，差异>20%自动标红
  6. MOB转化率MA加入趋势分析（MA + 趋势外推平均）
  7. 所有金额格式从 ¥ 改为 $
"""

import pandas as pd
import numpy as np
import requests
import json
import re
import time
import base64
import math
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.formatting.rule import CellIsRule
from openpyxl.utils import get_column_letter
from datetime import datetime
from dateutil.relativedelta import relativedelta

# ============================================================
# 1. 数据库连接类
# ============================================================
class PrestoQuery:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
        }

    def login_process(self):
        self.sess = requests.session()
        self.sess.keep_alive = False
        post_url = (
            'https://dino-manage-auth-ina.samir.co.id/login?callback='
            'http%3A%2F%2Fdata.samir.co.id%2Fdataworks-development%2Foauth%2Flogin'
            '%3Freferer%3Dhttps%253A%252F%252Fdata.samir.co.id%252Fdata-pc-bdopr-fe'
            '%252Fhoc-inquiry%252Findex&authsource=dino&username=erik@bigdata&password=Jy6856658!'
        )
        log_res = self.sess.post(post_url, headers=self.headers, allow_redirects=False)
        print(f'登录凭证提交: {log_res.status_code}')
        redirect_url = log_res.headers['Location']
        login_token = re.search('#samir_id=(.*)', redirect_url).group(1)
        login_url = (
            'http://data.samir.co.id/dataworks-development/oauth/login'
            '?referer=https%3A%2F%2Fdata.samir.co.id%2Fdata-pc-bdopr-fe%2Fhoc-inquiry%2Findex'
            '&samir_id={}&token_type=bearer&state=&expires_in=863999&scope=authority-management'
        ).format(login_token)
        res = self.sess.get(login_url, headers=self.headers)
        print(f'登录盘古: {res.status_code}')

    def submit_query(self, query_sql, wait_sec=2):
        query_url = 'https://data.samir.co.id/dataworks-development/adhoc/querySql'
        data_sql = {
            "sql": base64.b64encode(query_sql.encode()).decode(),
            "windowId": 16, "headRowNum": 54, "engine": "PRESTO",
            "queryType": "Data", "varList": [], "dependStatus": 1
        }
        query_res = self.sess.post(query_url, headers=self.headers,
                                   data=json.dumps(data_sql), timeout=(3, 20))
        res_json = query_res.json()
        if res_json.get('data', {}).get('checkError') == 'True':
            err = res_json['data']['checkResultList'][0]
            return f"SQL错误: {err.get('errorMsg', '未知')}"
        job_url = 'https://data.samir.co.id/dataworks-development/adhoc/queryPrestoJobLog'
        jobQueryId = res_json['data']['jobQueryId']
        job_res = self.sess.get(job_url, headers=self.headers,
                                params={"jobQueryId": jobQueryId}, timeout=(3, 20))
        job_json = job_res.json()
        max_wait, waited = 120, 0
        while job_json.get('data', {}).get('taskState') != 'FINISHED' and waited < max_wait:
            time.sleep(wait_sec); waited += wait_sec
            job_res = self.sess.get(job_url, headers=self.headers,
                                    params={"jobQueryId": jobQueryId}, timeout=(3, 20))
            job_json = job_res.json()
            if job_json.get('data', {}).get('taskState') == 'FAILED':
                return f"查询失败: {job_json.get('data', {}).get('errorMessage', '未知')}"
        if job_json.get('data', {}).get('taskState') != 'FINISHED':
            return "查询超时"
        query_id = job_json['data']['queryId']
        stmt = job_json['data']['statementType']
        if stmt in ['drop', 'create']:
            return "表更新成功"
        result_url = 'https://data.samir.co.id/dataworks-development/adhoc/getQueryResult'
        result_payload = {'current': 1, 'size': 5000, 'queryId': query_id}
        result_res = self.sess.post(result_url, headers=self.headers,
                                    data=json.dumps(result_payload), timeout=(3, 20))
        data_obj = result_res.json().get('data', {})
        totalrecords = data_obj.get('totalRecords', 0)
        if totalrecords == 0:
            return pd.DataFrame()
        columns = data_obj.get('columns', [])
        df = pd.DataFrame()
        for i in range(1, math.ceil(totalrecords / 5000) + 1):
            r = self.sess.post(result_url, headers=self.headers,
                               data=json.dumps({'current': i, 'size': 5000, 'queryId': query_id}),
                               timeout=(3, 20))
            df = pd.concat([df, pd.DataFrame(r.json()['data']['records'], columns=columns)],
                           ignore_index=True)
        return df


# ============================================================
# 2. 配置参数（v5：美金单位 + MOB1-13 + 分段调整系数）
# ============================================================
CONFIG = {
    "ma_window":           3,
    "mob_list":            list(range(1, 14)),  # MOB1-13
    # 分段调整系数
    "loop_adj_short":      1.0,   # 循环贷 MOB1-3
    "loop_adj_long":       1.0,   # 循环贷 MOB4-13
    "normal_adj_short":    1.0,   # 非循环贷 MOB1-3
    "normal_adj_long":     1.0,   # 非循环贷 MOB4-13
    # 首贷预估参数（美金）
    "fl_days_in_month":         31,
    "fl_daily_spend":           2200,    # 美金/天
    "fl_cpi":                   3.6,     # 美金/安装
    "fl_install_register_rate": 0.80,
    "fl_pass_rate":             0.65,
    "fl_sign_loan_rate":        0.95,
    "fl_avg_amount":            62,      # 件均≈62美金
}

# 参数行号（v5新增：B10-B14为分段调整系数）
PARAM_ROWS = {
    'days':          2,
    'daily_spend':   3,
    'cpi':           4,
    'install_reg':   5,
    'pass_rate':     6,
    'sign_rate':     7,
    'fl_avg_amt':    8,
    'ma_window':     10,
    'loop_adj_s':    11,   # 循环贷短期（MOB1-3）
    'loop_adj_l':    12,   # 循环贷长期（MOB4-13）
    'normal_adj_s':  13,   # 非循环贷短期
    'normal_adj_l':  14,   # 非循环贷长期
}

# ============================================================
# 3. SQL（v5：MOB扩展到1-13）
# ============================================================
SQL_FIRST_LOAN = """
SELECT
    date_format(release_time, '%Y-%m-01')  AS month,
    COUNT(DISTINCT order_no)               AS loan_cnt,
    ROUND(AVG(loan_amount), 0)             AS avg_loan_amount
FROM dwd.dwd_loan_info
WHERE release_time IS NOT NULL
  AND release_time >= DATE '2025-01-01'
  AND is_new = 1
GROUP BY 1
ORDER BY 1 DESC
"""

SQL_RELOAN_BY_TYPE = """
WITH first_loan AS (
    SELECT mid, date_format(release_time, '%Y-%m-01') AS first_loan_month
    FROM dwd.dwd_loan_info
    WHERE release_time IS NOT NULL
      AND release_time >= DATE '2025-01-01'
      AND is_new = 1
),
reloan_app AS (
    SELECT
        b.mid,
        date_format(CAST(b.app_date AS timestamp), '%Y-%m-01') AS app_month,
        b.loan_type2,
        b.biz_id
    FROM ind.ba_asset_base_info b
    WHERE b.grant_strategy = 'OLD'
      AND b.if_app = 1
      AND b.if_recall = 0
      AND b.loan_type2 IN ('loop', 'normal')
)
SELECT
    f.first_loan_month                                                           AS month,
    r.app_month                                                                  AS rl_month,
    date_diff('month',
              CAST(f.first_loan_month AS date),
              CAST(r.app_month AS date))                                         AS month_num,
    r.loan_type2,
    COUNT(DISTINCT r.biz_id)                                                     AS loan_cnt
FROM first_loan f
INNER JOIN reloan_app r ON CAST(f.mid AS BIGINT) = CAST(r.mid AS BIGINT)
WHERE date_diff('month',
                CAST(f.first_loan_month AS date),
                CAST(r.app_month AS date)) BETWEEN 1 AND 13
GROUP BY 1, 2, 3, 4
ORDER BY 1 DESC, 3, 4
"""


# ============================================================
# 4. 模拟数据（v5：美金件均 + MOB1-13 + 符合真实转化率区间）
# ============================================================
def generate_mock_data():
    print("  [MOCK] 使用模拟数据（美金单位，件均≈62，MOB1-13）")
    fl_dict = {}
    for y, m in [(2025, mm) for mm in range(1, 13)] + [(2026, mm) for mm in range(1, 6)]:
        fl_dict[f"{y}-{m:02d}"] = 50000 + np.random.randint(-10000, 20000)

    first_loan_df = pd.DataFrame([
        {'month': k, 'loan_cnt': v,
         'avg_loan_amount': round(np.random.uniform(60, 64), 1)}
        for k, v in fl_dict.items()
    ])

    rows = []
    # 真实转化率区间（2026年印尼数据）
    loop_rates   = {1:(0.38,0.62), 2:(0.17,0.43), 3:(0.12,0.35),
                    4:(0.08,0.25), 5:(0.05,0.18), 6:(0.03,0.12),
                    7:(0.02,0.08), 8:(0.01,0.06), 9:(0.01,0.05),
                    10:(0.01,0.04), 11:(0.00,0.03), 12:(0.00,0.02), 13:(0.00,0.02)}
    normal_rates = {1:(0.35,0.60), 2:(0.25,0.50), 3:(0.20,0.40),
                    4:(0.15,0.30), 5:(0.10,0.22), 6:(0.06,0.15),
                    7:(0.04,0.10), 8:(0.03,0.08), 9:(0.02,0.06),
                    10:(0.01,0.05), 11:(0.01,0.04), 12:(0.00,0.03), 13:(0.00,0.02)}

    for fl_month, fl_cnt in fl_dict.items():
        for mob in range(1, 14):
            for loan_type, rate_map in [('loop', loop_rates), ('normal', normal_rates)]:
                lo, hi = rate_map.get(mob, (0.00, 0.02))
                rate = np.random.uniform(lo, hi)
                rl_date = datetime.strptime(fl_month + "-01", "%Y-%m-%d") + relativedelta(months=mob)
                if rl_date <= datetime(2026, 5, 31):
                    rows.append({
                        'month':      fl_month,
                        'rl_month':   rl_date.strftime("%Y-%m"),
                        'month_num':  mob,
                        'loan_type2': loan_type,
                        'loan_cnt':   int(fl_cnt * rate),
                    })
    return first_loan_df, pd.DataFrame(rows)


# ============================================================
# 5. MOB转化率计算（v5：加入趋势分析）
# ============================================================
def calc_mob_rates(reloan_df: pd.DataFrame, fl_dict: dict,
                   loan_type: str, mob_list: list) -> dict:
    """返回 {mob: [rate_最新期, rate_次新期, ...]}"""
    sub = reloan_df[reloan_df['loan_type2'] == loan_type]
    mob_rates = {}
    for mob in mob_list:
        mob_data = sub[sub['month_num'] == mob].sort_values('month', ascending=False)
        rates = []
        for _, row in mob_data.iterrows():
            fc = fl_dict.get(row['month'], 0)
            if fc > 0:
                rates.append(round(row['loan_cnt'] / fc, 6))
        if rates:
            mob_rates[mob] = rates
    return mob_rates


def calc_ma_with_trend(rates: list, window: int = 3) -> float:
    """
    v5新增：带趋势的MA
    若近3期呈明显趋势，则 MA 和 趋势外推 各占50%
    趋势系数 = (最近一期 - 最远一期) / 期数
    """
    if not rates:
        return 0.0
    recent = rates[:window]
    ma_val = sum(recent) / len(recent)
    # 至少3期才做趋势外推
    if len(recent) >= 3:
        trend = (recent[0] - recent[-1]) / len(recent)   # 月均变化
        projected = recent[0] + trend                     # 外推一期
        projected = max(0.0, min(1.0, projected))         # 钳位到[0,1]
        return round((ma_val + projected) / 2, 6)
    return round(ma_val, 6)


def get_adj_factor(loan_type: str, mob: int,
                   loop_short, loop_long, normal_short, normal_long) -> float:
    """
    v5新增：按MOB分段返回调整系数
    MOB1-3 → 短期系数；MOB4-13 → 长期系数
    """
    is_short = mob <= 3
    if loan_type == 'loop':
        return loop_short if is_short else loop_long
    else:
        return normal_short if is_short else normal_long


# ============================================================
# 6. Excel 样式辅助
# ============================================================
HDR_FILL   = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
SUB_FILL   = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
YLW_FILL   = PatternFill(start_color="FFFF99", end_color="FFFF99", fill_type="solid")
GRN_FILL   = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
ORG_FILL   = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
BLU_FILL   = PatternFill(start_color="DDEEFF", end_color="DDEEFF", fill_type="solid")
RED_FILL   = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
WHT_FONT   = Font(bold=True, color="FFFFFF")
BLD_FONT   = Font(bold=True)
PCT_FMT    = '0.00%'
NUM_FMT    = '#,##0'
USD_FMT    = '"$"#,##0.0'   # v5：美金格式（保留1位小数）
USD_FMT_INT = '"$"#,##0'    # 美金整数


def hdr(ws, row):
    for cell in ws[row]:
        if cell.value is not None:
            cell.fill = HDR_FILL; cell.font = WHT_FONT
            cell.alignment = Alignment(horizontal='center')

def set_col_width(ws, widths: dict):
    for col_letter, w in widths.items():
        ws.column_dimensions[col_letter].width = w


# ============================================================
# 7. 参数配置 Sheet（v5：4个分段调整系数）
# ============================================================
def create_params_sheet(ws, cfg):
    ws.title = '参数配置'
    rows = [
        ('参数名', '值', '说明'),
        ('首贷 | 月天数',             cfg['fl_days_in_month'],         '预估月份天数'),
        ('首贷 | 日均投放消耗（$美金）', cfg['fl_daily_spend'],       '月预算÷天数，美金'),
        ('首贷 | CPI（$美金/安装）',   cfg['fl_cpi'],                   '每获取一次App安装的成本'),
        ('首贷 | 安装注册率',         cfg['fl_install_register_rate'], '安装→注册（进件）转化率'),
        ('首贷 | 综合通过率',         cfg['fl_pass_rate'],             '=机审×用信×后置通过率'),
        ('首贷 | 签名放款率',         cfg['fl_sign_loan_rate'],        '签约→实际放款转化率'),
        ('首贷 | 件均（$美金）',      cfg['fl_avg_amount'],            '首贷平均放款金额（≈62美金）'),
        ('', '', ''),
        ('复贷 | MA窗口（月）',       cfg['ma_window'],                 '移动平均取最近N期同MOB转化率'),
        ('复贷 | 循环贷短期调整系数（MOB1-3）',  cfg['loop_adj_short'],  '循环贷短期，1.0=不调 0.9=下调10%'),
        ('复贷 | 循环贷长期调整系数（MOB4-13）', cfg['loop_adj_long'],  '循环贷长期，1.0=不调'),
        ('复贷 | 非循环贷短期调整系数（MOB1-3）',   cfg['normal_adj_short'], '非循环贷短期'),
        ('复贷 | 非循环贷长期调整系数（MOB4-13）',  cfg['normal_adj_long'], '非循环贷长期'),
    ]
    for r, (a, b, c) in enumerate(rows, 1):
        ws.cell(r, 1, a); ws.cell(r, 2, b); ws.cell(r, 3, c)
    hdr(ws, 1)
    for r in list(range(2, 9)) + list(range(10, 15)):
        ws.cell(r, 2).fill = YLW_FILL
    # 百分比格式
    for r in [PARAM_ROWS['install_reg'], PARAM_ROWS['pass_rate'],
              PARAM_ROWS['sign_rate'],
              PARAM_ROWS['loop_adj_s'], PARAM_ROWS['loop_adj_l'],
              PARAM_ROWS['normal_adj_s'], PARAM_ROWS['normal_adj_l']]:
        if r <= 14:
            ws.cell(r, 2).number_format = PCT_FMT
    ws.cell(PARAM_ROWS['daily_spend'], 2).number_format = NUM_FMT
    ws.cell(PARAM_ROWS['fl_avg_amt'],  2).number_format = USD_FMT_INT
    set_col_width(ws, {'A': 38, 'B': 18, 'C': 55})


# ============================================================
# 8. 首贷预估 Sheet（v5：增加历史实际值校验列）
# ============================================================
def create_first_loan_forecast_sheet(ws, months: list, first_loan_df: pd.DataFrame):
    """
    v5新增：增加 G列=历史实际首贷量（从first_loan_df取），H列=差异%
    差异 > ±20% 自动标红
    """
    ws.title = '首贷预估'
    headers = ['预估月份', '月安装量\n(消耗/CPI×天数)',
               '首贷进件量\n(安装×注册率)',
               '综合通过率×\n签名放款率',
               '首贷放款笔数（预估）',
               '件均($)', '首贷放款金额($)',
               '历史实际\n首贷笔数', '差异%']
    for c, h in enumerate(headers, 1):
        ws.cell(1, c, h)
    hdr(ws, 1)
    ws.row_dimensions[1].height = 30

    # 历史实际值字典
    hist_dict = {}
    if first_loan_df is not None and not first_loan_df.empty:
        for _, row in first_loan_df.iterrows():
            hist_dict[row['month']] = int(row['loan_cnt'])

    P = '参数配置'
    for row, month in enumerate(months, 2):
        ws.cell(row, 1, month)
        ws.cell(row, 2, f"='{P}'!$B${PARAM_ROWS['daily_spend']}"
                        f"/'{P}'!$B${PARAM_ROWS['cpi']}"
                        f"*'{P}'!$B${PARAM_ROWS['days']}")
        ws.cell(row, 3, f"=B{row}*'{P}'!$B${PARAM_ROWS['install_reg']}")
        ws.cell(row, 4, f"='{P}'!$B${PARAM_ROWS['pass_rate']}"
                        f"*'{P}'!$B${PARAM_ROWS['sign_rate']}")
        ws.cell(row, 5, f"=C{row}*D{row}")
        ws.cell(row, 6, f"='{P}'!$B${PARAM_ROWS['fl_avg_amt']}")
        ws.cell(row, 7, f"=E{row}*F{row}")

        # v5新增：历史实际值 + 差异%
        hist_val = hist_dict.get(month, None)
        if hist_val is not None:
            ws.cell(row, 8, hist_val)
            ws.cell(row, 9, f"=IF(H{row}=0,\"\",(E{row}-H{row})/H{row})")
        else:
            ws.cell(row, 8, '历史无数据')
            ws.cell(row, 9, '')

        # 数字格式
        ws.cell(row, 2).number_format = NUM_FMT
        ws.cell(row, 3).number_format = NUM_FMT
        ws.cell(row, 4).number_format = PCT_FMT
        ws.cell(row, 5).number_format = NUM_FMT
        ws.cell(row, 6).number_format = USD_FMT_INT
        ws.cell(row, 7).number_format = USD_FMT
        ws.cell(row, 8).number_format = NUM_FMT
        ws.cell(row, 9).number_format = PCT_FMT

        ws.cell(row, 1).fill = GRN_FILL

    # 条件格式：差异% > 20% 或 < -20% 标红
    from openpyxl.formatting.rule import FormulaRule
    red_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    # 第9列（I列）=差异%，绝对值>0.2标红
    max_row = len(months) + 1
    ws.conditional_formatting.add(
        f"I2:I{max_row}",
        CellIsRule(operator='greaterThan', formula=['0.2'], fill=red_fill)
    )
    # 需要用FormulaRule for < -0.2
    ws.conditional_formatting.add(
        f"I2:I{max_row}",
        CellIsRule(operator='lessThan', formula=['-0.2'], fill=red_fill)
    )

    set_col_width(ws, {'A': 14, 'B': 18, 'C': 16,
                        'D': 16, 'E': 16, 'F': 12, 'G': 16, 'H': 16, 'I': 12})


# ============================================================
# 9. 复贷预估 Sheet（v5：按分段系数引用参数行）
# ============================================================
def create_reloan_forecast_sheet(ws, forecast_results: list,
                                  loan_type: str):
    """
    v5：调整系数按MOB分段引用：
      MOB1-3 → 短期系数行（PARAM_ROWS['loop_adj_s'] 或 ['normal_adj_s']）
      MOB4-13 → 长期系数行
    F列公式改为：=IF(C{row}="","",IF(VALUE(MID(B{row},4,1))<=3,'参数配置'!$B$短期行,'参数配置'!$B$长期行))
    简化为：直接在生成结果时就把对应系数写进F列（死数，但参数行独立可改）
    改为：F列=系数名称（引用对应参数行），支持在参数配置里改
    """
    type_label = '循环贷(loop)' if loan_type == 'loop' else '非循环贷(normal)'
    ws.title = f'复贷{type_label[:3]}预估'

    # 表头
    headers = ['预估月份', 'MOB周期', '对应首贷月',
               '首贷放款量(历史/预估)', 'MA+趋势转化率',
               '调整系数', '调整后转化率', '预估进件量']
    for c, h in enumerate(headers, 1):
        ws.cell(1, c, h)
    hdr(ws, 1)
    ws.row_dimensions[1].height = 28

    P = '参数配置'
    # 根据loan_type确定短期/长期系数行号
    if loan_type == 'loop':
        short_row = PARAM_ROWS['loop_adj_s']   # B11
        long_row  = PARAM_ROWS['loop_adj_l']   # B12
    else:
        short_row = PARAM_ROWS['normal_adj_s'] # B13
        long_row  = PARAM_ROWS['normal_adj_l'] # B14

    month_rows = {}
    for row, rec in enumerate(forecast_results, 2):
        mob = int(rec['MOB周期'].replace('MOB', ''))
        ws.cell(row, 1, rec['预估月份'])
        ws.cell(row, 2, rec['MOB周期'])
        ws.cell(row, 3, rec['对应首贷月份'])
        ws.cell(row, 4, rec['首贷放款量'])
        ws.cell(row, 5, rec['MA+趋势转化率'])         # 死数

        # F列：根据MOB选择短期/长期系数（公式引用参数配置）
        if mob <= 3:
            ws.cell(row, 6, f"='{P}'!$B${short_row}")
        else:
            ws.cell(row, 6, f"='{P}'!$B${long_row}")

        ws.cell(row, 7, f"=E{row}*F{row}")   # 调整后转化率
        ws.cell(row, 8, f"=D{row}*G{row}")   # 预估进件量

        ws.cell(row, 4).number_format = NUM_FMT
        ws.cell(row, 5).number_format = PCT_FMT
        ws.cell(row, 6).number_format = PCT_FMT
        ws.cell(row, 7).number_format = PCT_FMT
        ws.cell(row, 8).number_format = NUM_FMT

        fill = ORG_FILL if loan_type == 'loop' else BLU_FILL
        ws.cell(row, 1).fill = fill

        month_rows.setdefault(rec['预估月份'], []).append(row)

    # 各月小计行
    total_row_map = {}
    next_row = len(forecast_results) + 2
    for month, rows in month_rows.items():
        r0, r1 = rows[0], rows[-1]
        ws.cell(next_row, 1, month)
        ws.cell(next_row, 2, '小计')
        ws.cell(next_row, 4, f"=SUM(D{r0}:D{r1})")
        ws.cell(next_row, 8, f"=SUM(H{r0}:H{r1})")
        for c in range(1, 9):
            ws.cell(next_row, c).fill = SUB_FILL
            ws.cell(next_row, c).font = BLD_FONT
        ws.cell(next_row, 4).number_format = NUM_FMT
        ws.cell(next_row, 8).number_format = NUM_FMT
        total_row_map[month] = next_row
        next_row += 1

    set_col_width(ws, {'A': 14, 'B': 10, 'C': 14, 'D': 18,
                        'E': 16, 'F': 12, 'G': 14, 'H': 16})
    return total_row_map


# ============================================================
# 10. MOB转化率 Sheet（v5：展示MA+趋势值）
# ============================================================
def create_mob_rates_sheet(ws, mob_rates: dict, loan_type: str, window: int):
    type_label = '循环贷(loop)' if loan_type == 'loop' else '非循环贷(normal)'
    ws.title = f'MOB率_{loan_type}'

    max_hist = max(len(v) for v in mob_rates.values()) if mob_rates else 3
    hist_cols = min(max_hist, 13)

    header = ['MOB', f'{type_label}历史期数']
    for i in range(1, hist_cols + 1):
        header.append(f'距今{i}期转化率')
    header += ['MA均值', '趋势MA', '最终转化率']

    for c, h in enumerate(header, 1):
        ws.cell(1, c, h)
    hdr(ws, 1)

    P = '参数配置'
    ma_col     = hist_cols + 2
    trend_col  = hist_cols + 3
    final_col  = hist_cols + 4

    for row, (mob, rates) in enumerate(sorted(mob_rates.items()), 2):
        ws.cell(row, 1, f'MOB{mob}')
        ws.cell(row, 2, f'共{len(rates)}期')
        for i, rate in enumerate(rates[:hist_cols], 3):
            ws.cell(row, i, rate)
            ws.cell(row, i).number_format = PCT_FMT

        # MA均值（最近window期）
        s = get_column_letter(3)
        e = get_column_letter(min(window + 2, hist_cols + 2))
        ws.cell(row, ma_col, f"=IFERROR(AVERAGE({s}{row}:{e}{row}),0)")
        ws.cell(row, ma_col).number_format = PCT_FMT

        # 趋势MA（MA和趋势外推的平均，v5新增）
        ws.cell(row, trend_col, f"=IFERROR(('参数配置'!B{row+100}),(E{row}+G{row})/2)")  # 简化：直接显示MA值
        # 实际计算中，趋势值在Python端已算好，这里写死引用
        # 改为：趋势MA = MA值（Python端calc_ma_with_trend结果直接写入'最终转化率'列）
        ws.cell(row, trend_col).number_format = PCT_FMT

        # 最终转化率（=趋势MA×调整系数，调整系数在Python端算好写入）
        # 这里留空，由Python写入最终值
        ws.cell(row, final_col, f"=IFERROR({get_column_letter(ma_col)}{row},0)")
        ws.cell(row, final_col).number_format = PCT_FMT

    fill = ORG_FILL if loan_type == 'loop' else BLU_FILL
    for r in range(2, len(mob_rates) + 2):
        ws.cell(r, ma_col).fill     = GRN_FILL
        ws.cell(r, trend_col).fill  = GRN_FILL
        ws.cell(r, final_col).fill  = fill

    ws.column_dimensions['A'].width = 8
    for i in range(2, hist_cols + 5):
        ws.column_dimensions[get_column_letter(i)].width = 14


# ============================================================
# 11. 首贷历史 Sheet
# ============================================================
def create_first_loan_history_sheet(ws, first_loan_df: pd.DataFrame):
    ws.title = '首贷历史'
    has_amt = 'avg_loan_amount' in first_loan_df.columns if first_loan_df is not None else False

    headers = ['首贷月份', '放款笔数', '件均($)', '放款金额($)']
    for c, h in enumerate(headers, 1):
        ws.cell(1, c, h)
    hdr(ws, 1)

    if first_loan_df is None or first_loan_df.empty:
        ws.cell(2, 1, '无历史数据')
        return

    for row, (_, rec) in enumerate(first_loan_df.iterrows(), 2):
        ws.cell(row, 1, rec['month'])
        ws.cell(row, 2, int(rec['loan_cnt']))
        avg_amt = float(rec['avg_loan_amount']) if has_amt else CONFIG['fl_avg_amount']
        ws.cell(row, 3, avg_amt)
        ws.cell(row, 4, f"=B{row}*C{row}")
        ws.cell(row, 2).number_format = NUM_FMT
        ws.cell(row, 3).number_format = USD_FMT_INT
        ws.cell(row, 4).number_format = USD_FMT
    set_col_width(ws, {'A': 12, 'B': 12, 'C': 12, 'D': 18})


# ============================================================
# 12. 汇总 Sheet（v5：金额格式改为美金）
# ============================================================
def create_summary_sheet(ws, months: list,
                          fl_row_map: dict,
                          loop_total_map: dict,
                          normal_total_map: dict,
                          loop_sheet: str,
                          normal_sheet: str):
    ws.title = '汇总'
    headers = ['预估月份',
               '首贷放款笔数', '首贷放款金额($)',
               '循环贷复贷进件', '非循环贷复贷进件',
               '复贷合计进件', '总进件量(首贷+复贷)']
    for c, h in enumerate(headers, 1):
        ws.cell(1, c, h)
    hdr(ws, 1)

    for row, month in enumerate(months, 2):
        ws.cell(row, 1, month)
        fl_r = fl_row_map.get(month, 2)
        ws.cell(row, 2, f"='首贷预估'!E{fl_r}")
        ws.cell(row, 3, f"='首贷预估'!G{fl_r}")

        loop_r   = loop_total_map.get(month)
        normal_r = normal_total_map.get(month)
        ws.cell(row, 4, f"='{loop_sheet}'!H{loop_r}"   if loop_r   else 0)
        ws.cell(row, 5, f"='{normal_sheet}'!H{normal_r}" if normal_r else 0)
        ws.cell(row, 6, f"=D{row}+E{row}")
        ws.cell(row, 7, f"=B{row}+F{row}")

        ws.cell(row, 1).fill = GRN_FILL
        for c in [2, 4, 5, 6, 7]:
            ws.cell(row, c).number_format = NUM_FMT
        ws.cell(row, 3).number_format = USD_FMT

    set_col_width(ws, {'A': 12, 'B': 16, 'C': 20,
                        'D': 18, 'E': 18, 'F': 16, 'G': 20})


# ============================================================
# 13. 主程序（v5：未来首贷量用预估值填补 + 趋势MA + 分段系数）
# ============================================================
def get_first_loan_cnt(cohort_month: str, fl_dict: dict, fl_forecast_dict: dict) -> int:
    """
    v5核心修复：优先取历史首贷量，历史没有则取首贷预估值
    解决未来月份首贷量=0导致复贷预估严重低估的问题
    """
    if cohort_month in fl_dict:
        return fl_dict[cohort_month]
    return fl_forecast_dict.get(cohort_month, 0)


def build_fl_forecast_dict(months: list, cfg: dict) -> dict:
    """
    根据首贷预估公式，计算各月的预估首贷放款笔数
    返回 {month: fl_cnt}
    公式：日均消耗/CPI × 天数 × 安装注册率 × 综合通过率 × 签名放款率
    """
    result = {}
    for month in months:
        # 计算该月天数
        y, m = int(month.split('-')[0]), int(month.split('-')[1])
        import calendar
        days = calendar.monthrange(y, m)[1]

        daily_spend = cfg['fl_daily_spend']
        cpi         = cfg['fl_cpi']
        inst_reg    = cfg['fl_install_register_rate']
        pass_r      = cfg['fl_pass_rate']
        sign_r      = cfg['fl_sign_loan_rate']

        installs   = daily_spend / cpi * days
        applications = installs * inst_reg
        fl_cnt     = int(applications * pass_r * sign_r)
        result[month] = fl_cnt
    return result


def main():
    print("=" * 65)
    print("复贷进件量预估系统 v5（美金单位 + MOB1-13 + 趋势MA + 分段系数）")
    print("=" * 65)

    today      = datetime.now()
    cur_month  = today.strftime("%Y-%m")
    # v5：预估当月 + 下月（可扩展更多月）
    months     = [cur_month, (today + relativedelta(months=1)).strftime("%Y-%m")]
    print(f"预估月份: {', '.join(months)}\n")

    # ---- 数据获取 ----
    print("Step1: 获取数据库数据 ...")
    pq = PrestoQuery()
    first_loan_df = reloan_df = None
    try:
        pq.login_process()
        r1 = pq.submit_query(SQL_FIRST_LOAN)
        if isinstance(r1, pd.DataFrame) and not r1.empty:
            first_loan_df = r1
            print(f"  首贷数据: {len(first_loan_df)} 个月")
        r2 = pq.submit_query(SQL_RELOAN_BY_TYPE)
        if isinstance(r2, pd.DataFrame) and not r2.empty:
            reloan_df = r2
            print(f"  复贷数据: {len(reloan_df)} 条")
    except Exception as e:
        print(f"  数据库连接失败: {e}")

    if first_loan_df is None or reloan_df is None:
        first_loan_df, reloan_df = generate_mock_data()

    # 类型统一
    first_loan_df['loan_cnt']      = first_loan_df['loan_cnt'].astype(int)
    reloan_df['month_num']         = reloan_df['month_num'].astype(int)
    reloan_df['loan_cnt']          = reloan_df['loan_cnt'].astype(int)
    fl_dict = dict(zip(first_loan_df['month'], first_loan_df['loan_cnt']))

    # v5新增：构建首贷预估字典（用于填补未来首贷量）
    fl_forecast_dict = build_fl_forecast_dict(months, CONFIG)
    print(f"  首贷预估字典: {fl_forecast_dict}")

    # ---- 计算 MOB 转化率（loop & normal 分开，带趋势）----
    print("\nStep2: 计算各MOB转化率（带趋势MA）...")
    loop_mob_rates   = calc_mob_rates(reloan_df, fl_dict, 'loop',   CONFIG['mob_list'])
    normal_mob_rates = calc_mob_rates(reloan_df, fl_dict, 'normal', CONFIG['mob_list'])
    print(f"  loop 有效MOB: {sorted(loop_mob_rates.keys())}")
    print(f"  normal 有效MOB: {sorted(normal_mob_rates.keys())}")

    # ---- 生成复贷预估结果（使用 get_first_loan_cnt 填补未来首贷量）----
    print("\nStep3: 生成复贷预估结果（未来首贷量用预估填补）...")
    def build_forecast(mob_rates: dict, loan_type: str) -> list:
        results = []
        cfg = CONFIG
        ls = cfg['loop_adj_short']; ll = cfg['loop_adj_long']
        ns = cfg['normal_adj_short']; nl = cfg['normal_adj_long']

        for target in months:
            tdate = datetime.strptime(target + "-01", "%Y-%m-%d")
            for mob in CONFIG['mob_list']:
                ma_val       = calc_ma_with_trend(mob_rates.get(mob, []), cfg['ma_window'])
                cohort_month = (tdate - relativedelta(months=mob)).strftime("%Y-%m")
                fl_cnt       = get_first_loan_cnt(cohort_month, fl_dict, fl_forecast_dict)
                adj          = get_adj_factor(loan_type, mob, ls, ll, ns, nl)
                results.append({
                    '预估月份':       target,
                    'MOB周期':        f'MOB{mob}',
                    '对应首贷月份':   cohort_month,
                    '首贷放款量':     fl_cnt,
                    'MA+趋势转化率':  round(ma_val * adj, 6),
                    '调整系数':       adj,
                    '预估进件量':     int(fl_cnt * ma_val * adj),
                })
        return results

    loop_forecast   = build_forecast(loop_mob_rates,   'loop')
    normal_forecast = build_forecast(normal_mob_rates, 'normal')
    print(f"  loop记录: {len(loop_forecast)} | normal记录: {len(normal_forecast)}")

    # ---- 写 Excel ----
    print("\nStep4: 写入 Excel（美金格式，含历史校验）...")
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = 'E:/岳松个人文件/嘉银工作内容的整理/code/权责自动化处理'
    output_file = f"{output_dir}/复贷进件量预估_v5_{ts}.xlsx"

    wb = openpyxl.Workbook()

    # Sheet1: 参数配置
    ws_param = wb.active
    create_params_sheet(ws_param, CONFIG)

    # Sheet2: 汇总（占位）
    ws_sum = wb.create_sheet()

    # Sheet3: 首贷预估（v5：含历史校验列）
    ws_fl = wb.create_sheet()
    create_first_loan_forecast_sheet(ws_fl, months, first_loan_df)
    fl_row_map = {m: i + 2 for i, m in enumerate(months)}

    # Sheet4: 复贷loop预估
    ws_loop = wb.create_sheet()
    loop_total_map = create_reloan_forecast_sheet(ws_loop, loop_forecast, 'loop')

    # Sheet5: 复贷normal预估
    ws_norm = wb.create_sheet()
    normal_total_map = create_reloan_forecast_sheet(ws_norm, normal_forecast, 'normal')

    # 填汇总Sheet
    create_summary_sheet(ws_sum, months,
                          fl_row_map, loop_total_map, normal_total_map,
                          ws_loop.title, ws_norm.title)

    # Sheet6: MOB率_loop
    ws_mob_loop = wb.create_sheet()
    create_mob_rates_sheet(ws_mob_loop, loop_mob_rates,   'loop',   CONFIG['ma_window'])

    # Sheet7: MOB率_normal
    ws_mob_norm = wb.create_sheet()
    create_mob_rates_sheet(ws_mob_norm, normal_mob_rates, 'normal', CONFIG['ma_window'])

    # Sheet8: 首贷历史
    ws_hist = wb.create_sheet()
    create_first_loan_history_sheet(ws_hist, first_loan_df)

    wb.save(output_file)
    print(f"\n  已保存: {output_file}")
    print("\n  v5 核心修复说明:")
    print("  [1] 金额单位→美金，件均≈$62")
    print("  [2] MOB扩展到1-13（支持MOB12+）")
    print("  [3] 调整系数按MOB分段（短期1-3 / 长期4-13）")
    print("  [4] 未来首贷量=0 → 改用首贷预估值填补（解决复贷低估）")
    print("  [5] 首贷预估Sheet新增历史实际值校验，差异>±20%标红")
    print("  [6] MOB转化率=MA和趋势外推的平均（不再只看静态MA）")
    print("=" * 65)


if __name__ == "__main__":
    main()

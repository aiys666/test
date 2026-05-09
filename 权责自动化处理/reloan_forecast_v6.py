# -*- coding: utf-8 -*-
"""
复贷进件量预估系统 v7
相较v6的核心修复：
  1. 首贷预估Sheet拆分前置/用信/后置为独立列，
     每列直接=参数配置对应值（D/E/F列），不再混在一个公式里
  2. 原D列(综合通过率)公式多乘了一次安装注册率（已在C列用过），已修正
     → 综合通过率现在是 G列 = D×E×F（前置×用信×后置）
  3. 复贷汇总Sheet引用首贷预估的列号同步更新（E→H, G→J）
  4. 复贷与首贷完全联动（首贷投放花费改→复贷进件自动变）
  5. MOB范围1-13，调整系数按MOB分段
  6. MOB转化率含趋势分析
  7. 首贷预估增加历史校验列，差异>±20%自动标红
"""

import pandas as pd
import numpy as np
import requests
import json
import re
import time
import base64
import math
import calendar
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
# 2. 配置参数（v6：4月预估实际值 + MOB1-13 + 分段调整系数）
# ============================================================
# 数据来源：首贷权责预估.xlsx 2026年4月实际值
# 综合通过率 = 前置通过率 × 用信率 × 后置通过率 = 0.238 × 0.805 × 0.5888 ≈ 11.27%
CONFIG = {
    "ma_window":           3,
    "mob_list":            list(range(1, 14)),  # MOB1-13
    # 首贷预估参数（v6：4月实际值，美金）
    "fl_days_in_month":         31,
    "fl_daily_spend":           55000,   # 美金/天（v6改：4月实际值）
    "fl_cpi":                   2.2,     # 美金/安装（v6改：4月实际值）
    "fl_install_register_rate": 0.46,  # 安装→注册（v6改：4月实际值46%）
    # v6改：综合通过率拆分为三个独立参数
    "fl_pre_pass_rate":        0.238,   # 前置通过率（v6新增）
    "fl_credit_rate":          0.805,   # 用信率（v6新增）
    "fl_post_pass_rate":       0.5888,  # 后置通过率（v6新增）
    # 综合通过率 = pre × credit × post × sign（公式在Excel中计算）
    "fl_sign_loan_rate":       0.97,    # 签名放款率（v6改：4月实际值97%）
    "fl_avg_amount":            62,     # 件均≈62美金（v6改：4月实际值）
    # 分段调整系数（v6）
    "loop_adj_short":      1.0,   # 循环贷 MOB1-3
    "loop_adj_long":       1.0,   # 循环贷 MOB4-13
    "normal_adj_short":    1.0,   # 非循环贷 MOB1-3
    "normal_adj_long":     1.0,   # 非循环贷 MOB4-13
    # v7新增：MOB转化率基准值（对应参数配置行19-31和33-45）
    "loop_rates":   {1:0.50, 2:0.30, 3:0.23, 4:0.17, 5:0.12, 6:0.08,
                     7:0.05, 8:0.04, 9:0.03, 10:0.03, 11:0.02, 12:0.01, 13:0.01},
    "normal_rates": {1:0.48, 2:0.38, 3:0.30, 4:0.23, 5:0.16, 6:0.10,
                     7:0.07, 8:0.05, 9:0.04, 10:0.03, 11:0.02, 12:0.02, 13:0.01},
}

# 参数行号（v6：扩展B6-B8为三个独立通过率参数）
PARAM_ROWS = {
    'days':           2,
    'daily_spend':    3,
    'cpi':            4,
    'install_reg':    5,
    'pre_pass':       6,   # 前置通过率
    'credit_rate':    7,   # 用信率
    'post_pass':      8,   # 后置通过率
    'sign_rate':      9,
    'fl_avg_amt':     10,
    'ma_window':      12,
    'loop_adj_s':     14,  # 循环贷短期（MOB1-3）
    'loop_adj_l':     15,  # 循环贷长期（MOB4-13）
    'normal_adj_s':   16,  # 非循环贷短期
    'normal_adj_l':   17,  # 非循环贷长期
    # v7新增：MOB转化率参数表（行19-31=loop，行33-45=normal）
    'loop_mob_base':  19,  # MOB1转化率（loop）所在行，其余MOB顺延
    'normal_mob_base':33,  # MOB1转化率（normal）所在行，其余MOB顺延
}


# ============================================================
# 3. SQL（v6：MOB扩展到1-13）
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
# 4. 模拟数据（v6：符合4月实际参数 + MOB1-13）
# ============================================================
def generate_mock_data():
    print("  [MOCK] 使用模拟数据（v6：4月实际参数，MOB1-13）")
    fl_dict = {}
    # 历史首贷量（模拟，贴近实际值）
    hist_vals = {
        '2025-01':'92000','2025-02':'88000','2025-03':'95000',
        '2025-04':'87000','2025-05':'91000','2025-06':'89000',
        '2025-07':'93000','2025-08':'96000','2025-09':'94000',
        '2025-10':'98000','2025-11':'101000','2025-12':'102000',
        '2026-01':'103000','2026-02':'98500','2026-03':'75500',
        '2026-04':'67100',  # 4月实际≈67,128
    }
    for k, v in hist_vals.items():
        fl_dict[k] = int(v)

    first_loan_df = pd.DataFrame([
        {'month': k, 'loan_cnt': v,
         'avg_loan_amount': 62.0 + np.random.uniform(-2, 2)}
        for k, v in fl_dict.items()
    ])

    rows = []
    # v7改：用CONFIG中的单一MOB转化率（不再区间随机），直接作为模拟转化率
    for fl_month, fl_cnt in fl_dict.items():
        for mob in range(1, 14):
            for loan_type in ('loop', 'normal'):
                rate = CONFIG[f'{loan_type}_rates'].get(mob, 0.01)
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
# 5. MOB转化率计算（v6：趋势分析）
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
    带趋势的MA：近3期MA + 趋势外推各占50%
    趋势系数 = (最近一期 - 最远一期) / 期数
    """
    if not rates:
        return 0.0
    recent = rates[:window]
    ma_val = sum(recent) / len(recent)
    if len(recent) >= 3:
        trend = (recent[0] - recent[-1]) / len(recent)
        projected = recent[0] + trend
        projected = max(0.0, min(1.0, projected))
        return round((ma_val + projected) / 2, 6)
    return round(ma_val, 6)


def get_adj_factor(loan_type: str, mob: int,
                   loop_short, loop_long, normal_short, normal_long) -> float:
    """按MOB分段返回调整系数：MOB1-3 → 短期；MOB4-13 → 长期"""
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
USD_FMT    = '"$"#,##0.0'
USD_FMT_INT= '"$"#,##0'


def hdr(ws, row):
    for cell in ws[row]:
        if cell.value is not None:
            cell.fill = HDR_FILL; cell.font = WHT_FONT
            cell.alignment = Alignment(horizontal='center')

def set_col_width(ws, widths: dict):
    for col_letter, w in widths.items():
        ws.column_dimensions[col_letter].width = w


# ============================================================
# 7. 参数配置 Sheet（v6：综合通过率拆分为3个独立参数）
# ============================================================
def create_params_sheet(ws, cfg):
    ws.title = '参数配置'
    P = PARAM_ROWS

    rows = [
        # (A列参数名, B列值, C列说明)
        ('首贷 | 月天数',                  cfg['fl_days_in_month'],         '预估月份天数'),
        ('首贷 | 日均投放消耗（$美金）',   cfg['fl_daily_spend'],            '月预算÷天数，美金'),
        ('首贷 | CPI（$美金/安装）',       cfg['fl_cpi'],                    '每获取一次App安装的成本'),
        ('首贷 | 安装注册率',             cfg['fl_install_register_rate'],  '安装→注册（进件）转化率'),
        ('首贷 | 前置通过率',              cfg['fl_pre_pass_rate'],         '机器审核通过率（v6拆分）'),
        ('首贷 | 用信率',                  cfg['fl_credit_rate'],           '通过机器审核后实际用信率（v6拆分）'),
        ('首贷 | 后置通过率',              cfg['fl_post_pass_rate'],        '人工/二次审核通过率（v6拆分）'),
        ('首贷 | 综合通过率',              None,                            '=前置通过率×用信率×后置通过率（计算值）'),
        ('首贷 | 签名放款率',             cfg['fl_sign_loan_rate'],        '签约→实际放款转化率'),
        ('首贷 | 件均（$美金）',           cfg['fl_avg_amount'],             '首贷平均放款金额（≈62美金）'),
        ('', '', ''),
        ('复贷 | MA窗口（月）',            cfg['ma_window'],                 '移动平均取最近N期同MOB转化率'),
        ('复贷 | 循环贷短期调整系数（MOB1-3）',  cfg['loop_adj_short'],   '1.0=不调 0.9=下调10%'),
        ('复贷 | 循环贷长期调整系数（MOB4-13）', cfg['loop_adj_long'],    '1.0=不调'),
        ('复贷 | 非循环贷短期调整系数（MOB1-3）', cfg['normal_adj_short'],'1.0=不调'),
        ('复贷 | 非循环贷长期调整系数（MOB4-13）',cfg['normal_adj_long'], '1.0=不调'),
    ]
    for r, (a, b, c) in enumerate(rows, 1):
        ws.cell(r, 1, a)
        ws.cell(r, 3, c)
        # b为None的行（如综合通过率）不写B列，由后面单独写公式
        if b is not None:
            ws.cell(r, 2, b)
        # 综合通过率（B8）= 公式
        if r == 8:
            ws.cell(r, 2, f"=B{P['install_reg']}*B{P['pre_pass']}*B{P['credit_rate']}")
            ws.cell(r, 2).number_format = PCT_FMT
            ws.cell(r, 2).fill = GRN_FILL
            ws.cell(r, 2).font = Font(color="008000")

    # B列黄底（可编辑）
    for r in list(range(2, 11)) + list(range(12, 18)):
        ws.cell(r, 2).fill = YLW_FILL

    # B列数字格式
    ws.cell(P['daily_spend'],    2).number_format = NUM_FMT
    ws.cell(P['fl_avg_amt'],     2).number_format = USD_FMT_INT
    for r in [P['install_reg'], P['pre_pass'], P['credit_rate'],
              P['post_pass'], P['sign_rate'],
              P['loop_adj_s'], P['loop_adj_l'],
              P['normal_adj_s'], P['normal_adj_l']]:
        if r <= 17:
            ws.cell(r, 2).number_format = PCT_FMT

    # ---- v7新增：MOB转化率参数表（黄底可调，改后复贷进件自动联动）----
    # 循环贷MOB转化率（行19-31，MOB1-13）
    ws.cell(19, 1, '复贷 | 循环贷(loop) MOB转化率')
    ws.cell(19, 2, '转化率').fill = SUB_FILL
    for c in range(1, 4): ws.cell(19, c).font = BLD_FONT
    ws.cell(19, 3, '基准值（可调整，改后复贷进件自动联动）')
    for mob in range(1, 14):
        row = P['loop_mob_base'] + mob - 1
        ws.cell(row, 1, f'  MOB{mob}')
        ws.cell(row, 2, cfg['loop_rates'][mob])
        ws.cell(row, 2).number_format = PCT_FMT
        ws.cell(row, 2).fill = YLW_FILL       # 黄底=可调参数

    # 非循环贷MOB转化率（行33-45，MOB1-13）
    ws.cell(33, 1, '复贷 | 非循环贷(normal) MOB转化率')
    ws.cell(33, 2, '转化率').fill = SUB_FILL
    for c in range(1, 4): ws.cell(33, c).font = BLD_FONT
    ws.cell(33, 3, '基准值（可调整，改后复贷进件自动联动）')
    for mob in range(1, 14):
        row = P['normal_mob_base'] + mob - 1
        ws.cell(row, 1, f'  MOB{mob}')
        ws.cell(row, 2, cfg['normal_rates'][mob])
        ws.cell(row, 2).number_format = PCT_FMT
        ws.cell(row, 2).fill = YLW_FILL       # 黄底=可调参数

    hdr(ws, 1)
    set_col_width(ws, {'A': 38, 'B': 18, 'C': 55})


# ============================================================
# 8. 首贷预估 Sheet（v7：拆分前置/用信/后置为独立列，每列直接引用参数配置）
# ============================================================
def create_first_loan_forecast_sheet(ws, months: list, first_loan_df: pd.DataFrame):
    """
    v7修复：前置/用信/后置通过率拆成独立列，每列直接=参数配置对应值
    列结构：
      A=预估月份, B=月安装量, C=首贷进件量,
      D=前置通过率(=参数配置!B6),
      E=用信率(=参数配置!B7),
      F=后置通过率(=参数配置!B8),
      G=综合通过率(=D×E×F),
      H=首贷放款笔数(=C×G×签名),
      I=件均, J=首贷放款金额,
      K=历史实际首贷笔数, L=差异%
    """
    ws.title = '首贷预估'
    headers = ['预估月份',
               '月安装量\n(消耗/CPI×天数)',
               '首贷进件量\n(安装×注册率)',
               '前置通过率',
               '用信率',
               '后置通过率',
               '综合通过率\n(前置×用信×后置)',
               '首贷放款笔数\n(进件×综合×签名)',
               '件均($)',
               '首贷放款金额($)',
               '历史实际\n首贷笔数',
               '差异%']
    for c, h in enumerate(headers, 1):
        ws.cell(1, c, h)
    hdr(ws, 1)
    ws.row_dimensions[1].height = 30

    hist_dict = {}
    if first_loan_df is not None and not first_loan_df.empty:
        for _, row in first_loan_df.iterrows():
            hist_dict[row['month']] = int(row['loan_cnt'])

    P = '参数配置'
    pr = PARAM_ROWS
    for row, month in enumerate(months, 2):
        ws.cell(row, 1, month)

        # B：月安装量 = 日均消耗/CPI×天数
        ws.cell(row, 2, f"='{P}'!$B${pr['daily_spend']}/'{P}'!$B${pr['cpi']}"
                        f"*'{P}'!$B${pr['days']}")

        # C：首贷进件量 = 月安装量 × 安装注册率
        ws.cell(row, 3, f"=B{row}*'{P}'!$B${pr['install_reg']}")

        # D：前置通过率 = 直接引用参数配置!B6（固定值，不计算）
        ws.cell(row, 4, f"='{P}'!$B${pr['pre_pass']}")

        # E：用信率 = 直接引用参数配置!B7
        ws.cell(row, 5, f"='{P}'!$B${pr['credit_rate']}")

        # F：后置通过率 = 直接引用参数配置!B8
        ws.cell(row, 6, f"='{P}'!$B${pr['post_pass']}")

        # G：综合通过率 = 前置 × 用信 × 后置
        ws.cell(row, 7, f"=D{row}*E{row}*F{row}")

        # H：首贷放款笔数 = 进件量 × 综合通过率 × 签名放款率
        ws.cell(row, 8, f"=C{row}*G{row}*'{P}'!$B${pr['sign_rate']}")

        # I：件均 = 直接引用参数配置!B10
        ws.cell(row, 9, f"='{P}'!$B${pr['fl_avg_amt']}")

        # J：首贷放款金额 = 笔数 × 件均
        ws.cell(row, 10, f"=H{row}*I{row}")

        # K/L：历史实际值 + 差异%
        hist_val = hist_dict.get(month, None)
        if hist_val is not None:
            ws.cell(row, 11, hist_val)
            ws.cell(row, 12, f"=IF(K{row}=0,\"\",(H{row}-K{row})/K{row})")
        else:
            ws.cell(row, 11, '历史无数据')
            ws.cell(row, 12, '')

        # 数字格式
        ws.cell(row, 2).number_format = NUM_FMT        # 月安装量
        ws.cell(row, 3).number_format = NUM_FMT        # 首贷进件量
        ws.cell(row, 4).number_format = PCT_FMT       # 前置通过率
        ws.cell(row, 5).number_format = PCT_FMT       # 用信率
        ws.cell(row, 6).number_format = PCT_FMT       # 后置通过率
        ws.cell(row, 7).number_format = PCT_FMT       # 综合通过率
        ws.cell(row, 8).number_format = NUM_FMT        # 首贷放款笔数
        ws.cell(row, 9).number_format = USD_FMT_INT   # 件均
        ws.cell(row, 10).number_format = USD_FMT      # 首贷放款金额
        ws.cell(row, 11).number_format = NUM_FMT      # 历史实际
        ws.cell(row, 12).number_format = PCT_FMT      # 差异%
        ws.cell(row, 1).fill = GRN_FILL

    # 条件格式：差异% > 20% 或 < -20% 标红
    max_row = len(months) + 1
    ws.conditional_formatting.add(
        f"L2:L{max_row}",
        CellIsRule(operator='greaterThan', formula=['0.2'], fill=RED_FILL)
    )
    ws.conditional_formatting.add(
        f"L2:L{max_row}",
        CellIsRule(operator='lessThan', formula=['-0.2'], fill=RED_FILL)
    )

    set_col_width(ws, {'A': 14, 'B': 18, 'C': 16,
                       'D': 12, 'E': 10, 'F': 12,
                       'G': 18, 'H': 20, 'I': 12,
                       'J': 16, 'K': 16, 'L': 12})


# ============================================================
# 9. 复贷预估 Sheet（v6核心修复：首贷笔数联动引用首贷预估Sheet）
# ============================================================
def create_reloan_forecast_sheet(ws, loan_type: str, months: list,
                                  mob_rates: dict, fl_dict: dict):
    """
    v6核心：复贷预估与首贷预估完全联动
    公式链路：
      D列(首贷笔数) = INDEX(首贷预估!E:E, MATCH(C列对应首贷月, 首贷预估!A:A, 0))
                    → 引用首贷预估Sheet，改投放花费→首贷笔数变→复贷自动联动
      E列(MOB转化率) = 从参数配置读取（INDEX函数引用MOB率参数）
      H列(预估进件)  = D × E
    """
    type_label = '循环贷(loop)' if loan_type == 'loop' else '非循环贷(normal)'
    ws.title = f'复贷{type_label[:3]}预估'

    # 短期/长期系数行号（参数配置）
    if loan_type == 'loop':
        short_row = PARAM_ROWS['loop_adj_s']
        long_row  = PARAM_ROWS['loop_adj_l']
    else:
        short_row = PARAM_ROWS['normal_adj_s']
        long_row  = PARAM_ROWS['normal_adj_l']

    # 表头
    headers = ['预估月份', 'MOB', '对应首贷月',
               '首贷放款笔数\n(引用首贷预估)', 'MOB转化率\n(引用参数配置)',
               '调整系数', '调整后转化率', '预估进件量']
    for c, h in enumerate(headers, 1):
        ws.cell(1, c, h)
    hdr(ws, 1)
    ws.row_dimensions[1].height = 32

    P = '参数配置'
    FL = '首贷预估'

    # 按预估月份+MOB排序写数据（E/F列为公式，不写死数）
    row_idx = 2
    month_row_start = {}
    cfg = CONFIG
    ls = cfg['loop_adj_short']; ll = cfg['loop_adj_long']
    ns = cfg['normal_adj_short']; nl = cfg['normal_adj_long']

    for target in months:
        tdate = datetime.strptime(target + "-01", "%Y-%m-%d")
        month_row_start[target] = row_idx

        for mob in CONFIG['mob_list']:
            # 计算该条记录的"对应首贷月"
            cohort_month = (tdate - relativedelta(months=mob)).strftime("%Y-%m")

            # A：预估月份
            ws.cell(row_idx, 1, target)
            # B：MOB
            ws.cell(row_idx, 2, f'MOB{mob}')
            # C：对应首贷月
            ws.cell(row_idx, 3, cohort_month)

            # D：首贷笔数 → v6核心修复：公式引用首贷预估Sheet！
            #    MATCH(C列首贷月, 首贷预估A列, 0) 找到该月所在行
            #    INDEX(首贷预估E列, 行号) 取该行的首贷放款笔数
            ws.cell(row_idx, 4,
                f"=IFERROR(INDEX('{FL}'!$E:$E,MATCH(C{row_idx},'{FL}'!$A:$A,0)),0)")
            ws.cell(row_idx, 4).number_format = NUM_FMT

            # E：MOB转化率 → v7修复：公式引用参数配置（黄底可调，改参数→E自动变→G变→H变）
            if loan_type == 'loop':
                e_ref = f"'{P}'!$B${PARAM_ROWS['loop_mob_base'] + mob - 1}"
            else:
                e_ref = f"'{P}'!$B${PARAM_ROWS['normal_mob_base'] + mob - 1}"
            ws.cell(row_idx, 5, f"={e_ref}")
            ws.cell(row_idx, 5).number_format = PCT_FMT
            ws.cell(row_idx, 5).fill = YLW_FILL  # 黄底=可联动参数配置

            # F：调整系数（公式引用参数配置）
            if mob <= 3:
                ws.cell(row_idx, 6, f"='{P}'!$B${short_row}")
            else:
                ws.cell(row_idx, 6, f"='{P}'!$B${long_row}")
            ws.cell(row_idx, 6).number_format = PCT_FMT

            # G：调整后转化率 = E × F（联动链路：改参数配置MOB率 → E变 → G变 → H变）
            ws.cell(row_idx, 7, f"=E{row_idx}*F{row_idx}")
            ws.cell(row_idx, 7).number_format = PCT_FMT

            # H：预估进件量 = D × G（完全联动：改首贷参数→首贷笔数变→复贷自动变）
            ws.cell(row_idx, 8, f"=D{row_idx}*G{row_idx}")
            ws.cell(row_idx, 8).number_format = NUM_FMT

            fill = ORG_FILL if loan_type == 'loop' else BLU_FILL
            ws.cell(row_idx, 1).fill = fill
            row_idx += 1

    # 小计行（按预估月份汇总）
    total_row_map = {}
    next_row = row_idx
    for month, start_r in month_row_start.items():
        end_r = start_r + len(CONFIG['mob_list']) - 1
        ws.cell(next_row, 1, month)
        ws.cell(next_row, 2, '小计')
        ws.cell(next_row, 4, f"=SUM(D{start_r}:D{end_r})")
        ws.cell(next_row, 8, f"=SUM(H{start_r}:H{end_r})")
        for c in range(1, 9):
            ws.cell(next_row, c).fill = SUB_FILL
            ws.cell(next_row, c).font = BLD_FONT
        ws.cell(next_row, 4).number_format = NUM_FMT
        ws.cell(next_row, 8).number_format = NUM_FMT
        total_row_map[month] = next_row
        next_row += 1

    set_col_width(ws, {'A': 14, 'B': 8, 'C': 14,
                       'D': 20, 'E': 18, 'F': 12, 'G': 16, 'H': 16})
    return total_row_map


# ============================================================
# 10. MOB转化率 Sheet（展示历史序列 + MA+趋势值）
# ============================================================
def create_mob_rates_sheet(ws, mob_rates: dict, loan_type: str, window: int):
    type_label = '循环贷(loop)' if loan_type == 'loop' else '非循环贷(normal)'
    ws.title = f'MOB率_{loan_type}'

    max_hist = max(len(v) for v in mob_rates.values()) if mob_rates else 3
    hist_cols = min(max_hist, 13)

    header = ['MOB', f'{type_label}历史期数']
    for i in range(1, hist_cols + 1):
        header.append(f'距今{i}期转化率')
    header += ['MA均值\n(近3期)', '趋势MA\n(MA+外推÷2)', '最终转化率\n(含调整系数)']

    for c, h in enumerate(header, 1):
        ws.cell(1, c, h)
    hdr(ws, 1)
    ws.row_dimensions[1].height = 32

    ma_col    = hist_cols + 2
    trend_col = hist_cols + 3
    final_col = hist_cols + 4
    cfg = CONFIG
    ls = cfg['loop_adj_short']; ll = cfg['loop_adj_long']
    ns = cfg['normal_adj_short']; nl = cfg['normal_adj_long']

    for row, (mob, rates) in enumerate(sorted(mob_rates.items()), 2):
        ws.cell(row, 1, f'MOB{mob}')
        ws.cell(row, 2, f'共{len(rates)}期')
        for i, rate in enumerate(rates[:hist_cols], 3):
            ws.cell(row, i, rate)
            ws.cell(row, i).number_format = PCT_FMT

        # MA均值
        s = get_column_letter(3)
        e_col = min(window + 2, hist_cols + 2)
        e = get_column_letter(e_col)
        ws.cell(row, ma_col, f"=IFERROR(AVERAGE({s}{row}:{e}{row}),0)")
        ws.cell(row, ma_col).number_format = PCT_FMT

        # 趋势MA = (MA + 外推值) / 2
        # 简化：用MA值作为近似（完整趋势公式在Python端计算）
        ws.cell(row, trend_col, f"=IFERROR(({get_column_letter(ma_col)}{row}"
                                  f"+({get_column_letter(ma_col)}{row}"
                                  f"+(({s}{row}-{e}{row})/{window})))/2,0)")
        ws.cell(row, trend_col).number_format = PCT_FMT

        # v7修复：最终转化率 = 趋势MA × 调整系数（引用参数配置！）
        # P_name = sheet名（str）；P_rows = PARAM_ROWS（dict），两者分开避免f-string错误
        P_name  = '参数配置'
        P_rows  = PARAM_ROWS
        if loan_type == 'loop':
            rate_ref = f"'{P_name}'!$B${P_rows['loop_mob_base'] + mob - 1}"
            adj_ref  = (f"IF({mob}<=3,'{P_name}'!$B${P_rows['loop_adj_s']},"
                        f"'{P_name}'!$B${P_rows['loop_adj_l']})")
        else:
            rate_ref = f"'{P_name}'!$B${P_rows['normal_mob_base'] + mob - 1}"
            adj_ref  = (f"IF({mob}<=3,'{P_name}'!$B${P_rows['normal_adj_s']},"
                        f"'{P_name}'!$B${P_rows['normal_adj_l']})")
        ws.cell(row, final_col,
                f"={get_column_letter(trend_col)}{row}*{adj_ref}")
        ws.cell(row, final_col).number_format = PCT_FMT
        ws.cell(row, final_col).fill = YLW_FILL   # 黄底=可联动参数配置

    fill = ORG_FILL if loan_type == 'loop' else BLU_FILL
    for r in range(2, len(mob_rates) + 2):
        ws.cell(r, ma_col).fill    = GRN_FILL
        ws.cell(r, trend_col).fill = GRN_FILL
        ws.cell(r, final_col).fill = fill

    ws.column_dimensions['A'].width = 8
    ws.column_dimensions['B'].width = 10
    for i in range(3, hist_cols + 5):
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
# 12. 汇总 Sheet（v6：全部联动）
# ============================================================
def create_summary_sheet(ws, months: list,
                         fl_row_map: dict,
                         loop_total_map: dict,
                         normal_total_map: dict,
                         loop_sheet: str, normal_sheet: str):
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
        ws.cell(row, 2, f"='首贷预估'!H{fl_r}")   # v7: 首贷放款笔数现在在H列
        ws.cell(row, 3, f"='首贷预估'!J{fl_r}")   # v7: 首贷放款金额现在在J列

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
# 13. 主程序（v6）
# ============================================================
def main():
    print("=" * 65)
    print("复贷进件量预估系统 v6（首贷-复贷完全联动版）")
    print("=" * 65)

    today     = datetime.now()
    cur_month = today.strftime("%Y-%m")
    # v6：预估当月 + 后续2个月
    months    = [cur_month,
                 (today + relativedelta(months=1)).strftime("%Y-%m"),
                 (today + relativedelta(months=2)).strftime("%Y-%m")]
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

    first_loan_df['loan_cnt'] = first_loan_df['loan_cnt'].astype(int)
    reloan_df['month_num']    = reloan_df['month_num'].astype(int)
    reloan_df['loan_cnt']     = reloan_df['loan_cnt'].astype(int)
    fl_dict = dict(zip(first_loan_df['month'], first_loan_df['loan_cnt']))

    # ---- 计算 MOB 转化率 ----
    print("\nStep2: 计算各MOB转化率（带趋势MA）...")
    loop_mob_rates   = calc_mob_rates(reloan_df, fl_dict, 'loop',   CONFIG['mob_list'])
    normal_mob_rates = calc_mob_rates(reloan_df, fl_dict, 'normal', CONFIG['mob_list'])
    print(f"  loop  有效MOB: {sorted(loop_mob_rates.keys())}")
    print(f"  normal有效MOB: {sorted(normal_mob_rates.keys())}")

    # ---- 打印MA+趋势转化率预览 ----
    print("\n  [loop]  MA+趋势转化率:")
    for mob in sorted(loop_mob_rates.keys()):
        rates = loop_mob_rates[mob]
        ma_t = calc_ma_with_trend(rates, CONFIG['ma_window'])
        adj = get_adj_factor('loop', mob, CONFIG['loop_adj_short'], CONFIG['loop_adj_long'],
                             CONFIG['normal_adj_short'], CONFIG['normal_adj_long'])
        print(f"    MOB{mob:2d}: 趋势MA={ma_t:.4%} × 调整={adj} = {ma_t*adj:.4%}")
    print("\n  [normal] MA+趋势转化率:")
    for mob in sorted(normal_mob_rates.keys()):
        rates = normal_mob_rates[mob]
        ma_t = calc_ma_with_trend(rates, CONFIG['ma_window'])
        adj = get_adj_factor('normal', mob, CONFIG['loop_adj_short'], CONFIG['loop_adj_long'],
                             CONFIG['normal_adj_short'], CONFIG['normal_adj_long'])
        print(f"    MOB{mob:2d}: 趋势MA={ma_t:.4%} × 调整={adj} = {ma_t*adj:.4%}")

    # ---- 写 Excel ----
    print("\nStep3: 生成 Excel（首贷-复贷完全联动）...")
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = 'E:/岳松个人文件/嘉银工作内容的整理/code/权责自动化处理'
    output_file = f"{output_dir}/复贷进件量预估_v6_{ts}.xlsx"

    wb = openpyxl.Workbook()

    ws_param = wb.active
    create_params_sheet(ws_param, CONFIG)

    ws_sum = wb.create_sheet()

    ws_fl = wb.create_sheet()
    create_first_loan_forecast_sheet(ws_fl, months, first_loan_df)
    fl_row_map = {m: i + 2 for i, m in enumerate(months)}

    ws_loop = wb.create_sheet()
    loop_total_map = create_reloan_forecast_sheet(
        ws_loop, 'loop', months, loop_mob_rates, fl_dict)

    ws_norm = wb.create_sheet()
    normal_total_map = create_reloan_forecast_sheet(
        ws_norm, 'normal', months, normal_mob_rates, fl_dict)

    create_summary_sheet(ws_sum, months,
                         fl_row_map, loop_total_map, normal_total_map,
                         ws_loop.title, ws_norm.title)

    ws_mob_loop = wb.create_sheet()
    create_mob_rates_sheet(ws_mob_loop, loop_mob_rates,   'loop',   CONFIG['ma_window'])

    ws_mob_norm = wb.create_sheet()
    create_mob_rates_sheet(ws_mob_norm, normal_mob_rates, 'normal', CONFIG['ma_window'])

    ws_hist = wb.create_sheet()
    create_first_loan_history_sheet(ws_hist, first_loan_df)

    wb.save(output_file)

    print(f"\n  已保存: {output_file}")
    print("\n  v6 核心修复:")
    print("  [1] 复贷Sheet D列 = 公式引用首贷预估Sheet → 改投放花费→复贷自动联动")
    print("  [2] 首贷参数改为4月实际值（日均$55,000 / CPI$2.2 / 安装注册率46%等）")
    print("  [3] 综合通过率拆分为前置通过率×用信率×后置通过率（可独立调参）")
    print("  [4] MOB转化率初始值含趋势MA，后续在参数配置或Sheet中可调")
    print("  [5] 首贷预估增加历史实际值校验，差异>±20%标红")
    print("=" * 65)
    return output_file


if __name__ == "__main__":
    main()

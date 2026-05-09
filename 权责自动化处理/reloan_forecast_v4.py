# -*- coding: utf-8 -*-
"""
复贷进件量预估系统 v4
核心改进（相较v3）：
  1. 复贷按 loan_type2 拆分为 loop（循环贷）和 normal（非循环贷）
     - 分子：tag=application, grant_strategy=OLD, loan_type2=loop/normal
     - 分母：tag=loan, grant_strategy=NEW, month_num=0（首贷放款量）
     - 分别计算各自MOB转化率（MA），再分别预估，最后合并

【数据源字段说明（数据源 Sheet）】
  tag              : 'loan'=放款, 'application'=进件申请
  month            : 首贷放款月份（YYYY-MM）
  month_num        : MOB，首贷放款月距复贷申请月的月数差
  grant_strategy   : NEW=首贷, OLD=复贷
  loan_type2       : loop=循环贷（免审/快速审批）, normal=非循环贷（标准审批）
  loan_cnt         : 笔数
  rl_month         : 复贷申请月份

【复贷预估核心逻辑】
  ① 首贷放款量（分母）= tag=loan & grant_strategy=NEW & month_num=0，按首贷月汇总
  ② 循环贷进件量 = tag=application & grant_strategy=OLD & loan_type2=loop，按首贷月×MOB汇总
  ③ 非循环贷进件量 = tag=application & grant_strategy=OLD & loan_type2=normal，按首贷月×MOB汇总
  ④ 循环贷MOB N转化率 = ②[首贷月,N] / ①[首贷月]
  ⑤ 非循环贷MOB N转化率 = ③[首贷月,N] / ①[首贷月]
  ⑥ 移动平均（MA）= 最近 window 期同一MOB的历史转化率均值
  ⑦ 预估进件量 = 目标月对应首贷月放款量 × MA转化率 × 调整系数（loop和normal分开算，最后加总）

【Excel Sheet 结构】
  参数配置    ← 黄底可调参数（MA窗口、调整系数、首贷预估参数）
  汇总        ← 首贷+复贷loop+复贷normal合并
  首贷预估    ← 公式驱动（投放消耗→安装→进件→放款笔数→金额）
  复贷loop预估 ← 循环贷 MOB转化率 × 首贷量（MA死数 × 调整系数公式）
  复贷normal预估 ← 非循环贷 MOB转化率 × 首贷量
  MOB率_loop  ← 循环贷历史转化率 + MA公式
  MOB率_normal ← 非循环贷历史转化率 + MA公式
  首贷历史    ← 历史放款笔数 + 件均 + 金额公式
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
from openpyxl.utils import get_column_letter
from datetime import datetime
from dateutil.relativedelta import relativedelta

# ============================================================
# 1. 数据库连接类（与v2/v3完全一致）
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
# 2. 配置参数
# ============================================================
CONFIG = {
    # 复贷参数
    "ma_window":        3,     # MOB移动平均窗口（最近N期）
    "mob_list":         list(range(1, 13)),
    "loop_adj_factor":  1.0,   # 循环贷调整系数
    "normal_adj_factor":1.0,   # 非循环贷调整系数

    # 首贷预估参数（写入Excel参数配置，可在Excel修改）
    "fl_days_in_month":         31,
    "fl_daily_spend":           145161,   # 日均消耗（元）= 月预算/天数
    "fl_cpi":                   25,       # CPI（元/安装）
    "fl_install_register_rate": 0.80,     # 安装→注册（进件）转化率
    "fl_pass_rate":             0.65,     # 综合通过率（机审×用信×后置）
    "fl_sign_loan_rate":        0.95,     # 签名→放款率
    "fl_avg_amount":            1500,     # 首贷件均（元）
}

# ============================================================
# 3. SQL（数据源字段与Excel一致）
# ============================================================

# 3.1 首贷放款量（分母）：tag=loan, grant_strategy=NEW, month_num=0
SQL_FIRST_LOAN = """
SELECT
    date_format(release_time, '%Y-%m-01')  AS month,
    COUNT(DISTINCT order_no)               AS loan_cnt,
    ROUND(AVG(loan_amount), 0)             AS avg_loan_amount
FROM dwd.dwd_loan_info
WHERE release_time IS NOT NULL
  AND release_time >= DATE '2025-01-01'
  AND is_new = 1        -- 首贷（NEW）
GROUP BY 1
ORDER BY 1 DESC
"""
# 注：如果 dwd_loan_info 里没有 is_new 字段，等价于:
# ind.ba_asset_base_info 中 grant_strategy='NEW' AND if_issue=1

# 3.2 复贷进件量（分子，按loan_type2拆分）
# 按首贷月（month）× MOB（month_num）× loan_type2 汇总
SQL_RELOAN_BY_TYPE = """
WITH first_loan AS (
    -- 首贷放款月
    SELECT mid, date_format(release_time, '%Y-%m-01') AS first_loan_month
    FROM dwd.dwd_loan_info
    WHERE release_time IS NOT NULL
      AND release_time >= DATE '2025-01-01'
      AND is_new = 1
),
reloan_app AS (
    -- 复贷进件（grant_strategy=OLD，含loop和normal）
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
                CAST(r.app_month AS date)) BETWEEN 1 AND 12
GROUP BY 1, 2, 3, 4
ORDER BY 1 DESC, 3, 4
"""

# ============================================================
# 4. 模拟数据（结构与真实SQL返回一致，用于离线测试）
# ============================================================
def generate_mock_data():
    print("  [MOCK] 使用模拟数据")
    # 首贷放款量
    fl_dict = {}
    for y, m in [(2025, m) for m in range(1, 13)] + [(2026, m) for m in range(1, 5)]:
        fl_dict[f"{y}-{m:02d}"] = 50000 + np.random.randint(-10000, 20000)

    first_loan_df = pd.DataFrame([
        {'month': k, 'loan_cnt': v,
         'avg_loan_amount': round(np.random.uniform(1350, 1650), 0)}
        for k, v in fl_dict.items()
    ])

    # 复贷进件（loop & normal 分拆）
    rows = []
    # loop转化率参考区间：MOB1≈40-60%, MOB2≈20-35%, MOB3≈12-20%
    loop_rates  = {1:(0.40,0.62), 2:(0.20,0.36), 3:(0.12,0.20),
                   4:(0.08,0.14), 5:(0.05,0.10), 6:(0.03,0.07)}
    # normal转化率参考区间：MOB1≈35-60%, MOB2≈25-50%, MOB3≈20-30%
    normal_rates = {1:(0.35,0.60), 2:(0.25,0.50), 3:(0.20,0.30),
                    4:(0.15,0.25), 5:(0.10,0.20), 6:(0.06,0.13)}

    for fl_month, fl_cnt in fl_dict.items():
        for mob in range(1, 13):
            for loan_type, rate_map in [('loop', loop_rates), ('normal', normal_rates)]:
                lo, hi = rate_map.get(mob, (0.01, 0.03))
                rate = np.random.uniform(lo, hi)
                rl_date = datetime.strptime(fl_month + "-01", "%Y-%m-%d") + relativedelta(months=mob)
                if rl_date <= datetime(2026, 4, 30):
                    rows.append({
                        'month':     fl_month,
                        'rl_month':  rl_date.strftime("%Y-%m"),
                        'month_num': mob,
                        'loan_type2': loan_type,
                        'loan_cnt':  int(fl_cnt * rate),
                    })
    return first_loan_df, pd.DataFrame(rows)


# ============================================================
# 5. 计算 MOB 转化率（分 loan_type2）
# ============================================================
def calc_mob_rates(reloan_df: pd.DataFrame, fl_dict: dict,
                   loan_type: str, mob_list: list) -> dict:
    """
    返回 {mob: [rate_最新期, rate_次新期, ...]}
    """
    sub = reloan_df[reloan_df['loan_type2'] == loan_type]
    mob_rates = {}
    for mob in mob_list:
        mob_data = (sub[sub['month_num'] == mob]
                    .sort_values('month', ascending=False))
        rates = []
        for _, row in mob_data.iterrows():
            fc = fl_dict.get(row['month'], 0)
            if fc > 0:
                rates.append(round(row['loan_cnt'] / fc, 6))
        if rates:
            mob_rates[mob] = rates
    return mob_rates


def calc_ma(rates: list, window: int) -> float:
    recent = rates[:window]
    if not recent:
        return 0.0
    return round(sum(recent) / len(recent), 6)


# ============================================================
# 6. Excel 样式辅助
# ============================================================
HDR_FILL  = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
SUB_FILL  = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
YLW_FILL  = PatternFill(start_color="FFFF99", end_color="FFFF99", fill_type="solid")
GRN_FILL  = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
ORG_FILL  = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")  # loop橙
BLU_FILL  = PatternFill(start_color="DDEEFF", end_color="DDEEFF", fill_type="solid")  # normal蓝
WHT_FONT  = Font(bold=True, color="FFFFFF")
BLD_FONT  = Font(bold=True)
PCT_FMT   = '0.00%'
NUM_FMT   = '#,##0'

def hdr(ws, row):
    for cell in ws[row]:
        if cell.value is not None:
            cell.fill = HDR_FILL; cell.font = WHT_FONT
            cell.alignment = Alignment(horizontal='center')

def set_col_width(ws, widths: dict):
    for col_letter, w in widths.items():
        ws.column_dimensions[col_letter].width = w


# ============================================================
# 7. 参数配置 Sheet
# 行号约定（其他Sheet公式引用）：
#   B2=月天数  B3=日均消耗  B4=CPI  B5=安装注册率
#   B6=综合通过率  B7=签名放款率  B8=件均
#   B10=MA窗口  B11=循环贷调整系数  B12=非循环贷调整系数
# ============================================================
PARAM_ROWS = {
    'days':          2,
    'daily_spend':   3,
    'cpi':           4,
    'install_reg':   5,
    'pass_rate':     6,
    'sign_rate':     7,
    'fl_avg_amt':    8,
    'ma_window':    10,
    'loop_adj':     11,
    'normal_adj':   12,
}

def create_params_sheet(ws, cfg):
    ws.title = '参数配置'
    rows = [
        ('参数名', '值', '说明'),
        ('首贷 | 月天数',             cfg['fl_days_in_month'],         '预估月份天数'),
        ('首贷 | 日均投放消耗（元）', cfg['fl_daily_spend'],            '月预算 ÷ 月天数'),
        ('首贷 | CPI（元/安装）',     cfg['fl_cpi'],                    '每获取一次 App 安装的广告成本'),
        ('首贷 | 安装注册率',         cfg['fl_install_register_rate'],  '安装→注册（进件）转化率'),
        ('首贷 | 综合通过率',         cfg['fl_pass_rate'],              '= 机审 × 用信 × 后置通过率'),
        ('首贷 | 签名放款率',         cfg['fl_sign_loan_rate'],         '签约→实际放款转化率'),
        ('首贷 | 件均（元）',         cfg['fl_avg_amount'],             '首贷平均放款金额'),
        ('', '', ''),
        ('复贷 | MA窗口（月）',       cfg['ma_window'],                 '移动平均取最近 N 期同MOB转化率'),
        ('复贷 | 循环贷调整系数',     cfg['loop_adj_factor'],           '循环贷 1.0=不调 0.95=下调5%'),
        ('复贷 | 非循环贷调整系数',   cfg['normal_adj_factor'],         '非循环贷 1.0=不调 1.05=上调5%'),
    ]
    for r, (a, b, c) in enumerate(rows, 1):
        ws.cell(r, 1, a); ws.cell(r, 2, b); ws.cell(r, 3, c)
    hdr(ws, 1)
    for r in list(range(2, 9)) + [10, 11, 12]:
        ws.cell(r, 2).fill = YLW_FILL
    # 格式
    for r in [PARAM_ROWS['install_reg'], PARAM_ROWS['pass_rate'],
              PARAM_ROWS['sign_rate'], PARAM_ROWS['loop_adj'], PARAM_ROWS['normal_adj']]:
        ws.cell(r, 2).number_format = PCT_FMT
    ws.cell(PARAM_ROWS['daily_spend'], 2).number_format = NUM_FMT
    ws.cell(PARAM_ROWS['fl_avg_amt'],  2).number_format = NUM_FMT
    set_col_width(ws, {'A': 30, 'B': 18, 'C': 55})


# ============================================================
# 8. 首贷预估 Sheet（全公式）
# ============================================================
def create_first_loan_forecast_sheet(ws, months: list):
    ws.title = '首贷预估'
    headers = ['预估月份', '月安装量\n(消耗/CPI×天数)',
               '首贷进件量\n(安装×注册率)',
               '综合通过率×\n签名放款率',
               '首贷放款笔数',
               '件均(元)', '首贷放款金额(元)']
    for c, h in enumerate(headers, 1):
        ws.cell(1, c, h)
    hdr(ws, 1)
    ws.row_dimensions[1].height = 30

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

        ws.cell(row, 2).number_format = NUM_FMT
        ws.cell(row, 3).number_format = NUM_FMT
        ws.cell(row, 4).number_format = PCT_FMT
        ws.cell(row, 5).number_format = NUM_FMT
        ws.cell(row, 6).number_format = NUM_FMT
        ws.cell(row, 7).number_format = '"¥"#,##0'
        ws.cell(row, 1).fill = GRN_FILL

    set_col_width(ws, {'A': 12, 'B': 16, 'C': 16,
                       'D': 16, 'E': 14, 'F': 12, 'G': 18})


# ============================================================
# 9. 复贷预估 Sheet（loop 或 normal）
#    E列=MA转化率（死数）, F列=调整系数（公式）, G列=调整后率（公式）, H列=预估进件（公式）
# ============================================================
def create_reloan_forecast_sheet(ws, forecast_results: list,
                                  loan_type: str, adj_param_row: int):
    """
    loan_type    : 'loop' 或 'normal'
    adj_param_row: 调整系数所在参数配置行号（PARAM_ROWS['loop_adj'] 或 ['normal_adj']）
    """
    type_label = '循环贷(loop)' if loan_type == 'loop' else '非循环贷(normal)'
    ws.title = f'复贷{type_label[:3]}预估'
    headers = ['预估月份', 'MOB周期', '对应首贷月',
               '首贷放款量(历史)', 'MA转化率(均值)',
               '调整系数', '调整后转化率', '预估进件量']
    for c, h in enumerate(headers, 1):
        ws.cell(1, c, h)
    hdr(ws, 1)
    ws.row_dimensions[1].height = 28

    P = '参数配置'
    month_rows = {}
    for row, rec in enumerate(forecast_results, 2):
        ws.cell(row, 1, rec['预估月份'])
        ws.cell(row, 2, rec['MOB周期'])
        ws.cell(row, 3, rec['对应首贷月份'])
        ws.cell(row, 4, rec['首贷放款量'])
        ws.cell(row, 5, rec['MA转化率'])                         # 死数

        ws.cell(row, 6, f"='{P}'!$B${adj_param_row}")           # 公式
        ws.cell(row, 7, f"=E{row}*F{row}")                      # 公式
        ws.cell(row, 8, f"=D{row}*G{row}")                      # 公式

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

    set_col_width(ws, {'A': 12, 'B': 10, 'C': 14, 'D': 16,
                       'E': 14, 'F': 12, 'G': 14, 'H': 16})
    return total_row_map


# ============================================================
# 10. MOB转化率 Sheet（分 loan_type2）
# ============================================================
def create_mob_rates_sheet(ws, mob_rates: dict, loan_type: str, window: int):
    type_label = '循环贷(loop)' if loan_type == 'loop' else '非循环贷(normal)'
    ws.title = f'MOB率_{loan_type}'

    max_hist = max(len(v) for v in mob_rates.values()) if mob_rates else 3
    hist_cols = min(max_hist, 12)

    header = ['MOB', f'{type_label}历史期数']
    for i in range(1, hist_cols + 1):
        header.append(f'距今{i}期首贷转化率')
    header += ['MA均值', 'MA×调整系数']

    for c, h in enumerate(header, 1):
        ws.cell(1, c, h)
    hdr(ws, 1)

    P = '参数配置'
    adj_row = PARAM_ROWS['loop_adj'] if loan_type == 'loop' else PARAM_ROWS['normal_adj']
    ma_col  = hist_cols + 2
    adj_col = hist_cols + 3

    for row, (mob, rates) in enumerate(sorted(mob_rates.items()), 2):
        ws.cell(row, 1, f'MOB{mob}')
        ws.cell(row, 2, f'共{len(rates)}期')
        for i, rate in enumerate(rates[:hist_cols], 3):
            ws.cell(row, i, rate)
            ws.cell(row, i).number_format = PCT_FMT

        s = get_column_letter(3)
        e = get_column_letter(min(window + 2, hist_cols + 2))
        ws.cell(row, ma_col, f"=IFERROR(AVERAGE({s}{row}:{e}{row}),0)")
        ws.cell(row, ma_col).number_format = PCT_FMT

        ma_letter = get_column_letter(ma_col)
        ws.cell(row, adj_col, f"={ma_letter}{row}*'{P}'!$B${adj_row}")
        ws.cell(row, adj_col).number_format = PCT_FMT

    fill = ORG_FILL if loan_type == 'loop' else BLU_FILL
    for r in range(2, len(mob_rates) + 2):
        ws.cell(r, ma_col).fill  = GRN_FILL
        ws.cell(r, adj_col).fill = fill

    ws.column_dimensions['A'].width = 8
    ws.column_dimensions['B'].width = 12
    for i in range(3, hist_cols + 4):
        ws.column_dimensions[get_column_letter(i)].width = 14


# ============================================================
# 11. 首贷历史 Sheet
# ============================================================
def create_first_loan_history_sheet(ws, first_loan_df: pd.DataFrame):
    ws.title = '首贷历史'
    has_amt = 'avg_loan_amount' in first_loan_df.columns

    headers = ['首贷月份', '放款笔数', '件均(元)', '放款金额(元)']
    for c, h in enumerate(headers, 1):
        ws.cell(1, c, h)
    hdr(ws, 1)

    for row, (_, rec) in enumerate(first_loan_df.iterrows(), 2):
        ws.cell(row, 1, rec['month'])
        ws.cell(row, 2, int(rec['loan_cnt']))
        avg_amt = float(rec['avg_loan_amount']) if has_amt else 1500.0
        ws.cell(row, 3, avg_amt)
        ws.cell(row, 4, f"=B{row}*C{row}")
        ws.cell(row, 2).number_format = NUM_FMT
        ws.cell(row, 3).number_format = NUM_FMT
        ws.cell(row, 4).number_format = '"¥"#,##0'

    set_col_width(ws, {'A': 12, 'B': 12, 'C': 12, 'D': 18})


# ============================================================
# 12. 汇总 Sheet
# ============================================================
def create_summary_sheet(ws, months: list,
                         fl_row_map: dict,
                         loop_total_map: dict,
                         normal_total_map: dict,
                         loop_sheet: str,
                         normal_sheet: str):
    ws.title = '汇总'
    headers = ['预估月份',
               '首贷放款笔数', '首贷放款金额(元)',
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
        ws.cell(row, 3).number_format = '"¥"#,##0'

    set_col_width(ws, {'A': 12, 'B': 16, 'C': 20,
                       'D': 18, 'E': 18, 'F': 16, 'G': 20})


# ============================================================
# 13. 主程序
# ============================================================
def main():
    print("=" * 65)
    print("复贷进件量预估系统 v4（loop/normal 分拆 + Excel公式）")
    print("=" * 65)

    today      = datetime.now()
    cur_month  = today.strftime("%Y-%m")
    next_month = (today + relativedelta(months=1)).strftime("%Y-%m")
    months     = [cur_month, next_month]
    print(f"预估月份: {cur_month}（当月）, {next_month}（下月）\n")

    # ---- 数据获取 ----
    print("Step 1: 获取数据库数据 ...")
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
    first_loan_df['loan_cnt'] = first_loan_df['loan_cnt'].astype(int)
    reloan_df['month_num']    = reloan_df['month_num'].astype(int)
    reloan_df['loan_cnt']     = reloan_df['loan_cnt'].astype(int)
    fl_dict = dict(zip(first_loan_df['month'], first_loan_df['loan_cnt']))

    # ---- 计算 MOB 转化率（loop & normal 分开）----
    print("\nStep 2: 计算各 MOB 历史转化率（loop & normal 分开）...")
    loop_mob_rates   = calc_mob_rates(reloan_df, fl_dict, 'loop',   CONFIG['mob_list'])
    normal_mob_rates = calc_mob_rates(reloan_df, fl_dict, 'normal', CONFIG['mob_list'])
    print(f"  loop 有效MOB数: {len(loop_mob_rates)} | normal 有效MOB数: {len(normal_mob_rates)}")

    # ---- 生成复贷预估结果（loop & normal 分开）----
    print("\nStep 3: 生成复贷预估结果 ...")
    def build_forecast(mob_rates: dict, loan_type: str) -> list:
        results = []
        for target in months:
            tdate = datetime.strptime(target + "-01", "%Y-%m-%d")
            for mob, rates in mob_rates.items():
                ma = calc_ma(rates, CONFIG['ma_window'])
                cohort_month = (tdate - relativedelta(months=mob)).strftime("%Y-%m")
                fl_cnt = fl_dict.get(cohort_month, 0)
                adj    = CONFIG['loop_adj_factor'] if loan_type == 'loop' else CONFIG['normal_adj_factor']
                results.append({
                    '预估月份':     target,
                    'MOB周期':      f'MOB{mob}',
                    '对应首贷月份': cohort_month,
                    '首贷放款量':   fl_cnt,
                    'MA转化率':     ma,
                    '调整系数':     adj,
                    '预估进件量':   int(fl_cnt * ma * adj),
                })
        return results

    loop_forecast   = build_forecast(loop_mob_rates,   'loop')
    normal_forecast = build_forecast(normal_mob_rates, 'normal')
    print(f"  loop记录: {len(loop_forecast)} | normal记录: {len(normal_forecast)}")

    # ---- 写 Excel ----
    print("\nStep 4: 写入 Excel（含公式）...")
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = 'E:/岳松个人文件/嘉银工作内容的整理/code/权责自动化处理'
    output_file = f"{output_dir}/复贷进件量预估_v4_{ts}.xlsx"

    wb = openpyxl.Workbook()

    # Sheet1: 参数配置
    ws_param = wb.active
    create_params_sheet(ws_param, CONFIG)

    # Sheet2: 汇总（占位，后面更新公式时需要Sheet名已存在）
    ws_sum = wb.create_sheet()

    # Sheet3: 首贷预估
    ws_fl = wb.create_sheet()
    create_first_loan_forecast_sheet(ws_fl, months)
    fl_row_map = {m: i + 2 for i, m in enumerate(months)}

    # Sheet4: 复贷loop预估
    ws_loop = wb.create_sheet()
    loop_total_map = create_reloan_forecast_sheet(
        ws_loop, loop_forecast, 'loop', PARAM_ROWS['loop_adj'])

    # Sheet5: 复贷normal预估
    ws_norm = wb.create_sheet()
    normal_total_map = create_reloan_forecast_sheet(
        ws_norm, normal_forecast, 'normal', PARAM_ROWS['normal_adj'])

    # 现在填汇总（Sheet名已有）
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
    print("  Sheet 说明:")
    print("    参数配置       <- 修改黄色单元格，全部联动")
    print("    汇总           <- 首贷笔数/金额 + loop进件 + normal进件 = 合计")
    print("    首贷预估       <- 消耗/CPI×天数 → 安装 → 进件 → 放款 → 金额（全公式）")
    print(f"   {ws_loop.title} <- 循环贷 MOB转化率×首贷量 → 进件量")
    print(f"   {ws_norm.title} <- 非循环贷 MOB转化率×首贷量 → 进件量")
    print("    MOB率_loop     <- 循环贷历史转化率 + MA公式")
    print("    MOB率_normal   <- 非循环贷历史转化率 + MA公式")
    print("    首贷历史       <- 历史放款笔数 + 件均 + 金额公式")
    print()
    print("  ⚠️  v4 vs v3 核心变化：")
    print("  复贷不再统一用 grant_strategy 分类，而是按 loan_type2 拆成：")
    print("    loop   = 循环贷（免审/快速审批，通常转化率更高）")
    print("    normal = 非循环贷（标准审批流程）")
    print("  两类分别计算 MOB 转化率 MA，分别预估，最终在汇总 Sheet 合并。")
    print("=" * 65)


if __name__ == "__main__":
    main()

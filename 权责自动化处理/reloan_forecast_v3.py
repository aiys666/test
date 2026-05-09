# -*- coding: utf-8 -*-
"""
复贷进件量预估系统 v3
在v2基础上的核心改进：
  1. Excel公式支持 —— 关键列写入 openpyxl 公式，修改参数后 Excel 自动重算
  2. 首贷放款金额预估 —— 新增首贷预估Sheet（投放消耗→安装→进件→放款笔数→放款金额）
  3. 参数联动 —— 所有可调参数集中在"参数配置"Sheet，改一处全联动

【Excel Sheet 结构】
  参数配置  ← 用户可在 Excel 里直接修改（黄底）
  首贷预估  ← 全部公式引用参数配置，含放款金额
  复贷预估  ← MA 转化率（死数）× 调整系数（公式引用参数）= 预估进件量
  MOB转化率 ← 历史率（死数）+ MA公式
  首贷历史  ← 历史放款笔数 + 件均 + 金额公式
  汇总      ← 首贷预估笔数/金额 + 复贷预估进件量
"""

# ============================================================
# 导入
# ============================================================
import pandas as pd
import numpy as np
import requests
import json
import re
import time
import base64
import math
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime
from dateutil.relativedelta import relativedelta

# ============================================================
# 1. 数据库连接类（与v2完全一致）
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
    # 复贷预估参数
    "ma_window": 3,
    "mob_list": list(range(1, 13)),
    "adjustment_factor": 1.0,

    # 首贷预估参数（v3 新增）
    # -------- 以下值写入 Excel 参数配置 Sheet，用户可直接在 Excel 修改 --------
    "fl_days_in_month": 31,           # 预估月份天数
    "fl_daily_spend": 145161,          # 日均投放消耗（元）= 月预算450万 / 31天，约145161
    "fl_cpi": 25,                      # CPI（元/安装）
    "fl_install_register_rate": 0.80,  # 安装→注册转化率
    "fl_pass_rate": 0.65,              # 机审通过率 × 确认借款率(用信率) × 后置通过率
    "fl_sign_loan_rate": 0.95,         # 签名→放款转化率
    "fl_avg_amount": 1500,             # 首贷件均（元），参考历史或手动输入
}

# ============================================================
# 3. SQL 查询（v3 首贷 SQL 增加件均字段）
# ============================================================
SQL_FIRST_LOAN = """
SELECT 
    date_format(release_time, '%Y-%m-01') AS first_loan_month, 
    COUNT(DISTINCT order_no)              AS first_loan_cnt,
    ROUND(AVG(loan_amount), 0)            AS avg_loan_amount   -- 首贷件均（请确认实际字段名）
FROM dwd.dwd_loan_info
WHERE release_time IS NOT NULL
  AND release_time >= DATE('2025-01-01')
GROUP BY 1
ORDER BY 1 DESC
"""

SQL_RELOAN_BY_MOB = """
WITH first_loan AS (
    SELECT mid, release_time, order_no
    FROM dwd.dwd_loan_info
    WHERE release_time IS NOT NULL
      AND release_time >= DATE '2025-01-01'
),
reloan_base AS (
    SELECT b.mid, app_date, grant_strategy, biz_id
    FROM ind.ba_asset_base_info b
    WHERE (b.grant_strategy = 'NEW' AND b.if_issue = 1 AND b.if_app = 1)
       OR (b.grant_strategy = 'OLD' AND b.if_app = 1 AND b.if_recall = 0)
)
SELECT
    date_format(CAST(f.release_time AS timestamp), '%Y-%m-01') AS first_loan_month,
    date_format(CAST(r.app_date    AS timestamp), '%Y-%m-01') AS reloan_month,
    date_diff('month', CAST(f.release_time AS date), CAST(r.app_date AS date)) AS mob_num,
    COUNT(DISTINCT r.biz_id) AS reloan_apply_cnt
FROM first_loan f
INNER JOIN reloan_base r ON CAST(f.mid AS BIGINT) = CAST(r.mid AS BIGINT)
WHERE date_diff('month', CAST(f.release_time AS date), CAST(r.app_date AS date)) BETWEEN 1 AND 12
GROUP BY 1, 2, 3
ORDER BY 1 DESC, 3
"""

# ============================================================
# 4. 模拟数据（增加件均列）
# ============================================================
def generate_mock_data():
    print("  [MOCK] 使用模拟数据")
    first_loan_mock = {
        f"2025-{m:02d}": 10000 + (m - 1) * 1000 for m in range(1, 13)
    }
    first_loan_mock.update({
        "2026-01": 22000, "2026-02": 23000,
        "2026-03": 24000, "2026-04": 25000,
    })

    reloan_rows = []
    for fl_month, fl_cnt in first_loan_mock.items():
        for mob in range(1, 13):
            rate_map = {1: (0.08, 0.10), 2: (0.12, 0.14), 3: (0.10, 0.12),
                        4: (0.07, 0.09), 5: (0.05, 0.07), 6: (0.03, 0.05)}
            lo, hi = rate_map.get(mob, (0.01, 0.03))
            base_rate = np.random.uniform(lo, hi)
            reloan_date = datetime.strptime(fl_month, "%Y-%m") + relativedelta(months=mob)
            if reloan_date <= datetime(2026, 4, 30):
                reloan_rows.append({
                    'first_loan_month': fl_month,
                    'reloan_month': reloan_date.strftime("%Y-%m"),
                    'mob_num': mob,
                    'reloan_apply_cnt': int(fl_cnt * base_rate),
                    'first_loan_cnt': fl_cnt,
                })

    first_loan_df = pd.DataFrame([
        {
            'first_loan_month': k,
            'first_loan_cnt': v,
            'avg_loan_amount': round(np.random.uniform(1350, 1650), 0),  # 模拟件均
        }
        for k, v in first_loan_mock.items()
    ])
    return first_loan_df, pd.DataFrame(reloan_rows)

# ============================================================
# 5. 移动平均计算（与v2一致）
# ============================================================
def calc_ma_rate(rates, window=3):
    recent = rates[:window]
    if not recent:
        return 0.0
    return round(sum(recent) / len(recent), 6)

# ============================================================
# 6. Excel 样式辅助函数
# ============================================================
HDR_FILL  = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
SUB_FILL  = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
YLW_FILL  = PatternFill(start_color="FFFF99", end_color="FFFF99", fill_type="solid")
GRN_FILL  = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
WHT_FONT  = Font(bold=True, color="FFFFFF")
BLD_FONT  = Font(bold=True)
PCT_FMT   = '0.00%'
NUM_FMT   = '#,##0'
NUM1_FMT  = '#,##0.0'

def hdr(ws, row):
    """标题行：蓝底白字"""
    for cell in ws[row]:
        if cell.value is not None:
            cell.fill = HDR_FILL; cell.font = WHT_FONT
            cell.alignment = Alignment(horizontal='center')

def set_col_width(ws, widths: dict):
    for col_letter, w in widths.items():
        ws.column_dimensions[col_letter].width = w

def fmt_range(ws, row_start, row_end, col, fmt):
    for r in range(row_start, row_end + 1):
        ws.cell(r, col).number_format = fmt

# ============================================================
# 7. 创建"参数配置"Sheet
#    B 列 = 值（黄底，用户可在 Excel 直接改）
#    行号约定（供其他 Sheet 公式引用）：
#      B2  = 月天数           B3  = 日均投放消耗
#      B4  = CPI              B5  = 安装注册率
#      B6  = 综合通过率        B7  = 签名放款率
#      B8  = 首贷件均          B10 = MA窗口
#      B11 = 调整系数
# ============================================================
PARAM_ROWS = {
    'days':          2,
    'daily_spend':   3,
    'cpi':           4,
    'install_reg':   5,
    'pass_rate':     6,
    'sign_rate':     7,
    'fl_avg_amt':    8,
    'ma_window':     10,
    'adj_factor':    11,
}

def create_params_sheet(ws, cfg):
    ws.title = '参数配置'
    rows = [
        ('参数名', '值', '说明（改 B 列即可，其他 Sheet 自动联动）'),
        # 首贷
        ('首贷 | 月天数',             cfg['fl_days_in_month'],        '预估月份的实际天数'),
        ('首贷 | 日均投放消耗（元）', cfg['fl_daily_spend'],           '月总预算 ÷ 月天数，例如 450万元/31天 ≈ 145,161'),
        ('首贷 | CPI（元/安装）',     cfg['fl_cpi'],                   '每获取一个 App 安装的广告成本'),
        ('首贷 | 安装注册率',         cfg['fl_install_register_rate'], '安装 → 注册（进件）的转化率'),
        ('首贷 | 综合通过率',         cfg['fl_pass_rate'],             '= 机审通过率 × 确认借款率(用信率) × 后置通过率'),
        ('首贷 | 签名放款率',         cfg['fl_sign_loan_rate'],        '确认签约 → 实际放款的转化率'),
        ('首贷 | 件均（元）',         cfg['fl_avg_amount'],            '首贷平均放款金额，参考历史数据或手动输入'),
        ('', '', ''),  # 空行 -> row 9
        # 复贷
        ('复贷 | MA 窗口（月）',      cfg['ma_window'],                '移动平均使用最近 N 个月的历史转化率'),
        ('复贷 | 调整系数',           cfg['adjustment_factor'],        '手动调整倍率：1.0=不调整  0.95=下调5%  1.05=上调5%'),
    ]
    for r, (a, b, c) in enumerate(rows, 1):
        ws.cell(r, 1, a); ws.cell(r, 2, b); ws.cell(r, 3, c)
    hdr(ws, 1)
    # 黄底：B2:B8, B10:B11
    for r in list(range(2, 9)) + [10, 11]:
        ws.cell(r, 2).fill = YLW_FILL
    # 百分比格式
    for r in [PARAM_ROWS['install_reg'], PARAM_ROWS['pass_rate'],
              PARAM_ROWS['sign_rate'], PARAM_ROWS['adj_factor']]:
        ws.cell(r, 2).number_format = PCT_FMT
    # 数字格式
    ws.cell(PARAM_ROWS['daily_spend'], 2).number_format = NUM_FMT
    ws.cell(PARAM_ROWS['fl_avg_amt'],  2).number_format = NUM_FMT
    set_col_width(ws, {'A': 35, 'B': 18, 'C': 60})

# ============================================================
# 8. 创建"首贷预估"Sheet
#    完全用公式引用参数配置，含放款金额预估
#    列：A=预估月份  B=月安装量  C=首贷进件量  D=综合通过率×签名率
#        E=首贷放款笔数  F=件均  G=首贷放款金额
# ============================================================
def create_first_loan_forecast_sheet(ws, months: list):
    ws.title = '首贷预估'
    headers = ['预估月份', '月安装量\n(消耗/CPI×天数)',
               '首贷进件量\n(安装×注册率)',
               '综合通过率\n×签名放款率',
               '首贷放款笔数\n(预估)',
               '件均(元)',
               '首贷放款金额\n(预估，元)']
    for c, h in enumerate(headers, 1):
        ws.cell(1, c, h)
    hdr(ws, 1)
    ws.row_dimensions[1].height = 30

    P = '参数配置'  # Sheet名

    for row, month in enumerate(months, 2):
        ws.cell(row, 1, month)
        # B: 月安装量 = 日均消耗 / CPI × 月天数
        ws.cell(row, 2, f"='{P}'!$B${PARAM_ROWS['daily_spend']}"
                        f"/'{P}'!$B${PARAM_ROWS['cpi']}"
                        f"*'{P}'!$B${PARAM_ROWS['days']}")
        # C: 首贷进件量 = 月安装量 × 安装注册率
        ws.cell(row, 3, f"=B{row}*'{P}'!$B${PARAM_ROWS['install_reg']}")
        # D: 综合通过率 × 签名放款率
        ws.cell(row, 4, f"='{P}'!$B${PARAM_ROWS['pass_rate']}"
                        f"*'{P}'!$B${PARAM_ROWS['sign_rate']}")
        # E: 首贷放款笔数
        ws.cell(row, 5, f"=C{row}*D{row}")
        # F: 件均（引用参数）
        ws.cell(row, 6, f"='{P}'!$B${PARAM_ROWS['fl_avg_amt']}")
        # G: 首贷放款金额
        ws.cell(row, 7, f"=E{row}*F{row}")

        # 格式
        ws.cell(row, 2).number_format = NUM_FMT
        ws.cell(row, 3).number_format = NUM_FMT
        ws.cell(row, 4).number_format = PCT_FMT
        ws.cell(row, 5).number_format = NUM_FMT
        ws.cell(row, 6).number_format = NUM_FMT
        ws.cell(row, 7).number_format = '"¥"#,##0'
        ws.cell(row, 1).fill = GRN_FILL

    set_col_width(ws, {'A': 12, 'B': 16, 'C': 16,
                       'D': 16, 'E': 16, 'F': 12, 'G': 18})

# ============================================================
# 9. 创建"复贷预估"Sheet
#    E列(MA率)=死数，F列(调整系数)=公式，G列(调整后)=公式，H列(预估进件)=公式
# ============================================================
def create_reloan_forecast_sheet(ws, forecast_results: list):
    ws.title = '复贷预估'
    headers = ['预估月份', 'MOB周期', '对应首贷月份',
               '首贷放款量(历史)', 'MA转化率(历史均值)',
               '调整系数\n(引用参数)', '调整后转化率',
               '预估复贷进件量']
    for c, h in enumerate(headers, 1):
        ws.cell(1, c, h)
    hdr(ws, 1)
    ws.row_dimensions[1].height = 28

    P = '参数配置'
    month_total = {}  # 记录每个预估月份的小计行号

    for row, rec in enumerate(forecast_results, 2):
        ws.cell(row, 1, rec['预估月份'])
        ws.cell(row, 2, rec['MOB周期'])
        ws.cell(row, 3, rec['对应首贷月份'])
        ws.cell(row, 4, rec['首贷放款量'])                # 死数
        ws.cell(row, 5, rec['原始MA转化率'])              # 死数（Python算好的MA值）

        # F: 调整系数 —— 引用参数配置
        ws.cell(row, 6, f"='{P}'!$B${PARAM_ROWS['adj_factor']}")
        # G: 调整后转化率 = MA率 × 调整系数
        ws.cell(row, 7, f"=E{row}*F{row}")
        # H: 预估复贷进件量 = 首贷放款量 × 调整后转化率
        ws.cell(row, 8, f"=D{row}*G{row}")

        # 格式
        ws.cell(row, 4).number_format = NUM_FMT
        ws.cell(row, 5).number_format = PCT_FMT
        ws.cell(row, 6).number_format = PCT_FMT
        ws.cell(row, 7).number_format = PCT_FMT
        ws.cell(row, 8).number_format = NUM_FMT

        month_total.setdefault(rec['预估月份'], []).append(row)

    # 各月份小计行（SUM 公式）
    next_row = len(forecast_results) + 2
    for month, rows in month_total.items():
        r_first, r_last = rows[0], rows[-1]
        ws.cell(next_row, 1, month)
        ws.cell(next_row, 2, '小计')
        ws.cell(next_row, 8, f"=SUM(H{r_first}:H{r_last})")
        ws.cell(next_row, 4, f"=SUM(D{r_first}:D{r_last})")
        for c in range(1, 9):
            ws.cell(next_row, c).fill = SUB_FILL
            ws.cell(next_row, c).font = BLD_FONT
        ws.cell(next_row, 8).number_format = NUM_FMT
        ws.cell(next_row, 4).number_format = NUM_FMT
        next_row += 1

    set_col_width(ws, {'A': 12, 'B': 10, 'C': 14, 'D': 16,
                       'E': 16, 'F': 14, 'G': 14, 'H': 16})

# ============================================================
# 10. 创建"MOB转化率"Sheet
#
# 【MOB业务逻辑说明】
# MOB (Month on Book): 衡量首贷客户在放款后第几个月回来申请复贷
#
# 示例（以当前月=2026-04为例）:
#   首贷月份    →  客户在首贷月份首次放款
#   MOB1        →  首贷后第1个月来申请复贷（即4月首贷客户，5月可能来申请复贷）
#   MOB2        →  首贷后第2个月来申请复贷
#
# 【历史率含义】
#   历史率-1期前 = 距今最近一期首贷的MOB转化率
#                即：2026-03月首贷客户在MOB1时的转化率
#   历史率-2期前 = 距今第2期首贷的MOB转化率
#                即：2026-02月首贷客户在MOB1时的转化率
#
# 【移动平均预估】
#   4月份首贷的MOB1转化率，用(3月首贷的MOB1 + 2月首贷的MOB1) ÷ 2 预估
#   这就是为什么用最近两个月做移动平均
#
# 【Excel表格结构】
#   B列~D列: 最近3期首贷月份对应的MOB转化率（死数）
#   E列: MA公式 = AVERAGE(B:D) 即最近window个月的移动平均
#   F列: 调整后 = MA × 调整系数
# ============================================================
def create_mob_rates_sheet(ws, mob_rates: dict, window=3):
    ws.title = 'MOB转化率'

    # 计算历史期数（取所有MOB中最长的历史数据长度，最多显示12期）
    max_hist = max(len(v) for v in mob_rates.values()) if mob_rates else 3
    hist_cols = min(max_hist, 12)

    # 构建表头 - 更清晰的命名
    header = ['MOB', '首贷月份→转化率']
    for i in range(1, hist_cols + 1):
        # 显示"距离当前几期前"，更直观
        header.append(f'距今{i}期前首贷转化率')
    header += ['MA(最近两期平均)', 'MA×调整系数']

    for c, h in enumerate(header, 1):
        ws.cell(1, c, h)
    hdr(ws, 1)

    P = '参数配置'
    ma_col  = hist_cols + 2   # MA公式列号
    adj_col = hist_cols + 3   # 调整后列号

    for row, (mob, rates) in enumerate(sorted(mob_rates.items()), 2):
        ws.cell(row, 1, f'MOB{mob}')
        ws.cell(row, 2, f'共{len(rates)}期历史数据')

        # 历史率（死数，最近 hist_cols 期）
        for i, rate in enumerate(rates[:hist_cols], 3):
            ws.cell(row, i, rate)
            ws.cell(row, i).number_format = PCT_FMT

        # MA 公式：=AVERAGE(最近 window 列)
        # 历史数据从 C 列开始，最新的在前（C, D, E ...）
        start_letter = get_column_letter(3)
        end_letter   = get_column_letter(min(window + 2, hist_cols + 2))
        ws.cell(row, ma_col, f"=IFERROR(AVERAGE({start_letter}{row}:{end_letter}{row}),0)")
        ws.cell(row, ma_col).number_format = PCT_FMT

        # 调整后 = MA × 调整系数
        ma_letter  = get_column_letter(ma_col)
        ws.cell(row, adj_col,
                f"={ma_letter}{row}*'{P}'!$B${PARAM_ROWS['adj_factor']}")
        ws.cell(row, adj_col).number_format = PCT_FMT

    # 标注 MA 公式列和调整后列
    for r in range(2, len(mob_rates) + 2):
        ws.cell(r, ma_col).fill  = GRN_FILL
        ws.cell(r, adj_col).fill = YLW_FILL

    # 列宽
    ws.column_dimensions['A'].width = 8
    ws.column_dimensions['B'].width = 18
    for i in range(3, hist_cols + 4):
        ws.column_dimensions[get_column_letter(i)].width = 15

# ============================================================
# 11. 创建"首贷历史"Sheet（增加放款金额公式）
# ============================================================
def create_first_loan_history_sheet(ws, first_loan_df: pd.DataFrame):
    ws.title = '首贷历史'
    has_amt = 'avg_loan_amount' in first_loan_df.columns

    headers = ['首贷月份', '放款笔数', '件均(元)', '放款金额(公式，元)']
    for c, h in enumerate(headers, 1):
        ws.cell(1, c, h)
    hdr(ws, 1)

    for row, (_, rec) in enumerate(first_loan_df.iterrows(), 2):
        ws.cell(row, 1, rec['first_loan_month'])
        ws.cell(row, 2, int(rec['first_loan_cnt']))
        avg_amt = float(rec['avg_loan_amount']) if has_amt else 1500.0
        ws.cell(row, 3, avg_amt)
        # 放款金额 = 笔数 × 件均（公式）
        ws.cell(row, 4, f"=B{row}*C{row}")

        ws.cell(row, 2).number_format = NUM_FMT
        ws.cell(row, 3).number_format = NUM_FMT
        ws.cell(row, 4).number_format = '"¥"#,##0'

    set_col_width(ws, {'A': 12, 'B': 12, 'C': 12, 'D': 18})

# ============================================================
# 12. 创建"汇总"Sheet（公式汇总首贷+复贷）
# ============================================================
def create_summary_sheet(ws, months: list, first_loan_forecast_row_map: dict,
                         reloan_total_row_map: dict):
    ws.title = '汇总'
    headers = ['预估月份',
               '首贷放款笔数(预估)', '首贷放款金额(预估)',
               '复贷进件量(预估)', '合计进件量']
    for c, h in enumerate(headers, 1):
        ws.cell(1, c, h)
    hdr(ws, 1)

    for row, month in enumerate(months, 2):
        ws.cell(row, 1, month)
        # 引用首贷预估Sheet
        fl_row = first_loan_forecast_row_map.get(month, 2)
        ws.cell(row, 2, f"='首贷预估'!E{fl_row}")
        ws.cell(row, 3, f"='首贷预估'!G{fl_row}")
        # 引用复贷预估Sheet小计行
        rl_row = reloan_total_row_map.get(month)
        if rl_row:
            ws.cell(row, 4, f"='复贷预估'!H{rl_row}")
        else:
            ws.cell(row, 4, 0)
        # 合计进件量 = 首贷 + 复贷
        ws.cell(row, 5, f"=B{row}+D{row}")

        for c in [2, 4, 5]:
            ws.cell(row, c).number_format = NUM_FMT
        ws.cell(row, 3).number_format = '"¥"#,##0'
        ws.cell(row, 1).fill = GRN_FILL

    set_col_width(ws, {'A': 12, 'B': 18, 'C': 20, 'D': 18, 'E': 16})

# ============================================================
# 13. 主程序
# ============================================================
def main():
    print("=" * 65)
    print("复贷进件量预估系统 v3（含首贷放款金额 + Excel公式）")
    print("=" * 65)

    today = datetime.now()
    current_month = today.strftime("%Y-%m")
    next_month    = (today + relativedelta(months=1)).strftime("%Y-%m")
    months = [current_month, next_month]
    print(f"预估月份: {current_month}（当月）, {next_month}（下月）\n")

    # ---- 数据获取 ----
    print("Step 1: 获取数据库数据 ...")
    pq = PrestoQuery()
    first_loan_df = reloan_df = None
    try:
        pq.login_process()
        result = pq.submit_query(SQL_FIRST_LOAN)
        if isinstance(result, pd.DataFrame) and not result.empty:
            first_loan_df = result
            print(f"  首贷数据: {len(first_loan_df)} 个月")
        result = pq.submit_query(SQL_RELOAN_BY_MOB)
        if isinstance(result, pd.DataFrame) and not result.empty:
            reloan_df = result
            print(f"  复贷数据: {len(reloan_df)} 条")
    except Exception as e:
        print(f"  数据库连接失败: {e}")

    if first_loan_df is None or reloan_df is None:
        first_loan_df, reloan_df = generate_mock_data()

    # 类型转换
    first_loan_df['first_loan_cnt'] = first_loan_df['first_loan_cnt'].astype(int)
    reloan_df['mob_num']             = reloan_df['mob_num'].astype(int)
    reloan_df['reloan_apply_cnt']    = reloan_df['reloan_apply_cnt'].astype(int)
    first_loan_dict = dict(zip(first_loan_df['first_loan_month'],
                               first_loan_df['first_loan_cnt']))

    # ---- 计算 MOB 转化率 ----
    print("\nStep 2: 计算各 MOB 历史转化率 + MA ...")
    mob_rates = {}
    for mob in CONFIG['mob_list']:
        mob_data = reloan_df[reloan_df['mob_num'] == mob].sort_values(
            'first_loan_month', ascending=False)
        rates = []
        for _, row in mob_data.iterrows():
            fc = first_loan_dict.get(row['first_loan_month'], 0)
            if fc > 0:
                rates.append(row['reloan_apply_cnt'] / fc)
        if rates:
            mob_rates[mob] = rates
    print(f"  有效 MOB 数: {len(mob_rates)}")

    # ---- 生成预估结果 ----
    print("\nStep 3: 生成复贷预估结果 ...")
    forecast_results = []
    for target in months:
        target_date = datetime.strptime(target, "%Y-%m")
        for mob, rates in mob_rates.items():
            ma_rate = calc_ma_rate(rates, CONFIG['ma_window'])
            cohort_date  = target_date - relativedelta(months=mob)
            cohort_month = cohort_date.strftime("%Y-%m")
            fl_cnt = first_loan_dict.get(cohort_month, 0)
            forecast_results.append({
                '预估月份':      target,
                'MOB周期':       f'MOB{mob}',
                '对应首贷月份':  cohort_month,
                '首贷放款量':    fl_cnt,
                '原始MA转化率':  ma_rate,
                '调整系数':      CONFIG['adjustment_factor'],
                '调整后转化率':  ma_rate * CONFIG['adjustment_factor'],
                '预估复贷进件量': int(fl_cnt * ma_rate * CONFIG['adjustment_factor']),
            })
    print(f"  预估记录数: {len(forecast_results)}")

    # ---- 写 Excel ----
    print("\nStep 4: 写入 Excel（含公式）...")
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"复贷进件量预估_v3_{ts}.xlsx"

    wb = openpyxl.Workbook()

    # Sheet1: 参数配置
    ws_params = wb.active
    create_params_sheet(ws_params, CONFIG)

    # Sheet2: 首贷预估
    ws_fl = wb.create_sheet()
    create_first_loan_forecast_sheet(ws_fl, months)
    # 记录首贷预估的行号映射（月份→行）
    fl_row_map = {m: (i + 2) for i, m in enumerate(months)}

    # Sheet3: 复贷预估
    ws_rl = wb.create_sheet()
    create_reloan_forecast_sheet(ws_rl, forecast_results)
    # 记录复贷小计行号映射
    n_records = len(forecast_results)
    rl_total_row_map = {}
    next_row = n_records + 2
    month_keys = list(dict.fromkeys(r['预估月份'] for r in forecast_results))  # 保序去重
    for m in month_keys:
        rl_total_row_map[m] = next_row
        next_row += 1

    # Sheet4: 汇总
    ws_sum = wb.create_sheet()
    create_summary_sheet(ws_sum, months, fl_row_map, rl_total_row_map)

    # Sheet5: MOB转化率
    ws_mob = wb.create_sheet()
    create_mob_rates_sheet(ws_mob, mob_rates, CONFIG['ma_window'])

    # Sheet6: 首贷历史
    ws_hist = wb.create_sheet()
    create_first_loan_history_sheet(ws_hist, first_loan_df)

    wb.save(output_file)
    print(f"\n  已保存: {output_file}")
    print("  Sheet 说明:")
    print("    参数配置  <- 修改黄色单元格，所有预估自动联动")
    print("    首贷预估  <- 基于投放消耗→安装→进件→放款，含金额预估")
    print("    复贷预估  <- 首贷放款量 × MA转化率(最近两期平均) × 调整系数 = 预估进件")
    print("    汇总      <- 首贷+复贷合并汇总")
    print("    MOB转化率 <- 各MOB历史转化率(距今1期前、2期前...) + MA公式")
    print("    首贷历史  <- 历史放款笔数 + 件均 + 金额公式")

    print("\n" + "=" * 65)
    print('完成！修改"参数配置"Sheet 中任意黄色单元格，Excel 自动重算。')
    print("=" * 65)


if __name__ == "__main__":
    main()



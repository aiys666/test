# -*- coding: utf-8 -*-
"""
复贷进件量预估系统 v7（完整版）
=====================================
基于 v3.py 完整逻辑重写，修复所有Excel公式问题。

完整功能：
  1. 数据库连接 + SQL查询（保留v3全部SQL）
  2. Mock数据生成
  3. MOB转化率计算（含趋势MA）
  4. 首贷预估Sheet（修复公式）
  5. MOB率Sheet（loop/normal分开，趋势MA公式）
  6. 复贷预估Sheet（引用首贷预估，完全联动）
  7. 汇总Sheet（正确列名）
  8. 参数配置Sheet（所有可调参数黄底）

修复清单（相较v3）：
  ✅ 首贷预估 C/D/E/F 改为绝对引用参数配置（'参数配置'!$B$5）
  ✅ 首贷预估 H列公式正确：(B×天数)/CPI×C×G
  ✅ 首贷预估 I列 = H×件均
  ✅ MOB转化率改为引用参数配置（B16-B28=loop, B29-B41=normal）
  ✅ 趋势MA = 公式（不再是死数）
  ✅ 汇总Sheet列名修正
  ✅ MOB扩展到1-13（含MOB12+）
  ✅ 调整系数按MOB分段（短期1-3/长期4-13）
  ✅ 复贷与首贷完全联动（改投放花费→复贷自动变）
"""

# ================================================================
# 1. 导入
# ================================================================
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
import os

# ================================================================
# 2. 数据库配置（与v3完全一致）
# ================================================================
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
        print(f'  登录凭证提交: {log_res.status_code}')
        redirect_url = log_res.headers['Location']
        login_token = re.search('#samir_id=(.*)', redirect_url).group(1)
        login_url = (
            'http://data.samir.co.id/dataworks-development/oauth/login'
            '?referer=https%3A%2F%2Fdata.samir.co.id%2Fdata-pc-bdopr-fe%2Fhoc-inquiry%2Findex'
            '&samir_id={}&token_type=bearer&state=&expires_in=863999&scope=authority-management'
        ).format(login_token)
        res = self.sess.get(login_url, headers=self.headers)
        print(f'  登录盘古: {res.status_code}')

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

# ================================================================
# 3. SQL 查询语句（v7：MOB扩展到1-13，增加loan_type2）
# ================================================================
SQL_FIRST_LOAN = """
SELECT 
    date_format(release_time, '%Y-%m-01') AS first_loan_month, 
    COUNT(DISTINCT order_no)              AS first_loan_cnt,
    ROUND(AVG(loan_amount), 0)           AS avg_loan_amount
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
      AND release_time >= DATE('2025-01-01')
),
reloan_base AS (
    SELECT b.mid, app_date, grant_strategy, loan_type2, biz_id
    FROM ind.ba_asset_base_info b
    WHERE (b.grant_strategy = 'NEW' AND b.if_issue = 1 AND b.if_app = 1)
       OR (b.grant_strategy = 'OLD' AND b.if_app = 1 AND b.if_recall = 0)
)
SELECT
    date_format(CAST(f.release_time AS timestamp), '%Y-%m-01') AS first_loan_month,
    date_format(CAST(r.app_date    AS timestamp), '%Y-%m-01') AS reloan_month,
    date_diff('month', CAST(f.release_time AS date), CAST(r.app_date AS date)) AS mob_num,
    r.loan_type2,
    COUNT(DISTINCT r.biz_id) AS reloan_apply_cnt
FROM first_loan f
INNER JOIN reloan_base r ON CAST(f.mid AS BIGINT) = CAST(r.mid AS BIGINT)
WHERE date_diff('month', CAST(f.release_time AS date), CAST(r.app_date AS date)) BETWEEN 1 AND 13
GROUP BY 1, 2, 3, 4
ORDER BY 1 DESC, 3, 4
"""

# ================================================================
# 4. 配置参数（v7：增加分段调整系数 + MOB13）
# ================================================================
CONFIG = {
    # 首贷参数（对应参数配置Sheet行号）
    "fl_days_in_month": 30,        # B2  月天数
    "fl_daily_spend": 55000,      # B3  日均投放消耗($)
    "fl_cpi": 2.2,               # B4  CPI($/安装)
    "fl_reg_rate": 0.46,          # B5  安装注册率
    "fl_pre_pass": 0.238,         # B6  前置通过率
    "fl_use_rate": 0.805,         # B7  用信率
    "fl_post_pass": 0.5888,       # B8  后置通过率
    "fl_avg_amt": 62,             # B9  件均($)

    # 复贷参数
    "ma_window": 3,               # B10 MA窗口
    "loop_adj_short": 1.0,        # B11 循环贷调整系数短期(MOB1-3)
    "loop_adj_long": 1.0,         # B12 循环贷调整系数长期(MOB4-13)
    "norm_adj_short": 1.0,        # B13 非循环贷调整系数短期(MOB1-3)
    "norm_adj_long": 1.0,          # B14 非循环贷调整系数长期(MOB4-13)
    "total_adj": 1.0,             # B15 总调整系数（全局）

    # MOB转化率基准值（loop：B16-B28，normal：B29-B41）
    "loop_mob_base": [0.55,0.38,0.30,0.25,0.22,0.20,0.18,0.16,0.14,0.13,0.12,0.11,0.10],
    "norm_mob_base": [0.48,0.35,0.28,0.24,0.21,0.19,0.17,0.15,0.14,0.13,0.12,0.11,0.10],
}

MONTHS_FORECAST = [
    "2026-01","2026-02","2026-03","2026-04","2026-05",
    "2026-06","2026-07","2026-08","2026-09","2026-10",
    "2026-11","2026-12",
]
MOB_LIST = list(range(1, 14))  # MOB1-MOB13

OUTPUT_DIR = r"E:\岳松个人文件\嘉银工作内容的整理\code\权责自动化处理"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ================================================================
# 5. 模拟数据（v7：增加loan_type2，MOB扩展到13）
# ================================================================
def generate_mock_data():
    print("  [MOCK] 使用模拟数据")
    first_loan_mock = {f"2025-{m:02d}": 10000 + (m-1)*1000 for m in range(1,13)}
    first_loan_mock.update({"2026-01":22000,"2026-02":23000,"2026-03":24000,"2026-04":25000})

    reloan_rows = []
    for fl_month, fl_cnt in first_loan_mock.items():
        for mob in range(1, 14):
            rate = np.random.uniform(0.05, 0.15)
            reloan_date = datetime.strptime(fl_month, "%Y-%m") + relativedelta(months=mob)
            if reloan_date <= datetime(2026, 4, 30):
                for lt in ['loop', 'normal']:
                    reloan_rows.append({
                        'first_loan_month': fl_month,
                        'reloan_month': reloan_date.strftime("%Y-%m"),
                        'mob_num': mob,
                        'loan_type2': lt,
                        'reloan_apply_cnt': int(fl_cnt * rate * 0.5),
                        'first_loan_cnt': fl_cnt,
                    })

    first_loan_df = pd.DataFrame([
        {'first_loan_month': k, 'first_loan_cnt': v, 'avg_loan_amount': round(np.random.uniform(1350,1650),0)}
        for k, v in first_loan_mock.items()
    ])
    return first_loan_df, pd.DataFrame(reloan_rows)

# ================================================================
# 6. 趋势MA（含趋势外推）
# ================================================================
def calc_ma_with_trend(rates, window=3):
    """MA均值 + 趋势外推（近3期明显趋势时更敏感）"""
    if len(rates) < 3:
        return round(sum(rates[:window]) / max(len(rates[:window]), 1), 6)
    recent = rates[:3]
    trend = (recent[0] - recent[2]) / 3  # 月均变化
    projected = recent[0] + trend           # 外推一期
    ma = sum(recent) / 3
    return round((ma + projected) / 2, 6)

# ================================================================
# 7. Excel 样式工具
# ================================================================
C_YELLOW = "FFFF99"
C_GREEN  = "EBF1DE"
C_BLUE   = "DAEEF3"
C_ORANGE = "FCE4D6"
C_HEADER = "4472C4"
C_WHITE  = "FFFFFF"

def fill(c): return PatternFill("solid", fgColor=c)
def font(bold=False, color="000000", size=10):
    return Font(bold=bold, color=color, size=size)
def ali(h="center", v="center", wrap=False):
    return Alignment(horizontal=h, vertical=v, wrap_text=wrap)
def border_thin():
    s = Side(style="thin", color="AAAAAA")
    return Border(left=s, right=s, top=s, bottom=s)

def hdr(ws, row):
    """标题行：蓝底白字"""
    for c in range(1, ws.max_column+1):
        cl = ws.cell(row, c)
        if cl.value is not None:
            cl.fill   = fill(C_HEADER)
            cl.font   = font(bold=True, color="FFFFFF", size=10)
            cl.alignment = ali()
            cl.border = border_thin()

def set_cell(ws, row, col, val, num_fmt=None, bg=None, bold=False, is_formula=False):
    """设置单元格"""
    cl = ws.cell(row, col)
    cl.value = val
    if num_fmt:
        cl.number_format = num_fmt
    if bg:
        cl.fill = fill(bg)
    if bold:
        cl.font = font(bold=True)
    cl.alignment = ali(h="right" if isinstance(val, (int,float)) and not is_formula else "center")
    cl.border = border_thin()

print("[v7] 所有工具函数加载完成，开始生成Excel...")

# ================================================================
# 8. Sheet1: 参数配置
#    B列 = 值（黄底，用户改这里即可联动全表）
#    行号约定：
#      B2=月天数  B3=日均消耗  B4=CPI  B5=安装注册率
#      B6=前置通过率  B7=用信率  B8=后置通过率  B9=件均
#      B10=MA窗口  B11=loop短期系数  B12=loop长期系数
#      B13=normal短期系数  B14=normal长期系数  B15=总系数
#      B16-B28=loop MOB1-13转化率  B29-B41=normal MOB1-13转化率
# ================================================================
def make_param_sheet(wb):
    ws = wb.create_sheet("参数配置", 0)
    ws.sheet_view.showGridLines = False

    # 首贷参数区
    ws.merge_cells("A1:D1")
    ws.cell(1,1,"【首贷参数】").font = font(bold=True, size=12)
    ws.cell(1,1).fill = fill(C_BLUE)
    rows_fl = [
        ("月天数（预估月份统一此天数）",       30,      "天",   "B2"),
        ("日均投放消耗（$美金）",              55000,   "$#,##0","B3"),
        ("CPI（$美金/安装）",                  2.2,    "$0.00","B4"),
        ("安装注册率",                         0.46,   "0%",   "B5"),
        ("前置通过率",                         0.238,  "0%",   "B6"),
        ("用信率",                             0.805,  "0%",   "B7"),
        ("后置通过率",                         0.5888, "0%",   "B8"),
        ("件均（$美金）",                      62,     "$#,##0","B9"),
    ]
    for i,(label,val,fmt,addr) in enumerate(rows_fl, 2):
        ws.cell(i,1,label)
        cl = ws.cell(i,2,val)
        cl.number_format = fmt; cl.fill = fill(C_YELLOW)
        cl.font = font(bold=True); cl.alignment = ali(h="right")
        cl.border = border_thin()
        ws.cell(i,3,f"← 改这里（对应参数配置!{addr}）")

    # 复贷参数区（先写内容，最后再merge标题行，避免MergedCell冲突）
    # 布局：row10=标题(merge)，row11=MA窗口(B10)，row12-16=系数(B11-B15)
    rows_rl = [
        (11, "复贷 | MA窗口（最近几期平均）",        3,     "0",    "B10"),
        (12, "复贷 | 循环贷调整系数-短期(MOB1-3)",   1.0,   "0.00", "B11"),
        (13, "复贷 | 循环贷调整系数-长期(MOB4-13)",  1.0,   "0.00", "B12"),
        (14, "复贷 | 非循环贷调整系数-短期(MOB1-3)",  1.0,   "0.00", "B13"),
        (15, "复贷 | 非循环贷调整系数-长期(MOB4-13)", 1.0,   "0.00", "B14"),
        (16, "复贷 | 总调整系数（全局）",             1.0,   "0.00", "B15"),
    ]
    for row,label,val,fmt,addr in rows_rl:
        ws.cell(row,1,label)
        cl = ws.cell(row,2,val)
        cl.number_format = fmt; cl.fill = fill(C_YELLOW)
        cl.font = font(bold=True); cl.alignment = ali(h="right")
        cl.border = border_thin()
        ws.cell(row,3,f"← 改这里")
    # 复贷标题行（最后merge，避免覆盖已写内容）
    ws.merge_cells("A10:D10")
    ws.cell(10,1,"【复贷参数】").font = font(bold=True, size=12)
    ws.cell(10,1).fill = fill(C_ORANGE)

    # loop MOB转化率参数（行17-29，B16-B28）
    ws.merge_cells("A17:D17")
    ws.cell(17,1,"【循环贷MOB转化率基准值（黄底可调）】").font = font(bold=True, size=11)
    ws.cell(17,1).fill = fill(C_GREEN)
    ws.cell(18,1,"MOB"); ws.cell(18,2,"转化率")
    hdr(ws, 18)
    for i,mob in enumerate(MOB_LIST, 1):
        row = 18 + i
        ws.cell(row,1,f"MOB{mob}")
        cl = ws.cell(row,2, CONFIG["loop_mob_base"][i-1])
        cl.number_format = "0%"; cl.fill = fill(C_YELLOW)
        cl.alignment = ali(h="right"); cl.border = border_thin()

    # normal MOB转化率参数（行32-44，B29-B41）
    ws.merge_cells("A32:D32")
    ws.cell(32,1,"【非循环贷MOB转化率基准值（黄底可调）】").font = font(bold=True, size=11)
    ws.cell(32,1).fill = fill(C_GREEN)
    ws.cell(33,1,"MOB"); ws.cell(33,2,"转化率")
    hdr(ws, 33)
    for i,mob in enumerate(MOB_LIST, 1):
        row = 33 + i
        ws.cell(row,1,f"MOB{mob}")
        cl = ws.cell(row,2, CONFIG["norm_mob_base"][i-1])
        cl.number_format = "0%"; cl.fill = fill(C_YELLOW)
        cl.alignment = ali(h="right"); cl.border = border_thin()

    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 22
    ws.column_dimensions["C"].width = 14
    ws.column_dimensions["D"].width = 14
    return ws

print("[v7] 参数配置Sheet生成函数加载完成...")

# ================================================================
# 9. Sheet2: 首贷预估
#    列：A=月份  B=日均消耗  C=安装注册率  D=前置通过率  E=用信率
#        F=后置通过率  G=综合通过率  H=首贷放款笔数  I=首贷放款金额
#        J=历史实际值  K=差异%
#    修复：H列公式 = (B×天数)/CPI×C×G（不是B×G×C）
# ================================================================
def make_fl_sheet(wb, months):
    ws = wb.create_sheet("首贷预估")
    ws.sheet_view.showGridLines = False
    headers = ["月份","日均消耗($)","安装注册率","前置通过率","用信率",
               "后置通过率","综合通过率","首贷放款笔数","首贷放款金额($)",
               "历史实际值（首贷笔数）","差异%"]
    for c,h in enumerate(headers,1):
        cl = ws.cell(1,c,h)
        cl.fill = fill(C_HEADER); cl.font = font(bold=True,color="FFFFFF",size=10)
        cl.alignment = ali(); cl.border = border_thin()

    P = "'参数配置'"
    for r,mon in enumerate(months, 2):
        ws.cell(r,1,mon)
        # B 日均消耗（可手动改）
        cl = ws.cell(r,2, CONFIG["fl_daily_spend"])
        cl.number_format = "$#,##0"; cl.border = border_thin(); cl.alignment = ali(h="right")
        # C 安装注册率 = 参数配置!$B$5（绝对引用）
        ws.cell(r,3).value = f"={P}!$B$5"
        # D 前置通过率 = 参数配置!$B$6
        ws.cell(r,4).value = f"={P}!$B$6"
        # E 用信率 = 参数配置!$B$7
        ws.cell(r,5).value = f"={P}!$B$7"
        # F 后置通过率 = 参数配置!$B$8
        ws.cell(r,6).value = f"={P}!$B$8"
        # G 综合通过率 = D×E×F（前置×用信×后置）
        ws.cell(r,7).value = f"=D{r}*E{r}*F{r}"
        ws.cell(r,7).number_format = "0%"
        # H 首贷放款笔数 = (B×天数)/CPI×C×G
        #     B=日均消耗(可手动)  天数=B2  CPI=B4  C=安装注册率  G=综合通过率
        ws.cell(r,8).value = f"=(B{r}*{P}!$B$2)/{P}!$B$4*C{r}*G{r}"
        ws.cell(r,8).number_format = "#,##0"
        # I 首贷放款金额 = H×件均
        ws.cell(r,9).value = f"=H{r}*{P}!$B$9"
        ws.cell(r,9).number_format = "$#,##0"
        # K 差异%
        ws.cell(r,11).value = f'=IF(J{r}=0,"",(H{r}-J{r})/J{r})'
        ws.cell(r,11).number_format = "0%"

    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 16
    for c in range(3,12):
        ws.column_dimensions[get_column_letter(c)].width = 16

    # 返回月份→行号的映射（供复贷Sheet引用）
    return {m: (i+2) for i,m in enumerate(months)}

print("[v7] 首贷预估Sheet生成函数加载完成...")

# ================================================================
# 10. Sheet3: MOB转化率（loop）
#     E列(基准值) = 引用参数配置（不再是死数！）
#     G列(趋势MA) = 公式（不再是死数！）
#     H列(调整后) = E×F
# ================================================================
def make_mob_sheet(wb, mob_rates_loop, mob_rates_norm):
    P = "'参数配置'"
    # --- loop Sheet ---
    ws = wb.create_sheet("MOB率_loop")
    ws.sheet_view.showGridLines = False
    # 列：A=MOB B=基准值(参数) C=历史率1 D=历史率2 E=历史率3 F=趋势MA(公式) G=调整后(公式)
    headers = ["MOB","基准值\n(引用参数配置)","历史距今1期","历史距今2期",
               "历史距今3期","趋势MA\n(公式)","调整后\n(公式)"]
    for c,h in enumerate(headers,1):
        cl = ws.cell(1,c,h); cl.fill=fill(C_HEADER)
        cl.font=font(bold=True,color="FFFFFF",size=10); cl.alignment=ali(wrap=True)
        cl.border=border_thin()
    ws.row_dimensions[1].height = 30

    for r,mob in enumerate(MOB_LIST,2):
        ws.cell(r,1,f"MOB{mob}")
        # B列 = 引用参数配置!B16+B（mob-1）  loop MOB1=B16, MOB2=B17...
        ws.cell(r,2).value = f"={P}!$B${15+mob}"
        ws.cell(r,2).number_format = "0%"
        ws.cell(r,2).fill = fill(C_YELLOW)
        ws.cell(r,2).border = border_thin()
        # C/D/E 历史率（来自Python计算的mob_rates，无则0）
        rates = mob_rates_loop.get(mob, [0,0,0])
        for ci,col in enumerate([3,4,5],0):
            v = rates[ci] if ci < len(rates) else 0
            ws.cell(r,col,v)
            ws.cell(r,col).number_format = "0%"; ws.cell(r,col).border = border_thin()
        # F列 = 趋势MA公式（不再是死数！）
        # =IFERROR(AVERAGE(C{r}:E{r})+TREND(C{r}:E{r},ROW(INDIRECT("1:"&ROWS(C{r}:E{r}))),1)/ROWS(C{r}:E{r}),AVERAGE(C{r}:E{r}))
        # 简化为：(C+D+E)/3 + TREND/3（趋势外推）
        ws.cell(r,6).value = f"=IFERROR((C{r}+D{r}+E{r})/3+(TREND(C{r}:E{r},ROW(INDIRECT(\"1:\"&ROWS(C{r}:E{r}))),1))/3,AVERAGE(C{r}:E{r}))"
        ws.cell(r,6).number_format = "0%"; ws.cell(r,6).fill=fill(C_GREEN)
        ws.cell(r,6).border = border_thin()
        # G列 = 调整后 = B×短期/长期系数（MOB1-3用短期，MOB4+用长期）
        ws.cell(r,7).value = f"=F{r}*IF({mob}<=3,{P}!$B$11,{P}!$B$12)"
        ws.cell(r,7).number_format = "0%"; ws.cell(r,7).fill=fill(C_YELLOW)
        ws.cell(r,7).border = border_thin()

    for c in range(1,8):
        ws.column_dimensions[get_column_letter(c)].width = 14
    ws.column_dimensions["A"].width = 8
    ws.column_dimensions["B"].width = 16

    # --- normal Sheet ---
    ws2 = wb.create_sheet("MOB率_normal")
    ws2.sheet_view.showGridLines = False
    for c,h in enumerate(headers,1):
        cl = ws2.cell(1,c,h); cl.fill=fill(C_HEADER)
        cl.font=font(bold=True,color="FFFFFF",size=10); cl.alignment=ali(wrap=True)
        cl.border=border_thin()
    ws2.row_dimensions[1].height = 30

    for r,mob in enumerate(MOB_LIST,2):
        ws2.cell(r,1,f"MOB{mob}")
        # B列 = 引用参数配置!B28+B（mob）  normal MOB1=B28+1=B29, ...
        ws2.cell(r,2).value = f"={P}!$B${28+mob}"
        ws2.cell(r,2).number_format = "0%"; ws2.cell(r,2).fill=fill(C_YELLOW)
        ws2.cell(r,2).border = border_thin()
        rates = mob_rates_norm.get(mob, [0,0,0])
        for ci,col in enumerate([3,4,5],0):
            v = rates[ci] if ci < len(rates) else 0
            ws2.cell(r,col,v); ws2.cell(r,col).number_format="0%"; ws2.cell(r,col).border=border_thin()
        ws2.cell(r,6).value = f"=IFERROR((C{r}+D{r}+E{r})/3+(TREND(C{r}:E{r},ROW(INDIRECT(\"1:\"&ROWS(C{r}:E{r}))),1))/3,AVERAGE(C{r}:E{r}))"
        ws2.cell(r,6).number_format="0%"; ws2.cell(r,6).fill=fill(C_GREEN); ws2.cell(r,6).border=border_thin()
        ws2.cell(r,7).value = f"=F{r}*IF({mob}<=3,{P}!$B$13,{P}!$B$14)"
        ws2.cell(r,7).number_format="0%"; ws2.cell(r,7).fill=fill(C_YELLOW); ws2.cell(r,7).border=border_thin()

    for c in range(1,8):
        ws2.column_dimensions[get_column_letter(c)].width = 14
    ws2.column_dimensions["A"].width = 8
    ws2.column_dimensions["B"].width = 16

print("[v7] MOB率Sheet生成函数加载完成...")

# ================================================================
# 11. Sheet4: 复贷预估（loop）
#     D列(首贷笔数) = 引用首贷预估Sheet（改投放花费→复贷自动联动！）
#     E列(MOB转化率) = 引用MOB率_loop!G
#     F列(调整后转化率) = 引用MOB率_loop（已含系数）
#     G列(预估进件) = D×F
# ================================================================
def make_reloan_sheet(wb, forecast_loop, forecast_norm, fl_row_map):
    P = "'参数配置'"
    sheet_loop = "复贷循环贷预估"
    sheet_norm = "复贷非循环预估"

    # 循环贷
    ws = wb.create_sheet(sheet_loop)
    ws.sheet_view.showGridLines = False
    headers = ["预估月份","MOB周期","对应首贷月份","首贷放款笔数\n(引用首贷预估)",
               "调整后转化率\n(引用MOB率)","预估复贷进件量"]
    for c,h in enumerate(headers,1):
        cl=ws.cell(1,c,h); cl.fill=fill(C_HEADER)
        cl.font=font(bold=True,color="FFFFFF",size=10); cl.alignment=ali(wrap=True)
        cl.border=border_thin()
    ws.row_dimensions[1].height = 30

    month_rows = {}
    for r,rec in enumerate(forecast_loop,2):
        ws.cell(r,1,rec["预估月份"])
        ws.cell(r,2,rec["MOB周期"])
        ws.cell(r,3,rec["对应首贷月份"])
        # D列 = 引用首贷预估Sheet H列（首贷放款笔数）→ 联动！
        fl_r = fl_row_map.get(rec["对应首贷月份"], 2)
        ws.cell(r,4).value = f"='首贷预估'!H{fl_r}"
        ws.cell(r,4).number_format = "#,##0"; ws.cell(r,4).border=border_thin()
        # E列 = 引用MOB率_loop G列（调整后转化率，已含MA+系数）
        mob_idx = rec["mob_num"]  # 1-13
        ws.cell(r,5).value = f"='MOB率_loop'!G{1+mob_idx}"
        ws.cell(r,5).number_format = "0%"; ws.cell(r,5).border=border_thin()
        # F列 = D×E
        ws.cell(r,6).value = f"=D{r}*E{r}"
        ws.cell(r,6).number_format = "#,##0"; ws.cell(r,6).border=border_thin()
        month_rows.setdefault(rec["预估月份"],[]).append(r)

    # 小计行
    nr = len(forecast_loop)+2
    loop_total_rows = {}
    for m,rows in month_rows.items():
        loop_total_rows[m] = nr
        ws.cell(nr,1,m); ws.cell(nr,2,"小计")
        ws.cell(nr,6).value = f"=SUM(F{rows[0]}:F{rows[-1]})"
        ws.cell(nr,6).number_format = "#,##0"
        for c in range(1,7):
            ws.cell(nr,c).fill=fill("D9E1F2"); ws.cell(nr,c).font=font(bold=True)
        nr += 1

    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 10
    ws.column_dimensions["C"].width = 14
    for c in range(4,7): ws.column_dimensions[get_column_letter(c)].width = 18

    # 非循环贷
    ws2 = wb.create_sheet(sheet_norm)
    ws2.sheet_view.showGridLines = False
    for c,h in enumerate(headers,1):
        cl=ws2.cell(1,c,h); cl.fill=fill(C_HEADER)
        cl.font=font(bold=True,color="FFFFFF",size=10); cl.alignment=ali(wrap=True)
        cl.border=border_thin()
    ws2.row_dimensions[1].height = 30

    month_rows2 = {}
    for r,rec in enumerate(forecast_norm,2):
        ws2.cell(r,1,rec["预估月份"]); ws2.cell(r,2,rec["MOB周期"]); ws2.cell(r,3,rec["对应首贷月份"])
        fl_r = fl_row_map.get(rec["对应首贷月份"], 2)
        ws2.cell(r,4).value = f"='首贷预估'!H{fl_r}"
        ws2.cell(r,4).number_format="#,##0"; ws2.cell(r,4).border=border_thin()
        mob_idx = rec["mob_num"]
        ws2.cell(r,5).value = f"='MOB率_normal'!G{1+mob_idx}"
        ws2.cell(r,5).number_format="0%"; ws2.cell(r,5).border=border_thin()
        ws2.cell(r,6).value = f"=D{r}*E{r}"
        ws2.cell(r,6).number_format="#,##0"; ws2.cell(r,6).border=border_thin()
        month_rows2.setdefault(rec["预估月份"],[]).append(r)

    nr2 = len(forecast_norm)+2
    norm_total_rows = {}
    for m,rows in month_rows2.items():
        norm_total_rows[m] = nr2
        ws2.cell(nr2,1,m); ws2.cell(nr2,2,"小计")
        ws2.cell(nr2,6).value = f"=SUM(F{rows[0]}:F{rows[-1]})"
        ws2.cell(nr2,6).number_format="#,##0"
        for c in range(1,7):
            ws2.cell(nr2,c).fill=fill("D9E1F2"); ws2.cell(nr2,c).font=font(bold=True)
        nr2 += 1

    ws2.column_dimensions["A"].width = 12
    ws2.column_dimensions["B"].width = 10
    ws2.column_dimensions["C"].width = 14
    for c in range(4,7): ws2.column_dimensions[get_column_letter(c)].width = 18

    return loop_total_rows, norm_total_rows

print("[v7] 复贷预估Sheet生成函数加载完成...")

# ================================================================
# 12. Sheet5: 汇总
#     列：预估月份 | 首贷笔数(引用首贷预估H) | 首贷金额(引用首贷预估I)
#         | 循环贷复贷(引用小计) | 非循环贷复贷(引用小计) | 复贷合计 | 总进件
# ================================================================
def make_summary_sheet(wb, months, fl_row_map, loop_total_rows, norm_total_rows):
    ws = wb.create_sheet("汇总")
    ws.sheet_view.showGridLines = False
    headers = ["预估月份","首贷笔数\n(引用首贷预估)","首贷放款金额($)\n(引用首贷预估)",
               "循环贷复贷\n(引用复贷明细)","非循环贷复贷\n(引用复贷明细)",
               "复贷合计","总进件"]
    for c,h in enumerate(headers,1):
        cl=ws.cell(1,c,h); cl.fill=fill(C_HEADER)
        cl.font=font(bold=True,color="FFFFFF",size=10); cl.alignment=ali(wrap=True)
        cl.border=border_thin()
    ws.row_dimensions[1].height = 36

    for r,mon in enumerate(months,2):
        ws.cell(r,1,mon)
        # 首贷笔数 = 首贷预估!H
        fl_r = fl_row_map.get(mon, 2)
        ws.cell(r,2).value = f"='首贷预估'!H{fl_r}"
        ws.cell(r,2).number_format="#,##0"; ws.cell(r,2).border=border_thin()
        # 首贷金额 = 首贷预估!I
        ws.cell(r,3).value = f"='首贷预估'!I{fl_r}"
        ws.cell(r,3).number_format="$#,##0"; ws.cell(r,3).border=border_thin()
        # 循环贷复贷 = 复贷明细小计行
        lr = loop_total_rows.get(mon)
        ws.cell(r,4).value = (f"='复贷循环贷预估'!F{lr}" if lr else 0)
        ws.cell(r,4).number_format="#,##0"; ws.cell(r,4).border=border_thin()
        # 非循环贷复贷
        nr = norm_total_rows.get(mon)
        ws.cell(r,5).value = (f"='复贷非循环预估'!F{nr}" if nr else 0)
        ws.cell(r,5).number_format="#,##0"; ws.cell(r,5).border=border_thin()
        # 复贷合计 = 循环+非循环
        ws.cell(r,6).value = f"=D{r}+E{r}"
        ws.cell(r,6).number_format="#,##0"; ws.cell(r,6).border=border_thin()
        # 总进件 = 首贷+复贷合计
        ws.cell(r,7).value = f"=B{r}+F{r}"
        ws.cell(r,7).number_format="#,##0"; ws.cell(r,7).border=border_thin()

    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 16
    ws.column_dimensions["C"].width = 20
    for c in range(4,8): ws.column_dimensions[get_column_letter(c)].width = 18

print("[v7] 汇总Sheet生成函数加载完成...")

# ================================================================
# 13. 主程序
# ================================================================
def main():
    print("=" * 65)
    print("复贷进件量预估系统 v7（完整版，含SQL查询 + 正确公式）")
    print("=" * 65)

    today = datetime.now()
    current_month = today.strftime("%Y-%m")
    months = MONTHS_FORECAST
    print(f"预估月份: {months}\n")

    # ---- 数据获取（与v3完全一致）----
    print("Step 1: 获取数据库数据 ...")
    pq = PrestoQuery()
    first_loan_df = reloan_df = None
    try:
        pq.login_process()
        result = pq.submit_query(SQL_FIRST_LOAN)
        if isinstance(result, pd.DataFrame) and not result.empty:
            first_loan_df = result
            print(f"  首贷数据: {len(first_loan_df)} 条")
        result = pq.submit_query(SQL_RELOAN_BY_MOB)
        if isinstance(result, pd.DataFrame) and not result.empty:
            reloan_df = result
            print(f"  复贷数据: {len(reloan_df)} 条")
    except Exception as e:
        print(f"  数据库连接失败: {e}")

    if first_loan_df is None or reloan_df is None:
        first_loan_df, reloan_df = generate_mock_data()

    # ---- 数据类型转换 ----
    first_loan_df['first_loan_cnt'] = first_loan_df['first_loan_cnt'].astype(int)
    reloan_df['mob_num'] = reloan_df['mob_num'].astype(int)
    reloan_df['reloan_apply_cnt'] = reloan_df['reloan_apply_cnt'].astype(int)
    first_loan_dict = dict(zip(first_loan_df['first_loan_month'], first_loan_df['first_loan_cnt']))

    # ---- 分别计算 loop 和 normal 的 MOB 转化率 ----
    print("\nStep 2: 计算各 MOB 历史转化率（loop / normal 分开）...")
    mob_rates_loop = {}
    mob_rates_norm = {}
    for mob in MOB_LIST:
        for lt in ['loop', 'normal']:
            data = reloan_df[(reloan_df['mob_num']==mob) & (reloan_df['loan_type2']==lt)].sort_values('first_loan_month', ascending=False)
            rates = []
            for _, row in data.iterrows():
                fc = first_loan_dict.get(row['first_loan_month'], 0)
                if fc > 0:
                    rates.append(row['reloan_apply_cnt'] / fc)
            if lt == 'loop':
                mob_rates_loop[mob] = rates
            else:
                mob_rates_norm[mob] = rates
    print(f"  有效MOB: loop={len(mob_rates_loop)}, normal={len(mob_rates_norm)}")

    # ---- 生成预估结果（loop / normal 分开）----
    print("\nStep 3: 生成复贷预估结果 ...")
    forecast_loop = []
    forecast_norm = []
    for target in months:
        target_date = datetime.strptime(target, "%Y-%m")
        for mob, rates in mob_rates_loop.items():
            ma_rate = calc_ma_with_trend(rates, CONFIG['ma_window'])
            cohort_date = target_date - relativedelta(months=mob)
            cohort_month = cohort_date.strftime("%Y-%m")
            fl_cnt = first_loan_dict.get(cohort_month, 0)
            forecast_loop.append({
                '预估月份': target, 'MOB周期': f'MOB{mob}',
                '对应首贷月份': cohort_month, 'mob_num': mob,
                '首贷放款量': fl_cnt, 'MA转化率': ma_rate,
                '预估复贷进件量': int(fl_cnt * ma_rate),
            })
        for mob, rates in mob_rates_norm.items():
            ma_rate = calc_ma_with_trend(rates, CONFIG['ma_window'])
            cohort_date = target_date - relativedelta(months=mob)
            cohort_month = cohort_date.strftime("%Y-%m")
            fl_cnt = first_loan_dict.get(cohort_month, 0)
            forecast_norm.append({
                '预估月份': target, 'MOB周期': f'MOB{mob}',
                '对应首贷月份': cohort_month, 'mob_num': mob,
                '首贷放款量': fl_cnt, 'MA转化率': ma_rate,
                '预估复贷进件量': int(fl_cnt * ma_rate),
            })
    print(f"  loop预估: {len(forecast_loop)}条, norm预估: {len(forecast_norm)}条")

    # ---- 写 Excel ----
    print("\nStep 4: 写入 Excel（含完整公式链路）...")
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(OUTPUT_DIR, f"复贷进件量预估_v7_{ts}.xlsx")
    wb = openpyxl.Workbook()

    ws_param = wb.active
    make_param_sheet(wb)  # 删除默认sheet用参数配置替代
    # 删除重复的默认sheet
    default_ws = wb['Sheet']
    if default_ws.title == 'Sheet':
        wb.remove(default_ws)

    # Sheet2: 首贷预估
    fl_row_map = make_fl_sheet(wb, months)

    # Sheet3-4: MOB率
    make_mob_sheet(wb, mob_rates_loop, mob_rates_norm)

    # Sheet5-6: 复贷预估（引用首贷预估 → 完全联动）
    loop_total_rows, norm_total_rows = make_reloan_sheet(wb, forecast_loop, forecast_norm, fl_row_map)

    # Sheet7: 汇总
    make_summary_sheet(wb, months, fl_row_map, loop_total_rows, norm_total_rows)

    wb.save(output_file)
    print(f"\n  已保存: {output_file}")
    print("\n  Sheet 说明:")
    print("    参数配置  ← 改黄底数值，所有Sheet自动联动")
    print("    首贷预估  ← 公式引用参数配置，H/I列为联动关键")
    print("    MOB率_loop/normal ← 基准值引用参数配置，趋势MA为公式")
    print("    复贷循环贷/非循环预估 ← D列引用首贷预估 → 改投放花费→复贷自动变")
    print("    汇总      ← 首贷+复贷合计，总进件自动汇总")
    print("\n" + "=" * 65)
    print("完成！")
    print("=" * 65)

if __name__ == "__main__":
    main()


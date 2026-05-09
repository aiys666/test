# -*- coding: utf-8 -*-
"""
复贷进件量预估系统 v7
=====================
基于 v3.py 完整逻辑，修复 Excel 公式问题：

修复清单（相较v3）：
  1. 首贷预估 C/D/E/F 全部改为 ='参数配置'!$B$5 绝对引用（v3是相对引用B5，错）
  2. 首贷预估 H列（首贷放款笔数）正确公式：(B×天数)÷CPI×C×G
  3. 首贷预估 I列（首贷放款金额）= H×件均
  4. 复贷预估 E列（MOB转化率基准）= 引用参数配置（B16-B28=loop, B29-B41=normal）
  5. MOB率Sheet 最终转化率 = 趋势MA × 调整系数（公式，不是死数）
  6. 汇总Sheet列名修正：首贷笔数/首贷金额/循环贷复贷/非循环贷复贷/复贷合计/总进件
  7. 所有Sheet标题行按用户截图对齐
  8. 复贷与首贷完全联动（改首贷投放花费→复贷自动变）
  9. MOB扩展到1-13（含MOB12+）
  10. 调整系数按MOB分段（短期MOB1-3 / 长期MOB4-13）

依赖：pandas, numpy, requests, openpyxl, python-dateutil
用法：python reloan_forecast_v7.py
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
# 2. 数据库配置
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
# 3. SQL 查询语句（v7：MOB扩展到1-13）
# ================================================================
SQL_FIRST_LOAN = """
SELECT 
    date_format(release_time, '%%Y-%%m-01') AS first_loan_month, 
    COUNT(DISTINCT order_no)              AS first_loan_cnt,
    ROUND(AVG(loan_amount), 0)          AS avg_loan_amount
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
    date_format(CAST(f.release_time AS timestamp), '%%Y-%%m-01') AS first_loan_month,
    date_format(CAST(r.app_date    AS timestamp), '%%Y-%%m-01') AS reloan_month,
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
    # 首贷参数
    "fl_days_in_month": 30,
    "fl_daily_spend": 55000,
    "fl_cpi"        : 2.2,
    "fl_reg_rate"   : 0.46,
    "fl_pre_pass"   : 0.238,
    "fl_use_rate"   : 0.805,
    "fl_post_pass"  : 0.5888,
    "fl_avg_amt"    : 62,

    # 复贷参数
    "ma_window"      : 3,
    "loop_adj_short" : 1.0,   # MOB1-3
    "loop_adj_long"  : 1.0,   # MOB4-13
    "norm_adj_short" : 1.0,
    "norm_adj_long"  : 1.0,
    "total_adj"      : 1.0,

    # MOB转化率基准值
    "loop_mob_base" : [0.55,0.38,0.30,0.25,0.22,0.20,0.18,0.16,0.14,0.13,0.12,0.11,0.10],
    "norm_mob_base" : [0.48,0.35,0.28,0.24,0.21,0.19,0.17,0.15,0.14,0.13,0.12,0.11,0.10],
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

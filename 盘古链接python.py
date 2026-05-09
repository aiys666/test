
'''
盘古3.0在提交sql时使用了base64加密，需在请求提交sql时作相应处理
20231110 分页请求结果，每页1000，循环取到所有数据结果
'''

import random
import pandas as pd
import requests
import json
import re
# import numpy as np
# import datetime
import time
# from openpyxl import load_workbook
# from openpyxl.utils.dataframe import dataframe_to_rows
import base64
import math
import base64

# 加密
def encrypt(string):
    """
    使用 base64 编码对字符串进行加密
    encode() 方法将字符串 string 编码为 UTF-8 字节序列，您可以将其用于网络传输、文件写入或加密等场景。
    :param string: 要加密的字符串
    :return: 加密后的字符串
    """
    string_bytes = string.encode('utf-8')
    encoded_bytes = base64.b64encode(string_bytes)
    encoded_string = encoded_bytes.decode('utf-8')
    return encoded_string

# 解密
def decrypt(encoded_string):
    encoded_bytes = encoded_string.encode('utf-8')
    string_bytes = base64.b64decode(encoded_bytes)
    string = string_bytes.decode('utf-8')
    return string

class PrestoQuery:

    # 定义请求头为实例变量
    def __init__(self):
        self.headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"}

        # self.user_agent_list = ["Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36",
        #     "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36",
        #     "Mozilla/5.0 (Windows NT 10.0; …) Gecko/20100101 Firefox/61.0",
        #     "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36",
        #     "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.62 Safari/537.36",
        #     "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36",
        #     "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)",
        #     "Mozilla/5.0 (Macintosh; U; PPC Mac OS X 10.5; en-US; rv:1.9.2.15) Gecko/20110303 Firefox/3.6.15"]
        # self.headers['User-Agent'] = random.choice(self.user_agent_list)


    def login_process(self):
        '''
        模拟盘古登录的过程，获取重定向后url中登录的token后直接跳过重定向过程，直接访问登录url
        :return:
        '''

        # 实例化一个维持会话对象session
        self.sess = requests.session()
        # TODO   设置连接活跃状态为False
        # s.keep_alive = False
        self.sess.keep_alive = False

        # post_url = 'https://dino-manage-auth.samir.co.id/login'
        # # 使用session发送post请求，并且禁止重定向，以获取location
        #
        # pay_load = {
        #     "callback": "https%3A%2F%2Fbigdata.samir.co.id%2Fbigdata%2Foauth%2Flogin%3Freferer%3Dhttps%253A%252F%252Fbigdata.samir.co.id%252Fbigdata-pc-bdopr-fe%252Findex&authsource=dino",
        #     "username": "adenrondonuwu@bigdata",
        #     "password": "9ef267964cbf2489e81ff61b3fd14623"}
        #
        # log_res = self.sess.post(post_url, headers=self.headers, data=pay_load, allow_redirects=False)


        post_url = 'https://dino-manage-auth-ina.samir.co.id/login?callback=http%3A%2F%2Fdata.samir.co.id%2Fdataworks-development%2Foauth%2Flogin%3Freferer%3Dhttps%253A%252F%252Fdata.samir.co.id%252Fdata-pc-bdopr-fe%252Fhoc-inquiry%252Findex&authsource=dino&username=erik@bigdata&password=Jy6856658!'
        log_res = self.sess.post(post_url, headers=self.headers, allow_redirects=False)

        print('提交登陆凭证后，请求响应状态码为：{}'.format(log_res.status_code))

        redirect_url = log_res.headers['Location']
        # 重定向相应的headers的Location属性为str，可以用正则表达式提取token信息
        login_token = re.search('#samir_id=(.*)', redirect_url).group(1)

        # 直接分析登录后页面的请求记录，token信息填充到登录请求url中，模拟跳转后的登录请求过程
        # login_url = 'http://data.samir.co.id/bigdata/oauth/login?referer=https%3A%2F%2Fbigdata.samir.co.id%2Fbigdata-pc-bdopr-fe%2Findex&&samir_id={}'.format(login_token)
        login_url = 'http://data.samir.co.id/dataworks-development/oauth/login?referer=https%3A%2F%2Fdata.samir.co.id%2Fdata-pc-bdopr-fe%2Fhoc-inquiry%2Findex&samir_id={}&token_type=bearer&state=&expires_in=863999&scope=authority-management'.format(login_token)       
        res = self.sess.get(login_url, headers=self.headers)
        print('登录盘古，请求响应状态码为：{}'.format(res.status_code))

    def submit_query(self, query_sql, wait_sec = 1):
        '''
        模拟盘古提交sql query，等待sql执行queryPrestoJobLog，获取查询结果的请求过程 getQueryResult
        目前只支持提交建表语句或者查询语句，二者不能在一段代码里同时提交
        :param query_sql: 提交的sql
        :return: 返回查询提交报错或者返回查询结果
        '''
        query_url = 'https://data.samir.co.id/dataworks-development/adhoc/querySql'
        data_sql = {"sql": base64.b64encode(query_sql.encode()).decode(),
                    "windowId":16,
                    "headRowNum":54,
                    "engine":"PRESTO",
                    "queryType":"Data",
                    "varList":[],
                    "dependStatus": 1
                    }

        query_res = self.sess.post(query_url, headers=self.headers, data=json.dumps(data_sql), timeout=(3, 20))
        # print(base64.b64encode(query_sql.encode()).decode())


        if query_res.json()['data']['checkError'] == 'True':
            return query_res.json()['data']['checkResultList'][0]['query'], query_res.json()['data']['checkResultList'][0]['errorMsg']
        else:  # sql检验结果未报错，继续请求job执行状态
            job_url = 'https://data.samir.co.id/dataworks-development/adhoc/queryPrestoJobLog'
            jobQueryId = query_res.json()['data']['jobQueryId']
            job_payload = {"jobQueryId": jobQueryId}
            job_res = self.sess.get(job_url, headers=self.headers, params=job_payload, timeout=(3, 20))


        while job_res.json()['data']['taskState'] != 'FINISHED' and job_res.json()['data']['windowStatus'] == 'WINDOW_RUNNING':
            time.sleep(wait_sec)
            job_res = self.sess.get(job_url, headers=self.headers, params=job_payload, timeout=(3, 20))

        query_id = job_res.json()['data']['queryId']
        statement_type = job_res.json()['data']['statementType']

        # 区分查询是建表语句还是查询语句
        if statement_type in ['drop', 'create']:
            return ("表更新成功")
        elif statement_type in ['select']:
            ####获取select的结果
            result_url = 'https://data.samir.co.id/dataworks-development/adhoc/getQueryResult'
            # result_url ='https://pangu.tengoprestamos.com/pangu/query/getQueryResult'
            result_payload = {'current': 1, 'size': 1000, 'queryId': query_id}
            result_res = self.sess.post(result_url, headers=self.headers, data=json.dumps(result_payload), timeout=(3, 20))
            print(1)

            totalrecords = result_res.json()['data']['totalRecords']
            df = pd.DataFrame()
            for i in range(1, math.ceil(totalrecords/1000)+1):
                current_page = i
                result_payload = {'current': current_page, 'size': 1000, 'queryId': query_id}
                result_res = self.sess.post(result_url, headers=self.headers, data=json.dumps(result_payload),timeout=(3, 20))
                df1 = pd.DataFrame(result_res.json()['data']['records'], columns=result_res.json()['data']['columns'])
                df = pd.concat([df, df1])
                # print(df.shape)
            return(df)

# pq = PrestoQuery() # 加括号才是实例化类
# pq.login_process()
#
# # 这一步提交sql,读取sql文件中的sql代码并将其字符串化
# sql_path = r'E:\软件\pycharm\Nigeria_Aurora\投放数据分析脚本\partner_ads_merge.sql'
# with open(sql_path, 'r', encoding='utf8') as sql:
#     sqltxt = sql.readlines()
#     querysql = ''.join(sqltxt)
# # repr() 方法可以将读取到的格式字符，比如换行符、制表符，转化为其相应的转义字符，注意空格不能转化成转义。
#
# #字典中单引号和双引号不能混用
# r1 = pq.sumbit_query(query_sql=querysql)
# print(r1)

pq = PrestoQuery()
pq.login_process()
sql1 = '''-- ============================================================================
-- Part 1: Fee data summary (fee_summary)
-- ============================================================================
WITH fee_summary AS (
    SELECT
        a2.issue_month,
        a2.grant_strategy,
        CASE
            WHEN a2.product_tag_detail LIKE '%M%'                 THEN 'M'
            WHEN a2.product_tag_detail = 'F-NofeeNew'            THEN 'F'
            WHEN a2.product_tag_detail LIKE '%NR%'               THEN 'NR'
            WHEN a2.product_tag_detail LIKE '%NF%'               THEN 'NF'
            WHEN a2.product_tag_detail LIKE '%NW%'               THEN 'NW'
            ELSE 'R'
        END AS product_tag,
        CASE
            WHEN a2.product_tag_detail IN ('R-30')               THEN '30D'
            WHEN a2.product_tag_detail LIKE '%M%'                THEN 'M'
            WHEN a2.product_tag_detail = 'F-NofeeNew'            THEN 'F'
            WHEN a2.product_tag_detail LIKE '%NR%'               THEN 'NR'
            WHEN a2.product_tag_detail LIKE '%NF%'               THEN 'NF'
            WHEN a2.product_tag_detail LIKE '%NW%'               THEN 'NW'
            ELSE '15D'
        END AS period_tag,
        a2.loan_cycle,
        COUNT(DISTINCT a2.biz_id)                               AS biz_num,
        SUM(a1.haircut_amount)                                  AS haircut_amount,
        SUM(a1.contract_amount)                                 AS contract_amount,
        SUM(a1.interest)                                        AS interest,
        SUM(a1.contract_amount * a1.loan_cycle)                 AS cycle_contract,
        SUM(a1.contract_amount * 1.00000 / a3.exchange_rate_to_dollar) AS contract_amount_usd
    FROM ods.s02_loan a1
    JOIN (
        SELECT
            biz_id,
            CASE
                WHEN a.product_level LIKE 'M%'                         THEN 'M'
                WHEN a.product_level IN ('A14','B10','B12','C8','A15','B13','B14','C9','A16','B15','B16','C10','G1','G2','H1','H2','H3','H4','I1','I2','I3','I4','I5','I6') THEN 'F-NofeeNew'
                WHEN a.product_level IN ('B7','C7','A9','B8')          THEN 'F-NofeeOld'
                WHEN a.product_level LIKE 'J%' OR a.product_level LIKE 'K%' OR a.product_level LIKE 'L%' THEN 'NR'
                WHEN a.product_level LIKE 'R%' OR a.product_level LIKE 'S%' THEN 'NF'
                WHEN a.product_level LIKE 'Q%'                         THEN 'NW'
                WHEN a.product_level LIKE 'D%' OR a.product_level LIKE 'E%' OR a.product_level LIKE 'F%' THEN 'R-30'
                ELSE 'R-15'
            END AS product_tag_detail,
            loan_cycle,
            issue_date,
            issue_month,
            grant_strategy
        FROM ind.xly_application_funnel a
        WHERE if_app = 1
          AND if_issue = 1
          AND issue_date >= '2024-01-01'
    ) a2 ON CAST(a1.camera_id AS BIGINT) = CAST(a2.biz_id AS BIGINT)
    LEFT JOIN dim.dim_exchange_rate_cost a3
        ON TO_CHAR(DATE(a2.issue_date), 'yyyymm') = a3.month_id
        AND account_currency = 'IDR'
    GROUP BY 1, 2, 3, 4, 5
),

-- ============================================================================
-- Part 2: Join with bad debt rate table and calculate ratios
-- ============================================================================
detail_with_metrics AS (
    SELECT
        b.grant_month,
        b.product_tag,
        b.period_tag,
        b.grant_strategy,
        b.loan_cycle,
        b.bad_debt_rate,
        COALESCE(f.contract_amount, 0)  AS contract_amount,
        COALESCE(f.haircut_amount, 0)   AS haircut_amount,
        COALESCE(f.interest, 0)         AS interest,
        COALESCE(f.cycle_contract, 0)   AS cycle_contract,

        -- Haircut ratio (haircut_amount / contract_amount)
        CASE WHEN f.contract_amount > 0
             THEN f.haircut_amount / f.contract_amount
             ELSE NULL
        END AS haircut_ratio,

        -- Total fee ratio (haircut + interest) / contract_amount
        CASE WHEN f.contract_amount > 0
             THEN (f.haircut_amount + f.interest) / f.contract_amount
             ELSE NULL
        END AS total_fee_ratio,

        -- Fixed daily interest ratio (0.3% per day)
        0.003 * b.loan_cycle AS fixed_daily_interest_ratio,

        -- Actual fee ratio (based on real interest)
        CASE WHEN f.contract_amount > 0
             THEN (f.haircut_amount / f.contract_amount)
                  + ((f.haircut_amount + f.interest) / f.contract_amount - f.haircut_amount / f.contract_amount)
                    * (1 - COALESCE(b.bad_debt_rate, 0))
             ELSE NULL
        END AS actual_fee_ratio_real,

        -- Actual fee ratio (based on fixed 0.3% daily interest)
        CASE WHEN f.contract_amount > 0
             THEN (f.haircut_amount / f.contract_amount)
                  + (0.003 * b.loan_cycle - f.haircut_amount / f.contract_amount)
                    * (1 - COALESCE(b.bad_debt_rate, 0))
             ELSE NULL
        END AS actual_fee_ratio_fixed,

        -- Fee per cycle ratio (total fee / (contract_amount * loan_cycle))
        CASE WHEN f.cycle_contract > 0
             THEN (f.haircut_amount + f.interest) / f.cycle_contract
             ELSE NULL
        END AS fee_per_cycle_ratio

    FROM ind.ba_bad_debt_rate_lookup b
    LEFT JOIN fee_summary f
        ON DATE(b.grant_month) = DATE(f.issue_month)
        AND b.product_tag = f.product_tag
        AND b.period_tag = f.period_tag
        AND b.grant_strategy = f.grant_strategy
        AND b.loan_cycle = f.loan_cycle
        AND b.loan_cycle < 9999
)

-- ============================================================================
-- Query 1: Aggregate by month + grant_strategy (meaningful short names)
-- ============================================================================
-- SELECT
--     grant_month,
--     grant_strategy,
--     SUM(actual_fee_ratio_real * contract_amount) / NULLIF(SUM(contract_amount), 0) AS real_fee,
--     SUM(actual_fee_ratio_fixed * contract_amount) / NULLIF(SUM(contract_amount), 0) AS fixed_fee,
--     SUM(fee_per_cycle_ratio * contract_amount) / NULLIF(SUM(contract_amount), 0) AS cycle_fee,
--     SUM(bad_debt_rate * contract_amount) / NULLIF(SUM(contract_amount), 0) AS bad_rate,
--     SUM(contract_amount) AS amount
-- FROM detail_with_metrics
-- WHERE contract_amount > 0
-- GROUP BY grant_month, grant_strategy
-- ORDER BY grant_month DESC, grant_strategy;

-- ============================================================================
-- Query 2: Aggregate by grant_month + grant_strategy + product_tag (new)
-- ============================================================================
SELECT
    grant_month,
    grant_strategy,
    product_tag,
    SUM(actual_fee_ratio_real * contract_amount) / NULLIF(SUM(contract_amount), 0) AS real_fee,
    SUM(actual_fee_ratio_fixed * contract_amount) / NULLIF(SUM(contract_amount), 0) AS fixed_fee,
    SUM(fee_per_cycle_ratio * contract_amount) / NULLIF(SUM(contract_amount), 0) AS cycle_fee,
    SUM(bad_debt_rate * contract_amount) / NULLIF(SUM(contract_amount), 0) AS bad_rate,
    SUM(contract_amount) AS amount
FROM detail_with_metrics
WHERE contract_amount > 0
GROUP BY grant_month, grant_strategy, product_tag
ORDER BY grant_month DESC, grant_strategy, product_tag;'''
df1 = pq.submit_query(sql1)
# -*- coding: utf-8 -*-
"""
复贷进件量预估系统
基于历史MOB转化率和首贷放款量，预估当月和下个月的复贷进件量
"""

import pandas as pd
import numpy as np
import requests
import json
import re
import time
import base64
import math
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# ================================================
# 1. 数据库连接类
# ================================================
class PrestoQuery:
    def __init__(self):
        self.headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"}

    def login_process(self):
        self.sess = requests.session()
        self.sess.keep_alive = False
        post_url = 'https://dino-manage-auth-ina.samir.co.id/login?callback=http%3A%2F%2Fdata.samir.co.id%2Fdataworks-development%2Foauth%2Flogin%3Freferer%3Dhttps%253A%252F%252Fdata.samir.co.id%252Fdata-pc-bdopr-fe%252Fhoc-inquiry%252Findex&authsource=dino&username=erik@bigdata&password=Jy6856658!'
        log_res = self.sess.post(post_url, headers=self.headers, allow_redirects=False)
        print(f'登录凭证提交状态码: {log_res.status_code}')
        
        redirect_url = log_res.headers['Location']
        login_token = re.search('#samir_id=(.*)', redirect_url).group(1)
        login_url = 'http://data.samir.co.id/dataworks-development/oauth/login?referer=https%3A%2F%2Fdata.samir.co.id%2Fdata-pc-bdopr-fe%2Fhoc-inquiry%2Findex&samir_id={}&token_type=bearer&state=&expires_in=863999&scope=authority-management'.format(login_token)       
        res = self.sess.get(login_url, headers=self.headers)
        print(f'登录盘古状态码: {res.status_code}')

    def submit_query(self, query_sql, wait_sec = 2):
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
        res_json = query_res.json()
        
        if res_json.get('data', {}).get('checkError') == 'True':
            error_info = res_json['data']['checkResultList'][0]
            return f"SQL错误: {error_info.get('errorMsg', '未知错误')}"
        
        job_url = 'https://data.samir.co.id/dataworks-development/adhoc/queryPrestoJobLog'
        jobQueryId = res_json['data']['jobQueryId']
        job_payload = {"jobQueryId": jobQueryId}
        job_res = self.sess.get(job_url, headers=self.headers, params=job_payload, timeout=(3, 20))
        job_json = job_res.json()
        
        max_wait = 120
        waited = 0
        while job_json.get('data', {}).get('taskState') != 'FINISHED' and waited < max_wait:
            time.sleep(wait_sec)
            waited += wait_sec
            job_res = self.sess.get(job_url, headers=self.headers, params=job_payload, timeout=(3, 20))
            job_json = job_res.json()
            
            if job_json.get('data', {}).get('taskState') == 'FAILED':
                return f"查询失败: {job_json.get('data', {}).get('errorMessage', '未知错误')}"
        
        if job_json.get('data', {}).get('taskState') != 'FINISHED':
            return "查询超时"
        
        query_id = job_json['data']['queryId']
        statement_type = job_json['data']['statementType']

        if statement_type in ['drop', 'create']:
            return "表更新成功"
        elif statement_type in ['select']:
            result_url = 'https://data.samir.co.id/dataworks-development/adhoc/getQueryResult'
            result_payload = {'current': 1, 'size': 5000, 'queryId': query_id}
            result_res = self.sess.post(result_url, headers=self.headers, data=json.dumps(result_payload), timeout=(3, 20))
            result_json = result_res.json()
            
            if 'data' not in result_json:
                return f"获取结果失败: {result_json}"
            
            data_obj = result_json['data']
            totalrecords = data_obj.get('totalRecords', 0)
            
            if totalrecords == 0:
                return pd.DataFrame()
            
            df = pd.DataFrame()
            columns = data_obj.get('columns', [])
            records = data_obj.get('records', [])
            
            if not records:
                return pd.DataFrame()
            
            for i in range(1, math.ceil(totalrecords/5000)+1):
                current_page = i
                result_payload = {'current': current_page, 'size': 5000, 'queryId': query_id}
                result_res = self.sess.post(result_url, headers=self.headers, data=json.dumps(result_payload), timeout=(3, 20))
                result_data = result_res.json().get('data', {})
                df1 = pd.DataFrame(result_data.get('records', []), columns=columns)
                df = pd.concat([df, df1], ignore_index=True)
            return df
        
        return "未知的查询类型"

# ================================================
# 2. 配置参数
# ================================================
CONFIG = {
    "ma_window": 3,          # 移动平均窗口（3个月）
    "target_month": (datetime.now() - relativedelta(months=1)).strftime("%Y-%m"),  # 上个月作为目标月
    "forecast_months": 2,     # 预估月份数（当月+下月）
    "mob_list": list(range(1, 13)),  # MOB1~MOB12
}

# ================================================
# 3. SQL查询语句
# ================================================

# 查询1: 首贷放款量（按月份统计）
SQL_FIRST_LOAN = """

SELECT 
    date_format(release_time, '%Y-%m-01') AS first_loan_month, 
    COUNT(DISTINCT order_no) AS first_loan_cnt 
FROM dwd.dwd_loan_info
WHERE release_time IS NOT NULL
    AND release_time >= DATE('2025-01-01')
GROUP BY 1
ORDER BY 1 DESC
"""

# 查询2: 复贷进件量（按MOB分组）
SQL_RELOAN_BY_MOB = """WITH first_loan AS (
    SELECT 
        mid,
        release_time,
        order_no
    FROM dwd.dwd_loan_info
    WHERE release_time IS NOT NULL
        AND release_time >= DATE '2025-01-01'
),
reloan_base AS (
    SELECT 
        b.mid,
        app_date,
        grant_strategy,
        biz_id
    FROM ind.ba_asset_base_info b
    WHERE (b.grant_strategy = 'NEW' AND b.if_issue = 1 AND b.if_app = 1)
       OR (b.grant_strategy = 'OLD' AND b.if_app = 1 AND b.if_recall = 0)
)
SELECT 
    -- Presto  
    date_format(CAST(f.release_time AS timestamp), '%Y-%m-01') AS first_loan_month,
    date_format(CAST(r.app_date AS timestamp), '%Y-%m-01') AS reloan_month,
    
    -- 
    date_diff('month', CAST(f.release_time AS date), CAST(r.app_date AS date)) AS mob_num,
    
    COUNT(DISTINCT r.biz_id) AS reloan_apply_cnt
FROM first_loan f
INNER JOIN reloan_base r 
    ON CAST(f.mid AS BIGINT) = CAST(r.mid AS BIGINT)
WHERE date_diff('month', CAST(f.release_time AS date), CAST(r.app_date AS date)) BETWEEN 1 AND 12
GROUP BY 
    1,2,3
ORDER BY 1 DESC, 3 
"""

# ================================================
# 4. 计算移动平均转化率
# ================================================
def calc_ma_rate(rates, window=3):
    if not rates:
        return 0
    return round(np.mean(rates[-window:]), 4)

# ================================================
# 5. 主程序
# ================================================
def main():
    print("="*70)
    print("复贷进件量预估系统")
    print("="*70)
    print()
    
    # 初始化数据库连接
    pq = PrestoQuery()
    
    print("步骤1: 登录数据库...")
    pq.login_process()
    print()
    
    # 确定目标月份
    today = datetime.now()
    current_month = today.strftime("%Y-%m")
    next_month = (today + relativedelta(months=1)).strftime("%Y-%m")
    
    print(f"当前月份: {current_month}")
    print(f"目标月份: {CONFIG['target_month']}")
    print(f"预估月份: {current_month}（当月）, {next_month}（下月）")
    print()
    
    # 查询首贷放款量
    print("步骤2: 查询首贷放款量数据...")
    result = pq.submit_query(SQL_FIRST_LOAN)
    
    if isinstance(result, str):
        print(f"查询失败: {result}")
        return
    
    if result.empty:
        print("未查询到首贷放款量数据")
        return
    
    first_loan_df = result.copy()
    first_loan_dict = dict(zip(first_loan_df['first_loan_month'], first_loan_df['first_loan_cnt'].astype(int)))
    print(f"查询到 {len(first_loan_dict)} 个月的首贷放款数据")
    print(f"首贷放款量范围: {min(first_loan_dict.values())} ~ {max(first_loan_dict.values())}")
    print()
    
    # 查询复贷进件量（按MOB分组）
    print("步骤3: 查询复贷进件量数据...")
    result = pq.submit_query(SQL_RELOAN_BY_MOB)
    
    if isinstance(result, str):
        print(f"查询失败: {result}")
        return
    
    if result.empty:
        print("未查询到复贷进件量数据")
        return
    
    reloan_df = result.copy()
    reloan_df['mob_num'] = reloan_df['mob_num'].astype(int)
    reloan_df['reloan_apply_cnt'] = reloan_df['reloan_apply_cnt'].astype(int)
    print(f"查询到 {len(reloan_df)} 条复贷进件数据")
    print()
    
    # 计算各MOB的转化率
    print("步骤4: 计算各MOB历史转化率...")
    mob_rates = {}
    ma_window = CONFIG['ma_window']
    
    for mob in CONFIG['mob_list']:
        mob_data = reloan_df[reloan_df['mob_num'] == mob].sort_values('first_loan_month', ascending=False)
        
        if mob_data.empty:
            continue
        
        rates = []
        for _, row in mob_data.iterrows():
            first_cnt = first_loan_dict.get(row['first_loan_month'], 0)
            if first_cnt > 0:
                rate = row['reloan_apply_cnt'] / first_cnt
                rates.append(rate)
        
        if rates:
            mob_rates[mob] = rates
            ma_rate = calc_ma_rate(rates, ma_window)
            print(f"  MOB{mob:2d}: 历史{len(rates)}期, MA{ma_window}转化率={ma_rate:.2%}")
    
    print()
    
    # 生成预估结果
    print("步骤5: 生成复贷进件量预估...")
    print("-" * 70)
    
    forecast_results = []
    
    # 预估当月和下个月的复贷进件量
    for target in [current_month, next_month]:
        print(f"\n{target} 月复贷进件预估:")
        print(f"{'MOB':<8} {'转化率':<10} {'对应首贷月':<12} {'首贷量':<10} {'预估进件':<10}")
        print("-" * 50)
        
        month_total = 0
        
        for mob in CONFIG['mob_list']:
            if mob not in mob_rates:
                continue
            
            rates = mob_rates[mob]
            ma_rate = calc_ma_rate(rates, ma_window)
            
            # 计算对应的首贷月份（MOB n → 首贷月份 = 目标月份 - n个月）
            target_date = datetime.strptime(target, "%Y-%m")
            cohort_date = target_date - relativedelta(months=mob)
            cohort_month = cohort_date.strftime("%Y-%m")
            
            # 获取该首贷月份的首贷放款量
            cohort_first_loan = first_loan_dict.get(cohort_month, 0)
            
            # 预估复贷进件量
            if cohort_first_loan > 0 and ma_rate > 0:
                estimate_apply = int(cohort_first_loan * ma_rate)
                month_total += estimate_apply
            else:
                estimate_apply = 0
            
            forecast_results.append({
                '预估月份': target,
                'MOB周期': f'MOB{mob}',
                '移动平均转化率': ma_rate,
                '对应首贷月份': cohort_month,
                '首贷放款量': cohort_first_loan,
                '预估复贷进件量': estimate_apply
            })
            
            print(f"MOB{mob:<5} {ma_rate:>8.2%}   {cohort_month:<12} {cohort_first_loan:>8,}   {estimate_apply:>8,}")
        
        print("-" * 50)
        print(f"{'合计':<8} {'':<10} {'':<12} {'':<10} {month_total:>8,}")
    
    print()
    
    # 导出结果
    print("步骤6: 导出预估结果...")
    
    df_forecast = pd.DataFrame(forecast_results)
    
    # 创建透视表
    pivot_df = df_forecast.pivot_table(
        index='MOB周期',
        columns='预估月份',
        values='预估复贷进件量',
        aggfunc='sum'
    ).reset_index()
    
    # 添加转化率和首贷信息
    summary_df = df_forecast[df_forecast['预估月份'] == current_month][
        ['MOB周期', '移动平均转化率', '对应首贷月份', '首贷放款量']
    ].merge(
        pivot_df,
        on='MOB周期'
    )
    
    # 保存Excel（多个sheet）
    output_file = f"复贷进件量预估_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Sheet1: 透视表
        summary_df.to_excel(writer, sheet_name='MOB透视表', index=False)
        
        # Sheet2: 明细数据
        df_forecast.to_excel(writer, sheet_name='预估明细', index=False)
        
        # Sheet3: 首贷历史数据
        first_loan_df.to_excel(writer, sheet_name='首贷历史', index=False)
    
    print(f"已导出: {output_file}")
    print(f"  - Sheet 'MOB透视表': 各MOB预估汇总")
    print(f"  - Sheet '预估明细': 详细预估数据")
    print(f"  - Sheet '首贷历史': 历史首贷放款量")
    print()
    
    print("="*70)
    print("预估完成！")
    print("="*70)

if __name__ == "__main__":
    main()

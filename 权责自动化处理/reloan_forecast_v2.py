# -*- coding: utf-8 -*-
"""
复贷进件量预估系统 v2
基于历史MOB转化率和首贷放款量，预估当月和下个月的复贷进件量

【计算方法说明】
1. 移动平均（MA）: MA(n) = (X(t) + X(t-1) + ... + X(t-n+1)) / n
   - 使用最近n个月的转化率计算平均值作为预估转化率
   
2. 转化率 = 复贷进件数 / 首贷放款量

3. 预估复贷进件量 = 首贷放款量 × 预估转化率 × 调整系数
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
    "forecast_months": 2,     # 预估月份数（当月+下月）
    "mob_list": list(range(1, 13)),  # MOB1~MOB12
    "adjustment_factor": 1.0,  # 调整系数（可手动修改，例如0.95表示下调5%）
    "use_mock_data": True,    # 是否使用模拟数据（数据库无数据时自动启用）
}

# ================================================
# 3. 模拟数据生成器
# ================================================
def generate_mock_data():
    """
    生成模拟数据用于测试和演示
    实际使用时替换为数据库查询结果
    """
    print("⚠️  使用模拟数据进行预估（数据库暂无数据）")
    print()
    
    # 模拟首贷放款量（2025-01 ~ 2026-04）
    first_loan_mock = {
        "2025-01": 10000,
        "2025-02": 11000,
        "2025-03": 12000,
        "2025-04": 13000,
        "2025-05": 14000,
        "2025-06": 15000,
        "2025-07": 16000,
        "2025-08": 17000,
        "2025-09": 18000,
        "2025-10": 19000,
        "2025-11": 20000,
        "2025-12": 21000,
        "2026-01": 22000,
        "2026-02": 23000,
        "2026-03": 24000,
        "2026-04": 25000,
    }
    
    # 模拟复贷进件数据（按首贷月份和MOB分组）
    # 格式：{(首贷月份, MOB): 复贷进件数}
    reloan_mock = {}
    
    # 基于实际业务规律生成模拟数据
    for first_month, first_cnt in first_loan_mock.items():
        for mob in range(1, 13):
            # 复贷转化率规律：
            # MOB1: 8-10%
            # MOB2: 12-14%
            # MOB3: 10-12%
            # MOB4: 7-9%
            # MOB5: 5-7%
            # MOB6: 3-5%
            # MOB7-12: 逐渐下降
            
            if mob == 1:
                base_rate = np.random.uniform(0.08, 0.10)
            elif mob == 2:
                base_rate = np.random.uniform(0.12, 0.14)
            elif mob == 3:
                base_rate = np.random.uniform(0.10, 0.12)
            elif mob == 4:
                base_rate = np.random.uniform(0.07, 0.09)
            elif mob == 5:
                base_rate = np.random.uniform(0.05, 0.07)
            elif mob == 6:
                base_rate = np.random.uniform(0.03, 0.05)
            else:
                base_rate = np.random.uniform(0.01, 0.03)
            
            # 计算复贷进件数
            reloan_cnt = int(first_cnt * base_rate)
            
            # 计算复贷月份
            first_date = datetime.strptime(first_month, "%Y-%m")
            reloan_date = first_date + relativedelta(months=mob)
            reloan_month = reloan_date.strftime("%Y-%m")
            
            # 只保留2025-07之前的复贷数据（避免未来数据）
            if reloan_date <= datetime(2026, 4, 30):
                key = (first_month, mob)
                reloan_mock[key] = {
                    'first_loan_month': first_month,
                    'reloan_month': reloan_month,
                    'mob_num': mob,
                    'reloan_apply_cnt': reloan_cnt,
                    'first_loan_cnt': first_cnt
                }
    
    # 转换为DataFrame
    reloan_df = pd.DataFrame(list(reloan_mock.values()))
    
    # 创建首贷DataFrame
    first_loan_df = pd.DataFrame([
        {'first_loan_month': k, 'first_loan_cnt': v}
        for k, v in first_loan_mock.items()
    ])
    
    return first_loan_df, reloan_df

# ================================================
# 4. SQL查询语句（数据库有数据时使用）
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
    -- Presto日期格式转换
    date_format(CAST(f.release_time AS timestamp), '%Y-%m-01') AS first_loan_month,
    date_format(CAST(r.app_date AS timestamp), '%Y-%m-01') AS reloan_month,
    
    -- 计算MOB月份差
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
# 5. 计算移动平均转化率（带详细过程）
# ================================================
def calc_ma_rate_with_detail(rates, window=3):
    """
    计算移动平均转化率
    
    【计算公式】
    MA(n) = (X(t) + X(t-1) + ... + X(t-n+1)) / n
    
    【参数说明】
    - rates: 历史转化率列表（按时间倒序）
    - window: 移动平均窗口大小
    
    【返回值】
    - ma_rate: 移动平均转化率
    - detail: 计算过程详情
    """
    if not rates:
        return 0, "无历史数据"
    
    # 取最近window个月的数据
    recent_rates = rates[:window]
    detail_parts = []
    
    detail_parts.append(f"历史转化率（最新{len(rates)}期）: {[f'{r:.4f}' for r in rates]}")
    detail_parts.append(f"取最近 {min(window, len(rates))} 期: {[f'{r:.4f}' for r in recent_rates]}")
    detail_parts.append(f"求和: {' + '.join([f'{r:.4f}' for r in recent_rates])} = {sum(recent_rates):.4f}")
    detail_parts.append(f"除以期数 {len(recent_rates)}: {sum(recent_rates):.4f} / {len(recent_rates)} = {sum(recent_rates)/len(recent_rates):.4f}")
    
    ma_rate = round(sum(recent_rates) / len(recent_rates), 4)
    detail_parts.append(f"→ MA{window}转化率 = {ma_rate:.4f} ({ma_rate:.2%})")
    
    return ma_rate, " | ".join(detail_parts)

# ================================================
# 6. 主程序
# ================================================
def main():
    print("="*70)
    print("复贷进件量预估系统 v2")
    print("="*70)
    print()
    print("【预估方法说明】")
    print("1. 移动平均(MA): 使用最近3期的转化率平均值作为预估转化率")
    print("2. 转化率 = 复贷进件数 / 首贷放款量")
    print("3. 预估复贷进件量 = 首贷放款量 × MA转化率 × 调整系数")
    print()
    
    # 显示当前配置
    print("【当前配置】")
    print(f"  移动平均窗口: {CONFIG['ma_window']} 个月")
    print(f"  调整系数: {CONFIG['adjustment_factor']} (可手动修改)")
    print(f"  MOB周期: MOB1 ~ MOB{CONFIG['mob_list'][-1]}")
    print()
    
    # 确定目标月份
    today = datetime.now()
    current_month = today.strftime("%Y-%m")
    next_month = (today + relativedelta(months=1)).strftime("%Y-%m")
    
    print(f"【预估时间】")
    print(f"  当前月份: {current_month}")
    print(f"  预估月份: {current_month}（当月）, {next_month}（下月）")
    print()
    
    # 尝试从数据库获取数据
    print("步骤1: 尝试从数据库获取数据...")
    pq = PrestoQuery()
    
    try:
        pq.login_process()
        
        # 查询首贷放款量
        print("  查询首贷放款量...")
        result = pq.submit_query(SQL_FIRST_LOAN)
        
        if isinstance(result, str):
            print(f"    警告: {result}")
            first_loan_df = None
        elif result.empty:
            print("    警告: 数据库无首贷放款量数据")
            first_loan_df = None
        else:
            first_loan_df = result.copy()
            print(f"    ✓ 查询到 {len(first_loan_df)} 个月的首贷数据")
        
        # 查询复贷进件量
        print("  查询复贷进件量...")
        result = pq.submit_query(SQL_RELOAN_BY_MOB)
        
        if isinstance(result, str):
            print(f"    警告: {result}")
            reloan_df = None
        elif result.empty:
            print("    警告: 数据库无复贷进件量数据")
            reloan_df = None
        else:
            reloan_df = result.copy()
            print(f"    ✓ 查询到 {len(reloan_df)} 条复贷数据")
        
    except Exception as e:
        print(f"    错误: {e}")
        first_loan_df = None
        reloan_df = None
    
    # 如果数据库无数据，使用模拟数据
    if first_loan_df is None or reloan_df is None:
        print()
        first_loan_df, reloan_df = generate_mock_data()
    
    # 转换数据格式
    first_loan_dict = dict(zip(first_loan_df['first_loan_month'], first_loan_df['first_loan_cnt'].astype(int)))
    
    if 'mob_num' in reloan_df.columns:
        reloan_df['mob_num'] = reloan_df['mob_num'].astype(int)
    if 'reloan_apply_cnt' in reloan_df.columns:
        reloan_df['reloan_apply_cnt'] = reloan_df['reloan_apply_cnt'].astype(int)
    
    print()
    print(f"首贷数据范围: {min(first_loan_dict.keys())} ~ {max(first_loan_dict.keys())}")
    print(f"首贷放款量范围: {min(first_loan_dict.values()):,} ~ {max(first_loan_dict.values()):,}")
    print()
    
    # 计算各MOB的转化率及详细计算过程
    print("步骤2: 计算各MOB历史转化率及MA值")
    print("="*70)
    
    ma_window = CONFIG['ma_window']
    adjustment_factor = CONFIG['adjustment_factor']
    mob_rates = {}
    mob_details = {}
    
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
            ma_rate, detail = calc_ma_rate_with_detail(rates, ma_window)
            mob_details[mob] = {
                'ma_rate': ma_rate,
                'adjusted_rate': ma_rate * adjustment_factor,
                'detail': detail
            }
            
            print(f"\n【MOB{mob}】")
            print(f"  {detail}")
            print(f"  调整系数: ×{adjustment_factor}")
            print(f"  调整后转化率: {ma_rate:.4f} × {adjustment_factor} = {ma_rate * adjustment_factor:.4f} ({ma_rate * adjustment_factor:.2%})")
    
    print()
    print("="*70)
    
    # 生成预估结果
    print("步骤3: 生成复贷进件量预估")
    print("="*70)
    
    forecast_results = []
    calculation_details = []
    
    # 预估当月和下个月的复贷进件量
    for target in [current_month, next_month]:
        print(f"\n\n{'='*70}")
        print(f"【{target} 月复贷进件预估】")
        print(f"{'='*70}")
        print()
        
        month_total = 0
        mob_details_list = []
        
        for mob in CONFIG['mob_list']:
            if mob not in mob_rates:
                continue
            
            rates = mob_rates[mob]
            ma_rate, _ = calc_ma_rate_with_detail(rates, ma_window)
            adjusted_rate = ma_rate * adjustment_factor
            
            # 计算对应的首贷月份（MOB n → 首贷月份 = 目标月份 - n个月）
            target_date = datetime.strptime(target, "%Y-%m")
            cohort_date = target_date - relativedelta(months=mob)
            cohort_month = cohort_date.strftime("%Y-%m")
            
            # 获取该首贷月份的首贷放款量
            cohort_first_loan = first_loan_dict.get(cohort_month, 0)
            
            # 预估复贷进件量
            if cohort_first_loan > 0 and adjusted_rate > 0:
                estimate_apply = int(cohort_first_loan * adjusted_rate)
                month_total += estimate_apply
            else:
                estimate_apply = 0
                adjusted_rate = 0
            
            forecast_results.append({
                '预估月份': target,
                'MOB周期': f'MOB{mob}',
                '原始MA转化率': ma_rate,
                '调整系数': adjustment_factor,
                '调整后转化率': adjusted_rate,
                '对应首贷月份': cohort_month,
                '首贷放款量': cohort_first_loan,
                '预估复贷进件量': estimate_apply
            })
            
            mob_details_list.append({
                'mob': mob,
                'cohort_month': cohort_month,
                'cohort_first_loan': cohort_first_loan,
                'ma_rate': ma_rate,
                'adjusted_rate': adjusted_rate,
                'estimate': estimate_apply
            })
            
            # 记录计算过程
            calc_str = f"{target}月 MOB{mob}: {cohort_first_loan:,} × {adjusted_rate:.4f} = {estimate_apply:,}"
            calculation_details.append(calc_str)
        
        # 打印详细计算表
        print(f"\n{'MOB':<8} {'首贷月份':<12} {'首贷量':<10} {'MA转化率':<12} {'调整系数':<10} {'调整后':<12} {'预估进件':<10}")
        print("-" * 74)
        
        for d in mob_details_list:
            print(f"MOB{d['mob']:<5} {d['cohort_month']:<12} {d['cohort_first_loan']:>8,}   {d['ma_rate']:>9.2%}   {adjustment_factor:>8.2f}   {d['adjusted_rate']:>9.2%}   {d['estimate']:>8,}")
        
        print("-" * 74)
        print(f"{'合计':<8} {'':<12} {'':<10} {'':<12} {'':<10} {'':<12} {month_total:>8,}")
        print()
        
        # 打印计算公式
        print("【计算公式】")
        for calc in calculation_details[-len(mob_details_list):]:
            print(f"  {calc}")
    
    print()
    print("="*70)
    
    # 导出结果
    print("步骤4: 导出预估结果...")
    
    df_forecast = pd.DataFrame(forecast_results)
    
    # 创建透视表
    pivot_df = df_forecast.pivot_table(
        index='MOB周期',
        columns='预估月份',
        values='预估复贷进件量',
        aggfunc='sum'
    ).reset_index()
    
    # 添加汇总信息
    summary_df = df_forecast[df_forecast['预估月份'] == current_month][
        ['MOB周期', '原始MA转化率', '调整系数', '调整后转化率', '对应首贷月份', '首贷放款量']
    ].merge(pivot_df, on='MOB周期')
    
    # 保存Excel（多个sheet）
    output_file = f"复贷进件量预估_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Sheet1: MOB透视表
        summary_df.to_excel(writer, sheet_name='MOB透视表', index=False)
        
        # Sheet2: 预估明细
        df_forecast.to_excel(writer, sheet_name='预估明细', index=False)
        
        # Sheet3: 首贷历史
        first_loan_df.to_excel(writer, sheet_name='首贷历史', index=False)
        
        # Sheet4: 复贷明细
        reloan_df.to_excel(writer, sheet_name='复贷明细', index=False)
        
        # Sheet5: 配置参数
        config_df = pd.DataFrame([
            {'参数': '移动平均窗口', '值': CONFIG['ma_window'], '说明': '使用最近n个月的转化率平均'},
            {'参数': '调整系数', '值': CONFIG['adjustment_factor'], '说明': '手动调整转化率的乘数'},
            {'参数': 'MOB范围', '值': f'1~{CONFIG["mob_list"][-1]}', '说明': '计算的MOB周期范围'},
            {'参数': '预估月份', '值': f'{current_month}, {next_month}', '说明': '当月和下月'},
        ])
        config_df.to_excel(writer, sheet_name='配置参数', index=False)
    
    print(f"✓ 已导出: {output_file}")
    print(f"  - Sheet 'MOB透视表': 各MOB预估汇总")
    print(f"  - Sheet '预估明细': 详细预估数据")
    print(f"  - Sheet '首贷历史': 历史首贷放款量")
    print(f"  - Sheet '复贷明细': 复贷进件明细")
    print(f"  - Sheet '配置参数': 当前配置")
    print()
    
    print("="*70)
    print("预估完成！")
    print("="*70)

if __name__ == "__main__":
    main()

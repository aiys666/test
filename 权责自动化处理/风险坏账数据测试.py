# -*- coding: utf-8 -*-
import openpyxl, os, csv, sys, io
import random
import pandas as pd
import requests
import json
import re
import time
import base64
import math

# ================================================
# Part 1: 数据处理 - 从Excel读取坏账率数据
# ================================================
SRC = r"E:/岳松个人文件/嘉银工作内容的整理/01工作内容/权责分析/202605月预估/风险产品坏账.xlsx"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

wb = openpyxl.load_workbook(SRC, data_only=True)
ws = wb["Sheet1"]

COLUMN_RANGES = [
    (2,7,"常规产品（等本等息+老免息）","NEW","15D"),
    (8,11,"常规产品（等本等息+老免息）","NEW","30D"),
    (12,14,"花式-新免息","NEW","F"),
    (15,19,"本金前置","NEW","M"),
    (20,22,"无忧贷","NEW","NR"),
    (23,26,"优享贷","NEW","NF"),
    (27,29,"放心贷","NEW","NW"),
    (30,35,"常规产品（等本等息+老免息）","OLD","15D"),
    (36,39,"常规产品（等本等息+老免息）","OLD","30D"),
    (40,45,"花式-新免息","OLD","F"),
    (46,50,"本金前置","OLD","M"),
    (51,54,"无忧贷","OLD","NR"),
    (55,59,"优享贷","OLD","NF"),
    (60,62,"放心贷","OLD","NW"),
]

PRODUCT_TAG = {
    "常规产品（等本等息+老免息）": "R",
    "花式-新免息": "F",
    "本金前置":    "M",
    "无忧贷":      "NR",
    "优享贷":      "NF",
    "放心贷":      "NW",
}

records = []
HEJI_CYCLE = 9999

for data_row in range(4, ws.max_row + 1):
    month_raw = ws.cell(data_row, 1).value
    if not month_raw:
        continue
    month_str = str(month_raw).strip()[:10]

    for col_s, col_e, product_cn, grant, period in COLUMN_RANGES:
        pt = PRODUCT_TAG[product_cn]
        tenure_list = []
        for c in range(col_s, col_e + 1):
            v3 = ws.cell(3, c).value
            if v3 is None:
                continue
            val3 = str(v3).strip()
            if val3 == "":
                continue
            if val3 in ("合计","总计","合计_1","合计_2"):
                tenure_list.append((c, HEJI_CYCLE))
            else:
                num = "".join(ch for ch in val3 if ch.isdigit())
                if num:
                    tenure_list.append((c, int(num)))

        for t_col, t_days in tenure_list:
            cell_val = ws.cell(data_row, t_col).value
            if cell_val is None:
                bdr = "NULL"
            elif isinstance(cell_val, (int, float)):
                bdr = str(round(float(cell_val), 10))
            else:
                cs = str(cell_val).strip()
                if cs in ("/","") or cs == "-":
                    bdr = "NULL"
                else:
                    try:
                        bdr = str(round(float(cell_val), 10))
                    except:
                        bdr = "NULL"

            records.append({
                "grant_month":    month_str,
                "product_tag":    pt,
                "period_tag":     period,
                "grant_strategy": grant,
                "loan_cycle":     t_days,
                "bad_debt_rate":  bdr,
            })

# 打印数据统计
total = len(records)
null_count = sum(1 for r in records if r["bad_debt_rate"] == "NULL")
zero_count = sum(1 for r in records if r["bad_debt_rate"] in ("0","0.0"))
num_count = total - null_count - zero_count
print(f"Total records (no dedup): {total}")
print(f"  NULL: {null_count}, =0: {zero_count}, non-zero: {num_count}")

# 生成CSV文件
csv_path = os.path.join(OUT_DIR, "risk_bad_debt_v3.csv")
with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=["grant_month","product_tag","period_tag","grant_strategy","loan_cycle","bad_debt_rate"])
    writer.writeheader()
    writer.writerows(records)
print(f"CSV generated: {csv_path}")

# ================================================
# Part 2: 数据库操作类
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

    def submit_query(self, query_sql, wait_sec = 1):
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

        if query_res.json()['data']['checkError'] == 'True':
            return query_res.json()['data']['checkResultList'][0]['query'], query_res.json()['data']['checkResultList'][0]['errorMsg']
        else:
            job_url = 'https://data.samir.co.id/dataworks-development/adhoc/queryPrestoJobLog'
            jobQueryId = query_res.json()['data']['jobQueryId']
            job_payload = {"jobQueryId": jobQueryId}
            job_res = self.sess.get(job_url, headers=self.headers, params=job_payload, timeout=(3, 20))

        while job_res.json()['data']['taskState'] != 'FINISHED' and job_res.json()['data']['windowStatus'] == 'WINDOW_RUNNING':
            time.sleep(wait_sec)
            job_res = self.sess.get(job_url, headers=self.headers, params=job_payload, timeout=(3, 20))

        query_id = job_res.json()['data']['queryId']
        statement_type = job_res.json()['data']['statementType']

        if statement_type in ['drop', 'create']:
            return "表更新成功"
        elif statement_type in ['select']:
            result_url = 'https://data.samir.co.id/dataworks-development/adhoc/getQueryResult'
            result_payload = {'current': 1, 'size': 1000, 'queryId': query_id}
            result_res = self.sess.post(result_url, headers=self.headers, data=json.dumps(result_payload), timeout=(3, 20))

            totalrecords = result_res.json()['data']['totalRecords']
            df = pd.DataFrame()
            for i in range(1, math.ceil(totalrecords/1000)+1):
                current_page = i
                result_payload = {'current': current_page, 'size': 1000, 'queryId': query_id}
                result_res = self.sess.post(result_url, headers=self.headers, data=json.dumps(result_payload),timeout=(3, 20))
                df1 = pd.DataFrame(result_res.json()['data']['records'], columns=result_res.json()['data']['columns'])
                df = pd.concat([df, df1])
            return df

# ================================================
# Part 3: 执行数据库操作
# ================================================
print("\n" + "="*60)
print("开始连接数据库并执行操作...")
print("="*60)

# 初始化数据库连接
pq = PrestoQuery()
pq.login_process()

# 步骤1: 清空数据表
print("\n步骤1: 清空数据表 ind.ba_bad_debt_rate_lookup")
sql_delete = "DELETE from ind.ba_bad_debt_rate_lookup;"
result = pq.submit_query(sql_delete)
print(f"删除结果: {result}")

# 步骤2: 生成INSERT语句并执行
print("\n步骤2: 插入坏账率数据")
rows_sql = []
for rec in records:
    lc = rec["loan_cycle"]
    bdr = rec["bad_debt_rate"]
    rows_sql.append(
        f"  ('{rec['grant_month']}','{rec['product_tag']}','{rec['period_tag']}',"
        f"'{rec['grant_strategy']}',{lc},{bdr})"
    )

sql_insert = f"""INSERT INTO ind.ba_bad_debt_rate_lookup
  (grant_month, product_tag, period_tag, grant_strategy, loan_cycle, bad_debt_rate)
VALUES
{',\n'.join(rows_sql)};"""

result = pq.submit_query(sql_insert)
print(f"插入结果: {result}")
print(f"共插入 {len(records)} 条记录")

# ================================================
# 步骤3: 执行分析查询 - 简单高效版本
# ================================================
# 提取共用的CTE部分，避免代码重复
common_cte = '''
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
        CASE WHEN f.contract_amount > 0
             THEN f.haircut_amount / f.contract_amount
             ELSE NULL
        END AS haircut_ratio,
        CASE WHEN f.contract_amount > 0
             THEN (f.haircut_amount + f.interest) / f.contract_amount
             ELSE NULL
        END AS total_fee_ratio,
        0.003 * b.loan_cycle AS fixed_daily_interest_ratio,
        CASE WHEN f.contract_amount > 0
             THEN (f.haircut_amount / f.contract_amount)
                  + ((f.haircut_amount + f.interest) / f.contract_amount - f.haircut_amount / f.contract_amount)
                    * (1 - COALESCE(b.bad_debt_rate, 0))
             ELSE NULL
        END AS actual_fee_ratio_real,
        CASE WHEN f.contract_amount > 0
             THEN (f.haircut_amount / f.contract_amount)
                  + (0.003 * b.loan_cycle - f.haircut_amount / f.contract_amount)
                    * (1 - COALESCE(b.bad_debt_rate, 0))
             ELSE NULL
        END AS actual_fee_ratio_fixed,
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
'''

# 步骤3: 执行第一个查询（按产品分组）
print("\n步骤3: 执行查询 - 按产品分组")
sql_analysis1 = common_cte + '''
SELECT
    grant_month,
    grant_strategy,
    product_tag,
    ROUND(SUM(bad_debt_rate * contract_amount) / NULLIF(SUM(contract_amount), 0), 6) AS bad_rate,
    ROUND(SUM(actual_fee_ratio_real * contract_amount) / NULLIF(SUM(contract_amount), 0), 6) AS real_fee_rate,
    ROUND(SUM(actual_fee_ratio_fixed * contract_amount) / NULLIF(SUM(contract_amount), 0), 6) AS fixed3_fee_rate,
    ROUND(SUM(fee_per_cycle_ratio * contract_amount) / NULLIF(SUM(contract_amount), 0), 6) AS real_daily_fee_rate,
    ROUND(SUM(actual_fee_ratio_fixed * contract_amount) / NULLIF(SUM(contract_amount), 0) 
          - SUM(bad_debt_rate * contract_amount) / NULLIF(SUM(contract_amount), 0), 6) AS TR,
    SUM(contract_amount) AS amount
FROM detail_with_metrics
WHERE contract_amount > 0
GROUP BY grant_month, grant_strategy, product_tag
ORDER BY grant_month DESC, grant_strategy, product_tag;
'''

df_result1 = pq.submit_query(sql_analysis1)
print(f"   查询完成: {len(df_result1)} 条记录")
print(df_result1.head(5) if len(df_result1) > 0 else "无数据")

# 步骤4: 执行第二个查询（不按产品分组）
print("\n步骤4: 执行查询 - 按月份策略")
sql_analysis2 = common_cte + '''
SELECT
    grant_month,
    grant_strategy,
    ROUND(SUM(bad_debt_rate * contract_amount) / NULLIF(SUM(contract_amount), 0), 6) AS bad_rate,
    ROUND(SUM(actual_fee_ratio_real * contract_amount) / NULLIF(SUM(contract_amount), 0), 6) AS real_fee_rate,
    ROUND(SUM(actual_fee_ratio_fixed * contract_amount) / NULLIF(SUM(contract_amount), 0), 6) AS fixed3_fee_rate,
    ROUND(SUM(fee_per_cycle_ratio * contract_amount) / NULLIF(SUM(contract_amount), 0), 6) AS real_daily_fee_rate,
    ROUND(SUM(actual_fee_ratio_fixed * contract_amount) / NULLIF(SUM(contract_amount), 0) 
          - SUM(bad_debt_rate * contract_amount) / NULLIF(SUM(contract_amount), 0), 6) AS TR,
    SUM(contract_amount) AS amount
FROM detail_with_metrics
WHERE contract_amount > 0
GROUP BY grant_month, grant_strategy
ORDER BY grant_month DESC, grant_strategy;
'''

df_result2 = pq.submit_query(sql_analysis2)
print(f"   查询完成: {len(df_result2)} 条记录")
print(df_result2.head(5) if len(df_result2) > 0 else "无数据")

# 步骤5: 转置按月份策略的数据（NEW/OLD作为第一行，指标名称作为第二行）
print("\n步骤5: 转置按月份策略数据（NEW/OLD作为第一行，指标名称作为第二行）")
df_result2 = df_result2.set_index(['grant_month', 'grant_strategy'])

# 拆分成新客和老客
df_new2 = df_result2.xs('NEW', level='grant_strategy')
df_old2 = df_result2.xs('OLD', level='grant_strategy')

# 获取指标列表
metrics = ['bad_rate', 'real_fee_rate', 'fixed3_fee_rate', 'real_daily_fee_rate', 'TR', 'amount']

# 构建新的DataFrame，每行包含grant_month + NEW的6个指标 + OLD的6个指标
new_rows = []
for grant_month in df_new2.index.get_level_values('grant_month').unique():
    row = {'grant_month': grant_month}
    # NEW的指标
    for metric in metrics:
        row[f'NEW_{metric}'] = df_new2.loc[grant_month, metric] if metric in df_new2.columns else None
    # OLD的指标
    for metric in metrics:
        row[f'OLD_{metric}'] = df_old2.loc[grant_month, metric] if metric in df_old2.columns else None
    new_rows.append(row)

df_pivot2 = pd.DataFrame(new_rows)

# 构建多层表头
# 第一行：grant_month, NEW, NEW, NEW, NEW, NEW, NEW, OLD, OLD, OLD, OLD, OLD, OLD
# 第二行：空, bad_rate, real_fee_rate, fixed3_fee_rate, real_daily_fee_rate, TR, amount, bad_rate, real_fee_rate, fixed3_fee_rate, real_daily_fee_rate, TR, amount

header_row1 = ['grant_month'] + ['NEW'] * len(metrics) + ['OLD'] * len(metrics)
header_row2 = ['grant_month'] + metrics + metrics

# 创建带有两层表头的DataFrame
df_pivot2_multi = pd.DataFrame(
    [header_row1, header_row2] + df_pivot2.values.tolist(),
    columns=[f'col_{i}' for i in range(len(header_row1))]
)

# 实际需要的列名
final_columns = ['grant_month'] + [f'col_{i}' for i in range(1, len(header_row1))]
df_pivot2_multi.columns = final_columns

print(f"   转置完成: {len(df_pivot2)} 条记录")
print("表头预览:")
print(df_pivot2_multi.head(3))

# 步骤6: 保存结果到Excel（3个sheet）
from datetime import datetime
import glob

# 删除旧的Excel文件
old_files = glob.glob(os.path.join(OUT_DIR, "风险坏账分析结果*.xlsx"))
for old_file in old_files:
    try:
        os.remove(old_file)
        print(f"   已删除旧文件: {os.path.basename(old_file)}")
    except:
        pass

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_path = os.path.join(OUT_DIR, f"风险坏账分析结果_{timestamp}.xlsx")
with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
    df_result1.to_excel(writer, sheet_name='按产品分组', index=False)
    df_result2.reset_index().to_excel(writer, sheet_name='按月份策略', index=False)
    
    # 直接保存df_pivot2，不要多层表头，去掉多余的列名行
    # 重新构建带有正确双层表头的DataFrame
    df_final = df_pivot2.copy()
    
    # 创建MultiIndex表头
    headers_top = [''] + ['NEW'] * len(metrics) + ['OLD'] * len(metrics)
    headers_bottom = ['grant_month'] + metrics + metrics
    
    # 直接设置正确的列名，不带col_
    col_names = []
    for i in range(len(headers_top)):
        if i == 0:
            col_names.append('grant_month')
        else:
            col_names.append(f"{headers_top[i]}_{headers_bottom[i]}")
    
    df_final.columns = col_names
    
    # 现在保存，同时保留表头结构
    df_final.to_excel(writer, sheet_name='按月份策略_转置', index=False, startrow=1)
    
    # 然后在第一行手动写入NEW/OLD
    ws = writer.sheets['按月份策略_转置']
    for col_idx, val in enumerate(headers_top):
        ws.cell(row=1, column=col_idx + 1, value=val)

print(f"\n结果已保存到: {output_path}")
print(f"   - Sheet '按产品分组': {len(df_result1)} 条记录")
print(f"   - Sheet '按月份策略': {len(df_result2)} 条记录")
print(f"   - Sheet '按月份策略_转置': {len(df_pivot2)} 条记录（含多层表头）")

# ================================================
# 步骤7: 添加新的三段SQL查询
# ================================================
SQL_QUERIES = {
    'performance_history': """
        -- 业绩历史数据查询
        SELECT
    month,
    SUM(daily_avg_spend) AS daily_avg_spend,
    AVG(cps) AS cps,
    AVG(fl_pass_rate) AS fl_pass_rate,
    AVG(fl_avg_amt) AS fl_avg_amt,
    SUM(fl_issue_cnt) AS fl_issue_cnt,
    SUM(fl_contract_amt) AS fl_contract_amt,
    AVG(fl_loan_cycle) AS fl_loan_cycle,
    AVG(rl_avg_amt) AS rl_avg_amt,
    SUM(rl_issue_cnt) AS rl_issue_cnt,
    SUM(rl_pass_rate) AS rl_pass_rate,
    SUM(rl_contract_amt) AS rl_contract_amt,
    AVG(rl_loan_cycle) AS rl_loan_cycle
    FROM ind.ba_act_targets_process_m
    WHERE ba_type = 'act'
        AND month >= '2025-01'
    GROUP BY month
    ORDER BY month DESC;
    """,
    'fine_income': """
        -- 罚息收入查询（V3修正）
        SELECT
            substr(cast(a.fact_time as varchar), 1, 7) AS fact_month,
            SUM(a.fact_capital) AS fact_contract_ind,
            SUM(a.fact_interest) AS fact_interest_ind,
            SUM(a.fact_fine) AS fact_fine_ind
        FROM ods.s02_loan_repayment_detail a
        WHERE substr(cast(a.fact_time as varchar), 1, 7) >= '2025-01'
        GROUP BY substr(cast(a.fact_time as varchar), 1, 7)
        ORDER BY fact_month DESC
    """,
    'outstanding_monthly': """
        -- 在贷余额月度汇总
    SELECT
        DATE_FORMAT(CAST(data_date AS DATE), '%Y-%m') AS stat_month,
        SUM(CASE WHEN past_due <= 30 THEN outstanding ELSE 0 END) AS balance_30days,
        SUM(outstanding) AS total_outstanding,
        COUNT(DISTINCT data_date) AS data_days
    FROM ind.ind_daily_ojk_monthly_report
    WHERE CAST(data_date AS DATE) >= DATE_ADD('month', -12, CURRENT_DATE)
    GROUP BY DATE_FORMAT(CAST(data_date AS DATE), '%Y-%m')
    ORDER BY stat_month DESC;
    """
}

print("\n" + "="*60)
print("执行新增的三段SQL查询...")
print("="*60)

results = {}
for query_name, sql in SQL_QUERIES.items():
    print(f"\n正在执行: {query_name}")
    try:
        df = pq.submit_query(sql)
        results[query_name] = df
        print(f"   查询成功: {len(df)} 条记录")
        print(df.head(3))
    except Exception as e:
        print(f"   查询失败: {e}")
        results[query_name] = pd.DataFrame()

# 保存新增的结果到Excel的3个sheet页（转置后的）
timestamp2 = datetime.now().strftime("%Y%m%d_%H%M%S")
output_path2 = os.path.join(OUT_DIR, f"三段查询结果_{timestamp2}.xlsx")

with pd.ExcelWriter(output_path2, engine='openpyxl') as writer:
    for sheet_name, df in results.items():
        if len(df) > 0:
            # 转置数据，让指标作为行，月份作为列
            df_t = df.T
            df_t.columns = df_t.iloc[0]  # 使用第一行作为列名
            df_t = df_t[1:]  # 移除第一行
            df_t.reset_index(inplace=True)  # 重置索引，让原来的列名变成第一列
            df_t.rename(columns={'index': '指标'}, inplace=True)
            
            df_t.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"   已保存Sheet: {sheet_name} ({len(df_t)} 条记录，已转置)")
        else:
            pd.DataFrame([{'status': '无数据'}]).to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"   已保存Sheet: {sheet_name} (无数据)")

print(f"\n新增结果已保存到: {output_path2}")

print("\n" + "="*60)
print("所有操作完成!")
print("="*60)
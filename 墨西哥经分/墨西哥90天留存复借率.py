"""墨西哥90天留存率 & 复借率查询"""
import sys, os
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

if __name__ == "__main__":
    pq = PrestoQuery()
    pq.login()
    print("登录成功!")

    sql1 = """
        WITH first_loans AS (
            SELECT 
                DATE_TRUNC('month', t.release_time) AS issue_month,
                t.customer_id AS mid,
                t.release_time,
                DATE_ADD('day', 90, DATE(t.release_time)) AS first_loan_date_90plus
            FROM ods.s02_loan t
            INNER JOIN mx.risk_double_loan_tag rt
                ON CAST(t.camera_id AS BIGINT) = CAST(rt.biz_id AS BIGINT)
            WHERE rt.double_loan = 0
              AND t.release_time >= DATE '2026-01-01'
              AND t.state IN (1, 2, 3)
        ),
        no_overdue_90d AS (
            SELECT 
                DATE(DATE_PARSE(data_date, '%Y%m%d')) AS data_date,
                mid AS customer_id
            FROM dws.dws_risk_stgy_apply_mid_tags_his
            GROUP BY 1, 2
            HAVING MAX(curr_overdue_days) < 1
        ),
        onloan_90d AS (
            SELECT  
                DATE(DATE_PARSE(data_date, '%Y%m%d')) AS slice_date,
                customer_id
            FROM ods.s02_loan_repayment_his a1
            WHERE a1.state IN (0, 2, 4)
              AND DATE_DIFF('day', DATE(should_time), DATE_PARSE(data_date, '%Y%m%d')) <= 90
        )
        SELECT 
            a.issue_month,
            COUNT(DISTINCT a.mid) AS new_cnt,
            COUNT(DISTINCT CASE WHEN b.customer_id IS NOT NULL AND c.customer_id IS NOT NULL THEN a.mid END) AS onloan_no_ovd_cnt,
            ROUND(CAST(COUNT(DISTINCT CASE WHEN b.customer_id IS NOT NULL AND c.customer_id IS NOT NULL THEN a.mid END) AS DOUBLE) 
                / NULLIF(COUNT(DISTINCT a.mid), 0), 4) AS retention_90d_rate
        FROM first_loans a
        LEFT JOIN no_overdue_90d b
            ON a.mid = b.customer_id
           AND a.first_loan_date_90plus = b.data_date
        LEFT JOIN onloan_90d c
            ON a.mid = c.customer_id
           AND a.first_loan_date_90plus = c.slice_date
        GROUP BY 1
        ORDER BY 1
    """
    print("Step1: 执行90天留存率查询...")
    df1 = pq.query(sql1)
    
    if isinstance(df1, pd.DataFrame):
        print(f"成功，共 {len(df1)} 行数据")
        print(df1.to_string())
    else:
        print(f"失败: {df1}")

    sql2 = """
        WITH first_loans_r AS (
            SELECT 
                DATE_TRUNC('month', t.release_time) AS issue_month,
                t.customer_id AS mid,
                t.release_time,
                t.contract_amount
            FROM ods.s02_loan t
            INNER JOIN mx.risk_double_loan_tag rt
                ON CAST(t.camera_id AS BIGINT) = CAST(rt.biz_id AS BIGINT)
            WHERE rt.double_loan = 0
              AND t.release_time >= DATE '2026-01-01'
              AND t.state IN (1, 2, 3)
        ),
        reloans_r AS (
            SELECT 
                t.customer_id AS mid,
                CAST(t.camera_id AS VARCHAR) AS biz_id,
                t.release_time,
                t.contract_amount
            FROM ods.s02_loan t
            INNER JOIN mx.risk_double_loan_tag rt
                ON CAST(t.camera_id AS BIGINT) = CAST(rt.biz_id AS BIGINT)
            WHERE rt.double_loan = 1
              AND t.release_time >= DATE '2026-01-01'
              AND t.state IN (1, 2, 3)
        )
        SELECT 
            a.issue_month,
            d.exchange_rate_to_dollar,
            COUNT(DISTINCT a.mid) AS first_loan_cnt,
            COUNT(DISTINCT b.biz_id) AS reloan_bizid_cnt_90d,
            COUNT(DISTINCT b.mid) AS reloan_mid_cnt_90d,
            SUM(b.contract_amount) AS reloan_amount_90d_mxn,
            ROUND(SUM(b.contract_amount) / d.exchange_rate_to_dollar, 2) AS reloan_amount_90d_usd,
            ROUND(CAST(COUNT(DISTINCT b.biz_id) AS DOUBLE) / NULLIF(COUNT(DISTINCT a.mid), 0), 4) AS reloan_rate_biz,
            ROUND(CAST(COUNT(DISTINCT b.mid) AS DOUBLE) / NULLIF(COUNT(DISTINCT a.mid), 0), 4) AS reloan_rate_mid
        FROM first_loans_r a
        LEFT JOIN reloans_r b
            ON a.mid = b.mid
           AND b.release_time > a.release_time
           AND DATE_DIFF('day', a.release_time, b.release_time) <= 90
        LEFT JOIN dim.dim_exchange_rate_cost d 
            ON d.account_currency = 'MXN' 
           AND DATE_PARSE(d.month_id, '%Y%m') = a.issue_month
        GROUP BY 1, 2
        ORDER BY 1, 2
    """
    print("\nStep2: 执行90天复借率查询...")
    df2 = pq.query(sql2)
    
    if isinstance(df2, pd.DataFrame):
        print(f"成功，共 {len(df2)} 行数据")
        print(df2.to_string())
    else:
        print(f"失败: {df2}")

    if isinstance(df1, pd.DataFrame) and isinstance(df2, pd.DataFrame):
        out_path = os.path.join(os.path.dirname(__file__),
                               f"墨西哥90天留存复借率_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        with pd.ExcelWriter(out_path) as writer:
            df1.to_excel(writer, sheet_name="90天留存率", index=False)
            df2.to_excel(writer, sheet_name="90天复借率", index=False)
        print(f"\n数据已保存到: {out_path}")

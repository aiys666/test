"""墨西哥60/90天留存率 & 复借率查询 - SQL计算版"""
import sys, os
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

if __name__ == "__main__":
    pq = PrestoQuery()
    pq.login()
    print("登录成功!")

    sql_reloan = """
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
            COUNT(DISTINCT CASE WHEN DATE_DIFF('day', a.release_time, b.release_time) <= 60 THEN b.biz_id END) AS reloan_bizid_cnt_60d,
            COUNT(DISTINCT CASE WHEN DATE_DIFF('day', a.release_time, b.release_time) <= 60 THEN b.mid END) AS reloan_mid_cnt_60d,
            SUM(CASE WHEN DATE_DIFF('day', a.release_time, b.release_time) <= 60 THEN b.contract_amount ELSE 0 END) AS reloan_amount_60d_mxn,
            COUNT(DISTINCT CASE WHEN DATE_DIFF('day', a.release_time, b.release_time) <= 90 THEN b.biz_id END) AS reloan_bizid_cnt_90d,
            COUNT(DISTINCT CASE WHEN DATE_DIFF('day', a.release_time, b.release_time) <= 90 THEN b.mid END) AS reloan_mid_cnt_90d,
            SUM(CASE WHEN DATE_DIFF('day', a.release_time, b.release_time) <= 90 THEN b.contract_amount ELSE 0 END) AS reloan_amount_90d_mxn,
            ROUND(CAST(COUNT(DISTINCT CASE WHEN DATE_DIFF('day', a.release_time, b.release_time) <= 60 THEN b.mid END) AS DOUBLE) / NULLIF(COUNT(DISTINCT a.mid), 0), 4) AS reloan_rate_mid_60d,
            ROUND(CAST(COUNT(DISTINCT CASE WHEN DATE_DIFF('day', a.release_time, b.release_time) <= 90 THEN b.mid END) AS DOUBLE) / NULLIF(COUNT(DISTINCT a.mid), 0), 4) AS reloan_rate_mid_90d
        FROM first_loans_r a
        LEFT JOIN reloans_r b
            ON a.mid = b.mid
           AND b.release_time > a.release_time
        LEFT JOIN dim.dim_exchange_rate_cost d 
            ON d.account_currency = 'MXN' 
           AND DATE_PARSE(d.month_id, '%Y%m') = a.issue_month
        GROUP BY 1, 2
        ORDER BY 1, 2
    """
    print("执行60/90天复借率查询...")
    df_reloan = pq.query(sql_reloan)
    
    if isinstance(df_reloan, pd.DataFrame):
        print(f"成功，共 {len(df_reloan)} 行数据")
        print(df_reloan.to_string())
    else:
        print(f"失败: {df_reloan}")

    sql_retention = """
        WITH first_loans AS (
            SELECT 
                DATE_TRUNC('month', t.release_time) AS issue_month,
                t.customer_id AS mid,
                t.release_time,
                DATE_ADD('day', 60, DATE(t.release_time)) AS first_loan_date_60plus,
                DATE_ADD('day', 90, DATE(t.release_time)) AS first_loan_date_90plus
            FROM ods.s02_loan t
            INNER JOIN mx.risk_double_loan_tag rt
                ON CAST(t.camera_id AS BIGINT) = CAST(rt.biz_id AS BIGINT)
            WHERE rt.double_loan = 0
              AND t.release_time >= DATE '2026-01-01'
              AND t.state IN (1, 2, 3)
        ),
        no_overdue AS (
            SELECT 
                DATE(DATE_PARSE(data_date, '%Y%m%d')) AS data_date,
                mid AS customer_id
            FROM dws.dws_risk_stgy_apply_mid_tags_his
            GROUP BY 1, 2
            HAVING MAX(curr_overdue_days) < 1
        ),
        onloan AS (
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
            COUNT(DISTINCT CASE WHEN b60.customer_id IS NOT NULL AND c60.customer_id IS NOT NULL THEN a.mid END) AS onloan_no_ovd_cnt_60d,
            COUNT(DISTINCT CASE WHEN b90.customer_id IS NOT NULL AND c90.customer_id IS NOT NULL THEN a.mid END) AS onloan_no_ovd_cnt_90d,
            ROUND(CAST(COUNT(DISTINCT CASE WHEN b60.customer_id IS NOT NULL AND c60.customer_id IS NOT NULL THEN a.mid END) AS DOUBLE) 
                / NULLIF(COUNT(DISTINCT a.mid), 0), 4) AS retention_60d_rate,
            ROUND(CAST(COUNT(DISTINCT CASE WHEN b90.customer_id IS NOT NULL AND c90.customer_id IS NOT NULL THEN a.mid END) AS DOUBLE) 
                / NULLIF(COUNT(DISTINCT a.mid), 0), 4) AS retention_90d_rate
        FROM first_loans a
        LEFT JOIN no_overdue b60
            ON a.mid = b60.customer_id
           AND a.first_loan_date_60plus = b60.data_date
        LEFT JOIN onloan c60
            ON a.mid = c60.customer_id
           AND a.first_loan_date_60plus = c60.slice_date
        LEFT JOIN no_overdue b90
            ON a.mid = b90.customer_id
           AND a.first_loan_date_90plus = b90.data_date
        LEFT JOIN onloan c90
            ON a.mid = c90.customer_id
           AND a.first_loan_date_90plus = c90.slice_date
        GROUP BY 1
        ORDER BY 1
    """
    print("\n执行60/90天留存率查询...")
    df_retention = pq.query(sql_retention)
    
    if isinstance(df_retention, pd.DataFrame):
        print(f"成功，共 {len(df_retention)} 行数据")
        print(df_retention.to_string())
    else:
        print(f"失败: {df_retention}")

    if isinstance(df_reloan, pd.DataFrame) and isinstance(df_retention, pd.DataFrame):
        out_path = os.path.join(os.path.dirname(__file__),
                               f"墨西哥60_90天留存复借率_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        with pd.ExcelWriter(out_path) as writer:
            df_reloan.to_excel(writer, sheet_name="复借率", index=False)
            df_retention.to_excel(writer, sheet_name="留存率", index=False)
        print(f"\n数据已保存到: {out_path}")

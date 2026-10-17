"""印尼90天复借率 & 锁客率查询 - Python计算版"""
import sys, os
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from indonesia_presto import PrestoQuery
import pandas as pd

if __name__ == "__main__":
    pq = PrestoQuery()
    pq.login_process()
    print("登录成功!")

    sql = """
        SELECT 
            mid,
            issue_month,
            issue_date,
            grant_strategy,
            contract_amount_usd1
        FROM ind.ba_asset_base_info
        WHERE if_app = 1 AND if_issue = 1
          AND issue_month >= '2024-01'
        LIMIT 50000
    """
    print("查询基础数据...")
    df = pq.submit_query(sql)
    
    if not isinstance(df, pd.DataFrame):
        print(f"查询失败: {df}")
        sys.exit(1)
    print(f"查询成功，共 {len(df)} 行数据")

    df['issue_date'] = pd.to_datetime(df['issue_date'])
    df['contract_amount_usd1'] = pd.to_numeric(df['contract_amount_usd1'], errors='coerce')
    
    first_loan = df[df['grant_strategy'] == 'NEW'].copy()
    first_loan = first_loan.sort_values(['mid', 'issue_date'])
    first_loan = first_loan.drop_duplicates('mid', keep='first')
    first_loan = first_loan.rename(columns={'issue_month': 'first_loan_month', 'issue_date': 'first_loan_date', 'contract_amount_usd1': 'first_loan_amount'})
    
    reloan = df[df['grant_strategy'] != 'NEW'].copy()
    
    df_merge = pd.merge(first_loan[['mid', 'first_loan_month', 'first_loan_date', 'first_loan_amount']],
                       reloan[['mid', 'issue_date', 'contract_amount_usd1']],
                       on='mid', how='left')
    
    df_merge['days_diff'] = (df_merge['issue_date'] - df_merge['first_loan_date']).dt.days
    reloan_90d = df_merge[(df_merge['days_diff'] > 0) & (df_merge['days_diff'] <= 90)]
    
    first_loan_stats = first_loan.groupby('first_loan_month').agg(
        first_loan_user_cnt=('mid', 'nunique'),
        first_loan_amount_usd=('first_loan_amount', 'sum')
    ).reset_index()
    
    reloan_90d_stats = reloan_90d.groupby('first_loan_month').agg(
        reloan_90d_user_cnt=('mid', 'nunique'),
        reloan_90d_amount_usd=('contract_amount_usd1', 'sum')
    ).reset_index()
    
    result = first_loan_stats.merge(reloan_90d_stats, on='first_loan_month', how='left')
    
    for col in ['reloan_90d_user_cnt', 'reloan_90d_amount_usd']:
        result[col] = result[col].fillna(0)
    
    result['reloan_90d_user_rate'] = (result['reloan_90d_user_cnt'] / result['first_loan_user_cnt']).round(4)
    result['reloan_90d_amount_rate'] = (result['reloan_90d_amount_usd'] / result['first_loan_amount_usd']).round(4)

    print("\n===== 90天复借率 =====")
    print(result.to_string())

    out_path = os.path.join(os.path.dirname(__file__),
                           f"印尼90天复借率_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    result.to_excel(out_path, index=False)
    print(f"\n数据已保存到: {out_path}")

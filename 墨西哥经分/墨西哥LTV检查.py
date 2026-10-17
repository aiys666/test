"""墨西哥LTV代码全量检查 - 修正版"""
import sys, os
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

def run_ddl(pq, sql, table_name):
    print(f"\n执行DDL: {table_name}")
    try:
        result = pq.query(sql)
        if result is not None and "成功" in str(result):
            print(f"  DDL执行成功")
            return True
        elif isinstance(result, pd.DataFrame):
            if len(result) == 1 and 'result' in result.columns and result.iloc[0]['result'] == 'true':
                print(f"  DDL执行成功 (result=true)")
                return True
        print(f"  DDL执行失败: {result}")
        return False
    except Exception as e:
        print(f"  DDL异常: {e}")
        return False

def check_table(pq, table_name):
    count_sql = f"select count(*) as cnt from {table_name}"
    try:
        result = pq.query(count_sql)
        if isinstance(result, pd.DataFrame):
            cnt_val = result.iloc[0]['cnt']
            cnt = int(cnt_val)
            print(f"  表行数: {cnt}")
            
            if cnt > 0:
                sample_sql = f"select * from {table_name} limit 3"
                sample_result = pq.query(sample_sql)
                if isinstance(sample_result, pd.DataFrame):
                    print(f"  数据预览:")
                    print(sample_result.to_string())
            return cnt
    except Exception as e:
        print(f"  检查异常: {e}")
        try:
            result = pq.query(count_sql)
            print(f"  原始结果: {result}")
        except:
            pass
    return -1

if __name__ == "__main__":
    pq = PrestoQuery()
    pq.login()
    print("登录成功!")
    
    tables = [
        "mx.ys_mx_ltv_base_funnel",
        "mx.ys_mx_ltv_base_loan", 
        "mx.ys_dl_ltv_exchange_rate",
        "mx.ys_mx_ltv_ads_cost",
        "mx.ys_dl_ltv_zr",
        "mx.ys_dl_ltv_qz_danti",
        "mx.ys_dl_ltv_apply",
        "mx.ys_dl_ltv_repay",
        "mx.ys_dl_ltv_repay_order",
        "mx.ys_dl_ltv_first_loan_0511",
    ]
    
    print("\n===== 检查所有中间表数据 =====")
    results = []
    for table in tables:
        print(f"\n表: {table}")
        cnt = check_table(pq, table)
        results.append({"表": table, "行数": cnt})
    
    print("\n\n===== 检查结果汇总 =====")
    df_results = pd.DataFrame(results)
    print(df_results.to_string())
    
    out_path = os.path.join(os.path.dirname(__file__),
                           f"墨西哥LTV检查结果_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    df_results.to_excel(out_path, index=False)
    print(f"\n检查结果已保存到: {out_path}")
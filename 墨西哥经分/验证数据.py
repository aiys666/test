import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery()
pq.login()

 





tables = ['mx.ys_dl_ltv_first_loan_0511', 'mx.ys_mx_ltv_first_loan_cac', 'mx.ys_dl_ltv_doulbe_loan_0511', 'mx.ys_dl_ltv_double_loan_group', 'mx.ys_dl_ltv_double_loan_draw']
for t in tables:
    try:
        result = pq.query('select count(*) as cnt from ' + t)
        if isinstance(result, pd.DataFrame):
            print(t + ': ' + str(result.iloc[0]['cnt']) + ' 行')
        else:
            print(t + ': 返回非DataFrame - ' + str(result))
    except Exception as e:
        print(t + ': 检查失败 - ' + str(e))

print('\n首贷聚合前5行:')
result = pq.query('select * from mx.ys_mx_ltv_first_loan_cac limit 5')
if isinstance(result, pd.DataFrame):
    print(result.to_string())
else:
    print(result)

print('\n复贷聚合前5行:')
result = pq.query('select ltv_month_d, wob_d, app_channel_name_d, new_grade_level_d, double_cnt, contract_amount from mx.ys_dl_ltv_double_loan_group limit 5')
if isinstance(result, pd.DataFrame):
    print(result.to_string())
else:
    print(result)

print('\n首贷聚合字段:')
result = pq.query('select * from mx.ys_mx_ltv_first_loan_cac limit 1')
if isinstance(result, pd.DataFrame):
    print('字段列表:', list(result.columns))

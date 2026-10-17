"""墨西哥周报历史月度数据生成脚本

功能：
1. 从墨西哥Presto数据库获取月度历史数据（2025年1月1日起）
2. 计算首贷和复贷的各项指标
3. 将结果输出到Excel

输出指标：
首贷：成交金额、成交标数、笔均、通过率(0)、平均期限、预计实收息费%、砍头占比%、
      本金Vintage%(T7/T30)、本息Vintage%(T7/T30)、息费Vintage%(T7/T30)、
      投放花费、日均投放

复贷：成交金额、成交标数、笔均、进件订单数、用信率、通过率(0)、平均期限、
      预计实收息费%、砍头占比%、本金Vintage%(T7/T30)、本息Vintage%(T7/T30)、
      息费Vintage%(T7/T30)

输出文件：
墨西哥周报月度数据_{YYYYMMDD}.xlsx
"""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mexico_presto import PrestoQuery
import pandas as pd
from datetime import datetime

def get_pq():
    pq = PrestoQuery()
    pq.login()
    return pq

def exec_sql_with_retry(sql, desc, max_retries=3):
    print(f"\n{'='*60}")
    print(f"{desc}")
    print(f"{'='*60}")
    
    for retry in range(max_retries):
        pq = get_pq()
        try:
            result = pq.query(sql)
            if isinstance(result, pd.DataFrame):
                print(f"  查询完成，返回 {len(result)} 行")
            else:
                print(f"  DDL执行完成: {result}")
            return result
        except Exception as e:
            print(f"  错误 (重试 {retry + 1}/{max_retries}): {e}")
            if retry < max_retries - 1:
                time.sleep(5)
                print("  重新尝试...")
    
    print(f"  失败: 已重试 {max_retries} 次")
    return None

def main():
    print("="*60)
    print("墨西哥周报历史月度数据生成脚本")
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # ==================== 查询主数据 ====================
    print("\n查询主数据（首贷+复贷）...")
    main_df = exec_sql_with_retry("""
select
    date_trunc('month', date(r.release_time)) as ltv_month,
    case when r.is_reloan = 'new' then '首贷' when r.is_reloan = 'old' then '复贷' else '其他' end as loan_type,
    count(distinct r.camera_id) as deal_cnt,
    sum(r.contract_amount) as contract_amount,
    sum(r.haircut_amount) as haircut_amount,
    sum(r.should_interest) as should_interest,
    sum(r.t7_should_amt_4) as should_amt_t7,
    sum(r.t7_should_capit_4) as contract_t7,
    sum(r.t7_overdue_amount_4) as due_amt_t7,
    sum(r.t7_overdue_capit_4) as due_capit_t7,
    sum(r.t30_should_amt_4) as should_amt_t30,
    sum(r.t30_should_capit_4) as contract_t30,
    sum(r.t30_overdue_amount_4) as due_amt_t30,
    sum(r.t30_overdue_capit_4) as due_capit_t30,
    avg(cast(r.loan_cycle as double)) as avg_loan_cycle,
    sum(cast(r.loan_cycle as double)) as sum_loan_cycle
from mx.wxs_application_funnel r
left join ods.s02_loan t on r.camera_id = t.camera_id
where r.if_issue = 1
  and date(r.release_time) >= date '2025-01-01'
  and r.is_reloan in ('new', 'old')
group by 1, 2;
    """, "主数据查询")

    if not isinstance(main_df, pd.DataFrame):
        print("  主数据查询失败")
        return

    # ==================== 查询复贷进件数据 ====================
    print("\n查询复贷进件数据...")
    apply_df = exec_sql_with_retry("""
select
    date_trunc('month', date(r.release_time)) as ltv_month,
    count(distinct r.camera_id) as apply_cnt
from mx.wxs_application_funnel r
where r.is_reloan = 'old'
  and date(r.release_time) >= date '2025-01-01'
group by 1;
    """, "复贷进件查询")

    # ==================== 查询首贷投放花费 ====================
    print("\n查询首贷投放花费...")
    cost_df = exec_sql_with_retry("""
with channel_mapping as (
    select app_key, app_channel
    from (
        values
            ('com.tiri.mx', '2930a02e-07b9-4851-aedd-200244a62b75'),
            ('com.tengoprestamos.cash.credito.mx', '2930a02e-07b9-4851-aedd-200244a62b75'),
            ('com.prestamos.credito.peso.cashvivas', '5653600e-256f-4768-8b27-8020e16c2587'),
            ('com.cash.prestamo.yaweycredito', '56c660de-3549-4482-9ad5-0404eef0d70d'),
            ('com.cash.rapido.dinero.credito.yawey', '56c660de-3549-4482-9ad5-0404eef0d70d'),
            ('com.cash.rapido.dinero.credito.yaweycredito', '56c660de-3549-4482-9ad5-0404eef0d70d'),
            ('com.prestamo.credito.cash.loan.yawey', '56c660de-3549-4482-9ad5-0404eef0d70d'),
            ('com.mx.dinero.yawey', '56c660de-3549-4482-9ad5-0404eef0d70d'),
            ('com.cash.credito.prestamo.holapresto', 'fe939ba4-4acb-4311-82cf-cfbbd190dfb5'),
            ('com.mxprestamo.credito.cash.rapido.holapresto', 'fe939ba4-4acb-4311-82cf-cfbbd190dfb5'),
            ('id6504391085', 'fe939ba4-4acb-4311-82cf-cfbbd190dfb5'),
            ('com.voltrixcredito.prestamos', '91379659-2dc0-42d2-8205-9de6d81f7550'),
            ('com.cash.prestamos.credito.prontofondo', '026f5e80-4582-4821-847a-4665660d8451'),
            ('com.holapresto.se', 'faa92afe-b81a-4d94-ba1a-15eb9d536833'),
            ('com.holapresto.pro', 'db0d289f-d217-49ea-a889-c191776115ef'),
            ('com.holapresto.max', '4cc31ae6-937e-4fd3-bc98-862314e7cb68'),
            ('com.cash.prestamo.yaweycredito.plus', 'cdf58da5-801a-4575-9af4-a56453cea6f3'),
            ('com.cash.prestamo.yaweycredito.ultra', '9922eb08-b998-46d9-b81e-469ae4c2e0ec'),
            ('com.mexcredo.loan.mx', '002e5068-2b82-443e-9447-88ddba989753'),
            ('com.efectivo.presto.credi.tuna', '38cb07f1-21ce-47ed-b552-384381fbaa92'),
            ('com.dinero.prest.balam.plata', 'f280d23f-8d33-49c8-8aff-cbbda6045c75'),
            ('id6751942954', 'a73166d6-364d-405f-bb38-a06ba2141a0f'),
            ('com.quikpeso.credito.dinerorapido', 'a73166d6-364d-405f-bb38-a06ba2141a0f'),
            ('com.rapido.credito.mikredi', '20fbd6af-b9f8-48d4-bc30-4ad3040e7205')
    ) as t(app_key, app_channel)
)
select
    date_trunc('month', date(c.ad_date)) as ltv_month,
    sum(c.spend_usd) as spend_usd
from dwd.dwd_ads_cost c
left join channel_mapping cm
    on c.app_channel_name = cm.app_key
where cast(c.ad_date as date) >= date '2025-01-01'
group by 1;
    """, "首贷投放花费查询")

    # ==================== 数据处理 ====================
    print("\n数据处理...")
    main_df['avg_amount'] = main_df['contract_amount'] / main_df['deal_cnt']
    main_df['fee_rate'] = (main_df['haircut_amount'] + main_df['should_interest']) / main_df['contract_amount']
    main_df['haircut_rate'] = main_df['haircut_amount'] / main_df['contract_amount']
    
    main_df['principal_bad_t7'] = main_df['due_capit_t7'] / main_df['contract_t7']
    main_df['principal_bad_t30'] = main_df['due_capit_t30'] / main_df['contract_t30']
    
    main_df['principal_interest_bad_t7'] = main_df['due_amt_t7'] / main_df['should_amt_t7']
    main_df['principal_interest_bad_t30'] = main_df['due_amt_t30'] / main_df['should_amt_t30']
    
    main_df['fee_bad_t7'] = (main_df['principal_bad_t7'] * (main_df['haircut_amount'] + main_df['should_interest'])) / (main_df['haircut_amount'] + main_df['should_interest'])
    main_df['fee_bad_t30'] = (main_df['principal_bad_t30'] * (main_df['haircut_amount'] + main_df['should_interest'])) / (main_df['haircut_amount'] + main_df['should_interest'])
    
    main_df['pass_rate'] = 0
    
    if isinstance(apply_df, pd.DataFrame):
        apply_df = apply_df.rename(columns={'apply_cnt': '复贷进件数'})
        main_df = main_df.merge(apply_df, on='ltv_month', how='left')
        main_df['apply_cnt'] = main_df['复贷进件数'].fillna(0)
        main_df['usage_rate'] = main_df.apply(lambda row: row['deal_cnt'] / row['apply_cnt'] if row['loan_type'] == '复贷' and row['apply_cnt'] > 0 else 0, axis=1)
    else:
        main_df['apply_cnt'] = 0
        main_df['usage_rate'] = 0
    
    if isinstance(cost_df, pd.DataFrame):
        cost_df = cost_df.rename(columns={'spend_usd': '投放花费'})
        main_df = main_df.merge(cost_df, on='ltv_month', how='left')
        main_df['投放花费'] = main_df['投放花费'].fillna(0)
    else:
        main_df['投放花费'] = 0
    
    main_df['day_count'] = main_df['ltv_month'].dt.days_in_month
    main_df['日均投放'] = main_df['投放花费'] / main_df['day_count']
    
    # ==================== 生成首贷和复贷结果 ====================
    first_loan_df = main_df[main_df['loan_type'] == '首贷'].copy()
    double_loan_df = main_df[main_df['loan_type'] == '复贷'].copy()
    
    first_loan_df = first_loan_df[[
        'ltv_month', 'contract_amount', 'deal_cnt', 'avg_amount', 'pass_rate',
        'avg_loan_cycle', 'fee_rate', 'haircut_rate',
        'principal_bad_t7', 'principal_interest_bad_t7', 'fee_bad_t7',
        'principal_bad_t30', 'principal_interest_bad_t30', 'fee_bad_t30',
        '投放花费', '日均投放'
    ]]
    
    first_loan_df.columns = [
        '月份', '成交金额', '成交标数', '笔均', '通过率',
        '平均期限', '预计实收息费%', '砍头占比%',
        '本金Vintage_T7%', '本息Vintage_T7%', '息费Vintage_T7%',
        '本金Vintage_T30%', '本息Vintage_T30%', '息费Vintage_T30%',
        '投放花费', '日均投放'
    ]
    
    double_loan_df = double_loan_df[[
        'ltv_month', 'contract_amount', 'deal_cnt', 'avg_amount', 'apply_cnt', 'usage_rate',
        'pass_rate', 'avg_loan_cycle', 'fee_rate', 'haircut_rate',
        'principal_bad_t7', 'principal_interest_bad_t7', 'fee_bad_t7',
        'principal_bad_t30', 'principal_interest_bad_t30', 'fee_bad_t30'
    ]]
    
    double_loan_df.columns = [
        '月份', '成交金额', '成交标数', '笔均', '进件订单数', '用信率',
        '通过率', '平均期限', '预计实收息费%', '砍头占比%',
        '本金Vintage_T7%', '本息Vintage_T7%', '息费Vintage_T7%',
        '本金Vintage_T30%', '本息Vintage_T30%', '息费Vintage_T30%'
    ]
    
    first_loan_df = first_loan_df.sort_values('月份')
    double_loan_df = double_loan_df.sort_values('月份')
    
    # ==================== 输出Excel ====================
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = f"墨西哥周报月度数据_{datetime.now().strftime('%Y%m%d')}.xlsx"
    output_path = os.path.join(output_dir, output_file)
    
    print(f"\n输出Excel文件: {output_path}")
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        first_loan_df.to_excel(writer, sheet_name='首贷', index=False)
        double_loan_df.to_excel(writer, sheet_name='复贷', index=False)
    
    print("\n" + "="*60)
    print("墨西哥周报历史月度数据生成完成")
    print(f"输出文件: {output_path}")
    print(f"首贷数据: {len(first_loan_df)} 行")
    print(f"复贷数据: {len(double_loan_df)} 行")
    print("="*60)

if __name__ == "__main__":
    main()
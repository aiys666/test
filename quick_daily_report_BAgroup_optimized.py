'''
盘古3.0在提交sql时使用了base64加密，需在请求提交sql时作相应处理
20231110 分页请求结果，每页1000，循环取到所有数据结果

优化版说明：
- 保留所有原始 SQL 查询逻辑不变
- 提取 sfloat/to_num 辅助函数用于安全转换 Presto 返回的字符串值
- 把 SQL 查询组织为 build_sqls(day_delta) 函数返回字典
- 添加 None/空 DataFrame 保护
- 清理注释掉的代码（sql8, sql9_3, sql10, sql12_3, sql13, sql15_1, sql15_3 等）
- 保持日志输出
- 输出格式与原版完全一致
'''

import random
import pandas as pd
import requests
import json
import re
import time
import base64
import math
import sys
import datetime
import calendar
import logging
import os

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


def sfloat(x, default=0.0):
    """
    安全转 float；None / NaN / 无法转换时返回 default。
    Presto 返回的数值多为字符串类型，统一用此函数转换可避免异常。
    如果传入 pandas Series，取第一个值。
    """
    if x is None:
        return default
    try:
        if isinstance(x, pd.Series):
            if len(x) == 0:
                return default
            x = x.iloc[0]
        if isinstance(x, float) and math.isnan(x):
            return default
        return float(x)
    except (TypeError, ValueError):
        return default


def to_num(x, default=0):
    """
    安全转 int；None / NaN / 无法转换时返回 default。
    Presto 返回的数值多为字符串类型，统一用此函数转换可避免异常。
    如果传入 pandas Series，取第一个值。
    """
    if x is None:
        return default
    try:
        if isinstance(x, pd.Series):
            if len(x) == 0:
                return default
            x = x.iloc[0]
        if isinstance(x, float) and math.isnan(x):
            return default
        return int(float(x))
    except (TypeError, ValueError):
        return default


class PrestoQuery:

    # 定义请求头为实例变量
    def __init__(self):
        self.headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"}

    def login_process(self):
        '''
        模拟盘古登录的过程，获取重定向后url中登录的token后直接跳过重定向过程，直接访问登录url
        :return:
        '''

        # 实例化一个维持会话对象session
        self.sess = requests.session()
        self.sess.keep_alive = False

        post_url = 'https://dino-manage-auth-ina.samir.co.id/login?callback=http%3A%2F%2Fdata.samir.co.id%2Fdataworks-development%2Foauth%2Flogin%3Freferer%3Dhttps%253A%252F%252Fdata.samir.co.id%252Fdata-pc-bdopr-fe%252Fhoc-inquiry%252Findex&authsource=dino&username=wintang@bigdata&password=20010911Pai.9'
        log_res = self.sess.post(post_url, headers=self.headers, allow_redirects=False)

        print('提交登陆凭证后，请求响应状态码为：{}'.format(log_res.status_code))

        redirect_url = log_res.headers['Location']
        # 重定向相应的headers的Location属性为str，可以用正则表达式提取token信息
        login_token = re.search('#samir_id=(.*)', redirect_url).group(1)

        # 直接分析登录后页面的请求记录，token信息填充到登录请求url中，模拟跳转后的登录请求过程
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

        query_res = self.sess.post(query_url, headers=self.headers, data=json.dumps(data_sql), timeout=(3, 120))

        if query_res.json()['data']['checkError'] == 'True':
            return query_res.json()['data']['checkResultList'][0]['query'], query_res.json()['data']['checkResultList'][0]['errorMsg']
        else:  # sql检验结果未报错，继续请求job执行状态
            job_url = 'https://data.samir.co.id/dataworks-development/adhoc/queryPrestoJobLog'
            jobQueryId = query_res.json()['data']['jobQueryId']
            job_payload = {"jobQueryId": jobQueryId}
            job_res = self.sess.get(job_url, headers=self.headers, params=job_payload, timeout=(3, 120))


        while job_res.json()['data']['taskState'] != 'FINISHED' and job_res.json()['data']['windowStatus'] == 'WINDOW_RUNNING':
            time.sleep(wait_sec)
            job_res = self.sess.get(job_url, headers=self.headers, params=job_payload, timeout=(3, 120))

        query_id = job_res.json()['data']['queryId']
        statement_type = job_res.json()['data']['statementType']

        # 区分查询是建表语句还是查询语句
        if statement_type in ['drop', 'create']:
            return ("表更新成功")
        elif statement_type in ['select']:
            ####获取select的结果
            result_url = 'https://data.samir.co.id/dataworks-development/adhoc/getQueryResult'
            result_payload = {'current': 1, 'size': 1000, 'queryId': query_id}
            result_res = self.sess.post(result_url, headers=self.headers, data=json.dumps(result_payload), timeout=(3, 120))

            result_json = result_res.json()
            if result_json.get('data') is None:
                return pd.DataFrame()
            totalrecords = result_json['data']['totalRecords']
            df = pd.DataFrame()
            for i in range(1, math.ceil(totalrecords/1000)+1):
                current_page = i
                result_payload = {'current': current_page, 'size': 1000, 'queryId': query_id}
                result_res = self.sess.post(result_url, headers=self.headers, data=json.dumps(result_payload),timeout=(3, 120))
                result_json = result_res.json()
                if result_json.get('data') is None:
                    break
                df1 = pd.DataFrame(result_json['data']['records'], columns=result_json['data']['columns'])
                df = pd.concat([df, df1])
            return(df)


##################################更新日志#############################################
# 1017 更新可定义跑距今多少天的数据，即新增了day_delta参数
# 1101 更新判断时周一还是其他工作日，从而生成不同天的快报
# 230215 信审板块只有初审打标，复审做决策。同时新增进件后第二天开始仍未审批完成案件统计
# 240322 风险审批 和 逾期数据新增近7天数据，日均审批通过笔数，通过率，合同件均美元，首逾T0，T7，T7催回率
#####################################################################################

today = datetime.date.today()
yesterday = today - datetime.timedelta(days=1)
days = calendar.monthrange(yesterday.year, yesterday.month)[1]


def build_sqls(day_delta):
    """
    把所有 SQL 查询组织为字典返回。
    每个 SQL 与原版完全一致，不做任何合并或改写。
    """
    sqls = {}

    # sql1_1：当日放款（按 double_loan 拆分）
    sqls['sql1_1'] = '''
    select
    date(release_time) as release_date
    ,case when grant_strategy='NEW' then 0 when grant_strategy='OLD' then 1 end as double_loan
    ,count(biz_id) as loan_cnt
    --,round(sum(a.contract_amt)) as release_amt_idr
    ,round(sum(case when if_issue=1 then contract_amount_usd1 end)) as release_amt_usd
    ,cast(sum(case when if_issue=1 then contract_amount_usd1 end)*1.00 / count(case when if_issue=1 then biz_id end) as decimal(4,1)) as amt_per_loan 
    ,sum(contract_amount_usd1)*100.0/sum(grantcredit_amount) as limit_usage_1d
    from ind.ba_asset_base_info
    where release_time is not null 
    and date(issue_date) = current_date - interval '{day_delta}' day
    and if_issue=1
    group by 1,2
    order by 1 desc
    ;'''.format(day_delta=day_delta)

    # sql1_2：近7日放款（按 double_loan 拆分）
    sqls['sql1_2'] = '''
    select
    case when grant_strategy='NEW' then 0 when grant_strategy='OLD' then 1 end as double_loan
    ,count(biz_id) as loan_cnt
    --,round(sum(a.contract_amt)) as release_amt_idr
    ,round(sum(case when if_issue=1 then contract_amount_usd1 end)) as release_amt_usd
    ,cast(sum(case when if_issue=1 then contract_amount_usd1 end)*1.00 / count(case when if_issue=1 then biz_id end) as decimal(4,1)) as amt_per_loan 
    ,sum(contract_amount_usd1)*100.0/sum(grantcredit_amount) as limit_usage_7d
    from ind.ba_asset_base_info
    where date(issue_date) >= current_date - interval '7' day 
    and if_issue=1
    group by 1
    order by 1 desc
    ;'''

    # sql1_3：当月截至昨日放款（按 double_loan 拆分）
    sqls['sql1_3'] = '''
    SELECT
    case when grant_strategy='NEW' then 0 when grant_strategy='OLD' then 1 end as double_loan
    ,count(biz_id) as loan_cnt
    --,round(sum(a.contract_amt)) as release_amt_idr
    ,round(sum(case when if_issue=1 then contract_amount_usd1 end)) as release_amt_usd_month
    ,cast(sum(case when if_issue=1 then contract_amount_usd1 end)*1.00 / count(case when if_issue=1 then biz_id end) as decimal(4,1)) as amt_per_loan 
    from ind.ba_asset_base_info
    where issue_month = to_char(date_trunc('month',current_date),'yyyy-mm-dd')
    and if_issue=1
    group by 1
    order by 1 desc
    ;'''

    # sql2：回款
    sqls['sql2'] = '''
    select
    date(fact_time) as fact_date
    ,round(c.exchange_rate_to_dollar) as exchange_rate_to_dollar
    ,count(1) as fact_cnt
    --,round(sum(a.fact_capital + a.fact_interest + a.fact_fine)) as fact_amt_idr
    ,round(sum(a.fact_capital + a.fact_interest + a.fact_fine) / c.exchange_rate_to_dollar) as fact_amt_usd
    from ods.s02_loan_repayment_detail  a 
    left join dim.dim_exchange_rate_cost c on to_char(a.fact_time,'yyyymm') = c.month_id and account_currency = 'IDR'
    where date(a.fact_time) = current_date - interval '{day_delta}' day
    group by date(fact_time),c.exchange_rate_to_dollar
    order by 1 desc
    ;'''.format(day_delta=day_delta)

    # sql3：激活量（1d / 7d）
    sqls['sql3'] = '''
    select
    '1d' as day_gap
    ,count(distinct a.appsflyer_id) as cnt_install
    from ods.s08_appsflyer_push_data a
    where etl_date>=to_char(date_add('day',-7,current_date),'yyyymmdd')
    and a.event_name = 'install' and date(a.install_time + interval '7' hour) = current_date - interval '{day_delta}' day
    union all
    select
    '7d' as day_gap
    ,count(distinct a.appsflyer_id) as cnt_install
    from ods.s08_appsflyer_push_data a
    where etl_date>=to_char(date_add('day',-14,current_date),'yyyymmdd')
    and a.event_name = 'install' 
    and date(a.install_time + interval '7' hour) <= current_date - interval '1' day
    and date(a.install_time + interval '7' hour) >= current_date - interval '7' day
    ;
    ;'''.format(day_delta=day_delta)

    # sql4：注册量（1d / 7d）
    sqls['sql4'] = '''
    select
        '1d' as day_gap,
        count(t1.mid) as reg_cnt
    from ods.s01_mem_member_account t1
    where date(t1.reg_time) = current_date - interval '{day_delta}' day
    group by 1
    union all
    select
        '7d' as day_gap,
        count(t1.mid) as reg_cnt
    from ods.s01_mem_member_account t1
    where date(t1.reg_time) <= current_date - interval '1' day
    and date(t1.reg_time) >= current_date - interval '7' day
    group by 1
    ;
    ;'''.format(day_delta=day_delta)

    # sql5_1：当日进件（按 double_loan 拆分）
    sqls['sql5_1'] = '''
    SELECT
    app_date as apply_date
    ,case when grant_strategy='NEW' then 0 when grant_strategy='OLD' then 1 end as double_loan
    ,sum(case when if_recall=0 and is_reloan2='NEW_PURE' then if_app end) as new_pure_apply_cnt
    ,sum(case when if_recall=0 then if_app end) as apply_cnt
    ,sum(if_model_passed) as model_pass_cnt
    ,sum(if_confirm_passed_final) as confirm_pass_cnt
    ,sum(case when grant_strategy='OLD' and if_recall=0 then if_external_data_3_passed 
              when grant_strategy='NEW' then if_in_confirm_final end) as external_data_3_pass_cnt
    ,sum(case when grant_strategy='OLD' and if_recall=0 then if_in_external_data_4 
              when grant_strategy='NEW' then if_confirm_passed_final end) as in_external_data_4_cnt
    ,sum(if_external_data_4_passed) as external_data_4_pass_cnt
    from
    ind.ba_asset_base_info
    where date(app_date) = current_date - interval '{day_delta}' day  
    group by 1,2
    order by 1 desc,2
    ;'''.format(day_delta=day_delta)

    # sql5_2：近7日进件（按 double_loan 拆分）
    sqls['sql5_2'] = '''
    SELECT
    case when grant_strategy='NEW' then 0 when grant_strategy='OLD' then 1 end as double_loan
    ,sum(case when if_recall=0 then if_app end) as apply_cnt
    ,sum(case when if_recall=0 and is_reloan2='NEW_PURE' then if_app end) as new_pure_apply_cnt
    ,sum(if_model_passed) as model_pass_cnt
    ,sum(if_confirm_passed_final) as confirm_pass_cnt
    ,sum(case when grant_strategy='OLD' and if_recall=0 then if_external_data_3_passed 
              when grant_strategy='NEW' then if_in_confirm_final end) as external_data_3_pass_cnt
    ,sum(case when grant_strategy='OLD' and if_recall=0 then if_in_external_data_4 
              when grant_strategy='NEW' then if_confirm_passed_final end) as in_external_data_4_cnt
    ,sum(if_external_data_4_passed) as external_data_4_pass_cnt
    from
    ind.ba_asset_base_info
    where date(app_date) >= current_date - interval '7' day 
    group by 1
    ;'''

    # sql6：信审人效（近7天）
    sqls['sql6'] = '''
    select
    to_char(coalesce(t1.end_time,t1.claim_time,t1.start_time),'yyyy-mm-dd') as audit_date
    ,count(distinct case when approve_user_name not in ('martin','samto','indonesia_samir') and t1.end_time is not null
     then approve_user_name end) as approve_user_cnt
    ,count(distinct case when approve_user_name not in ('martin','samto','indonesia_samir') and t1.end_time is not null
     and (t1.current_processor like '%manual_first') then approve_user_name end) as fst_approve_user_cnt
        ,count(distinct case when approve_user_name not in ('martin','samto','indonesia_samir') and t1.end_time is not null
     and (t1.current_processor like '%manual_second' or t1.current_processor like '%manual_flag_decision') then approve_user_name end) as sec_approve_user_cnt
    ,count(case when t1.manual_status = 30 and (t1.current_processor like '%manual_first') then t1.biz_id end) as fst_audit_processed_case
    ,count(case when t1.manual_status != 30 and (t1.current_processor like '%manual_first') then t1.biz_id end) as fst_audit_unmanaged_case
    ,count(case when t1.manual_status = 30 and (t1.current_processor like '%manual_second' or t1.current_processor like '%manual_flag_decision') then t1.biz_id end) as sec_audit_processed_case
    ,count(case when t1.manual_status != 30 and (t1.current_processor like '%manual_second' or t1.current_processor like '%manual_flag_decision') then t1.biz_id end) as sec_audit_unmanaged_case
    from
    (   
        select
        biz_id,start_time,end_time,manual_status,claim_time,approve_result,current_processor,approve_user_name
        from ods.s05_creditx_processor_record
        where current_processor in ('first_loan_manual_first','reloan_manual_first','first_loan_manual_second','reloan_manual_second','first_loan_manual_flag_decision','reloan_manual_flag_decision')
    ) t1
    where date(coalesce(t1.end_time,t1.claim_time,t1.start_time)) between current_date -interval '7' day
     and current_date - interval '{day_delta}' day
    group by 1
    order by 1 desc
    ;'''.format(day_delta=day_delta)

    # sql6_1：进件后第二天开始仍未审批完成案件统计
    sqls['sql6_1'] = '''
    select
    count(case when status=1 then t1.biz_id end) fst_audit_unmanaged_case
    from
    (   
        select
        biz_id,start_time,end_time,manual_status,claim_time,approve_result,current_processor,approve_user_name
        from ods.s05_creditx_processor_record
        where current_processor in ('first_loan_manual_first','reloan_manual_first','first_loan_manual_second','reloan_manual_second','first_loan_manual_flag_decision','reloan_manual_flag_decision')
    ) t1
    left JOIN
    ods.s05_creditx_order t2
    on t1.biz_id=t2.biz_id
    where date(coalesce(t1.end_time,t1.claim_time,t1.start_time)) between current_date -interval '7' day
     and current_date - interval '1' day
    ;'''.format(day_delta=day_delta)

    # sql7：投放花费（1d / 7d）
    sqls['sql7'] = '''
    select 
    '1d' as day_gap
    ,sum(spend_usd_discount) as spend
    from ind.tyn_ads_cost_discount a
    where ad_date = current_date - interval '{day_delta}' day 
    union all
    select 
    '7d' as day_gap
    ,sum(spend_usd_discount) as spend
    from ind.tyn_ads_cost_discount a
    where ad_date <= current_date - interval '1' day 
    AND ad_date >= current_date - interval '7' day
    ;
    ;'''.format(day_delta=day_delta)

    # sql9_1：近7天首复贷首逾T0
    sqls['sql9_1'] = '''
    select 
    sum(case when grant_strategy='NEW' then overdue_amount_1_0 end)*100.0/sum(case when grant_strategy='NEW' then should_capital_1_0 end) as fst_t0_ovd
    ,sum(case when grant_strategy='OLD' then overdue_amount_1_0 end)*100.0/sum(case when grant_strategy='OLD' then should_capital_1_0 end) as rl_t0_ovd
    from ind.ba_asset_base_info a
    where should_cnt_1_0=1
    and (
    (product_tag_detail<>'R_30D' and date_diff('day',date(issue_date),current_date) between 16 and 22)
    or 
    (product_tag_detail='R_30D' and date_diff('day',date(issue_date),current_date) between 31 and 37)
    )
    ;'''

    # sql9_2：近7天首复贷首逾T7
    sqls['sql9_2'] = '''
    select 
    sum(case when grant_strategy='NEW' then overdue_amount_1_7 end)*100.0/sum(case when grant_strategy='NEW' then should_capital_1_7 end) as fst_t7_ovd
    ,sum(case when grant_strategy='OLD' then overdue_amount_1_7 end)*100.0/sum(case when grant_strategy='OLD' then should_capital_1_7 end) as rl_t7_ovd
    from ind.ba_asset_base_info a
    where should_cnt_1_7=1
    and (
    (product_tag_detail<>'R_30D' and date_diff('day',date(issue_date),current_date) between 23 and 29)
    or 
    (product_tag_detail='R_30D' and date_diff('day',date(issue_date),current_date) between 38 and 44)
    )
    ;'''

    # sql11：当月截至昨日业绩金额
    sqls['sql11'] = '''
    select  
    round(sum(a.contract_amount_usd1)) as cur_amt 
    ,round(sum(a.contract_amount_usd1)) as cur_amt2 
    from ind.ba_asset_base_info a  
    where to_char(a.release_time,'yyyymm') = to_char(current_date- interval '1' day,'yyyymm') and date(a.release_time) < current_date;
    '''

    # sql12_1：近1天首复贷首逾T0
    sqls['sql12_1'] = '''
    select 
    sum(case when grant_strategy='NEW' then overdue_amount_1_0 end)*100.0/sum(case when grant_strategy='NEW' then should_capital_1_0 end) as fst_t0_ovd
    ,sum(case when grant_strategy='OLD' then overdue_amount_1_0 end)*100.0/sum(case when grant_strategy='OLD' then should_capital_1_0 end) as rl_t0_ovd
    from ind.ba_asset_base_info a
    where should_cnt_1_0=1
    and (
    (product_tag_detail<>'R_30D' and date_diff('day',date(issue_date),current_date) between 16 and 16)
    or 
    (product_tag_detail='R_30D' and date_diff('day',date(issue_date),current_date) between 31 and 31)
    )
    ;'''

    # sql12_2：近1天首复贷首逾T7
    sqls['sql12_2'] = '''
        select 
    sum(case when grant_strategy='NEW' then overdue_amount_1_7 end)*100.0/sum(case when grant_strategy='NEW' then should_capital_1_7 end) as fst_t7_ovd
    ,sum(case when grant_strategy='OLD' then overdue_amount_1_7 end)*100.0/sum(case when grant_strategy='OLD' then should_capital_1_7 end) as rl_t7_ovd
    from ind.ba_asset_base_info a
    where should_cnt_1_7=1
    and (
    (product_tag_detail<>'R_30D' and date_diff('day',date(issue_date),current_date) between 23 and 23)
    or 
    (product_tag_detail='R_30D' and date_diff('day',date(issue_date),current_date) between 38 and 38)
    )
    ;'''

    # sql14：当月目标
    sqls['sql14'] = '''
    SELECT
    try_cast(floor(total_amt*exchange_rate*1.00000/ f1.exchange_rate_to_dollar) as bigint) as target_amt
    ,try_cast(floor(fl_issue_cnt+rl_issue_cnt) as bigint) as target_cnt
    from
    ind.ba_kpi_targets_m a
    LEFT JOIN 
    dim.dim_exchange_rate_cost f1 
    ON to_char(date(a.month),'yyyymm') = f1.month_id 
    AND f1.account_currency = 'IDR'
    where month=date_format(date_trunc('month', date_add('day', -1, current_date)), '%Y-%m-01') 
    '''

    # sql15_2：当日用信率（按 grant_strategy）
    sqls['sql15_2'] = '''
    SELECT
    grant_strategy
    ,sum(if_confirm_passed_num_t0)*100.0/sum(if_in_confirm_temp) as confirm_rate_1d
    from
    ind.ba_asset_base_info
    where create_date=current_date - interval '1' day 
    group by 1
    ;
    '''

    # sql15_4：近7日用信率（按 grant_strategy）
    sqls['sql15_4'] = '''
    SELECT
    grant_strategy
    ,sum(if_confirm_passed_num_t0)*100.0/sum(if_in_confirm_temp) as confirm_rate_7d
    from
    ind.ba_asset_base_info
    where create_date>=current_date - interval '7' day 
    group by 1
    ;
    '''

    # sql15_5：首贷注册 t0 转化漏斗（1d / 7d）
    sqls['sql15_5'] = '''
    SELECT
    '1d' as day_gap
    ,sum(app_cnt)*100.00/sum(reg_cnt) as t0_complete_rate
    ,sum(grantcredit_cnt)*100.00/sum(app_cnt) as t0_front_pass_rate
    ,sum(confirm_cnt)*100.00/sum(grantcredit_cnt) as t0_confirm_rate
    ,sum(pass_cnt)*100.00/sum(confirm_cnt) as t0_back_pass_rate
    ,sum(release_cnt)*100.00/sum(pass_cnt) as t0_release_rate
    ,sum(release_cnt)*100.00/sum(reg_cnt) as t0_issue_rate
    from
    ind.wl_first_loan_funnel
    where reg_date=current_date - interval '1' day
    and tn='T0'
    union all
    SELECT
    '7d' as day_gap
    ,sum(app_cnt)*100.00/sum(reg_cnt) as t0_complete_rate
    ,sum(grantcredit_cnt)*100.00/sum(app_cnt) as t0_front_pass_rate
    ,sum(confirm_cnt)*100.00/sum(grantcredit_cnt) as t0_confirm_rate
    ,sum(pass_cnt)*100.00/sum(confirm_cnt) as t0_back_pass_rate
    ,sum(release_cnt)*100.00/sum(pass_cnt) as t0_release_rate
    ,sum(release_cnt)*100.00/sum(reg_cnt) as t0_issue_rate
    from
    ind.wl_first_loan_funnel
    where reg_date>=current_date - interval '7' day
    and tn='T0'
    ;
    '''

    # sql16：首贷用户质量（1d / 7d）
    sqls['sql16'] = '''
    SELECT
    '1d' as day_gap
    ,count(case when model_score_a100_5bin<=2 then a.biz_id end)*100.00/count(model_score_a100_5bin) as a100_bin2_rate
    ,count(case when model_score_a101_10bin_ios<=3 then a.biz_id end)*100.00/count(model_score_a101_10bin_ios) as a101_bin3_rate
    ,count(case when if_issue=1 and a.new_grade_level<='2' then a.biz_id end)*100.00/count(case when if_issue=1 then a.biz_id end) as deal_top_rate
    from
    ind.ba_asset_base_info a
    left join
    ind.tyn_allconvers_detail_new b
    on a.biz_id=b.biz_id
    where a.reloan_num=1
    -- and if_issue=1
    and a.if_recall=0
    and create_date=current_date-interval '1' day
    union all
    SELECT
    '7d' as day_gap
    ,count(case when model_score_a100_5bin<=2 then a.biz_id end)*100.00/count(model_score_a100_5bin) as a100_bin2_rate
    ,count(case when model_score_a101_10bin_ios<=3 then a.biz_id end)*100.00/count(model_score_a101_10bin_ios) as a101_bin3_rate
    ,count(case when if_issue=1 and a.new_grade_level<='2' then a.biz_id end)*100.00/count(case when if_issue=1 then a.biz_id end) as deal_top_rate
    from
    ind.ba_asset_base_info a
    left join
    ind.tyn_allconvers_detail_new b
    on a.biz_id=b.biz_id
    where a.reloan_num=1
    -- and if_issue=1
    and a.if_recall=0
    and create_date >= current_date - interval '7' day
    ;
    '''

    return sqls


def day_quick_report(day_delta):

    pq = PrestoQuery()
    pq.login_process()


    log_path = 'output.log'

    file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    file_handler.setLevel(logging.INFO)
    
    # 用系统真实 stdout，不走 Python 缓冲
    sys.stdout = open(os.devnull, "w") if not os.isatty(0) else sys.stdout
    
    console_handler = logging.StreamHandler(sys.__stdout__)  # 用底层 stdout
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    console_handler.setLevel(logging.INFO)
    
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    try:
        sqls = build_sqls(day_delta)

        # ---------------- sql1_1：当日放款 ----------------
        df1_1 = pq.submit_query(sqls['sql1_1'])
        if df1_1 is None or df1_1.empty:
            loan_cnt = 0
            fst_loan_cnt = 0
            sec_loan_cnt = 0
            release_amt_usd = 0
            fst_release_amt_usd = 0
            sec_release_amt_usd = 0
            fst_amt_per_loan_1d = 0
            sec_amt_per_loan_1d = 0
            fst_limit_usage_1d = 0
            rl_limit_usage_1d = 0
        else:
            loan_cnt = sum(map(int, df1_1['loan_cnt']))
            fst_loan_cnt = sum(df1_1.loc[df1_1['double_loan'] == '0', 'loan_cnt'].astype(int))
            sec_loan_cnt = sum(df1_1.loc[df1_1['double_loan'] == '1', 'loan_cnt'].astype(int))
            release_amt_usd = sum(map(int, df1_1['release_amt_usd']))
            fst_release_amt_usd = sum(df1_1.loc[df1_1['double_loan'] == '0', 'release_amt_usd'].astype(int))
            sec_release_amt_usd = sum(df1_1.loc[df1_1['double_loan'] == '1', 'release_amt_usd'].astype(int))
            fst_amt_per_loan_1d = sum(df1_1.loc[df1_1['double_loan'] == '0', 'amt_per_loan'].astype(float))
            sec_amt_per_loan_1d = sum(df1_1.loc[df1_1['double_loan'] == '1', 'amt_per_loan'].astype(float))
            fst_limit_usage_1d = sfloat(df1_1.loc[df1_1['double_loan'] == '0', 'limit_usage_1d'].iloc[0]) if len(df1_1.loc[df1_1['double_loan'] == '0']) > 0 else 0
            rl_limit_usage_1d = sfloat(df1_1.loc[df1_1['double_loan'] == '1', 'limit_usage_1d'].iloc[0]) if len(df1_1.loc[df1_1['double_loan'] == '1']) > 0 else 0

        print('finish1_1')
        time.sleep(2)



        # ---------------- sql1_2：近7日放款 ----------------
        df1_2 = pq.submit_query(sqls['sql1_2'])
        if df1_2 is None or df1_2.empty:
            fst_loan_cnt_7d = 0
            sec_loan_cnt_7d = 0
            fst_amt_per_loan_7d = 0
            sec_amt_per_loan_7d = 0
            fst_limit_usage_7d = 0
            rl_limit_usage_7d = 0
        else:
            fst_loan_cnt_7d = int(sum(df1_2.loc[df1_2['double_loan'] == '0', 'loan_cnt'].astype(int))/7)
            sec_loan_cnt_7d = int(sum(df1_2.loc[df1_2['double_loan'] == '1', 'loan_cnt'].astype(int))/7)
            fst_amt_per_loan_7d = sum(df1_2.loc[df1_2['double_loan'] == '0', 'amt_per_loan'].astype(float))
            sec_amt_per_loan_7d = sum(df1_2.loc[df1_2['double_loan'] == '1', 'amt_per_loan'].astype(float))
            fst_limit_usage_7d = sfloat(df1_2.loc[df1_2['double_loan'] == '0', 'limit_usage_7d'].iloc[0]) if len(df1_2.loc[df1_2['double_loan'] == '0']) > 0 else 0
            rl_limit_usage_7d = sfloat(df1_2.loc[df1_2['double_loan'] == '1', 'limit_usage_7d'].iloc[0]) if len(df1_2.loc[df1_2['double_loan'] == '1']) > 0 else 0

        print('finish1_2')
        time.sleep(2)



        # ---------------- sql1_3：当月截至昨日放款 ----------------
        df1_3 = pq.submit_query(sqls['sql1_3'])
        if df1_3 is None or df1_3.empty:
            loan_cnt_month = 0
            fst_loan_cnt_month = 0
            sec_loan_cnt_month = 0
            fst_amt_per_loan_month = 0
            sec_amt_per_loan_month = 0
            release_amt_usd_month = 0
            fst_release_amt_usd_month = 0
            sec_release_amt_usd_month = 0
        else:
            loan_cnt_month = sum(map(int, df1_3['loan_cnt']))
            fst_loan_cnt_month = int(sum(df1_3.loc[df1_3['double_loan'] == '0', 'loan_cnt'].astype(int)))
            sec_loan_cnt_month = int(sum(df1_3.loc[df1_3['double_loan'] == '1', 'loan_cnt'].astype(int)))
            fst_amt_per_loan_month = sum(df1_3.loc[df1_3['double_loan'] == '0', 'amt_per_loan'].astype(float))
            sec_amt_per_loan_month = sum(df1_3.loc[df1_3['double_loan'] == '1', 'amt_per_loan'].astype(float))
            fst_release_amt_usd_month = int(sum(df1_3.loc[df1_3['double_loan'] == '0', 'release_amt_usd_month'].astype(int)))
            sec_release_amt_usd_month = int(sum(df1_3.loc[df1_3['double_loan'] == '1', 'release_amt_usd_month'].astype(int)))
            release_amt_usd_month = fst_release_amt_usd_month + sec_release_amt_usd_month

        print('finish1_3')
        time.sleep(2)



        # ---------------- sql2：回款 ----------------
        df2 = pq.submit_query(query_sql=str(sqls['sql2']))
        if df2 is None or df2.empty:
            fact_cnt = 0
            fact_amt_usd = 0
            exchange_rate_to_dollar = 0
        else:
            fact_cnt = df2.loc[0, 'fact_cnt']
            fact_amt_usd = df2.loc[0, 'fact_amt_usd']
            exchange_rate_to_dollar = df2.loc[0, 'exchange_rate_to_dollar']



        print('finish2')
        time.sleep(2)

        # ---------------- sql3：激活量 ----------------
        df3 = pq.submit_query(query_sql=str(sqls['sql3']))
        if df3 is None or df3.empty:
            cnt_install = 0
            cnt_install_7d = 0
        else:
            cnt_install = to_num(df3.loc[df3['day_gap'] == '1d', 'cnt_install'])
            cnt_install_7d = to_num(df3.loc[df3['day_gap'] == '7d', 'cnt_install'])

        print('finish3')
        time.sleep(2)

        # ---------------- sql4：注册量 ----------------
        df4 = pq.submit_query(query_sql=str(sqls['sql4']))
        if df4 is None or df4.empty:
            reg_cnt = 0
            reg_cnt_7d = 0
        else:
            reg_cnt = to_num(df4.loc[df4['day_gap'] == '1d', 'reg_cnt'])
            reg_cnt_7d = to_num(df4.loc[df4['day_gap'] == '7d', 'reg_cnt'])


        print('finish4')
        time.sleep(2)


        # ---------------- sql5_1：当日进件 ----------------
        df5_1 = pq.submit_query(query_sql=str(sqls['sql5_1']))
        if df5_1 is None or df5_1.empty:
            apply_cnt = 0
            fst_apply_cnt = pd.Series(dtype=object)
            new_pure_apply_cnt = pd.Series(dtype=object)
            sec_apply_cnt = pd.Series(dtype=object)
            fst_pre_pass_cnt = pd.Series(dtype=object)
            sec_pre_pass_cnt = pd.Series(dtype=object)
            fst_post_apply_cnt = pd.Series(dtype=object)
            sec_post_apply_cnt = pd.Series(dtype=object)
            fst_approve_cnt = 0
            sec_approve_cnt = 0
        else:
            apply_cnt = sum(map(int, df5_1['apply_cnt']))
            fst_apply_cnt = df5_1.loc[df5_1['double_loan'] == '0', 'apply_cnt']
            new_pure_apply_cnt = df5_1.loc[df5_1['double_loan'] == '0', 'new_pure_apply_cnt']
            sec_apply_cnt = df5_1.loc[df5_1['double_loan'] == '1', 'apply_cnt']
            fst_pre_pass_cnt = df5_1.loc[df5_1['double_loan'] == '0', 'model_pass_cnt']
            sec_pre_pass_cnt = df5_1.loc[df5_1['double_loan'] == '1', 'external_data_3_pass_cnt']
            fst_post_apply_cnt = df5_1.loc[df5_1['double_loan'] == '0', 'confirm_pass_cnt']
            sec_post_apply_cnt = df5_1.loc[df5_1['double_loan'] == '1', 'in_external_data_4_cnt']
            fst_approve_cnt = to_num(df5_1.loc[df5_1['double_loan'] == '0', 'external_data_4_pass_cnt'])
            sec_approve_cnt = to_num(df5_1.loc[df5_1['double_loan'] == '1', 'external_data_4_pass_cnt'])

        if fst_apply_cnt.empty:
            fst_pass_rate = 0
        elif fst_post_apply_cnt.empty:
            fst_pass_rate = 0
        else:
            fst_pass_rate = to_num(fst_pre_pass_cnt)*100 / to_num(fst_apply_cnt) * to_num(fst_approve_cnt) / to_num(fst_post_apply_cnt)

        if sec_apply_cnt.empty:
            sec_pass_rate = 0
        elif sec_post_apply_cnt.empty:
            sec_pass_rate = 0
        else:
            sec_pass_rate = to_num(sec_pre_pass_cnt)*100 / to_num(sec_apply_cnt) * to_num(sec_approve_cnt) / to_num(sec_post_apply_cnt)

        # 把 Series 形式转为 int，便于后续模板渲染
        new_pure_apply_cnt = to_num(new_pure_apply_cnt)
        fst_apply_cnt = to_num(fst_apply_cnt)
        sec_apply_cnt = to_num(sec_apply_cnt)
        fst_pre_pass_cnt = to_num(fst_pre_pass_cnt)
        sec_pre_pass_cnt = to_num(sec_pre_pass_cnt)

        print('finish5_1')
        time.sleep(2)



        # ---------------- sql5_2：近7日进件 ----------------
        df5_2 = pq.submit_query(query_sql=str(sqls['sql5_2']))
        if df5_2 is None or df5_2.empty:
            apply_cnt_7d = 0
            fst_apply_cnt_7d = pd.Series(dtype=object)
            new_pure_apply_cnt_7d = pd.Series(dtype=object)
            sec_apply_cnt_7d = pd.Series(dtype=object)
            fst_pre_pass_cnt_7d = pd.Series(dtype=object)
            sec_pre_pass_cnt_7d = pd.Series(dtype=object)
            fst_post_apply_cnt_7d = pd.Series(dtype=object)
            sec_post_apply_cnt_7d = pd.Series(dtype=object)
            fst_approve_cnt_7d = pd.Series(dtype=object)
            sec_approve_cnt_7d = pd.Series(dtype=object)
        else:
            apply_cnt_7d = sum(map(int, df5_2['apply_cnt']))
            fst_apply_cnt_7d = df5_2.loc[df5_2['double_loan'] == '0', 'apply_cnt']
            new_pure_apply_cnt_7d = df5_2.loc[df5_2['double_loan'] == '0', 'new_pure_apply_cnt']
            sec_apply_cnt_7d = df5_2.loc[df5_2['double_loan'] == '1', 'apply_cnt']
            fst_pre_pass_cnt_7d = df5_2.loc[df5_2['double_loan'] == '0', 'external_data_3_pass_cnt']
            sec_pre_pass_cnt_7d = df5_2.loc[df5_2['double_loan'] == '1', 'external_data_3_pass_cnt']
            fst_post_apply_cnt_7d = df5_2.loc[df5_2['double_loan'] == '0', 'in_external_data_4_cnt']
            sec_post_apply_cnt_7d = df5_2.loc[df5_2['double_loan'] == '1', 'in_external_data_4_cnt']
            fst_approve_cnt_7d = df5_2.loc[df5_2['double_loan'] == '0', 'external_data_4_pass_cnt']
            sec_approve_cnt_7d = df5_2.loc[df5_2['double_loan'] == '1', 'external_data_4_pass_cnt']

        if fst_apply_cnt_7d.empty:
            fst_pass_rate_7d = 0
        elif fst_approve_cnt_7d.empty:
            fst_pass_rate_7d = 0
        elif fst_post_apply_cnt_7d.empty:
            fst_pass_rate_7d = 0
        else:
            fst_pass_rate_7d = to_num(fst_pre_pass_cnt_7d)*100 / to_num(fst_apply_cnt_7d) * to_num(fst_approve_cnt_7d) / to_num(fst_post_apply_cnt_7d)

        if sec_apply_cnt_7d.empty:
            sec_pass_rate_7d = 0
        elif sec_approve_cnt_7d.empty:
            sec_pass_rate_7d = 0
        elif sec_post_apply_cnt_7d.empty:
            sec_pass_rate_7d = 0
        else:
            sec_pass_rate_7d = to_num(sec_pre_pass_cnt_7d)*100 / to_num(sec_apply_cnt_7d) * to_num(sec_approve_cnt_7d) / to_num(sec_post_apply_cnt_7d)

        # 把 Series 形式转为 int，便于后续模板渲染
        new_pure_apply_cnt_7d = to_num(new_pure_apply_cnt_7d)
        fst_apply_cnt_7d = to_num(fst_apply_cnt_7d)
        sec_apply_cnt_7d = to_num(sec_apply_cnt_7d)
        fst_pre_pass_cnt_7d = to_num(fst_pre_pass_cnt_7d)

        print('finish5_2')
        time.sleep(2)


        # ---------------- sql6：信审人效（近7天） ----------------
        sql6 = sqls['sql6']
        df6 = pq.submit_query(query_sql=str(sql6))

        if df6 is None or df6.empty:
            fst_audit_processed_case = 0
            sec_audit_processed_case = 0
            approve_user_cnt = '0'
            fst_approve_user_cnt = '0'
            sec_approve_user_cnt = '0'
        else:
            fst_audit_processed_case = df6.loc[0, 'fst_audit_processed_case']
            sec_audit_processed_case = df6.loc[0,  'sec_audit_processed_case']
            approve_user_cnt = df6.loc[0, 'approve_user_cnt']
            fst_approve_user_cnt = df6.loc[0, 'fst_approve_user_cnt']
            sec_approve_user_cnt = df6.loc[0, 'sec_approve_user_cnt']

        if approve_user_cnt == '0' or to_num(approve_user_cnt) == 0:
            perform = '0'
        else:
            perform = math.ceil((to_num(fst_audit_processed_case) + to_num(sec_audit_processed_case)) / to_num(approve_user_cnt))

        if fst_approve_user_cnt == '0' or to_num(fst_approve_user_cnt) == 0:
            fst_perform = '0'
        else:
            fst_perform = math.ceil(to_num(fst_audit_processed_case) / to_num(fst_approve_user_cnt))

        if sec_approve_user_cnt == '0' or to_num(sec_approve_user_cnt) == 0:
            sec_perform = '0'
        else:
            sec_perform = math.ceil(to_num(sec_audit_processed_case) / to_num(sec_approve_user_cnt))

        print('finish6')
        time.sleep(2)


        # ---------------- sql6_1：进件后第二天开始仍未审批完成案件统计 ----------------
        sql6_1 = sqls['sql6_1']
        df6_1 = pq.submit_query(query_sql=str(sql6_1))

        if df6_1 is None or df6_1.empty:
            fst_audit_unmanaged_case = 0
        else:
            fst_audit_unmanaged_case = sum(map(int, df6_1['fst_audit_unmanaged_case']))

        print('finish6_1')
        time.sleep(2)



        # ---------------- sql7：投放花费 ----------------
        df7 = pq.submit_query(query_sql=str(sqls['sql7']))
        if df7 is not None and len(df7) > 0:
            spend = sum(df7.loc[df7['day_gap'] == '1d', 'spend'].astype(float))
            spend_7d = sum(df7.loc[df7['day_gap'] == '7d', 'spend'].astype(float))
        else:
            spend = 0
            spend_7d = 0

        # cpi / cpr 默认值保护（避免除零）
        cpi = spend / cnt_install if cnt_install else 0
        cpr = spend / to_num(reg_cnt) if to_num(reg_cnt) else 0

        cpi_7d = spend_7d / cnt_install_7d if cnt_install_7d else 0
        cpr_7d = spend_7d / to_num(reg_cnt_7d) if to_num(reg_cnt_7d) else 0

        if fst_loan_cnt == 0:
            cps = 0
            cpd = 0
            cpk = 0
            cps_7d = 0
            cpd_7d = 0
            cpk_7d = 0
        else:
            cps = spend / fst_loan_cnt
            cpd = spend / fst_release_amt_usd
            cpk = spend / to_num(fst_pre_pass_cnt) if to_num(fst_pre_pass_cnt) else 0
            cps_7d = float(spend_7d / fst_loan_cnt_7d) if fst_loan_cnt_7d else 0
            cpd_7d = float(spend_7d / fst_amt_per_loan_7d / fst_loan_cnt_7d) if (fst_amt_per_loan_7d and fst_loan_cnt_7d) else 0
            cpk_7d = float(spend_7d / to_num(fst_pre_pass_cnt_7d)) if to_num(fst_pre_pass_cnt_7d) else 0


        print('finish7')
        time.sleep(2)

        # ---------------- sql9_1：近7天首复贷首逾T0 ----------------
        df9_1 = pq.submit_query(query_sql=str(sqls['sql9_1']))
        if df9_1 is None or df9_1.empty:
            fst_fpd_t0 = 0.0
            rl_fpd_t0 = 0.0
        else:
            fst_fpd_t0 = round(sfloat(df9_1.loc[0, 'fst_t0_ovd']), 1)
            rl_fpd_t0 = round(sfloat(df9_1.loc[0, 'rl_t0_ovd']), 1)


        # ---------------- sql9_2：近7天首复贷首逾T7 ----------------
        df9_2 = pq.submit_query(query_sql=str(sqls['sql9_2']))
        if df9_2 is None or df9_2.empty:
            fst_fpd_t7 = 0.0
            rl_fpd_t7 = 0.0
        else:
            fst_fpd_t7 = round(sfloat(df9_2.loc[0, 'fst_t7_ovd']), 1)
            rl_fpd_t7 = round(sfloat(df9_2.loc[0, 'rl_t7_ovd']), 1)


        # ---------------- sql11：当月截至昨日业绩金额 ----------------
        df11 = pq.submit_query(query_sql=str(sqls['sql11']))
        if df11 is None or df11.empty:
            cur_amt = 0
            cur_amt2 = 0
        elif df11.loc[0, 'cur_amt'] is None:
            cur_amt = 0
            cur_amt2 = 0
        else:
            cur_amt = to_num(df11.loc[0, 'cur_amt'])
            cur_amt2 = to_num(df11.loc[0, 'cur_amt2'])

        # ---------------- sql12_1：近1天首复贷首逾T0 ----------------
        df12_1 = pq.submit_query(query_sql=str(sqls['sql12_1']))
        if df12_1 is None or df12_1.empty:
            fst_fpd_t0_1d = 0.0
            rl_fpd_t0_1d = 0.0
        else:
            fst_fpd_t0_1d = round(sfloat(df12_1.loc[0, 'fst_t0_ovd']), 1)
            rl_fpd_t0_1d = round(sfloat(df12_1.loc[0, 'rl_t0_ovd']), 1)


        # ---------------- sql12_2：近1天首复贷首逾T7 ----------------
        df12_2 = pq.submit_query(query_sql=str(sqls['sql12_2']))
        if df12_2 is None or df12_2.empty:
            fst_fpd_t7_1d = 0.0
            rl_fpd_t7_1d = 0.0
        else:
            fst_fpd_t7_1d = round(sfloat(df12_2.loc[0, 'fst_t7_ovd']), 1)
            rl_fpd_t7_1d = round(sfloat(df12_2.loc[0, 'rl_t7_ovd']), 1)


        # ---------------- sql14：当月目标 ----------------
        df14 = pq.submit_query(query_sql=str(sqls['sql14']))
        if df14 is None or df14.empty:
            target_amt = 0
            target_cnt = 0
        else:
            target_amt = to_num(df14.loc[0, 'target_amt'])
            target_cnt = to_num(df14.loc[0, 'target_cnt'])
        print('finish14')


        # ---------------- sql15_2：当日用信率 ----------------
        df15_2 = pq.submit_query(query_sql=str(sqls['sql15_2']))
        if df15_2 is None or df15_2.empty:
            fst_confirm_rate_1d = 0.0
            rl_confirm_rate_1d = 0.0
        else:
            fst_confirm_rate_1d = sfloat(df15_2.loc[df15_2['grant_strategy'] == 'NEW', 'confirm_rate_1d'])
            rl_confirm_rate_1d = sfloat(df15_2.loc[df15_2['grant_strategy'] == 'OLD', 'confirm_rate_1d'])

        print('finish15_2')


        # ---------------- sql15_4：近7日用信率 ----------------
        df15_4 = pq.submit_query(query_sql=str(sqls['sql15_4']))
        if df15_4 is None or df15_4.empty:
            fst_confirm_rate_7d = 0.0
            rl_confirm_rate_7d = 0.0
        else:
            fst_confirm_rate_7d = sfloat(df15_4.loc[df15_4['grant_strategy'] == 'NEW', 'confirm_rate_7d'])
            rl_confirm_rate_7d = sfloat(df15_4.loc[df15_4['grant_strategy'] == 'OLD', 'confirm_rate_7d'])

        print('finish15_4')


        reg_to_apply_rate = to_num(new_pure_apply_cnt) * 100.0 / to_num(reg_cnt) if to_num(reg_cnt) else 0
        reg_to_apply_rate_7d = to_num(new_pure_apply_cnt_7d) * 100.0 / to_num(reg_cnt_7d) if to_num(reg_cnt_7d) else 0




        # ---------------- sql15_5：首贷注册 t0 转化漏斗 ----------------
        df15_5 = pq.submit_query(query_sql=str(sqls['sql15_5']))
        if df15_5 is None or df15_5.empty:
            t0_complete_rate_1d = 0.0
            t0_front_pass_rate_1d = 0.0
            t0_confirm_rate_1d = 0.0
            t0_back_pass_rate_1d = 0.0
            t0_release_rate_1d = 0.0
            t0_issue_rate_1d = 0.0
            t0_complete_rate_7d = 0.0
            t0_front_pass_rate_7d = 0.0
            t0_confirm_rate_7d = 0.0
            t0_back_pass_rate_7d = 0.0
            t0_release_rate_7d = 0.0
            t0_issue_rate_7d = 0.0
        else:
            t0_complete_rate_1d = sfloat(df15_5.loc[df15_5['day_gap'] == '1d', 't0_complete_rate'])
            t0_front_pass_rate_1d = sfloat(df15_5.loc[df15_5['day_gap'] == '1d', 't0_front_pass_rate'])
            t0_confirm_rate_1d = sfloat(df15_5.loc[df15_5['day_gap'] == '1d', 't0_confirm_rate'])
            t0_back_pass_rate_1d = sfloat(df15_5.loc[df15_5['day_gap'] == '1d', 't0_back_pass_rate'])
            t0_release_rate_1d = sfloat(df15_5.loc[df15_5['day_gap'] == '1d', 't0_release_rate'])
            t0_issue_rate_1d = sfloat(df15_5.loc[df15_5['day_gap'] == '1d', 't0_issue_rate'])

            t0_complete_rate_7d = sfloat(df15_5.loc[df15_5['day_gap'] == '7d', 't0_complete_rate'])
            t0_front_pass_rate_7d = sfloat(df15_5.loc[df15_5['day_gap'] == '7d', 't0_front_pass_rate'])
            t0_confirm_rate_7d = sfloat(df15_5.loc[df15_5['day_gap'] == '7d', 't0_confirm_rate'])
            t0_back_pass_rate_7d = sfloat(df15_5.loc[df15_5['day_gap'] == '7d', 't0_back_pass_rate'])
            t0_release_rate_7d = sfloat(df15_5.loc[df15_5['day_gap'] == '7d', 't0_release_rate'])
            t0_issue_rate_7d = sfloat(df15_5.loc[df15_5['day_gap'] == '7d', 't0_issue_rate'])

        print('finish15_5')


        reg_to_apply_rate = to_num(new_pure_apply_cnt) * 100.0 / to_num(reg_cnt) if to_num(reg_cnt) else 0
        reg_to_apply_rate_7d = to_num(new_pure_apply_cnt_7d) * 100.0 / to_num(reg_cnt_7d) if to_num(reg_cnt_7d) else 0


        today_dt = datetime.datetime.today()
        yestoday = today_dt - datetime.timedelta(days=1)
        timerange = calendar.monthrange(yestoday.year, yestoday.month)

        print('---1-----')
        print(exchange_rate_to_dollar)
        print(type(exchange_rate_to_dollar))

        print(type(int(exchange_rate_to_dollar)) if exchange_rate_to_dollar else 'N/A')

        print('-----1---')


        if yestoday.day == 0:
            period_finish_rate = 0
            total_finish_rate = 0
        else:
            period_finish_rate = round(cur_amt2 / (target_amt / timerange[1] * (yestoday.day)) * 100, 1) if target_amt else 0
            total_finish_rate = round(cur_amt2 / target_amt * 100, 1) if target_amt else 0

        print('finish11')

        # ---------------- sql16：首贷用户质量 ----------------
        df16 = pq.submit_query(query_sql=str(sqls['sql16']))
        if df16 is None or df16.empty:
            a100_bin2_rate_1d = 0.0
            a101_bin3_rate_1d = 0.0
            deal_top_rate_1d = 0.0
            a100_bin2_rate_7d = 0.0
            a101_bin3_rate_7d = 0.0
            deal_top_rate_7d = 0.0
        else:
            a100_bin2_rate_1d = sfloat(df16.loc[df16['day_gap'] == '1d', 'a100_bin2_rate'])
            a101_bin3_rate_1d = sfloat(df16.loc[df16['day_gap'] == '1d', 'a101_bin3_rate'])
            deal_top_rate_1d = sfloat(df16.loc[df16['day_gap'] == '1d', 'deal_top_rate'])

            a100_bin2_rate_7d = sfloat(df16.loc[df16['day_gap'] == '7d', 'a100_bin2_rate'])
            a101_bin3_rate_7d = sfloat(df16.loc[df16['day_gap'] == '7d', 'a101_bin3_rate'])
            deal_top_rate_7d = sfloat(df16.loc[df16['day_gap'] == '7d', 'deal_top_rate'])

        print('finish16')

        reprot_date = (datetime.date.today() - datetime.timedelta(days=day_delta - 1)).strftime('%Y-%m-%d')
        Daily_completion_required = (target_amt - cur_amt) / (days - yesterday.day) if (days - yesterday.day) else 0

        quick_report = '''【{reprot_date} 印尼快报】
    1. 成交：昨日成交{loan_cnt:,}笔, {release_amt_usd:.1f}w美元; 首贷{fst_loan_cnt:,}笔, {fst_release_amt_usd:,.1f}w美元, 合同件均{fst_amt_per_loan_1d:.1f}美元; 复贷{sec_loan_cnt:,}笔, {sec_release_amt_usd:,.1f}w美元, 合同件均{sec_amt_per_loan_1d:.1f}美元
    (月累计成交{loan_cnt_month:,}笔, {release_amt_usd_month:,.1f}w美元; 首贷{fst_loan_cnt_month:,}笔, {fst_release_amt_usd_month:,.1f}w美元, 合同件均{fst_amt_per_loan_month:.1f}美元; 复贷{sec_loan_cnt_month:,}笔, {sec_release_amt_usd_month:,.1f}w美元, 合同件均{sec_amt_per_loan_month:.1f}美元;
     月目标成交{target_cnt:,.0f}笔, {target_amt:,.1f}w美元, 当前金额达成率{period_finish_rate}%, 后续日均需完成{Daily_completion_required:,.1f}w美元)
    
    2. 投放：投放{spend:.1f}w美元, 激活量{cnt_install:,}, 注册量{reg_cnt:,}, 流水CPI {cpi}, 流水CPR {cpr}, 流水CPK {cpk}, 流水CPS {cps}, 流水CPD {cpd:.1f}%
    (近7日日均：投放{spend_7d:.1f}w美元, 激活量{cnt_install_7d:,}, 注册量{reg_cnt_7d:,}, 流水CPI {cpi_7d}, 流水CPR {cpr_7d}, 流水CPK {cpk_7d}, 流水CPS {cps_7d:.1f}, 流水CPD {cpd_7d:.1f}%)
    
    3. 运营：首贷流水注册进件率 {reg_to_apply_rate:.1f}%(仅包含纯新), 用信率 {fst_confirm_rate_1d:.1f}%, 额度使用率 {fst_limit_usage_1d:.1f}%; 复贷流水进件用信率 {rl_confirm_rate_1d:.1f}%, 额度使用率 {rl_limit_usage_1d:.1f}%
    (近7日日均：首贷流水注册进件率 {reg_to_apply_rate_7d:.1f}%(仅包含纯新), 用信率 {fst_confirm_rate_7d:.1f}%, 额度使用率 {fst_limit_usage_7d:.1f}%; 复贷流水进件用信率 {rl_confirm_rate_7d:.1f}%, 额度使用率 {rl_limit_usage_7d:.1f}%)
    
    4. 首贷注册t0转化：首贷用户注册进件率 {t0_complete_rate_1d:.1f}%, 前置通过率 {t0_front_pass_rate_1d:.1f}%, 用信率 {t0_confirm_rate_1d:.1f}%, 后置通过率 {t0_back_pass_rate_1d:.1f}%, 发标成功率 {t0_release_rate_1d:.1f}%(尚未跑完), 整体转化率 {t0_issue_rate_1d:.1f}%
    (近7日日均：首贷用户注册进件率 {t0_complete_rate_7d:.1f}%, 前置通过率 {t0_front_pass_rate_7d:.1f}%, 用信率 {t0_confirm_rate_7d:.1f}%, 后置通过率 {t0_back_pass_rate_7d:.1f}%, 发标成功率 {t0_release_rate_7d:.1f}%(尚未跑完), 整体转化率 {t0_issue_rate_7d:.1f}%)
    
    5. 风控：首贷进件{fst_apply_cnt:,}, 进件审批通过{fst_approve_cnt:,}笔, 通过率{fst_pass_rate}%(尚未跑完); 复贷进件{sec_apply_cnt:,}, 流水进件审批通过{sec_approve_cnt:,}笔, 通过率{sec_pass_rate}%(尚未跑完)
    (近7日日均：首贷进件{fst_apply_cnt_7d:,.0f}, 进件审批通过{fst_approve_cnt_7d:,}笔, 通过率{fst_pass_rate_7d}%; 复贷进件{sec_apply_cnt_7d:,.0f}, 进件审批通过{sec_approve_cnt_7d:,}笔, 通过率{sec_pass_rate_7d}%)
             
    6. 信审：已完成{fst_audit_processed_case:,}件, 待执行{fst_audit_unmanaged_case}件(信审人员{fst_approve_user_cnt}人, 人效{fst_perform}件/天) 
    
    7. 首贷用户质量：安卓a100_bin1-2进件占比 {a100_bin2_rate_1d:.2f}%, IOS a101_bin1-3进件占比 {a101_bin3_rate_1d:.2f}%, 成交资产等级1-2人数占比 {deal_top_rate_1d:.2f}%
    (近7日日均：安卓a100_bin1-2进件占比 {a100_bin2_rate_7d:.2f}%, IOS a101_bin1-3进件占比 {a101_bin3_rate_7d:.2f}%, 成交资产等级1-2人数占比 {deal_top_rate_7d:.2f}%)
    
    8. 逾期：首贷 1T0 {fst_fpd_t0_1d}%, 1T7 {fst_fpd_t7_1d}%; 复贷1T0 {rl_fpd_t0_1d}%, 1T7 {rl_fpd_t7_1d}%
    (近7日日均：首贷 1T0 {fst_fpd_t0}%, 1T7 {fst_fpd_t7}%; 复贷1T0 {rl_fpd_t0}%, 1T7 {rl_fpd_t7}%)
       
    9. 资金：回款{fact_cnt:,}笔, 金额{fact_amt_usd:,.1f}w美元
    
    当前使用汇率值{exchange_rate_to_dollar:,}'''.format(reprot_date=reprot_date, target_cnt=to_num(target_cnt), target_amt=to_num(target_amt)/10000, period_finish_rate=period_finish_rate, total_finish_rate=total_finish_rate, cur_amt=cur_amt, Daily_completion_required=to_num(Daily_completion_required)/10000,
                   loan_cnt=loan_cnt, release_amt_usd=to_num(release_amt_usd)/10000,  fst_loan_cnt=to_num(fst_loan_cnt),
                   fst_release_amt_usd=to_num(fst_release_amt_usd)/10000, sec_loan_cnt=sec_loan_cnt, sec_release_amt_usd=to_num(sec_release_amt_usd)/10000,
                   fact_cnt=to_num(fact_cnt), fact_amt_usd=to_num(fact_amt_usd)/10000,
                   spend=to_num(spend)/10000, spend_7d=to_num(spend_7d)/70000, cnt_install=cnt_install, cnt_install_7d=to_num(cnt_install_7d/7), cpi='%.1f' % cpi, cpr='%.1f' % cpr, cpk='%.1f' % cpk, cpd= cpd*100, cps='%.1f' % cps,cpi_7d='%.1f' % cpi_7d, cpr_7d='%.1f' % cpr_7d, cpk_7d='%.1f' % cpk_7d, cpd_7d = cpd_7d*100/7, cps_7d = cps_7d/7,
                   reg_cnt=to_num(reg_cnt), reg_cnt_7d=to_num(reg_cnt_7d/7), fst_apply_cnt=to_num(fst_apply_cnt), sec_apply_cnt=to_num(sec_apply_cnt),fst_apply_cnt_7d=to_num(fst_apply_cnt_7d)/7,sec_apply_cnt_7d=to_num(sec_apply_cnt_7d)/7,
                   fst_audit_processed_case=to_num(fst_audit_processed_case), fst_audit_unmanaged_case=to_num(fst_audit_unmanaged_case),
                   fst_approve_user_cnt=fst_approve_user_cnt,
                   fst_perform=fst_perform,
                   a100_bin2_rate_1d=float(a100_bin2_rate_1d),a101_bin3_rate_1d=float(a101_bin3_rate_1d),deal_top_rate_1d=float(deal_top_rate_1d),a100_bin2_rate_7d=float(a100_bin2_rate_7d),a101_bin3_rate_7d=float(a101_bin3_rate_7d),deal_top_rate_7d=float(deal_top_rate_7d),
                   fst_approve_cnt=to_num(fst_approve_cnt), fst_pass_rate='%.1f' % fst_pass_rate,fst_amt_per_loan_1d=fst_amt_per_loan_1d, fst_fpd_t0_1d=fst_fpd_t0_1d, fst_fpd_t7_1d=fst_fpd_t7_1d, 
                   sec_approve_cnt=to_num(sec_approve_cnt), sec_pass_rate='%.1f' % sec_pass_rate,sec_amt_per_loan_1d=sec_amt_per_loan_1d, rl_fpd_t0_1d=rl_fpd_t0_1d, rl_fpd_t7_1d=rl_fpd_t7_1d, 
                   fst_approve_cnt_7d=round(fst_loan_cnt_7d,0), fst_pass_rate_7d='%.1f' % fst_pass_rate_7d, fst_amt_per_loan_7d='%.1f' % fst_amt_per_loan_7d, fst_fpd_t0=fst_fpd_t0, fst_fpd_t7=fst_fpd_t7, 
                   sec_approve_cnt_7d=round(sec_loan_cnt_7d,0), sec_pass_rate_7d='%.1f' % sec_pass_rate_7d, sec_amt_per_loan_7d='%.1f' % sec_amt_per_loan_7d, rl_fpd_t0=rl_fpd_t0, rl_fpd_t7=rl_fpd_t7,  
                   exchange_rate_to_dollar=to_num(exchange_rate_to_dollar),
                   loan_cnt_month=to_num(loan_cnt_month),release_amt_usd_month=to_num(release_amt_usd_month)/10000,fst_loan_cnt_month=to_num(fst_loan_cnt_month),fst_release_amt_usd_month=to_num(fst_release_amt_usd_month)/10000,fst_amt_per_loan_month=fst_amt_per_loan_month,
                   sec_loan_cnt_month=to_num(sec_loan_cnt_month),sec_release_amt_usd_month=to_num(sec_release_amt_usd_month)/10000,sec_amt_per_loan_month=sec_amt_per_loan_month,
                   reg_to_apply_rate=float(reg_to_apply_rate),reg_to_apply_rate_7d=float(reg_to_apply_rate_7d),
                   t0_complete_rate_1d=float(t0_complete_rate_1d),t0_front_pass_rate_1d=float(t0_front_pass_rate_1d),t0_confirm_rate_1d=float(t0_confirm_rate_1d),t0_back_pass_rate_1d=float(t0_back_pass_rate_1d),t0_issue_rate_1d=float(t0_issue_rate_1d),t0_release_rate_1d=float(t0_release_rate_1d),
                   t0_complete_rate_7d=float(t0_complete_rate_7d),t0_front_pass_rate_7d=float(t0_front_pass_rate_7d),t0_confirm_rate_7d=float(t0_confirm_rate_7d),t0_back_pass_rate_7d=float(t0_back_pass_rate_7d),t0_issue_rate_7d=float(t0_issue_rate_7d),t0_release_rate_7d=float(t0_release_rate_7d),
                   fst_confirm_rate_1d=float(fst_confirm_rate_1d),rl_confirm_rate_1d=float(rl_confirm_rate_1d),fst_limit_usage_1d=float(fst_limit_usage_1d),rl_limit_usage_1d=float(rl_limit_usage_1d),
                   fst_confirm_rate_7d=float(fst_confirm_rate_7d),rl_confirm_rate_7d=float(rl_confirm_rate_7d),fst_limit_usage_7d=float(fst_limit_usage_7d),rl_limit_usage_7d=float(rl_limit_usage_7d)
                   )
        return quick_report#.replace(' ', '')
    except Exception:
        root.exception('error')

def send_robot(content):
    url3 = 'https://open.feishu.cn/open-apis/bot/v2/hook/63a8a286-0123-4dca-9bdd-98ba5f9f5eaa' #经分
    headers = {'Content-type': 'application/json'}

    data_fs = {"msg_type":"text","content":{"text":content}}
    r3 = requests.post(url3, headers=headers, json=data_fs)
    print(r3)

if __name__== "__main__":
    if datetime.datetime.today().weekday() in (0, 1, 2, 3, 4, 5, 6):
        day_delta = 1
        quick_report = day_quick_report(day_delta=day_delta)
        send_robot(quick_report)
        with open(r'快报内容文件.txt', 'a+', encoding='utf8') as fp:
            print(quick_report, file=fp)

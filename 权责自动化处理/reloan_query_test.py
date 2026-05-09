# -*- coding: utf-8 -*-
"""
复贷进件量查询测试
"""

import requests
import json
import re
import time
import base64
import math
import pandas as pd
from datetime import datetime

# ================================================
# 数据库操作类（复用原文件的连接方式）
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
        
        max_wait = 60
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
            result_payload = {'current': 1, 'size': 1000, 'queryId': query_id}
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
            
            for i in range(1, math.ceil(totalrecords/1000)+1):
                current_page = i
                result_payload = {'current': current_page, 'size': 1000, 'queryId': query_id}
                result_res = self.sess.post(result_url, headers=self.headers, data=json.dumps(result_payload), timeout=(3, 20))
                result_data = result_res.json().get('data', {})
                df1 = pd.DataFrame(result_data.get('records', []), columns=columns)
                df = pd.concat([df, df1], ignore_index=True)
            return df
        
        return "未知的查询类型"

# ================================================
# SQL查询语句
# ================================================
SQL_QUERY = """
select 
  'application' as tag, 
  to_char(a.release_time, 'yyyy-mm') as first_loan_month,  -- 首贷月份 
  product_level_type, 
  new_grade_level, 
  loan_cycle, 
   
  -- MOB周期：首贷后第几个月复贷 
  (year(date(b.app_date)) - year(a.release_time)) * 12 
  + (month(date(b.app_date)) - month(a.release_time)) as mob_num, 
   
  to_char(date(b.app_date), 'yyyy-mm') as reloan_month,   -- 复贷进件月份 
   
  -- 关键：区分 循环贷 / 非循环贷 
  b.grant_strategy, 
  b.loan_type2, 
   
  count(distinct b.biz_id) as reloan_apply_cnt  -- 复贷进件量 
 from 
   ( 
     select 
       a.release_time, 
       a.mid, 
       c.new_grade_level, 
       c.loan_cycle, 
       c.product_level 
     from dwd.dwd_loan_info a 
     left join ind.xly_application_funnel c 
       on try_cast(a.order_no as bigint) = try_cast(c.biz_id as bigint) 
     where c.grant_strategy in ('NEW')  -- NEW=首贷 
       and a.release_time is not null 
   ) a 
 left join ( 
   select 
     app_date, 
     grant_strategy, 
     loan_type2, 
     biz_id, 
     mid 
   from ind.ba_asset_base_info a 
   where 
     -- 复贷进件规则 
     (grant_strategy = 'NEW' and if_issue = 1 and if_app=1 ) 
     or 
     (grant_strategy = 'OLD' and if_app=1 and if_recall=0) 
 ) b on cast(a.mid as bigint) = cast(b.mid as bigint) 
 group by 1,2,3,4,5,6,7,8,9
"""

# ================================================
# 主程序
# ================================================
def main():
    print("="*60)
    print("复贷进件量查询测试")
    print("="*60)
    print()
    
    # 初始化数据库连接
    pq = PrestoQuery()
    
    print("步骤1: 登录数据库...")
    pq.login_process()
    print()
    
    print("步骤2: 执行SQL查询...")
    print("-" * 60)
    
    try:
        result = pq.submit_query(SQL_QUERY, wait_sec=2)
        
        # 检查返回结果类型
        if isinstance(result, str):
            # 如果是字符串，说明是错误信息或成功消息
            print(f"查询结果: {result}")
        elif isinstance(result, pd.DataFrame):
            # 如果是DataFrame，检查是否为空
            df = result
            if df is None or (hasattr(df, 'empty') and df.empty):
                print("查询成功，但返回数据为空")
            else:
                print(f"查询成功！共返回 {len(df)} 条记录")
                print()
                print("前10条数据预览:")
                print(df.head(10))
                print()
                print("数据列名:")
                print(df.columns.tolist())
                print()
                print("数据类型:")
                print(df.dtypes)
                
                # 保存到CSV文件
                output_path = f"reloan_query_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                df.to_csv(output_path, index=False, encoding='utf-8-sig')
                print(f"\n结果已保存到: {output_path}")
        else:
            print(f"未知的返回类型: {type(result)}")
    
    except Exception as e:
        print(f"查询失败: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("="*60)
    print("测试完成")
    print("="*60)

if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
import sys, json, base64, time
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery

pq = PrestoQuery()
pq.login()
print("登录成功")

def raw_exec(sql, wait_sec=3, timeout=600):
    r = pq.sess.post(
        f"{pq.base}/dataworks-development/adhoc/querySql",
        headers=pq.headers,
        data=json.dumps({
            "sql": base64.b64encode(sql.encode()).decode(),
            "engine": "PRESTO", "headRowNum": 54, "queryType": "Data",
            "dependStatus": 1, "windowId": 16, "varList": []
        }),
        timeout=(10, 180), verify=False
    )
    d = r.json().get("data", {})
    job_id = d.get("jobQueryId")
    print("jobQueryId:", job_id)
    job_url = f"{pq.base}/dataworks-development/adhoc/queryPrestoJobLog"
    start = time.time()
    while time.time() - start < timeout:
        rj = pq.sess.get(job_url, params={"jobQueryId": job_id}, headers=pq.headers, timeout=(5,120), verify=False)
        task = rj.json().get("data", {})
        state = task.get("taskState")
        if state in ("FINISHED", "FAILED", "CANCELLED"):
            print("终态:", state)
            print("errorMsg:", task.get("errorMsg"))
            print("msg:", task.get("msg"))
            if task.get("errorLocateList"):
                print("errorLocateList:", json.dumps(task.get("errorLocateList"), ensure_ascii=False)[:1500])
            return task
        time.sleep(wait_sec)
    print("超时")
    return None

ddl = """
drop table if exists mx.ys_dl_ltv_double_loan_group;
create table mx.ys_dl_ltv_double_loan_group as 
select
    ltv_week as ltv_week_d,
    wob as wob_d,
    app_channel_name as app_channel_name_d,
    reloan_app_channel as reloan_app_channel_d,
    reloan_app_channel_name as reloan_app_channel_name_d,
    loan_cycle as loan_period, 
    new_grade_level as new_grade_level_d,
    is_low_amount_flag as is_low_amount_flag_d,
    count(distinct biz_id) as double_cnt,
    count(distinct mid) as double_mid,
    sum(contract_amount) as contract_amount,
    sum(haircut_amount+should_interest) as fee_amount,
    sum(contract_amount) / nullif(count(distinct biz_id), 0) as avg_amount,
    sum(should_amt) as  should_amt_t0,
    sum(should_amt_t7) as should_amt_t7,
    sum(should_amt_t30) as should_amt_t30,
    sum(contract_t0) as contract_t0,
    sum(contract_t7) as contract_t7,
    sum(contract_t30) as contract_t30,
    sum(should_amt_1t0) as should_amt_1t0,
    sum(should_amt_1t3) as should_amt_1t3,
    sum(contract_1t0) as contract_1t0,
    sum(contract_1t3) as contract_1t3,
    sum(fact_capital_1t0) as fact_capital_1t0,
    sum(fact_capital_1t3) as fact_capital_1t3,
    sum(fact_1t0) as fact_1t0,
    sum(fact_1t3) as fact_1t3,
    (sum(contract_1t0) - sum(fact_capital_1t0)) / nullif(sum(contract_1t0), 0) as bad_1t0_capital,
    (sum(contract_1t3) - sum(fact_capital_1t3)) / nullif(sum(contract_1t3), 0) as bad_1t3_capital,
    (sum(should_amt_1t0) - sum(fact_1t0)) / nullif(sum(should_amt_1t0), 0) as bad_1t0_amt,
    (sum(should_amt_1t3) - sum(fact_1t3)) / nullif(sum(should_amt_1t3), 0) as bad_1t3_amt,
    0 as should_cnt_t0, 
    sum(should_cnt_t7) as should_cnt_t7, 
    0 as fact_t0,
    sum(fact_t7) as fact_t7,
    sum(fact_t7_coup) as fact_t7_coup,
    sum(fact_t30) as fact_t30,
    sum(fact_t30_coup) as fact_t30_coup,
    0 as fact_cnt_t0,
    sum(fact_cnt_t7) as fact_cnt_t7,
    sum(fact_cnt_t30) as fact_cnt_t30,
    sum(fact_cnt_till_now) as fact_cnt_till_now,
    0 as contract_amount_7d,
    0 as contract_amount_14d,
    0 as should_amt_7d,
    0 as should_amt_14d,
    0 as fact_t30_7d,
    0 as fact_t30_14d,
    0 as double_cnt_7d,
    0 as double_cnt_14d,
    0 as avg_amount_7d,
    0 as avg_amount_14d,
    0 as zr_mid,
    0 as zr_pass_mid,
    0 as zr_cnt,
    0 as zr_pass_cnt,
    0 as qz_mid,
    0 as qz_pass_mid,
    0 as qz_cnt,
    0 as qz_pass_cnt,
    0 as apply_mid,
    0 as apply_pass_mid,
    0 as apply_cnt,
    0 as apply_pass_cnt,
    0 as fact_cnt_t7_for_rzt30,
    0 as fact_cnt_t7_for_rzt7,
    0 as re_zr_cnt_t30,
    0 as re_zr_cnt_t7,
    sum(contract_amount_usd) as contract_amount_usd
from mx.ys_dl_ltv_double_loan_0511
group by 1, 2, 3, 4, 5, 6, 7, 8 ;
"""

raw_exec(ddl)

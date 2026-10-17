# -*- coding: utf-8 -*-
import sys, json, base64, time
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery

pq = PrestoQuery()
pq.login()
print("登录成功")

def raw_query(sql, wait_sec=3, timeout=300):
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
    job_url = f"{pq.base}/dataworks-development/adhoc/queryPrestoJobLog"
    start = time.time()
    while time.time() - start < timeout:
        rj = pq.sess.get(job_url, params={"jobQueryId": job_id}, headers=pq.headers, timeout=(5,120), verify=False)
        task = rj.json().get("data", {})
        state = task.get("taskState")
        if state in ("FINISHED", "FAILED", "CANCELLED"):
            return state, task
        time.sleep(wait_sec)
    return "TIMEOUT", {}

# 1. 列出所有相关表
state, task = raw_query("show tables from mx like 'ys_dl_ltv%'")
print("show tables 状态:", state)
if state == "FINISHED":
    df = pq.query("show tables from mx like 'ys_dl_ltv%'")
    print(df.to_string() if hasattr(df, 'to_string') else df)
else:
    print("errorMsg:", task.get("errorMsg"))

# 2. 渠道名 group by 真实错误
state, task = raw_query("select reloan_app_channel_name, sum(double_cnt) as dc from mx.ys_dl_ltv_double_loan_group group by 1 order by 2 desc")
print("\n渠道名group by 状态:", state)
if state != "FINISHED":
    print("errorMsg:", task.get("errorMsg"))
    print("errorLocateList:", json.dumps(task.get("errorLocateList"), ensure_ascii=False)[:1500])

# 3. 渠道名 + id 一起看
state, task = raw_query("select reloan_app_channel_name from mx.ys_dl_ltv_double_loan_group limit 20")
print("\n渠道名 limit 状态:", state)
if state == "FINISHED":
    df = pq.query("select distinct reloan_app_channel_name from mx.ys_dl_ltv_double_loan_group limit 20")
    print(df.to_string() if hasattr(df, 'to_string') else df)
else:
    print("errorMsg:", task.get("errorMsg"))

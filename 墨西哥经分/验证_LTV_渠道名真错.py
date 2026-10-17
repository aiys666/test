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

state, task = raw_query("select reloan_app_channel_name, count(*) as c from mx.ys_dl_ltv_double_loan_group group by 1 order by 2 desc")
print("状态:", state)
if state != "FINISHED":
    print("errorMsg:", task.get("errorMsg"))
    print("msg:", task.get("msg"))
    print("errorLocateList:", json.dumps(task.get("errorLocateList"), ensure_ascii=False)[:2000])
else:
    df = pq.query("select reloan_app_channel_name, count(*) as c from mx.ys_dl_ltv_double_loan_group group by 1 order by 2 desc")
    print(df.to_string() if hasattr(df, 'to_string') else df)

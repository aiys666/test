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
    print("提交响应 data keys:", list(d.keys()) if isinstance(d, dict) else type(d))
    if d.get("checkError") == True:
        print("checkError:", d.get("checkResultList"))
        return
    job_id = d.get("jobQueryId")
    print("jobQueryId:", job_id)
    job_url = f"{pq.base}/dataworks-development/adhoc/queryPrestoJobLog"
    start = time.time()
    while time.time() - start < timeout:
        rj = pq.sess.get(job_url, params={"jobQueryId": job_id}, headers=pq.headers, timeout=(5,120), verify=False)
        task = rj.json().get("data", {})
        state = task.get("taskState")
        print("  state:", state, "keys:", list(task.keys()))
        if state == "FINISHED":
            print("FINISHED. task:", json.dumps(task, ensure_ascii=False)[:800])
            return
        if state in ("FAILED", "CANCELLED"):
            print("FAILED/CANCELLED. task:", json.dumps(task, ensure_ascii=False)[:2000])
            return
        time.sleep(wait_sec)

raw_query("select count(*) as cnt from mx.ys_dl_ltv_double_loan_group")

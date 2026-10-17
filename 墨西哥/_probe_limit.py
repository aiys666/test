# -*- coding: utf-8 -*-
"""验证 getQueryResult 的行数上限 & headRowNum 参数影响"""
import sys, json, base64, time
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
print("登录:", pq.login())

def raw_job(sql, head=54):
    r = pq.sess.post(
        f"{pq.base}/dataworks-development/adhoc/querySql",
        headers=pq.headers,
        data=json.dumps({"sql": base64.b64encode(sql.encode()).decode(),
                         "engine": "PRESTO", "headRowNum": head, "queryType": "Data",
                         "dependStatus": 1, "windowId": 16, "varList": []}),
        timeout=(10, 180), verify=False)
    d = r.json().get("data", {})
    if d.get("checkError"):
        print("checkError", d.get("checkResultList")); return None
    jid = d.get("jobQueryId")
    job_url = f"{pq.base}/dataworks-development/adhoc/queryPrestoJobLog"
    while True:
        rj = pq.sess.get(job_url, params={"jobQueryId": jid}, headers=pq.headers, timeout=(5, 120), verify=False)
        t = rj.json().get("data", {})
        if t.get("taskState") == "FINISHED":
            return t["queryId"]
        if t.get("taskState") in ("FAILED", "CANCELLED"):
            print("失败", t.get('errorMessage')); return None
        time.sleep(1)

def page_total(qid, page=1, size=1000):
    res_url = f"{pq.base}/dataworks-development/adhoc/getQueryResult"
    rr = pq.sess.post(res_url, headers=pq.headers,
                      data=json.dumps({"current": page, "size": size, "queryId": qid}),
                      timeout=(10, 120), verify=False)
    d = rr.json().get("data")
    if isinstance(d, dict):
        return d.get("totalRecords"), len(d.get("records") or []), list(d.keys())
    return None, None, rr.text[:100]

# 1. limit 15000 看 totalRecords
print("=" * 80)
sql = "select camera_id from ods.s02_loan where release_time >= timestamp '2026-05-01' and state in (1,2) limit 15000"
qid = raw_job(sql)
print("limit15000 totalRecords:", page_total(qid))

# 2. limit 15000, headRowNum=100000
print("=" * 80)
qid = raw_job(sql, head=100000)
print("limit15000 head=100000 totalRecords:", page_total(qid))

# 3. 全量无 limit, head=100000
print("=" * 80)
sql_full = "select camera_id from ods.s02_loan where release_time >= timestamp '2026-05-01' and state in (1,2)"
qid = raw_job(sql_full, head=100000)
print("full head=100000 totalRecords:", page_total(qid))

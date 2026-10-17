# -*- coding: utf-8 -*-
"""测试 OFFSET 分片能否稳定取全量（突破 10000 行限制）"""
import sys, json, base64, time
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
print("登录:", pq.login())

def run_job(sql):
    r = pq.sess.post(
        f"{pq.base}/dataworks-development/adhoc/querySql",
        headers=pq.headers,
        data=json.dumps({"sql": base64.b64encode(sql.encode()).decode(),
                         "engine": "PRESTO", "headRowNum": 54, "queryType": "Data",
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

def get_total(qid):
    res_url = f"{pq.base}/dataworks-development/adhoc/getQueryResult"
    rr = pq.sess.post(res_url, headers=pq.headers,
                      data=json.dumps({"current": 1, "size": 1000, "queryId": qid}),
                      timeout=(10, 120), verify=False)
    d = rr.json().get("data")
    if isinstance(d, dict):
        return d.get("totalRecords")
    return rr.text[:100]

# 测试 offset 分片
print("=" * 80)
for off in (0, 9999, 19998):
    sql = (f"select camera_id from ods.s02_loan where release_time >= timestamp '2026-05-01' "
           f"and state in (1,2) order by camera_id limit 9999 offset {off}")
    qid = run_job(sql)
    print(f"offset={off}: totalRecords={get_total(qid)}")

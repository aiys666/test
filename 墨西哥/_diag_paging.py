# -*- coding: utf-8 -*-
import sys, io, json, base64, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
pq = PrestoQuery(); pq.login()

SQL = "select biz_id, if_issue from mx.wxs_application_funnel where is_reloan='old' and tenant='yawey' and if_app=1 and date(create_time)>=date '2026-08-03' and date(create_time)<date '2026-08-10' order by biz_id"

# 直接提交任务拿 jobQueryId
r = pq.sess.post(
    f"{pq.base}/dataworks-development/adhoc/querySql",
    headers=pq.headers,
    data=json.dumps({"sql": base64.b64encode(SQL.encode()).decode(), "engine": "PRESTO",
                     "headRowNum": 54, "queryType": "Data", "dependStatus": 1, "windowId": 16, "varList": []}),
    timeout=(10, 180), verify=False
)
d = r.json().get("data", {})
job_id = d.get("jobQueryId")
print("jobQueryId:", job_id)

# 轮询到 FINISHED
job_url = f"{pq.base}/dataworks-development/adhoc/queryPrestoJobLog"
while True:
    rj = pq.sess.get(job_url, params={"jobQueryId": job_id}, headers=pq.headers, timeout=(5,120), verify=False)
    task = rj.json().get("data", {})
    st = task.get("taskState")
    if st == "FINISHED":
        qid = task["queryId"]
        print("queryId:", qid)
        break
    if st in ("FAILED","CANCELLED"):
        print("FAILED:", task.get("errorMessage") or task.get("errorInfo") or task.get("errorMsg")); sys.exit()
    time.sleep(2)

# 手动翻页看 totalRecords
result_url = f"{pq.base}/dataworks-development/adhoc/getQueryResult"
for p in [1, 2, 5, 10, 11, 12, 13]:
    rp = pq.sess.post(result_url, headers=pq.headers,
                      data=json.dumps({"current": p, "size": 1000, "queryId": qid}),
                      timeout=(10,120), verify=False)
    dd = rp.json().get("data")
    if isinstance(dd, dict):
        recs = dd.get("records")
        print(f"page={p} total={dd.get('totalRecords')} 本页行数={len(recs) if recs else 0} 首行={recs[0][:3] if recs else None}")
    else:
        print(f"page={p} data类型={type(dd)} text={rp.text[:120]}")

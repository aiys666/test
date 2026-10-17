# -*- coding: utf-8 -*-
"""探针：确认三表真实行数 + getQueryResult 分页行为（totalRecords 是否被限 10000）"""
import sys, os, time, json, base64
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
print("登录:", pq.login())

# 1. count 三张表真实行数
def count(sql):
    df = pq.query(sql, wait_sec=1)
    print("COUNT结果:", type(df), df if isinstance(df, str) else df.to_dict('records'))

print("=" * 80)
count("select count(*) as c from ods.s02_loan where release_time >= timestamp '2026-05-01' and state in (1,2)")
count("select count(*) as c from ods.s02_loan_repayment rp join ods.s02_loan l on l.camera_id=rp.camera_id where l.release_time >= timestamp '2026-05-01' and l.state in (1,2)")
count("select count(*) as c from ods.s02_loan_repayment_detail rd join ods.s02_loan l on l.camera_id=rd.camera_id where l.release_time >= timestamp '2026-05-01' and l.state in (1,2)")

# 2. 小 job 检查分页原始返回
print("=" * 80)
sql = "select camera_id from ods.s02_loan where release_time >= timestamp '2026-05-01' and state in (1,2) limit 5"
r = pq.sess.post(
    f"{pq.base}/dataworks-development/adhoc/querySql",
    headers=pq.headers,
    data=json.dumps({"sql": base64.b64encode(sql.encode()).decode(),
                     "engine": "PRESTO", "headRowNum": 54, "queryType": "Data",
                     "dependStatus": 1, "windowId": 16, "varList": []}),
    timeout=(10, 180), verify=False)
jid = r.json().get("data", {}).get("jobQueryId")
print("jobId:", jid)

job_url = f"{pq.base}/dataworks-development/adhoc/queryPrestoJobLog"
while True:
    rj = pq.sess.get(job_url, params={"jobQueryId": jid}, headers=pq.headers, timeout=(5, 120), verify=False)
    t = rj.json().get("data", {})
    if t.get("taskState") == "FINISHED":
        qid = t["queryId"]
        break
    if t.get("taskState") in ("FAILED", "CANCELLED"):
        print("失败", t); sys.exit()
    time.sleep(1)

res_url = f"{pq.base}/dataworks-development/adhoc/getQueryResult"
for page in (1, 2):
    rr = pq.sess.post(res_url, headers=pq.headers,
                      data=json.dumps({"current": page, "size": 1000, "queryId": qid}),
                      timeout=(10, 120), verify=False)
    d = rr.json().get("data")
    if isinstance(d, dict):
        print(f"page={page}: keys={list(d.keys())}, totalRecords={d.get('totalRecords')}, records_len={len(d.get('records') or [])}")
    else:
        print(f"page={page}: 非dict ->", rr.text[:200])
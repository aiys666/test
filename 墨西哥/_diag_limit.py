# -*- coding: utf-8 -*-
import sys, io, json, base64, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
pq = PrestoQuery(); pq.login()

# 测试：SQL 加 LIMIT 100000 后，totalRecords 是否突破 10000 上限
cases = {
    "无LIMIT": "select biz_id from mx.wxs_application_funnel where is_reloan='old' and tenant='yawey' and if_app=1 and date(create_time)>=date '2026-08-03' and date(create_time)<date '2026-08-10'",
    "LIMIT100000": "select biz_id from mx.wxs_application_funnel where is_reloan='old' and tenant='yawey' and if_app=1 and date(create_time)>=date '2026-08-03' and date(create_time)<date '2026-08-10' LIMIT 100000",
}

for name, SQL in cases.items():
    r = pq.sess.post(
        f"{pq.base}/dataworks-development/adhoc/querySql", headers=pq.headers,
        data=json.dumps({"sql": base64.b64encode(SQL.encode()).decode(), "engine": "PRESTO",
                         "headRowNum": 54, "queryType": "Data", "dependStatus": 1, "windowId": 16, "varList": []}),
        timeout=(10, 180), verify=False)
    d = r.json().get("data", {})
    job_id = d.get("jobQueryId")
    job_url = f"{pq.base}/dataworks-development/adhoc/queryPrestoJobLog"
    while True:
        rj = pq.sess.get(job_url, params={"jobQueryId": job_id}, headers=pq.headers, timeout=(5,120), verify=False)
        task = rj.json().get("data", {})
        st = task.get("taskState")
        if st == "FINISHED":
            qid = task["queryId"]; break
        if st in ("FAILED","CANCELLED"):
            print(name, "FAILED:", task.get("errorMessage") or task.get("errorInfo")); qid=None; break
        time.sleep(2)
    if qid is None:
        continue
    result_url = f"{pq.base}/dataworks-development/adhoc/getQueryResult"
    rp = pq.sess.post(result_url, headers=pq.headers,
                      data=json.dumps({"current": 1, "size": 1000, "queryId": qid}),
                      timeout=(10,120), verify=False)
    dd = rp.json().get("data")
    if isinstance(dd, dict):
        print(f"{name}: totalRecords={dd.get('totalRecords')} 首行={dd['records'][0][:3] if dd.get('records') else None}")
    else:
        print(f"{name}: {rp.text[:150]}")

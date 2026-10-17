import sys, json, base64, time
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
pq.login()

sql = """
SELECT dim_name, dim_group, week, billed_cnt, overdue_cnt, billed_amt, overdue_amt
FROM mx.tmp_effect_decomp_all_dims
WHERE week IN (date'2026-08-03', date'2026-08-10')
ORDER BY dim_name, dim_group, week
"""
r = pq.sess.post(f"{pq.base}/dataworks-development/adhoc/querySql", headers=pq.headers,
    data=json.dumps({"sql": base64.b64encode(sql.encode()).decode(), "engine":"PRESTO",
    "headRowNum":54, "queryType":"Data", "dependStatus":1, "windowId":16, "varList":[]}),
    timeout=(10,180), verify=False)
job_id = r.json().get("data", {}).get("jobQueryId")
job_url = f"{pq.base}/dataworks-development/adhoc/queryPrestoJobLog"
query_id = None
for _ in range(600):
    rj = pq.sess.get(job_url, params={"jobQueryId": job_id}, headers=pq.headers, timeout=(5,120), verify=False)
    task = rj.json().get("data", {})
    if task.get("taskState") == "FINISHED":
        query_id = task["queryId"]; break
    time.sleep(2)

result_url = f"{pq.base}/dataworks-development/adhoc/getQueryResult"
def post_page(page, size):
    return pq.sess.post(result_url, headers=pq.headers,
        data=json.dumps({"current": page, "size": size, "queryId": query_id}),
        timeout=(10,120), verify=False)

# size=1000 分页
seen = set()
total_rows = 0
for p in [1, 2, 3]:
    rp = post_page(p, 1000)
    dp = rp.json().get("data")
    recs = dp.get("records", [])
    cols = dp.get("columns", [])
    print(f"current={p} size=1000: totalRecords={dp.get('totalRecords')}, 返回={len(recs)}")
    if not recs:
        break
    for rec in recs:
        key = (rec[0], rec[1], rec[2])
        seen.add(key)
    total_rows += len(recs)
print('累计行数:', total_rows, '去重行数:', len(seen))

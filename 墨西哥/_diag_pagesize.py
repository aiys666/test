import sys, json, base64
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
pq.login()

sql = """
SELECT dim_name, dim_group, week, billed_cnt, overdue_cnt, billed_amt, overdue_amt
FROM mx.tmp_effect_decomp_all_dims
WHERE week IN (date'2026-08-03', date'2026-08-10')
"""

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

# 轮询到 FINISHED
import time
job_url = f"{pq.base}/dataworks-development/adhoc/queryPrestoJobLog"
query_id = None
for _ in range(600):
    rj = pq.sess.get(job_url, params={"jobQueryId": job_id}, headers=pq.headers, timeout=(5,120), verify=False)
    task = rj.json().get("data", {})
    state = task.get("taskState")
    if state == "FINISHED":
        query_id = task["queryId"]
        print("FINISHED, queryId:", query_id)
        break
    if state in ("FAILED","CANCELLED"):
        print("FAILED:", task.get("errorMessage"))
        break
    time.sleep(2)

# 拉第一页，看 totalRecords 和 records 长度
result_url = f"{pq.base}/dataworks-development/adhoc/getQueryResult"
def post_page(page, size):
    return pq.sess.post(result_url, headers=pq.headers,
        data=json.dumps({"current": page, "size": size, "queryId": query_id}),
        timeout=(10,120), verify=False)

for size in [5000, 1000, 500, 200, 100]:
    rp = post_page(1, size)
    dp = rp.json().get("data")
    if dp:
        print(f"size={size}: totalRecords={dp.get('totalRecords')}, records返回={len(dp.get('records', []))}")
    else:
        print(f"size={size}: data={rp.text[:200]}")

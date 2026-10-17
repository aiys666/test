# -*- coding: utf-8 -*-
import sys, json, base64
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import urllib3
urllib3.disable_warnings()
from mexico_presto import PrestoQuery

pq = PrestoQuery()
ok = pq.login()
print("login ok:", ok)
sql = "select 1 as a"
r = pq.sess.post(
    pq.base + "/dataworks-development/adhoc/querySql",
    headers=pq.headers,
    data=json.dumps({"sql": base64.b64encode(sql.encode()).decode(),
                     "engine": "PRESTO", "headRowNum": 54, "queryType": "Data",
                     "dependStatus": 1, "windowId": 16, "varList": []}),
    timeout=(10, 180), verify=False
)
print("http:", r.status_code)
try:
    d = r.json()
    print("json keys:", list(d.keys()) if isinstance(d, dict) else type(d))
    print("data:", json.dumps(d.get("data"), ensure_ascii=False)[:800])
except Exception as e:
    print("non-json text:", r.text[:800])

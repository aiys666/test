import sys, json, base64
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
pq.login()

tests = {
    'group_by_plain': "SELECT app_week, COUNT(*) AS c FROM mx.yj_test_table_250225 WHERE app_time >= date'2026-08-03' GROUP BY app_week LIMIT 5",
    'group_by_two_col': "SELECT app_week, is_reloan, COUNT(*) AS c FROM mx.yj_test_table_250225 WHERE app_time >= date'2026-08-03' GROUP BY app_week, is_reloan LIMIT 5",
    'cube': "SELECT app_week, is_reloan, COUNT(*) AS c FROM mx.yj_test_table_250225 WHERE app_time >= date'2026-08-03' GROUP BY CUBE (app_week, is_reloan) LIMIT 5",
    'rollup': "SELECT app_week, is_reloan, COUNT(*) AS c FROM mx.yj_test_table_250225 WHERE app_time >= date'2026-08-03' GROUP BY ROLLUP (app_week, is_reloan) LIMIT 5",
}

for name, sql in tests.items():
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
    print(f'--- {name} ---')
    print('status', r.status_code)
    print(r.text[:400])
    print()

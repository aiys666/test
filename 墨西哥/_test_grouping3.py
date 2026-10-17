import sys, json, base64
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
pq.login()

tests = {
    'grouping_func_with_cube': "SELECT app_week, is_reloan, GROUPING(is_reloan) AS g, COUNT(*) AS c FROM mx.yj_test_table_250225 WHERE app_time >= date'2026-08-03' GROUP BY CUBE (app_week, is_reloan) LIMIT 5",
    'grouping_sets_no_space': "SELECT app_week, COUNT(*) AS c FROM mx.yj_test_table_250225 WHERE app_time >= date'2026-08-03' GROUP BY GROUPING SETS((app_week)) LIMIT 5",
    'cast_varchar_group': "SELECT CAST(is_reloan AS VARCHAR) AS g, COUNT(*) AS c FROM mx.yj_test_table_250225 WHERE app_time >= date'2026-08-03' GROUP BY CAST(is_reloan AS VARCHAR) LIMIT 5",
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

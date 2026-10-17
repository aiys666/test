import sys, json, base64
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
pq.login()

tests = {
    'unnest_two_arrays': "SELECT d, v FROM (SELECT 1 AS a) CROSS JOIN UNNEST(ARRAY['x','y'], ARRAY['1','2']) AS t(d, v)",
    'unnest_on_source': """
SELECT dim_name, dim_group, COUNT(*) AS c
FROM (
    SELECT CAST(is_reloan AS VARCHAR) AS g
    FROM mx.yj_test_table_250225
    WHERE app_time >= date'2026-08-03'
) s
CROSS JOIN UNNEST(ARRAY['是否复贷'], ARRAY[g]) AS t(dim_name, dim_group)
GROUP BY dim_name, dim_group
LIMIT 5
""",
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
    print(r.text[:500])
    print()

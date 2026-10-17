# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
pq.login()

def run(title, sql):
    print("=" * 90)
    print(title)
    print("-" * 90)
    r = pq.query(sql)
    print(r if isinstance(r, str) else r.to_string())

# 1) t4 表 externalid 重复分布（分区表，多 etl_date 快照是最大嫌疑）
run("1) t4 表 externalid 重复分布",
    "select cnt, count(*) n from (select externalid, count(*) cnt from mx.darren_jieqing_base_table_t4 group by 1) t group by 1 order by 1 limit 20")

# 2) t4 表 一个 externalid 的 etl_date 分布（看是不是多天快照）
run("2) t4 表 distinct externalid vs 总行数",
    "select count(*) total, count(distinct externalid) d_ext from mx.darren_jieqing_base_table_t4")

# 3) t5(t2源) 重复分布
run("3) t5(t2源) externalid 重复分布",
    "select cnt, count(*) n from (select externalid, count(*) cnt from mx.darren_jieqing_base_table_t2 group by 1) t group by 1 order by 1 limit 20")

# 4) t10-t17 中可能引入重复：t15(有 externalid 字段?) 直接查各表是否有 externalid 且重复
for tbl in ["t10","t11","t12","t13","t14","t15","t16","t17"]:
    run(f"4) {tbl} 重复分布",
        f"select cnt, count(*) n from (select externalid, count(*) cnt from mx.darren_jieqing_base_table_{tbl} group by 1) t group by 1 order by 1 limit 10")

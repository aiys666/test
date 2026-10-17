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

# 1. base_table 里重复的 externalid 长什么样
run("1) base_table 重复 externalid 样例(取3个看各行差异)",
    """
    select * from mx.darren_jieqing_dt_base_table
    where externalid in (
      select externalid from mx.darren_jieqing_dt_base_table group by 1 having count(*)>1 limit 3
    )
    order by externalid, settle_time
    """)

# 2. 判断 base_table 膨胀来源：t2 表里同一 externalid 的记录数
run("2) t2表(base_t2) externalid 重复分布",
    "select cnt, count(*) n from (select externalid, count(*) cnt from mx.darren_jieqing_base_table_t2 group by 1) t group by 1 order by 1")

# 3. t9 表 externalid 重复分布
run("3) t9表(base_t9) externalid 重复分布",
    "select cnt, count(*) n from (select externalid, count(*) cnt from mx.darren_jieqing_base_table_t9 group by 1) t group by 1 order by 1")

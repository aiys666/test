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

# 定位 base_table 重复来源：各源表 externalid 重复分布
run("1) t0 源表(base_t0) externalid 重复分布",
    "select cnt, count(*) n from (select externalid, count(*) cnt from mx.darren_jieqing_base_table_t0 group by 1) t group by 1 order by 1 limit 20")

run("2) t1 源表(base_t1) externalid 重复分布",
    "select cnt, count(*) n from (select externalid, count(*) cnt from mx.darren_jieqing_base_table_t1 group by 1) t group by 1 order by 1 limit 20")

run("3) t3 源表(base_t3) externalid 重复分布",
    "select cnt, count(*) n from (select externalid, count(*) cnt from mx.darren_jieqing_base_table_t3 group by 1) t group by 1 order by 1 limit 20")

run("4) t8 源表(base_t8) externalid 重复分布",
    "select cnt, count(*) n from (select externalid, count(*) cnt from mx.darren_jieqing_base_table_t8 group by 1) t group by 1 order by 1 limit 20")

# 是否存在 t4 表
run("5) 检查 t4 表是否存在",
    "show tables in mx like '%darren_jieqing_base_table_t4%'")

# 重复 externalid 是否在 dt_table 中被进一步放大
run("6) base_table 重复的 externalid，在 dt_table 中的总行数",
    """
    select count(*) as total_rows, count(distinct externalid) as d_ext
    from mx.darren_jieqing_dt_table
    where externalid in (
      select externalid from mx.darren_jieqing_dt_base_table group by 1 having count(*)>1
    )
    """)

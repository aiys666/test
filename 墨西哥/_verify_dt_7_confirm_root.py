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

# 1) t2 源表(t5) 重复 externalid 总数
run("1) t2源(t5) 重复 externalid 总数",
    "select count(*) dup_ext_cnt from (select externalid from mx.darren_jieqing_base_table_t2 group by 1 having count(*)>1) t")

# 2) t0 源表 重复 externalid 总数(注意 t0 在 base 里已做 rn_outer=1 去重, 不贡献重复)
run("2) t0 源 重复 externalid 总数",
    "select count(*) dup_ext_cnt from (select externalid from mx.darren_jieqing_base_table_t0 group by 1 having count(*)>1) t")

# 3) base_table 各 v3_flag 分布(用于抽样)
run("3) base_table v3_flag 分布",
    "select v3_flag, count(*) n, count(distinct externalid) d_ext from mx.darren_jieqing_dt_base_table group by 1 order by 2 desc")

# 4) adjust_quota_tag 分布
run("4) adjust_quota_tag 分布",
    "select adjust_quota_tag, count(*) n from mx.darren_jieqing_dt_base_table group by 1 order by 2 desc")

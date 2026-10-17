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

# 1. base_table 行数与去重后 externalid 数（应有相同）
run("1) base_table 总行数 vs distinct externalid",
    "select count(*) total, count(distinct externalid) d_externalid from mx.darren_jieqing_dt_base_table")

# 2. dt_table 总行数 vs distinct externalid（一对多，看膨胀）
run("2) dt_table 总行数 vs distinct externalid",
    "select count(*) total, count(distinct externalid) d_externalid from mx.darren_jieqing_dt_table")

# 3. dt_table 按 externalid 重复情况
run("3) dt_table externalid 重复(行数>1)统计",
    "select cnt, count(*) as externalid_num from (select externalid, count(*) cnt from mx.darren_jieqing_dt_table group by 1) t group by 1 order by 1")

# 4. base_table 是否 externalid 唯一（完全重复检查）
run("4) base_table externalid 完全重复检查(应有0)",
    "select count(*) as dup_externalid from (select externalid from mx.darren_jieqing_dt_base_table group by 1 having count(*)>1) t")

# 5. dt_table 是否按 (externalid, jq_mid, settle_time) 唯一
run("5) dt_table 按 externalid+jq_mid+settle_time 重复检查",
    "select count(*) as dup_keys from (select externalid, jq_mid, settle_time from mx.darren_jieqing_dt_table group by 1,2,3 having count(*)>1) t")

# 6. dt_table 一对多的 externalid 里，一个 externalid 最多对应多少行(申请记录)
run("6) dt_table 单 externalid 最大行数",
    "select max(cnt) as max_rows_per_externalid from (select externalid, count(*) cnt from mx.darren_jieqing_dt_table group by 1) t")

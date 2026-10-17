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

# 1) t4 表是否存在（改用 show create table）
run("1) t4 表结构(show create table)",
    "show create table mx.darren_jieqing_base_table_t4")

# 2) t0 中重复的 externalid，是否是完全相同行
run("2) t0 重复 externalid 样例(按 externalid 取重复, 看关键列是否一致)",
    """
    select externalid, count(*) cnt,
           count(distinct credit_amount) d_credit,
           count(distinct daily_max_available_limit) d_daily,
           count(distinct is_settle_adjust_quota_flag) d_flag
    from mx.darren_jieqing_base_table_t0
    group by 1 having count(*)>1 order by 2 desc limit 10
    """)

# 3) base_table 294 重复 externalid 在 t0 的匹配情况
run("3) base_table 294个重复 externalid 在 t0 中的行数分布",
    """
    select b.cnt, count(*) n
    from (
      select externalid from mx.darren_jieqing_dt_base_table group by 1 having count(*)>1
    ) d
    join (select externalid, count(*) cnt from mx.darren_jieqing_base_table_t0 group by 1) b
      on d.externalid = b.externalid
    group by 1 order by 1
    """)

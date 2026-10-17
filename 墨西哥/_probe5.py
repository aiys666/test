# -*- coding: utf-8 -*-
"""探测：mx schema 建表权限 + 订单级 CTE 能否跑通（小范围）。"""
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
print("登录:", pq.login())

# 1. 建一张小测试表（2天数据）验证 create table as 权限
create_sql = """
drop table if exists mx.yuesong_asset_probe
"""
r = pq.execute(create_sql, wait_sec=2)
print("drop:", r)

create_sql = """
create table mx.yuesong_asset_probe as
select date(release_time) d, loan_cycle, count(*) n, sum(contract_amount) s
from ods.s02_loan
where release_time >= timestamp '2026-05-01 00:00:00'
  and release_time < timestamp '2026-05-03 00:00:00'
  and state in (1,2)
group by 1, 2
"""
r = pq.execute(create_sql, wait_sec=3, timeout=300)
print("create:", r)

df = pq.query("select * from mx.yuesong_asset_probe order by d, loan_cycle", wait_sec=2)
print(df.to_string(index=False) if not isinstance(df, str) else df)

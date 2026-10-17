# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
pq.login()

# 检查 V3_3 的 adjust_quota_tag 是否为 null
print("V3_3 的 adjust_quota_tag 分布:")
r = pq.query("select adjust_quota_tag, count(*) n from mx.darren_jieqing_dt_base_table where v3_flag='V3_3' group by 1")
print(r.to_string())

# 抽取10个样本: 覆盖 V3_3/V4_2/V5_1/V5_2/V5_3/V6_1 + 提额/平额/降额
sql = """
with s1 as (  -- V3_3 任意1个(最新)
  select externalid, jq_mid, settle_time, v3_flag, adjust_quota_tag, 1 ord
  from mx.darren_jieqing_dt_base_table
  where v3_flag='V3_3' order by settle_time desc limit 1
),
s2 as (  -- V4_2 降额
  select externalid, jq_mid, settle_time, v3_flag, adjust_quota_tag, 2 ord
  from mx.darren_jieqing_dt_base_table
  where v3_flag='V4_2' and adjust_quota_tag='降额组' order by settle_time desc limit 1
),
s3 as (  -- V5_1 降额
  select externalid, jq_mid, settle_time, v3_flag, adjust_quota_tag, 3 ord
  from mx.darren_jieqing_dt_base_table
  where v3_flag='V5_1' and adjust_quota_tag='降额组' order by settle_time desc limit 1
),
s4 as (  -- V5_2 提额
  select externalid, jq_mid, settle_time, v3_flag, adjust_quota_tag, 4 ord
  from mx.darren_jieqing_dt_base_table
  where v3_flag='V5_2' and adjust_quota_tag='提额组' order by settle_time desc limit 1
),
s5 as (  -- V5_3 降额
  select externalid, jq_mid, settle_time, v3_flag, adjust_quota_tag, 5 ord
  from mx.darren_jieqing_dt_base_table
  where v3_flag='V5_3' and adjust_quota_tag='降额组' order by settle_time desc limit 1
),
s6 as (  -- V6_1 提额
  select externalid, jq_mid, settle_time, v3_flag, adjust_quota_tag, 6 ord
  from mx.darren_jieqing_dt_base_table
  where v3_flag='V6_1' and adjust_quota_tag='提额组' order by settle_time desc limit 1
),
s7 as (  -- V4_2 提额(近期)
  select externalid, jq_mid, settle_time, v3_flag, adjust_quota_tag, 7 ord
  from mx.darren_jieqing_dt_base_table
  where v3_flag='V4_2' and adjust_quota_tag='提额组' order by settle_time desc limit 1
),
s8 as (  -- V5_1 提额(近期)
  select externalid, jq_mid, settle_time, v3_flag, adjust_quota_tag, 8 ord
  from mx.darren_jieqing_dt_base_table
  where v3_flag='V5_1' and adjust_quota_tag='提额组' order by settle_time desc limit 1
),
s9 as (  -- V5_2 降额
  select externalid, jq_mid, settle_time, v3_flag, adjust_quota_tag, 9 ord
  from mx.darren_jieqing_dt_base_table
  where v3_flag='V5_2' and adjust_quota_tag='降额组' order by settle_time desc limit 1
),
s10 as (  -- V5_3 平额
  select externalid, jq_mid, settle_time, v3_flag, adjust_quota_tag, 10 ord
  from mx.darren_jieqing_dt_base_table
  where v3_flag='V5_3' and adjust_quota_tag='平额组' order by settle_time desc limit 1
)
select * from (
  select * from s1 union all select * from s2 union all select * from s3
  union all select * from s4 union all select * from s5 union all select * from s6
  union all select * from s7 union all select * from s8 union all select * from s9
  union all select * from s10
) t order by ord
"""
r = pq.query(sql)
print(r.to_string())

exts = r['externalid'].tolist()
with open('_verify_sample_exts.txt', 'w') as f:
    f.write('\n'.join(exts))
print("\n共", len(exts), "个样本 externalid:")
for e in exts:
    print(e)

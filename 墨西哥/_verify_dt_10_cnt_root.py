# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
pq.login()

with open('_verify_sample_exts.txt') as f:
    exts = [x.strip() for x in f if x.strip()]
ext_in = ",".join("'%s'" % e for e in exts)

def run(title, sql):
    print("=" * 90)
    print(title)
    print("-" * 90)
    r = pq.query(sql)
    print(r if isinstance(r, str) else r.to_string())

# settle_adjust_quota_cnt 差异根因: 宽表里该字段来自 t7 = t2源按 mid_t2 取 createtime 最早(rn=1)
run("1) t7逻辑: t2源按mid_t2取rn=1的 settle_adjust_quota_cnt",
    f"""
    select mid_t2, settle_adjust_quota_cnt, createtime, rn
    from (
      select mid_t2,
        row_number() over (partition by mid_t2 order by createtime) as rn,
        settle_adjust_quota_cnt, createtime
      from mx.darren_jieqing_base_table_t2
      where mid_t2 in (select distinct jq_mid from mx.darren_jieqing_dt_base_table where externalid in ({ext_in}))
    ) t where rn = 1
    """)

# 对比: 该mid在t2源里所有记录(看为什么rn=1那条cnt=0)
run("2) t2源中相关mid的所有记录",
    f"""
    select mid_t2, externalid, settle_adjust_quota_cnt, last_credit_amount, createtime
    from mx.darren_jieqing_base_table_t2
    where mid_t2 in (select distinct jq_mid from mx.darren_jieqing_dt_base_table where externalid in ({ext_in}))
    order by mid_t2, createtime
    """)

# 复贷授信 t7(productid=196) 是否存在对应记录
run("3) 复贷授信(productid=196) 10样本是否命中",
    f"""
    select biz_id, cast(json_extract(outputdata,'$.credit_amount') as double) sx_credit,
      cast(json_extract(outputdata,'$.daily_max_available_limit') as double) sx_daily
    from ods.s21_risk_strategy_record
    where productid=196 and strategytype='CHAMPION'
      and cast(biz_id as varchar) in (select distinct jq_mid from mx.darren_jieqing_dt_base_table where externalid in ({ext_in}))
    order by biz_id
    """)

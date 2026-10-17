# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
pq.login()

with open('_verify_sample_exts.txt') as f:
    exts = [x.strip() for x in f if x.strip()]

mids = ",".join("'%s'" % e.split('_')[0] for e in exts)
ext_in = ",".join("'%s'" % e for e in exts)

def run(title, sql):
    print("=" * 90)
    print(title)
    print("-" * 90)
    r = pq.query(sql)
    print(r if isinstance(r, str) else r.to_string())

# 1) 复贷授信(productid=196) 10样本mid是否命中
run("1) 复贷授信(productid=196) 命中情况",
    f"""
    select cast(biz_id as varchar) biz_id,
      cast(json_extract(outputdata,'$.credit_amount') as double) sx_credit,
      cast(json_extract(outputdata,'$.daily_max_available_limit') as double) sx_daily
    from ods.s21_risk_strategy_record
    where productid=196 and strategytype='CHAMPION'
      and cast(biz_id as varchar) in ({mids})
    """)

# 2) dt_table 中10样本的复贷授信字段 + 申请漏斗关联字段
run("2) dt_table 10样本复贷授信与申请漏斗字段",
    f"""
    select externalid,
      sx_credit_amount, sx_daily_max_available_limit,
      count(*) over (partition by externalid) as row_cnt
    from mx.darren_jieqing_dt_table
    where externalid in ({ext_in})
    """)

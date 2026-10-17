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

# 1) 最终表 dt_table 中 10 样本的核心字段
run("1) dt_table 10样本核心字段",
    f"""
    select externalid, jq_mid, settle_time,
      credit_amount, daily_max_available_limit, is_settle_adjust_quota_flag,
      last_credit_amount, settle_adjust_quota_cnt,
      champion_global_limit, champion_fd_grantcredit_global_amount_uncapped,
      champion_fd_grantcredit_global_amount_add_cap,
      v3_flag, adjust_quota_tag, limit_recommend_grp
    from mx.darren_jieqing_dt_base_table
    where externalid in ({ext_in})
    order by settle_time
    """)

# 2) t0 源表原始 credit_amount / daily_max_available_limit
run("2) t0 源表原始记录",
    f"""
    select externalid, mid as jq_mid, endtime as settle_time,
      cast(json_extract_scalar(outputdata,'$.credit_amount') as double) credit_amount,
      cast(json_extract_scalar(outputdata,'$.daily_max_available_limit') as double) daily_max
    from ods.s21_risk_strategy_record
    where productid=428 and strategytype='CHAMPION'
      and externalid in ({ext_in})
    order by externalid, endtime
    """)

# 3) t1 源表 is_settle_adjust_quota_flag
run("3) t1 源表(modelmainid=1063)",
    f"""
    select externalid, cast(json_extract_scalar(outputdata,'$.is_settle_adjust_quota_flag') as double) flag
    from ods.s21_risk_model_record
    where modelmainid=1063 and strategytype='CHAMPION'
      and externalid in ({ext_in})
    order by externalid, createtime desc
    """)

# 4) t2 源表(modelmainid=1364) 低额首次结清
run("4) t2 源表(modelmainid=1364)",
    f"""
    select externalid, mid as mid_t2,
      cast(json_extract_scalar(inputdata,'$.settle_adjust_quota_cnt') as double) settle_adjust_quota_cnt,
      cast(json_extract_scalar(inputdata,'$.last_credit_amount') as double) last_credit_amount,
      cast(json_extract_scalar(outputdata,'$.low_limit_first_settle_increase_tag') as double) low_tag
    from ods.s21_risk_model_record
    where modelmainid=1364 and strategytype='CHAMPION'
      and externalid in ({ext_in})
    order by externalid, createtime desc
    """)

# 5) t3 源表 全局额度cap
run("5) t3 源表(modelId 2402/3033/3114/4631)",
    f"""
    select externalid,
      max(cast(json_extract_scalar(inputdata,'$.fd_grantcredit_global_amount_uncapped') as double)) uncapped,
      max(cast(json_extract_scalar(inputdata,'$.fd_grantcredit_global_amount_add_cap') as double)) add_cap,
      max(cast(json_extract_scalar(outputdata,'$.global_limit') as double)) global_limit
    from ods.s21_risk_model_record
    where modelId in (2402,3033,3114,4631) and strategytype='CHAMPION' and productid=428
      and externalid in ({ext_in})
    group by externalid
    """)

# -*- coding: utf-8 -*-
"""口径核查 & V6_1 & 发临额人群画像"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None); pd.set_option('display.width', 420)

def q(sql, tag="", show=120):
    print("="*130); print(tag)
    r = pq.query(sql)
    if isinstance(r, str): print("[ERR]", r[:1200]); return None
    if r is None or len(r)==0: print("[空]"); return None
    print(r.head(show).to_string() if len(r)>show else r.to_string())
    print(f"[rows={len(r)}]"); return r

# ============================================================
# 口径核查1: yj表 vs funnel表 进件数对比 (复贷, 0903-0922)
# ============================================================
q("""
select 'yj_table' src, count(*) app_cnt, count(if(if_issue=1,1,null)) issue_cnt
from mx.yj_test_table_250225
where is_reloan='old' and app_date >= date'2026-09-03' and app_date < date'2026-09-22'
union all
select 'funnel' src, count(*) app_cnt, count(if(if_issue=1,1,null)) issue_cnt
from mx.wxs_application_funnel
where is_reloan='old' and tenant='yawey'
  and app_time >= cast('2026-09-03 00:00:00.000' as timestamp)
  and app_time <  cast('2026-09-22 00:00:00.000' as timestamp)
""", "C0 进件数: yj表 vs funnel表 (复贷 9/3-9/22)")

# 口径核查2: yj表字段 if_issue, issue_date 分布
q("""
select if_issue, count(*) cnt
from mx.yj_test_table_250225
where is_reloan='old' and app_date >= date'2026-09-03' and app_date < date'2026-09-22'
group by 1 order by 1
""", "C1 yj表 if_issue 取值分布")

# ============================================================
# V6_1 策略字段定位
# ============================================================
q("""
select column_name
from information_schema.columns
where table_schema='mx' and table_name='yj_test_table_250225'
  and (column_name like '%v6%' or column_name like '%V6%' or column_name like '%strategy%' or column_name like '%test_flag%')
order by 1
""", "C2 yj表中 V6/strategy/test_flag 相关字段")

# ============================================================
# 发临额人群画像 (V5_3组C, P2, 放款口径, issue_tag 1 vs 0)
# ============================================================
HASH = """case when from_base(substr(to_hex(sha256(to_utf8('20260811'||y.credit_no||y.app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.7 then 'A'
     when from_base(substr(to_hex(sha256(to_utf8('20260811'||y.credit_no||y.app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.3 then 'C'
     else 'B' end"""

q(f"""
select
  cast(issue_tag as varchar) tag,
  count(*) cnt,
  round(avg(real_issue_amount),0) loan_avg,
  round(avg(temp_grant_amount)/1000.0,1) temp_avg_k,
  round(sum(t0_overdue_amount_1)/nullif(sum(t0_should_amt_1),0)*100,2) t0_rate,
  -- 评级分布
  round(avg(cast(new_grade_level as double)),2) grade_avg,
  count(if(new_grade_level between 1 and 5,1,null)) g1_5,
  count(if(new_grade_level between 6 and 8,1,null)) g6_8,
  count(if(new_grade_level >= 9,1,null)) g9p,
  -- 产品
  count(if(product_name_new like '%28%',1,null)) p28_cnt,
  count(if(product_name_new like '%14%',1,null)) p14_cnt,
  count(if(product_name_new like '%7%',1,null)) p7_cnt,
  -- 额度使用率相关
  round(avg(credit_amount),0) credit_avg,
  round(avg(loan_contract_amount),0) contract_avg,
  -- 复贷次数
  round(avg(repayment_clearing_count_tenant),1) clear_cnt_avg,
  round(avg(repayment_clearing_count_index_tenant),1) clear_idx_avg
from mx.yj_test_table_250225 y
where if_issue=1 and is_reloan='old' and {HASH}='C'
  and app_date >= date'2026-09-03' and app_date < date'2026-09-22'
group by 1 order by 1
""", "C3 V5_3组(C)放款 发临额tag1 vs 未发tag0 人群画像")

# 发临额人群画像: 全复贷(不限hash) issue_tag 1 vs 0, 对比客户资质
q(f"""
select
  cast(issue_tag as varchar) tag,
  count(*) cnt,
  round(sum(t0_overdue_amount_1)/nullif(sum(t0_should_amt_1),0)*100,2) t0_rate,
  round(avg(cast(new_grade_level as double)),2) grade_avg,
  count(if(new_grade_level <= 5,1,null))*100.0/count(*) g1_5_pct,
  count(if(new_grade_level between 6 and 8,1,null))*100.0/count(*) g6_8_pct,
  count(if(new_grade_level >= 9,1,null))*100.0/count(*) g9p_pct,
  round(avg(credit_amount),0) credit_avg,
  round(avg(real_issue_amount),0) loan_avg,
  round(avg(temp_grant_amount)/1000.0,1) temp_avg_k,
  round(avg(repayment_clearing_count_tenant),1) clear_cnt,
  round(avg(fd_use_creditamount_score_v1),2) score_avg
from mx.yj_test_table_250225 y
where if_issue=1 and is_reloan='old'
  and app_date >= date'2026-08-10' and app_date < date'2026-09-22'
group by 1 order by 1
""", "C4 全复贷放款(8/10-9/22) 发临额 vs 未发 整体画像对比")

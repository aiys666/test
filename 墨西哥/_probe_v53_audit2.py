# -*- coding: utf-8 -*-
"""深查: funnel真实进件口径 / fd_changepro_v6_1 / 画像修正"""
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

# 1. funnel表全量复贷进件(不加过滤) + 授信/风险拒绝字段
q("""
select count(*) total,
  count(if(is_reloan='old',1,null)) old_cnt,
  count(if(is_reloan='old' and tenant='yawey',1,null)) old_yawey_cnt,
  count(if(is_reloan='old' and if_issue=1,1,null)) old_issue
from mx.wxs_application_funnel
where app_time >= cast('2026-09-03 00:00:00.000' as timestamp)
  and app_time <  cast('2026-09-22 00:00:00.000' as timestamp)
""", "D0 funnel全量(9/3-9/22) 复贷/放款计数")

# 2. funnel表是否有授信拒绝/拒绝原因字段
q("""
select column_name
from information_schema.columns
where table_schema='mx' and table_name='wxs_application_funnel'
  and (column_name like '%reject%' or column_name like '%deny%' or column_name like '%credit_result%'
       or column_name like '%result%' or column_name like '%status%' or column_name like '%approve%')
order by 1
""", "D1 funnel拒绝/状态相关字段")

# 3. fd_changepro_v6_1 分布
q("""
select fd_changepro_v6_1, count(*) cnt, count(if(if_issue=1,1,null)) issue_cnt
from mx.yj_test_table_250225
where is_reloan='old' and app_date >= date'2026-09-01' and app_date < date'2026-10-06'
group by 1 order by 1
""", "D2 fd_changepro_v6_1 分布(9/1后)")

# 4. fd_changepro_v6_1 按日 (看0922是否有跳变)
q("""
select app_date, fd_changepro_v6_1, count(*) cnt, count(if(if_issue=1,1,null)) issue
from mx.yj_test_table_250225
where is_reloan='old' and app_date >= date'2026-09-15' and app_date < date'2026-10-01'
group by 1,2 order by 1,2
""", "D3 fd_changepro_v6_1 按日分布(9/15-9/30)")

HASH = """case when from_base(substr(to_hex(sha256(to_utf8('20260811'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.7 then 'A'
     when from_base(substr(to_hex(sha256(to_utf8('20260811'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.3 then 'C'
     else 'B' end"""

# 5. 修正画像: V5_3组(C)放款 temp_credit_amount_issue_tag 1 vs 0
q(f"""
select
  cast(temp_credit_amount_issue_tag as varchar) tag,
  count(*) cnt,
  round(avg(real_issue_amount),0) loan_avg,
  round(avg(temp_grant_amount)/1000.0,1) temp_avg_k,
  round(sum(t0_overdue_amount_1)/nullif(sum(t0_should_amt_1),0)*100,2) t0_rate,
  round(avg(cast(new_grade_level as double)),2) grade_avg,
  round(count(if(new_grade_level <= 5,1,null))*100.0/count(*),1) g1_5_pct,
  round(count(if(new_grade_level between 6 and 8,1,null))*100.0/count(*),1) g6_8_pct,
  round(count(if(new_grade_level >= 9,1,null))*100.0/count(*),1) g9p_pct,
  round(avg(credit_amount),0) credit_avg,
  round(avg(loan_contract_amount),0) contract_avg,
  round(avg(repayment_clearing_count_tenant),1) clear_cnt,
  round(avg(fd_use_creditamount_score_v1),2) score_avg,
  -- 产品
  round(count(if(product_name_new like '%28%',1,null))*100.0/count(*),1) p28_pct,
  round(count(if(product_name_new like '%14%',1,null))*100.0/count(*),1) p14_pct,
  round(count(if(product_name_new like '%7%',1,null))*100.0/count(*),1) p7_pct
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old' and {HASH}='C'
  and app_date >= date'2026-09-03' and app_date < date'2026-09-22'
group by 1 order by 1
""", "D4 V5_3组(C)放款 发临额(tag1) vs 未发(tag0) 画像(P2)")

# 6. 全复贷 发临额 vs 未发 画像(8/10-9/22)
q(f"""
select
  cast(temp_credit_amount_issue_tag as varchar) tag,
  count(*) cnt,
  round(sum(t0_overdue_amount_1)/nullif(sum(t0_should_amt_1),0)*100,2) t0_rate,
  round(avg(cast(new_grade_level as double)),2) grade_avg,
  round(count(if(new_grade_level <= 5,1,null))*100.0/count(*),1) g1_5_pct,
  round(count(if(new_grade_level between 6 and 8,1,null))*100.0/count(*),1) g6_8_pct,
  round(count(if(new_grade_level >= 9,1,null))*100.0/count(*),1) g9p_pct,
  round(avg(credit_amount),0) credit_avg,
  round(avg(real_issue_amount),0) loan_avg,
  round(avg(temp_grant_amount)/1000.0,1) temp_avg_k,
  round(avg(repayment_clearing_count_tenant),1) clear_cnt,
  round(avg(fd_use_creditamount_score_v1),2) score_avg,
  round(count(if(product_name_new like '%28%',1,null))*100.0/count(*),1) p28_pct
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old'
  and app_date >= date'2026-08-10' and app_date < date'2026-09-22'
group by 1 order by 1
""", "D5 全复贷放款(8/10-9/22) 发临额 vs 未发 画像")

# 7. 发临额人群按评分分层坏账(DID意义: 同资质下发与不发的差异)
q(f"""
select
  cast(temp_credit_amount_issue_tag as varchar) tag,
  case when fd_use_creditamount_score_v1 <= 0 then 'S1_low<=0'
       when fd_use_creditamount_score_v1 <= 3 then 'S2_mid'
       when fd_use_creditamount_score_v1 = 5 then 'S3_hi5'
       else 'null' end sg,
  count(*) cnt,
  round(sum(t0_overdue_amount_1)/nullif(sum(t0_should_amt_1),0)*100,2) t0_rate,
  round(avg(cast(new_grade_level as double)),2) grade
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old'
  and app_date >= date'2026-08-10' and app_date < date'2026-09-22'
group by 1,2 order by 2,1
""", "D6 发临额×评分档 坏账(控制资质后发与不发差异)")

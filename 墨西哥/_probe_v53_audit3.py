# -*- coding: utf-8 -*-
"""评级字段 / V6_1拒尾档位 / TR口径多版本"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None); pd.set_option('display.width', 420)

def q(sql, tag="", show=150):
    print("="*130); print(tag)
    r = pq.query(sql)
    if isinstance(r, str): print("[ERR]", r[:1500]); return None
    if r is None or len(r)==0: print("[空]"); return None
    print(r.head(show).to_string() if len(r)>show else r.to_string())
    print(f"[rows={len(r)}]"); return r

# 1. 评级字段
q("""
select column_name
from information_schema.columns
where table_schema='mx' and table_name='yj_test_table_250225'
  and (column_name like '%grade%' or column_name like '%level%' or column_name like '%credit_level%')
order by 1
""", "E0 yj表评级相关字段")

# 2. V6_1 各档位放款率 (看哪个档位被拒尾)
q("""
select fd_changepro_v6_1, count(*) app, count(if(if_issue=1,1,null)) issue,
  round(count(if(if_issue=1,1,null))*100.0/count(*),1) issue_rate
from mx.yj_test_table_250225
where is_reloan='old' and app_date >= date'2026-09-15' and app_date < date'2026-10-01'
group by 1 order by 1
""", "E1 fd_changepro_v6_1 各档放款率(9/15-9/30)")

# 3. V6_1 按日: 看0922前后各档放款率变化
q("""
select
  case when app_date < date'2026-09-22' then 'before_0922' else 'after_0922' end as period,
  fd_changepro_v6_1, count(*) app, count(if(if_issue=1,1,null)) issue,
  round(count(if(if_issue=1,1,null))*100.0/count(*),1) issue_rate
from mx.yj_test_table_250225
where is_reloan='old' and app_date >= date'2026-09-15' and app_date < date'2026-09-29'
group by 1,2 order by 2,1
""", "E2 V6_1 0922前后 各档放款率变化")

# 4. TR口径探索: 多种定义
q("""
select
  count(*) app_cnt,
  count(if(if_issue=1,1,null)) issue_cnt,
  count(if(if_issue=1,1,null))*1.0/count(*) tr_by_count,
  round(sum(if(if_issue=1,real_issue_amount,null))/1000.0,0) issue_amt_k,
  round(sum(credit_amount)/1000.0,0) credit_amt_k,
  round(sum(if(if_issue=1,real_issue_amount,null))/nullif(sum(credit_amount),0)*100,2) tr_by_amt
from mx.yj_test_table_250225
where is_reloan='old' and app_date >= date'2026-09-03' and app_date < date'2026-09-22'
""", "E3 TR多口径: 笔数转化率 vs 金额/授信转化率")

# 5. funnel表完整链路: 是否有授信环节字段
q("""
select column_name
from information_schema.columns
where table_schema='mx' and table_name='wxs_application_funnel'
  and (column_name like '%credit%' or column_name like '%limit%' or column_name like '%quota%')
order by 1 limit 40
""", "E4 funnel表额度/授信相关字段")

# 6. 用 credit_level 替代 new_grade_level 画像 (V5_3 C组 tag1 vs tag0)
HASH = """case when from_base(substr(to_hex(sha256(to_utf8('20260811'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 > 0.7 then 'A'
     when from_base(substr(to_hex(sha256(to_utf8('20260811'||credit_no||app_group_sha256))),1,4),16)/65536.0000000000000000 <= 0.3 then 'C'
     else 'B' end"""

q(f"""
select
  cast(temp_credit_amount_issue_tag as varchar) tag,
  count(*) cnt,
  round(avg(real_issue_amount),0) loan_avg,
  round(avg(temp_grant_amount)/1000.0,1) temp_avg_k,
  round(sum(t0_overdue_amount_1)/nullif(sum(t0_should_amt_1),0)*100,2) t0_rate,
  round(avg(cast(credit_level as double)),2) grade_avg,
  round(count(if(credit_level <= 5,1,null))*100.0/count(*),1) g1_5_pct,
  round(count(if(credit_level between 6 and 8,1,null))*100.0/count(*),1) g6_8_pct,
  round(count(if(credit_level >= 9,1,null))*100.0/count(*),1) g9p_pct,
  round(avg(credit_amount),0) credit_avg,
  round(avg(loan_contract_amount),0) contract_avg,
  round(avg(repayment_clearing_count_tenant),1) clear_cnt,
  round(avg(fd_use_creditamount_score_v1),2) score_avg,
  round(count(if(product_name_new like '%28%',1,null))*100.0/count(*),1) p28_pct,
  round(count(if(product_name_new like '%14%',1,null))*100.0/count(*),1) p14_pct
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old' and {HASH}='C'
  and app_date >= date'2026-09-03' and app_date < date'2026-09-22'
group by 1 order by 1
""", "E5 V5_3组(C)放款 tag1 vs tag0 画像(P2,用credit_level)")

# 7. 全复贷 发临额×评分档 坏账(控制资质)
q(f"""
select
  cast(temp_credit_amount_issue_tag as varchar) tag,
  case when fd_use_creditamount_score_v1 <= 0 then 'S1_low'
       when fd_use_creditamount_score_v1 <= 3 then 'S2_mid'
       when fd_use_creditamount_score_v1 = 5 then 'S3_hi'
       else 'null' end sg,
  count(*) cnt,
  round(sum(t0_overdue_amount_1)/nullif(sum(t0_should_amt_1),0)*100,2) t0_rate,
  round(avg(cast(credit_level as double)),2) grade
from mx.yj_test_table_250225
where if_issue=1 and is_reloan='old'
  and app_date >= date'2026-08-10' and app_date < date'2026-09-22'
group by 1,2 order by 2,1
""", "E6 发临额×评分档 坏账(控制资质)")

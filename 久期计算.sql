SELECT c.loan_year,c.loan_month
,c.product_type
,c.loan_term
,haircut_rate 
,sum(day_diff*should_capital) as day_diff_capital_without_haircut 
,sum(day_diff*should_capital*(1-haircut_rate)) as day_diff_capital 
,sum(should_capital) as should_capital 
from (

  SELECT camera_id 
  ,date_diff('day',date(create_time),coalesce(date(fact_time),date(should_time))) as day_diff 
  ,date(create_time) as issue_date 
  ,should_capital 
from ods.s02_loan_repayment 
) a 
left join (

  SELECT biz_id,haircut_amount*1.00/contract_amount as haircut_rate 
  from ind.ba_asset_base_info 
  where if_issue=1
  ) b 
  on a.camera_id=try_cast(b.biz_id as bigint) 
join (
    
  select product_type,id_loan as camera_id
  ,loan_term
  ,substr(cast(disbursement_date as varchar),1,7) as loan_month 
  ,substr(cast(disbursement_date as varchar),1,4) as loan_year 
from ind.ind_daily_ojk_monthly_report 
where data_date='2026-02-28' 
and ((product_type='R-30' and substr(cast(disbursement_date as varchar),1,7)<='2025-09') 
or (product_type!='R-30' and substr(cast(disbursement_date as varchar),1,7)<='2025-12'))
) c 
on a.camera_id=c.camera_id 
group by 1,2,3,4,5 
order by 1,2,3
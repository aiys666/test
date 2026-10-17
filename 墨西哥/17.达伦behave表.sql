 

drop table if exists mx.darren_behave_var;
create table if not exists mx.darren_behave_var as
with var_basetable as (
  select
    a.biz_id,
    a.create_time,
    b.biz_id as his_biz_id,
    b1.state,
    b1.fact_time,
    b1.rid,
    c1.finish_time,
    case when other_loan.other_release_time is not null then 1 else 0 end as other_app_has_loan_flag
  from (
    select 
      t0.biz_id, t0.create_time, t0.credit_no, t0.app_channel,
      t1.app_group
    from ods_view_presto.s05_creditx_order t0
    left join ods.s08_app_category_mapping t1 on t0.app_channel = t1.app_channel
  ) a
  left join (
    select 
      t0.biz_id, t0.credit_no, t0.create_time, t0.app_channel,
      t1.app_group
    from ods_view_presto.s05_creditx_order t0
    left join ods.s08_app_category_mapping t1 on t0.app_channel = t1.app_channel
  ) b on a.credit_no = b.credit_no and a.create_time > b.create_time and a.app_group = b.app_group
  left join ods_view_presto.s02_loan_repayment b1 on cast(b.biz_id as bigint) = b1.camera_id
  left join ods_view_presto.s02_loan c1 on cast(b.biz_id as bigint) = c1.camera_id
  left join (
    select distinct
      b_other.credit_no,
      b_other.app_channel,
      b1_other.create_time as other_release_time
    from ods_view_presto.s05_creditx_order b_other
    left join ods.s08_app_category_mapping t1 on b_other.app_channel = t1.app_channel
    left join ods_view_presto.s02_loan_repayment b1_other on cast(b_other.biz_id as bigint) = b1_other.camera_id
    where b1_other.camera_id is not null
  ) other_loan on a.credit_no = other_loan.credit_no and a.app_channel != other_loan.app_channel and a.create_time > other_loan.other_release_time
)
select
  biz_id,
  count(distinct case when state in (1,3,5) and fact_time < create_time then rid end) as repayment_clearing_count_index_tenant,
  count(distinct case when state in (1,3,5) and finish_time < create_time then his_biz_id end) as repayment_clearing_count_tenant,
  max(other_app_has_loan_flag) as other_app_has_loan_flag
from var_basetable
group by biz_id;
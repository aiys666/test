@presto

DROP TABLE IF EXISTS tmp.tmp_reloan_loan_info_ind;
CREATE TABLE tmp.tmp_reloan_loan_info_ind AS
SELECT  a.biz_id
       ,CASE WHEN baseinfo_onloan_hit_mid >= 1 THEN 'OLD_PLUS'
             WHEN double_loan = 0 THEN 'NEW'
             WHEN double_loan = 1 THEN 'OLD_SINGLE' END AS is_reloan
FROM ods.s05_creditx_order a
LEFT JOIN
(
   SELECT  cid
         ,cast(json_extract(value,'$.baseinfo_onloan_hit_mid') AS bigint) AS baseinfo_onloan_hit_mid
         ,row_number() over (partition by cid ORDER BY create_time) rn
  FROM ods.s09_os_variable_log
  WHERE name = 'baseinfo_onloan_hit_mid' 
)b
ON a.BIZ_ID = b.cid AND rn = 1
;

--TODO
    drop table if exists tmp.tmp_loan_info_ind;
    create table tmp.tmp_loan_info_ind as
    select cast(l.lid as bigint) as lid, 
           cast(l.tenant_id as bigint) as tenant_id, 
           t.name as tenant_name,
           l.app_channel,
           case when l.app_channel = '850792dc-e673-4131-8d0f-b0a70b2772be' then 'samir'
            else 'none' end as app_channel_name,
           cast(co.cust_id as bigint) as cust_id,
           cast(l.customer_id as bigint) as mid, 
           cast(co.biz_id as bigint) as order_no, 
           cast(l.product_id as bigint) as product_id,
           l.product_name as product_name,
           cast(l.amount as bigint) as arrived_amt,
           cast(l.contract_amount as bigint) as contract_amt,
           cast(l.haircut_amount as bigint) as haircut_amt, 
           l.interest, 
           cast(l.rate_type as bigint) as rate_type_code, 
           case when l.rate_type =100 then 'daily_rate' else 'others' end as rate_type_name, 
           cast(l.rate as bigint) as rate, 
           cast(l.loan_indexs as bigint) as loan_indexs,
           cast(l.loan_cycle as bigint) as loan_period,
           cast(l.loan_cycle_unit as bigint) as loan_period_attr,
           cast(l.paid_type as bigint) as repayment_type_code,
           l.paid_type as repayment_type_name,
           l.create_time as loan_create_time,
           l.release_time,
           date(l.trade_start_time) as trade_start_date, 
           date(l.trade_end_time) as trade_end_date, 
           l.finish_time,
           cast(l.state as bigint) as lid_status_code, 
           l.state   as lid_status_name, 
           cast(l.fine_scale as bigint) as fine_scale, 
           cast(coalesce(d.exchange_rate_to_dollar,400) as decimal(20,6)) as exchange_rate_to_dollar,
           cast(64 as decimal(20,6)) as exchange_rate_to_cny,
           localtimestamp as load_time,
           tl.is_reloan as double_loan,
           co.source as loan_source,
           l.cancel_time as cancel_time,
           ld.lend_customer_id as lender_id,
           la.account_name as lender_name
      from ods.s02_loan l
     inner join ods.s05_creditx_order co
        on l.tenant_id=cast(co.tenant_id as bigint) and l.camera_id=cast(co.biz_id as bigint)
     left join ods.s07_t_tenant t
        on co.tenant_id = t.id
     left join dim.dim_exchange_rate_cost d on d.month_id = to_char(l.create_time,'yyyymm')  and d.account_currency='IDR'
     left join tmp.tmp_reloan_loan_info_ind tl on l.camera_id=cast(tl.biz_id as bigint)
     left join ods.s02_lend ld on l.camera_id= ld.camera_id
     left join ods.s02_lend_account la on ld.lend_customer_id= la.customer_id
    where co.biz_id<>'null'
    ;

@hive
 insert overwrite table dwd.dwd_loan_info select * from tmp.tmp_loan_info_ind;
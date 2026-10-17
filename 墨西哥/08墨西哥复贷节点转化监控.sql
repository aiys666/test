SELECT * from mx.wxs_aurora_za



--:{author=tudalun, department=墨西哥风险策略, dagName=wxs_wide_table_create, taskName=wxs_aurora_za}
drop table if exists mx.wxs_aurora_za
;
--:{author=tudalun, department=墨西哥风险策略, dagName=wxs_wide_table_create, taskName=wxs_aurora_za}
create table if not exists mx.wxs_aurora_za as 
select app_date as apply_date,
       app_week as apply_week,
       app,
       tenant,
       app_group,
       double_loan,
       app_version,
       case when app_version >= '1.2.1' and a.app_channel='56c660de-3549-4482-9ad5-0404eef0d70d' then '置空版本' else '其他版本' end as app_status,
       case when app_version >= '1.2.4' and a.app_channel='56c660de-3549-4482-9ad5-0404eef0d70d' then '置空版本' else '其他版本' end as msg_status,
       c.channel_category,
       lower(source) source,
       case when fd_finishloan_num_main >=4 then 4 else fd_finishloan_num_main end fd_finishloan_num_main,
       repayment_clearing_count_index_tenant,
       one_click_loan_tag,
          count(distinct a.biz_id) as apply_cnt
         ,sum(if_in_fu_anti_fraud) qfc
         ,sum(if_fu_anti_fraud_passed) qfp  
         ,sum(if_in_fu_anti_fraud_weak) rfc
         ,sum(if_fu_anti_fraud_weak_passed) rfp
		     ,sum(if_in_fu_model) mc
         ,sum(if_fu_model_passed) mp 
         ,sum(if_in_fu_sx_refuse) sxrc
         ,sum(if_fu_sx_refuse_passed) sxrp
         ,sum(if_in_sx) sxc
         ,sum(if_sx_passed) sxp 
         ,sum(if_sx_passed_6h) sxp_6h
         ,sum(if_sx_passed_24h) sxp_24h
		     ,sum(if_in_fu_external_data) sfc
         ,sum(if_in_fu_post_anti_fraud_rerun) qfcr
         ,sum(if_fu_post_anti_fraud_rerun_passed) qfcrp
         ,sum(if_in_fu_post_weak_anti_fraud_rerun) rfcr
         ,sum(if_fu_post_weak_anti_fraud_rerun_passed) rfcrp
         ,sum(if_in_fu_post_model_reject_rerun) mcr
         ,sum(if_fu_post_model_reject_rerun_passed) mcrp
         ,sum(if_fu_external_data_passed) sfp
         ,sum(if(if_fu_post_anti_fraud_rerun_passed = 1 and fd_high_pass_label = 1,1,if_fu_external_data_passed)) if_issue_except_loan_fail
         ,sum(if_issue) if_issue
         ,sum(should_capital) as should_capital
         ,sum(if_in_sx_24h) as if_in_sx_24h
         ,sum(if_in_sx_72h) as if_in_sx_72h
         ,sum(if_in_sx_120h) as if_in_sx_120h
         ,sum(if_sx_passed_24h) as if_sx_passed_24h
         ,sum(if_sx_passed_72h) as if_sx_passed_72h
         ,sum(if_sx_passed_120h) as if_sx_passed_120h
from mx.wxs_application_funnel a
left join mx.zzy_behave_var0903_aurora aa on a.biz_id = aa.biz_id        
-- left join (SELECT biz_id,app,app_group,app_week,if_in_fu_anti_fraud,if_fu_anti_fraud_passed,if_in_fu_anti_fraud_weak,if_fu_anti_fraud_weak_passed,if_in_fu_model,if_fu_model_passed,if_in_sx,if_sx_passed,if_sx_passed_6h,if_sx_passed_24h,if_in_fu_external_data,if_fu_external_data_passed,if_in_fu_sx_refuse,if_fu_sx_refuse_passed from mx.wxs_application_funnel)  b on a.biz_id=b.biz_id 
left join
(SELECT 
mid,
new_media_source channel_category
FROM mx.gm_attribution_detail) c
on a.mid=c.mid
left join (
  select biz_id,
    repayment_clearing_count_index_tenant
  from mx.darren_behave_var) d 
on a.biz_id = d.biz_id
where date_diff('day',date(apply_time),current_date)<184
and a.is_reloan='old'
group by 1,2,3,4,5,6,7,8,9,10,11,12,13,14
;
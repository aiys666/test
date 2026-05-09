
drop table if exists ind.ys_zhouyizhoubao_tmp;
create table IF NOT EXISTS ind.ys_zhouyizhoubao_tmp as

select 
   a1.reg_week
   ,a2.loan_cnt 
   ,a2.contract_amt 
   ,a2.release_amt 
   ,a2.per_loan
   ,a2.fst_loan_cnt 
   ,a2.fst_contract_amt 
   ,a2.fst_avg_period
   ,a2.fst_per_loan
   ,a2.rl_loan_cnt 
   ,a2.rl_contract_amt 
   ,a2.rl_avg_period
   ,a2.rl_per_loan
   ,a2.rl_ratio
   ,a5.spend
   ,a7.install_cnt
   ,a1.reg
   ,a3.fst_apply_cnt
   ,a2.fst_loan_cnt as fst_loan_cnt2
   ,a3.approve_rate
   ,a3.fst_approve_rate
   ,a3.fst_machine_pass_rate  
   ,a3.fst_manual_inflow_rate 
   ,a3.fst_manual_pass_rate  
   ,a3.fst_external_pass_rate 
   ,a3.sec_approve_rate
   ,a3.sec_machine_pass_rate  
   ,a3.sec_manual_inflow_rate 
   ,a3.sec_datapre2_pass_rate  
   ,a3.sec_external_pass_rate
   ,a4.t7_collect
   ,a4.t15_collect
   ,a4.t30_collect
   ,a4.t0_ovd
   ,a4.t7_ovd
   ,a4.t15_ovd
   ,a4.t30_ovd
   ,a4.fst_t0_ovd
   ,a4.fst_t7_ovd
   ,a4.fst_t15_ovd
   ,a4.fst_t30_ovd
   ,a4.rl_t0_ovd
   ,a4.rl_t7_ovd
   ,a4.rl_t15_ovd
   ,a4.rl_t30_ovd
   ,a6.overdue_rate_1_0_total
   ,a6.overdue_rate_1_7_total
   ,a6.overdue_rate_1_30_total
   ,a6.overdue_rate_3_30_total
   ,a6.overdue_rate_6_30_total
   ,a6.overdue_rate_1_0_new
   ,a6.overdue_rate_1_7_new
   ,a6.overdue_rate_1_30_new
   ,a6.overdue_rate_3_30_new
   ,a6.overdue_rate_6_30_new
   ,a6.overdue_rate_1_0_old
   ,a6.overdue_rate_1_7_old
   ,a6.overdue_rate_1_30_old
   ,a6.overdue_rate_3_30_old
   ,a6.overdue_rate_6_30_old
   from
    (SELECT
    to_char(date_trunc('week',date(reg_time)),'yyyy-mm-dd') as reg_week
    ,count(mid) as reg FROM ods.s01_mem_member_account 
    where date(reg_time)> date'2024-09-30'
    group by 1
    )a1

    left join
    
    (select
    to_char(date_trunc('week',date(release_date)),'yyyy-mm-dd') as release_week
    ,sum(loan_cnt) as loan_cnt 
    ,sum(loan_contract_amt_usd) as contract_amt 
    ,sum(loan_amt_usd) as release_amt 
    ,sum(loan_contract_amt_usd) *1.0 / sum(loan_cnt) as per_loan
    ,sum(case when a.double_loan = 'fst' then loan_cnt else 0 end) as fst_loan_cnt 
    ,sum(case when a.double_loan = 'fst' then loan_contract_amt_usd else 0 end) as fst_contract_amt 
    ,sum(case when a.double_loan = 'fst' then loan_contract_amt_usd * product_name else 0 end) *1.0 / sum(case when a.double_loan = 'fst' then loan_contract_amt_usd else 0 end) as fst_avg_period
    ,sum(case when a.double_loan = 'fst' then loan_contract_amt_usd else 0 end) *1.0 / sum(case when a.double_loan = 'fst' then loan_cnt else 0 end) as fst_per_loan
    ,sum(case when a.double_loan like '%rl%'  then loan_cnt else 0 end) as rl_loan_cnt 
    ,sum(case when a.double_loan like '%rl%' then loan_contract_amt_usd else 0 end) as rl_contract_amt 
    ,sum(case when a.double_loan like '%rl%' then loan_contract_amt_usd * product_name else 0 end) *1.0 / sum(case when a.double_loan like '%rl%' then loan_contract_amt_usd else 0 end) as rl_avg_period
    ,sum(case when a.double_loan like '%rl%' then loan_contract_amt_usd else 0 end) *1.0 / sum(case when a.double_loan like '%rl%' then loan_cnt else 0 end) as rl_per_loan
    ,sum(case when a.double_loan like '%rl%' then loan_contract_amt_usd else 0 end) / sum(loan_contract_amt_usd)  as  rl_ratio
    from ind.my_loan_detail a  
    where release_date > date'2024-09-30'
    and release_date < current_date
    --and release_date between date'{start_day}' and date'{end_day}'
    group by 1
    order by 1
    )a2
    
    on a1.reg_week=a2.release_week



    left join
    
    (select
    app_week
    ,fst_apply_cnt
    ,(fst_apply_cnt * fst_approve_rate + sec_apply_cnt *sec_approve_rate * sec_external_pass_rate )*1.0000/(fst_apply_cnt+sec_apply_cnt) as approve_rate
    ,fst_approve_rate
    ,fst_machine_pass_rate  
    ,fst_manual_inflow_rate 
    ,fst_manual_pass_rate  
    ,fst_external_pass_rate 
    ,(sec_approve_rate * sec_external_pass_rate) as sec_approve_rate
    ,sec_machine_pass_rate  
    ,sec_manual_inflow_rate 
    ,sec_datapre2_pass_rate  
    ,sec_external_pass_rate
    from
        (select
        app_week
        ,sum(CASE WHEN grant_strategy = 'NEW' then if_model_passed else 0 end) *1.0000 / sum(CASE WHEN grant_strategy = 'NEW' then if_app else 0 end) *
        sum(CASE WHEN grant_strategy = 'NEW' then if_pass else 0 end) *1.0000 / sum(CASE WHEN grant_strategy = 'NEW' then if_confirm_passed else 0 end) as fst_approve_rate 
        ,sum(CASE WHEN grant_strategy = 'NEW' then if_model_passed else 0 end) *1.0000 / sum(CASE WHEN grant_strategy = 'NEW' then if_app else 0 end) as fst_machine_pass_rate  
        ,sum(CASE WHEN grant_strategy = 'NEW' then if_in_manual_check_1 else 0 end) *1.0000 / sum(CASE WHEN grant_strategy = 'NEW' then if_in_manual_check else 0 end) as fst_manual_inflow_rate 
        ,case when sum(CASE WHEN grant_strategy = 'NEW' then if_in_manual_check_1 else 0 end) =0 then 0 else
        sum(CASE WHEN grant_strategy = 'NEW' then if_manual_check_2_passed else 0 end) *1.0000 / sum(CASE WHEN grant_strategy = 'NEW' then if_in_manual_check_1 else 0 end) end as fst_manual_pass_rate         
        ,sum(CASE WHEN grant_strategy = 'NEW' then if_pass else 0 end) *1.0000 / sum(CASE WHEN grant_strategy = 'NEW' then if_in_external_data_pre2 else 0 end) as fst_external_pass_rate
        ,sum(CASE WHEN grant_strategy = 'OLD' then if_in_confirm else 0 end) *1.0000/ sum(CASE WHEN grant_strategy = 'OLD'  then if_app else 0 end) as sec_approve_rate
        ,sum(CASE WHEN grant_strategy = 'OLD' then if_model_passed else 0 end) *1.0000/ sum(CASE WHEN grant_strategy = 'OLD' then if_app else 0 end) as sec_machine_pass_rate  
        ,sum(CASE WHEN grant_strategy = 'OLD' then if_in_manual_check_1 else 0 end) *1.0000/ sum(CASE WHEN grant_strategy = 'OLD'  then if_in_manual_check else 0 end) as sec_manual_inflow_rate 
        ,case when sum(CASE WHEN grant_strategy = 'OLD'  then if_in_manual_check_1 else 0 end) = 0 then 0 else 
        sum(CASE WHEN grant_strategy = 'OLD' then if_manual_check_2_passed else 0 end) *1.0000/ sum(CASE WHEN grant_strategy = 'OLD'  then if_in_manual_check_1 else 0 end) end  as sec_manual_pass_rate
        ,sum(CASE WHEN grant_strategy = 'OLD' then if_external_data_3_passed else 0 end) *1.0000/ sum(CASE WHEN grant_strategy = 'OLD'  then if_in_external_data_pre2 else 0 end) as sec_datapre2_pass_rate  
        --,sum(CASE WHEN grant_strategy = 'OLD' then if_external_data_4_passed else 0 end) *1.0000/ sum(CASE WHEN grant_strategy = 'OLD'  then if_in_external_data_4 else 0 end) as sec_external_pass_rate
        ,sum(CASE WHEN grant_strategy = 'OLD' then if_external_data_4_passed else 0 end) *1.0000/ sum(CASE WHEN grant_strategy = 'OLD'  then if_confirm_passed else 0 end) as sec_external_pass_rate
        
        ,sum(CASE WHEN grant_strategy = 'NEW' then if_app else 0 end)fst_apply_cnt
        ,sum(CASE WHEN grant_strategy = 'OLD'  then if_app else 0 end)sec_apply_cnt
        from
            (select
            grant_strategy
            ,app_date
            ,app_week
            ,app_month
            ,if_app
            ,CASE WHEN if_recall = 0 then if_model_passed 
            when if_recall = 1 and if_in_confirm_final=1 then 1
            else 0 end as if_model_passed
            ,if_pass
            ,if_in_confirm_final as if_in_confirm
            ,if_confirm_passed_final as if_confirm_passed
            ,CASE WHEN if_recall = 0 then if_in_manual_check_1 
            when grant_strategy = 'NEW' and if_recall = 1 and if_in_confirm_final=1 and if_confirm_passed_final=1 then 1
            else 0 end as if_in_manual_check_1
            ,CASE WHEN if_recall = 0 then if_in_manual_check 
            when grant_strategy = 'NEW' and if_recall = 1 and if_in_confirm_final=1 and if_confirm_passed_final=1 then 1
            else 0 end as if_in_manual_check
            ,CASE WHEN if_recall = 0 then if_manual_check_2_passed 
            when grant_strategy = 'NEW' and if_recall = 1 and if_in_confirm_final=1 and if_confirm_passed_final=1 then 1
            else 0 end as if_manual_check_2_passed
            ,CASE WHEN if_recall = 0 then if_in_external_data_pre2 
            when grant_strategy = 'NEW' and if_recall = 1 and if_in_confirm_final=1 and if_confirm_passed_final=1 then 1
            when grant_strategy = 'OLD' and if_recall = 1 and if_in_confirm_final=1 then 1
            else 0 end as if_in_external_data_pre2
            ,CASE WHEN if_recall = 0 then if_external_data_3_passed 
            when grant_strategy = 'NEW' and if_recall = 1 and if_in_confirm_final=1 and if_confirm_passed_final=1 then 1
            when grant_strategy = 'OLD' and if_recall = 1 and if_in_confirm_final=1 then 1
            else 0 end as if_external_data_3_passed
            ,CASE WHEN if_recall = 0 then if_in_external_data_4 
            when if_recall = 1 and if_in_confirm_final=1 and if_confirm_passed_final=1 then 1
            else 0 end as if_in_external_data_4
            ,CASE WHEN if_recall = 0 then if_external_data_4_passed 
            when if_recall = 1 and if_in_confirm_final=1 and if_confirm_passed_final=1 then 1
            else 0 end as if_external_data_4_passed
            from
                (select 
                a.*
                ,case when source_channel2 not in('IOS') and app_version <= '2.1.4' then 1
                    when loan_type2 = 'loop' then if_app
                    else if_in_confirm end as if_in_confirm_final
                ,case when source_channel2 not in('IOS') and app_version <= '2.1.4' then 1
                    when confirm_date is not null then 1
                    when loan_type2 = 'loop' then if_app
                    else if_confirm_passed end as if_confirm_passed_final 
                from ind.xly_application_funnel a
                )a
            where app_date>'2024-09-30' and cast(app_date as date)<current_date
            --and cast(app_date as date) between date'{start_day}' and date'{end_day}'
            )a
            group by 1
        )a
    )a3
    on a1.reg_week=a3.app_week
    
    left join
    (select
    to_char(date_trunc('week',date(should_date)),'yyyy-mm-dd') as should_week
    ,1- sum(case when is_due_8 > 0 then a.due_8 end) /sum(case when is_due_8>0 then a.due_1 end) as t7_collect
    ,1- sum(case when is_due_16 > 0 then a.due_16 end) /sum(case when is_due_16 > 0 then a.due_1 end) as t15_collect
    ,1- sum(case when is_due_31 > 0 then a.due_31 end) /sum(case when is_due_31 > 0 then a.due_1 end) as t30_collect
    ,sum(case when a.is_due_31 > 0 then a.due_31 end) /sum(case when a.is_due_31 > 0 then a.contract_amount end) as t30_ovd
    ,sum(case when a.is_due_31 > 0 and a.is_reloan2 like '%fstloan%' then due_31 end)/sum(case when a.is_due_31 > 0 and a.is_reloan2 like '%fstloan%' then contract_amount end) as fst_t30_ovd
    ,sum(case when a.is_due_31 > 0 and a.is_reloan2 like '%reloan%' then due_31 end)/sum(case when a.is_due_31 > 0 and a.is_reloan2 like '%reloan%' then contract_amount end) as rl_t30_ovd
    ,sum(case when a.is_due_16 > 0 then a.due_16 end) /sum(case when a.is_due_16 > 0 then a.contract_amount end) as t15_ovd
    ,sum(case when a.is_due_16 > 0 and a.is_reloan2 like '%fstloan%' then due_16 end)/sum(case when a.is_due_16 > 0 and a.is_reloan2 like '%fstloan%' then contract_amount end) as fst_t15_ovd
    ,sum(case when a.is_due_16 > 0 and a.is_reloan2 like '%reloan%' then due_16 end)/sum(case when a.is_due_16 > 0 and a.is_reloan2 like '%reloan%' then contract_amount end) as rl_t15_ovd
    ,sum(case when a.is_due_8>0 then a.due_8 end) /sum(case when a.is_due_8>0 then a.contract_amount end) as t7_ovd
    ,sum(case when a.is_due_8>0 and a.is_reloan2 like '%fstloan%' then due_8 end)/sum(case when a.is_due_8>0 and a.is_reloan2 like '%fstloan%' then contract_amount end) as fst_t7_ovd
    ,sum(case when a.is_due_8>0 and a.is_reloan2 like '%reloan%' then due_8 end)/sum(case when a.is_due_8>0 and a.is_reloan2 like '%reloan%' then contract_amount end) as rl_t7_ovd
    ,sum(case when a.is_due_1 > 0 then a.due_1 end) /sum(case when a.is_due_1 > 0 then a.contract_amount end) as t0_ovd
    ,sum(case when a.is_due_1 > 0 and a.is_reloan2 like '%fstloan%' then due_1 end)/sum(case when a.is_due_1 > 0 and a.is_reloan2 like '%fstloan%' then contract_amount end) as fst_t0_ovd
    ,sum(case when a.is_due_1 > 0 and a.is_reloan2 like '%reloan%' then due_1 end)/sum(case when a.is_due_1 > 0 and a.is_reloan2 like '%reloan%' then contract_amount end) as rl_t0_ovd
    from ind.gqy_case_fetch_all a 
    where is_due = 0 and customer_tag != 'T'
    --and should_date between date'{start_day}' and date'{end_day}'
    and should_date >= date'2024-09-30'
    group by 1
    )a4
    on a1.reg_week=a4.should_week
    

    /*left join
    (select
    to_char(date_trunc('week',date(ad_date)),'yyyy-mm-dd') as ad_week 	
    ,sum(spend_usd) as spend
    from dwd.dwd_ads_cost a
    where ad_date >= date'2024-09-30'
    group by 1        
    )a5
    on a1.reg_week=a5.ad_week*/
    left join
    (select
    to_char(date_trunc('week',date(ad_date)),'yyyy-mm-dd') as ad_week 	
    ,sum(spend_usd_discount) as spend
    from ind.tyn_ads_cost_discount a
    where ad_date >= date'2024-09-30'
    group by 1        
    )a5
    on a1.reg_week=a5.ad_week

    left join
    (select
    issue_week
    ,(case when should_capital_1_0_total<>0 then overdue_amount_1_0_total/should_capital_1_0_total end) as overdue_rate_1_0_total
    ,(case when should_capital_1_7_total<>0 then overdue_amount_1_7_total/should_capital_1_7_total end) as overdue_rate_1_7_total
    ,(case when should_capital_1_30_total<>0 then overdue_amount_1_30_total/should_capital_1_30_total end) as overdue_rate_1_30_total
    ,(case when should_capital_3_30_total<>0 then overdue_amount_3_30_total/should_capital_3_30_total end) as overdue_rate_3_30_total
    ,(case when should_capital_6_30_total<>0 then overdue_amount_6_30_total/should_capital_6_30_total end) as overdue_rate_6_30_total

    ,(case when should_capital_1_0_new<>0 then overdue_amount_1_0_new/should_capital_1_0_new end) as overdue_rate_1_0_new
    ,(case when should_capital_1_7_new<>0 then overdue_amount_1_7_new/should_capital_1_7_new end) as overdue_rate_1_7_new
    ,(case when should_capital_1_30_new<>0 then overdue_amount_1_30_new/should_capital_1_30_new end) as overdue_rate_1_30_new
    ,(case when should_capital_3_30_new<>0 then overdue_amount_3_30_new/should_capital_3_30_new end) as overdue_rate_3_30_new
    ,(case when should_capital_6_30_new<>0 then overdue_amount_6_30_new/should_capital_6_30_new end) as overdue_rate_6_30_new

    ,(case when should_capital_1_0_old<>0 then overdue_amount_1_0_old/should_capital_1_0_old end) as overdue_rate_1_0_old
    ,(case when should_capital_1_7_old<>0 then overdue_amount_1_7_old/should_capital_1_7_old end) as overdue_rate_1_7_old
    ,(case when should_capital_1_30_old<>0 then overdue_amount_1_30_old/should_capital_1_30_old end) as overdue_rate_1_30_old
    ,(case when should_capital_3_30_old<>0 then overdue_amount_3_30_old/should_capital_3_30_old end) as overdue_rate_3_30_old
    ,(case when should_capital_6_30_old<>0 then overdue_amount_6_30_old/should_capital_6_30_old end) as overdue_rate_6_30_old
    from
        (select
            issue_week 
            ,sum(overdue_amount_1_0) as overdue_amount_1_0_total
            , sum(case when grant_strategy = 'NEW' then overdue_amount_1_0 else 0 end) as overdue_amount_1_0_new
            , sum(case when grant_strategy = 'OLD' then overdue_amount_1_0 else 0 end) as overdue_amount_1_0_old
            , sum(should_capital_1_0) as should_capital_1_0_total
            , sum(case when grant_strategy = 'NEW' then should_capital_1_0 else 0 end) as should_capital_1_0_new
            , sum(case when grant_strategy = 'OLD' then should_capital_1_0 else 0 end) as should_capital_1_0_old
            , sum(overdue_amount_1_7) as overdue_amount_1_7_total
            , sum(case when grant_strategy = 'NEW' then overdue_amount_1_7 else 0 end) as overdue_amount_1_7_new
            , sum(case when grant_strategy = 'OLD' then overdue_amount_1_7 else 0 end) as overdue_amount_1_7_old
            , sum(should_capital_1_7) as should_capital_1_7_total
            , sum(case when grant_strategy = 'NEW' then should_capital_1_7 else 0 end) as should_capital_1_7_new
            , sum(case when grant_strategy = 'OLD' then should_capital_1_7 else 0 end) as should_capital_1_7_old
            , sum(overdue_amount_1_30) as overdue_amount_1_30_total
            , sum(case when grant_strategy = 'NEW' then overdue_amount_1_30 else 0 end) as overdue_amount_1_30_new
            , sum(case when grant_strategy = 'OLD' then overdue_amount_1_30 else 0 end) as overdue_amount_1_30_old
            , sum(should_capital_1_30) as should_capital_1_30_total	
            , sum(case when grant_strategy = 'NEW' then should_capital_1_30 else 0 end) as should_capital_1_30_new
            , sum(case when grant_strategy = 'OLD' then should_capital_1_30 else 0 end) as should_capital_1_30_old

            , sum(overdue_amount_3_0) as overdue_amount_3_0_total
            , sum(case when grant_strategy = 'NEW' then overdue_amount_3_0 else 0 end) as overdue_amount_3_0_new
            , sum(case when grant_strategy = 'OLD' then overdue_amount_3_0 else 0 end) as overdue_amount_3_0_old
            , sum(should_capital_3_0) as should_capital_3_0_total
            , sum(case when grant_strategy = 'NEW' then should_capital_3_0 else 0 end) as should_capital_3_0_new
            , sum(case when grant_strategy = 'OLD' then should_capital_3_0 else 0 end) as should_capital_3_0_old
            , sum(overdue_amount_3_7) as overdue_amount_3_7_total
            , sum(case when grant_strategy = 'NEW' then overdue_amount_3_7 else 0 end) as overdue_amount_3_7_new
            , sum(case when grant_strategy = 'OLD' then overdue_amount_3_7 else 0 end) as overdue_amount_3_7_old
            , sum(should_capital_3_7) as should_capital_3_7_total
            , sum(case when grant_strategy = 'NEW' then should_capital_3_7 else 0 end) as should_capital_3_7_new
            , sum(case when grant_strategy = 'OLD' then should_capital_3_7 else 0 end) as should_capital_3_7_old
            , sum(overdue_amount_3_30) as overdue_amount_3_30_total
            , sum(case when grant_strategy = 'NEW' then overdue_amount_3_30 else 0 end) as overdue_amount_3_30_new
            , sum(case when grant_strategy = 'OLD' then overdue_amount_3_30 else 0 end) as overdue_amount_3_30_old
            , sum(should_capital_3_30) as should_capital_3_30_total	
            , sum(case when grant_strategy = 'NEW' then should_capital_3_30 else 0 end) as should_capital_3_30_new
            , sum(case when grant_strategy = 'OLD' then should_capital_3_30 else 0 end) as should_capital_3_30_old

            , sum(overdue_amount_6_0) as overdue_amount_6_0_total
            , sum(case when grant_strategy = 'NEW' then overdue_amount_6_0 else 0 end) as overdue_amount_6_0_new
            , sum(case when grant_strategy = 'OLD' then overdue_amount_6_0 else 0 end) as overdue_amount_6_0_old
            , sum(should_capital_6_0) as should_capital_6_0_total
            , sum(case when grant_strategy = 'NEW' then should_capital_6_0 else 0 end) as should_capital_6_0_new
            , sum(case when grant_strategy = 'OLD' then should_capital_6_0 else 0 end) as should_capital_6_0_old
            , sum(overdue_amount_6_7) as overdue_amount_6_7_total
            , sum(case when grant_strategy = 'NEW' then overdue_amount_6_7 else 0 end) as overdue_amount_6_7_new
            , sum(case when grant_strategy = 'OLD' then overdue_amount_6_7 else 0 end) as overdue_amount_6_7_old
            , sum(should_capital_6_7) as should_capital_6_7_total
            , sum(case when grant_strategy = 'NEW' then should_capital_6_7 else 0 end) as should_capital_6_7_new
            , sum(case when grant_strategy = 'OLD' then should_capital_6_7 else 0 end) as should_capital_6_7_old
            , sum(overdue_amount_6_30) as overdue_amount_6_30_total
            , sum(case when grant_strategy = 'NEW' then overdue_amount_6_30 else 0 end) as overdue_amount_6_30_new
            , sum(case when grant_strategy = 'OLD' then overdue_amount_6_30 else 0 end) as overdue_amount_6_30_old
            , sum(should_capital_6_30) as should_capital_6_30_total	
            , sum(case when grant_strategy = 'NEW' then should_capital_6_30 else 0 end) as should_capital_6_30_new
            , sum(case when grant_strategy = 'OLD' then should_capital_6_30 else 0 end) as should_capital_6_30_old
            from ind.whx_vintage_all4
            where cast(issue_date as date)>=date'2024-09-30'
            group by 1
        )a           
    )a6
    on a1.reg_week=a6.issue_week
    left join
    (select
    to_char(date_trunc('week',date(install_date)),'yyyy-mm-dd') as ad_week
    ,count(distinct appsflyer_id) as install_cnt
    from
        (select
        date(a.install_time + interval '7' hour) as install_date
        ,a.appsflyer_id
        from ods.s08_appsflyer_push_data a
        where a.event_name = 'install' and date(a.install_time + interval '7' hour)  between date'2025-02-03' and date(current_date)
        and etl_date>='2025-02-03'   
        )a6
    group by 1
    )a7
    on a1.reg_week=a7.ad_week 
    order by 1 asc;
     
drop table if exists ind.ys_zhouyizhoubao_onloan_amt_tmp;
create table IF NOT EXISTS ind.ys_zhouyizhoubao_onloan_amt_tmp as
  select data_date,reg_week,c.exchange_rate_to_dollar,sum(a.should_capital  -a.fact_capital) as onloan_amt ,
    sum(a.should_capital  -a.fact_capital)/c.exchange_rate_to_dollar as onloan_amt_usd
    from ods.s02_loan_repayment_his a
    JOIN ind.ys_zhouyizhoubao_tmp b ON a.data_date =to_char(date(reg_week) + interval '6' day,'yyyymmdd') and a.state in (0,2,4) 
    JOIN dim.dim_exchange_rate_cost c on to_char(date(reg_week) + interval '6' day,'yyyymm')=c.month_id and account_currency = 'IDR'
   group by 1,2,3
   order by 1 ;
   
   
   
   
   
   
   
   
    
 

 


drop table if exists ind.ba_apply_should_result_week;
create table
if not exists ind.ba_apply_should_result_week as

WITH application_metrics AS ( 
    SELECT 
        app_week,
        app_month,
        grant_strategy,
        product_tag,
        is_reloan2,
        new_grade_level,
        user_level,
         loan_type2,
        media_source2,
        source_channel2,
        case when if_regular_backup='1' then 1 else 0 end as if_regular_backup,
        case when if_backup_switch=1 then 1 else 0 end as if_backup_switch,

        sum(case when if_recall=0 then if_app end) if_app,
        sum(case when grant_strategy='OLD' and if_recall=0 then if_external_data_3_passed 
                 when grant_strategy='NEW' then if_in_confirm_temp end) if_external_3_passed,
        sum(if_in_confirm_final ) AS in_confirm_cnt_final,
        sum(if_in_confirm_temp) AS in_confirm_cnt,
        sum(case when new_grade_level IN ('1','2') then if_in_confirm_temp else 0 end) AS in_confirm_cnt_1_2,
        sum(case when new_grade_level IN ('1','2','3','4') then if_in_confirm_temp else 0 end) AS in_confirm_cnt_1_4,
        sum(case when user_level IN ('1','2') then if_in_confirm_temp else 0 end) AS rl_in_confirm_cnt_1_2,
        sum(case when user_level IN ('1','2','3') then if_in_confirm_temp else 0 end) AS rl_in_confirm_cnt_1_3,
        sum(if_confirm_passed_final) AS confirm_passed_cnt, 
        sum(if_confirm_passed_num_24h) AS if_confirm_passed_num_24h,
        sum(if_confirm_passed_num_t0) AS if_confirm_passed_num_t0,
        sum(if_confirm_passed_num_t7) AS if_confirm_passed_num_t7,
        SUM(case when if_in_confirm_final = 1 then grant_amount_max else NULL end) AS in_confirm_grantcredit_amount_total,
        SUM(case when if_in_confirm_final = 1 then grantcredit_amount else NULL end) AS in_confirm_grantcredit_amount,
        SUM(case when if_confirm_passed_final= 1 then apply_grantcredit_amount else NULL end) AS confirm_grantcredit_amount,
        SUM(case when if_confirm_passed_final= 1 then apply_amount else NULL end) AS confirm_apply_amount,
 
        SUM(case when if_confirm_passed_final= 1 and if_issue=1 then apply_grantcredit_amount else NULL end) AS issue_confirm_grantcredit_amount,
        SUM(case when if_confirm_passed_final= 1 and if_issue=1 then apply_amount else NULL end) AS issue_confirm_apply_amount,
        sum(case when grant_strategy='OLD' and if_recall=0 then if_in_external_data_4 
                 when grant_strategy='NEW' then if_confirm_passed_final end) if_in_external_data_4,

        sum(if_external_data_4_passed ) as pass_cnt,
         sum(if_issue) AS issue_cnt_from_app,
        sum(is_released_within_24h) AS is_released_within_24h
    FROM ind.ba_asset_base_info
    WHERE date(app_date) >= DATE('2025-01-01')  
    AND date(app_date) < CURRENT_DATE
    -- AND if_app = 1
    GROUP BY 1,2,3,4,5,6,7,8,9,10,11,12




),

 
issue_metrics AS ( 
    SELECT 
        issue_week,
        issue_month,
        grant_strategy,
        product_tag,
        is_reloan2,
        loan_type2,
        new_grade_level,
        user_level,
 
        media_source2,
        source_channel2,
        case when if_regular_backup='1' then 1 else 0 end as if_regular_backup,
        case when if_backup_switch=1 then 1 else 0 end as if_backup_switch,
        sum(if_issue) AS issue_cnt_from_issue,
        sum(case when new_grade_level IN ('1','2') then if_issue else 0 end) AS issue_cnt_1_2,
        sum(case when new_grade_level IN ('1','2','3','4') then if_issue else 0 end) AS issue_cnt_1_4,
        sum(case when user_level IN ('1','2') then if_issue else 0 end) AS rl_issue_cnt_1_2,
        sum(case when user_level IN ('1','2','3') then if_issue else 0 end) AS rl_issue_cnt_1_3,

        sum(haircut_amount) as issue_haircut_amount,
        sum(interest) as issue_interest,
        sum(revenue) as issue_revenue,
        sum(contract_amount) AS issue_contract_amount,
        sum(contract_amount_usd1) AS issue_contract_amount_usd,
     
        sum(case when grant_strategy = 'NEW' then contract_amount_usd1 else 0 end) AS issue_contract_amount_usd_new,
        sum(case when grant_strategy = 'OLD' then contract_amount_usd1 else 0 end) AS issue_contract_amount_usd_old,
        sum(overdue_amount_1_0) AS overdue_amount_1_0,
        sum(should_capital_1_0) AS should_capital_1_0,
        sum(overdue_amount_1_7) AS overdue_amount_1_7,
        sum(should_capital_1_7) AS should_capital_1_7,
        sum(overdue_amount_1_14) AS overdue_amount_1_14,
        sum(should_capital_1_14) AS should_capital_1_14,
        sum(overdue_amount_1_30) AS overdue_amount_1_30,
        sum(should_capital_1_30) AS should_capital_1_30,
        sum(overdue_amount_2_0) AS overdue_amount_2_0,
        sum(should_capital_2_0) AS should_capital_2_0,
        sum(overdue_amount_2_7) AS overdue_amount_2_7,
        sum(should_capital_2_7) AS should_capital_2_7,
        sum(overdue_amount_2_14) AS overdue_amount_2_14,
        sum(should_capital_2_14) AS should_capital_2_14,
        sum(overdue_amount_2_30) AS overdue_amount_2_30,
        sum(should_capital_2_30) AS should_capital_2_30,

        sum(loan_cycle_amount) AS loan_cycle_amount
 

    FROM ind.ba_asset_base_info
    WHERE if_issue = 1
    AND date(issue_date) >= DATE('2025-01-01') 
    AND date(issue_date) < CURRENT_DATE 
    GROUP BY 1,2,3,4,5,6,7,8,9,10,11,12 





),



should_metrics AS (


    SELECT
    to_char(date_trunc('month',a.should_date),'yyyy-mm-dd') as should_month,
	to_char(date_trunc('week', a.should_date),'yyyy-mm-dd') as should_week,
    c.grant_strategy,
    c.product_tag,
    c.is_reloan2,
    c.loan_type2,
    c.new_grade_level,
     c.user_level,
    c.media_source2,
    c.source_channel2,  
    case when c.if_regular_backup='1' then 1 else 0 end as if_regular_backup,
    case when c.if_backup_switch=1 then 1 else 0 end as if_backup_switch,

    SUM(a.should_capital) AS should_capital, 
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 1 THEN a.should_capital ELSE null END) AS should_capital_d0, 
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 2 THEN a.should_capital ELSE null END) AS should_capital_d1,
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 8 THEN a.should_capital ELSE null END) AS should_capital_d7,
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 16 THEN a.should_capital ELSE null END) AS should_capital_d15,
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 31 THEN a.should_capital ELSE null END) AS should_capital_d30,
 
 
    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 1 THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d0, 
    SUM(CASE WHEN due_day <= 1  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 2 THEN a.fact_capital ELSE 0 END) AS t1_capital_paid_d1,
    SUM(CASE WHEN due_day <= 7  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 8 THEN a.fact_capital ELSE 0 END) AS t7_capital_paid_d7,
    SUM(CASE WHEN due_day <= 15 and DATE_DIFF('day',should_date,CURRENT_DATE) >= 16 THEN a.fact_capital ELSE 0 END) AS t15_capital_paid_d15,
    SUM(CASE WHEN due_day <= 30 and DATE_DIFF('day',should_date,CURRENT_DATE) >= 31 THEN a.fact_capital ELSE 0 END) AS t30_capital_paid_d30,

    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 8  THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d7,
    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 16 THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d15,
    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 31 THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d30


 
FROM (
    SELECT  
        customer_id,
        camera_id AS biz_id, 
        should_date, 
        due_day, 
        SUM(should_amount) AS should_amount,
        SUM(should_capital) AS should_capital,
        SUM(should_interest) AS should_interest,
        SUM(should_fine) AS should_fine,
        SUM(fact_amount) AS fact_amount,
        SUM(fact_capital) AS fact_capital,
        SUM(fact_interest) AS fact_interest,
        SUM(fact_fine) AS fact_fine
    FROM ind.gqy_case_info_f
    WHERE is_due = 0
        AND should_date >= DATE('2025-01-01') 
        AND should_date < CURRENT_DATE
    GROUP BY 
        1,2,3,4

) a 
LEFT JOIN (
    SELECT 
        data_date,
        customer_id,
        MAX(max_due_day) AS cus_ovd_day
    FROM ind.gqy_daliy_case
    GROUP BY 1,2
    HAVING MAX(max_due_day) >= 1
) b ON a.customer_id = b.customer_id AND should_date = b.data_date
left join ind.ba_asset_base_info c 
on  TRY_CAST (a.biz_id AS BIGINT) = TRY_CAST (c.biz_id AS BIGINT)
WHERE b.customer_id IS NULL 
GROUP BY 1,2,3,4,5,6,7,8,9,10,11,12 






),
data_date as (
    select distinct 
    date_mon,
    date_format(DATE_PARSE(data_date, '%Y%m%d'), '%Y-%m-01') AS data_month, 
    month_days,  
    day(DATE_ADD('day', -1, CURRENT_DATE)) as current_date_day,
    case when DATE_PARSE(month_end, '%Y%m%d')<DATE_TRUNC('month', CURRENT_DATE) 
    then day(DATE_PARSE(month_end, '%Y%m%d'))
    else day(DATE_ADD('day', -1, CURRENT_DATE))
    end as date_month_end_actual 
    from dim.dim_data_info
)

 


        SELECT 
    COALESCE(a.grant_strategy, i.grant_strategy, s.grant_strategy) AS grant_strategy,
    COALESCE(a.product_tag, i.product_tag, s.product_tag) AS product_tag,
    COALESCE(a.is_reloan2, i.is_reloan2, s.is_reloan2) AS is_reloan2,
    COALESCE(a.new_grade_level, i.new_grade_level, s.new_grade_level) AS new_grade_level,
    COALESCE(a.user_level, i.user_level, s.user_level) AS user_level,
 
    COALESCE(a.media_source2, i.media_source2, s.media_source2) AS media_source,
    COALESCE(a.source_channel2, i.source_channel2, s.source_channel2) AS source_channel2, 
    COALESCE(a.if_regular_backup,i.if_regular_backup, s.if_regular_backup) AS if_regular_backup,
    COALESCE(a.if_backup_switch, i.if_backup_switch, s.if_backup_switch) AS if_backup_switch,


    COALESCE(a.app_week, i.issue_week, s.should_week) AS app_week,
    COALESCE(a.app_month, i.issue_month, s.should_month) AS app_month,  
    COALESCE(a.if_app, 0) AS if_app,
    COALESCE(a.if_external_3_passed, 0) AS if_external_3_passed,
    COALESCE(a.in_confirm_cnt_final, 0) AS in_confirm_cnt_final,
    COALESCE(a.in_confirm_cnt, 0) AS in_confirm_cnt,
    COALESCE(a.in_confirm_cnt_1_2, 0) AS in_confirm_cnt_1_2,
    COALESCE(a.in_confirm_cnt_1_4, 0) AS in_confirm_cnt_1_4,
    COALESCE(a.rl_in_confirm_cnt_1_2, 0) AS rl_in_confirm_cnt_1_2,
    COALESCE(a.rl_in_confirm_cnt_1_3, 0) AS rl_in_confirm_cnt_1_3,

    COALESCE(a.confirm_passed_cnt, 0) AS confirm_passed_cnt,
    COALESCE(a.if_confirm_passed_num_24h, 0) AS if_confirm_passed_num_24h,

    COALESCE(a.if_confirm_passed_num_t0, 0) AS if_confirm_passed_num_t0,
    COALESCE(a.if_confirm_passed_num_t7, 0) AS if_confirm_passed_num_t7,

    COALESCE(a.in_confirm_grantcredit_amount_total, 0) AS in_confirm_grantcredit_amount_total,
    COALESCE(a.in_confirm_grantcredit_amount, 0) AS in_confirm_grantcredit_amount,
    COALESCE(a.confirm_grantcredit_amount, 0) AS confirm_grantcredit_amount,
    COALESCE(a.confirm_apply_amount, 0) AS confirm_apply_amount,
    COALESCE(a.if_in_external_data_4, 0) AS if_in_external_data_4,
    COALESCE(a.pass_cnt, 0) AS pass_cnt, 
    COALESCE(a.issue_cnt_from_app, 0) AS issue_cnt_from_app,
    COALESCE(a.is_released_within_24h, 0) AS is_released_within_24h, 
    COALESCE(i.issue_cnt_from_issue, 0) AS issue_cnt_from_issue,
    COALESCE(i.issue_cnt_1_2, 0) AS issue_cnt_1_2,
    COALESCE(i.issue_cnt_1_4, 0) AS issue_cnt_1_4,
    COALESCE(i.rl_issue_cnt_1_2, 0) AS rl_issue_cnt_1_2,
    COALESCE(i.rl_issue_cnt_1_3, 0) AS rl_issue_cnt_1_3,
    COALESCE(i.issue_contract_amount, 0) AS issue_contract_amount,
    COALESCE(i.issue_contract_amount_usd, 0) AS issue_contract_amount_usd,
    SUM(COALESCE(i.issue_contract_amount_usd, 0)) OVER (PARTITION BY COALESCE(a.app_month, i.issue_month, s.should_month)) AS issue_contract_group,
    SUM(case when COALESCE(a.grant_strategy, i.grant_strategy, s.grant_strategy)='NEW'
    then COALESCE(i.issue_contract_amount_usd, 0)
    else 0 end ) OVER (PARTITION BY COALESCE(a.app_month, i.issue_month, s.should_month)) AS issue_contract_new_group,
    SUM(case when COALESCE(a.grant_strategy, i.grant_strategy, s.grant_strategy)='OLD'
    then COALESCE(i.issue_contract_amount_usd, 0)
    else 0 end ) OVER (PARTITION BY COALESCE(a.app_month, i.issue_month, s.should_month)) AS issue_contract_old_group,
    
    COALESCE(i.overdue_amount_1_0, 0) AS overdue_amount_1_0,
    COALESCE(i.should_capital_1_0, 0) AS should_capital_1_0,
    COALESCE(i.overdue_amount_1_7, 0) AS overdue_amount_1_7,
    COALESCE(i.should_capital_1_7, 0) AS should_capital_1_7,
    COALESCE(i.overdue_amount_1_14, 0) AS overdue_amount_1_14,
    COALESCE(i.should_capital_1_14, 0) AS should_capital_1_14,
    COALESCE(i.overdue_amount_1_30, 0) AS overdue_amount_1_30,
    COALESCE(i.should_capital_1_30, 0) AS should_capital_1_30, 
    COALESCE(i.overdue_amount_2_0, 0) AS overdue_amount_2_0,
    COALESCE(i.should_capital_2_0, 0) AS should_capital_2_0,
    COALESCE(i.overdue_amount_2_7, 0) AS overdue_amount_2_7,
    COALESCE(i.should_capital_2_7, 0) AS should_capital_2_7, 
    COALESCE(i.overdue_amount_2_30, 0) AS overdue_amount_2_30,
    COALESCE(i.should_capital_2_30, 0) AS should_capital_2_30, 
    COALESCE(s.should_capital_d0, 0) AS should_capital_d0, 
    COALESCE(s.should_capital_d1, 0) AS should_capital_d1,
    COALESCE(s.should_capital_d7, 0) AS should_capital_d7,
    COALESCE(s.should_capital_d15, 0) AS should_capital_d15,
    COALESCE(s.should_capital_d30, 0) AS should_capital_d30, 
    COALESCE(s.should_capital_d0 - s.t0_capital_paid_d0, 0) AS t0_capital_due_d0,
    COALESCE(s.should_capital_d1 - s.t1_capital_paid_d1, 0) AS t1_capital_due_d1,
    COALESCE(s.should_capital_d7 - s.t7_capital_paid_d7, 0) AS t7_capital_due_d7,
    COALESCE(s.should_capital_d15 - s.t15_capital_paid_d15, 0) AS t15_capital_due_d15,
    COALESCE(s.should_capital_d30 - s.t30_capital_paid_d30, 0) AS t30_capital_due_d30,
    COALESCE(s.t0_capital_paid_d7, 0) AS t0_capital_paid_d7,
    COALESCE(s.t0_capital_paid_d15, 0) AS t0_capital_paid_d15,
    COALESCE(s.t0_capital_paid_d30, 0) AS t0_capital_paid_d30,
    COALESCE(s.t7_capital_paid_d7 - s.t0_capital_paid_d7, 0) AS t0_7_capital_paid_d7,
    COALESCE(s.t15_capital_paid_d15 - s.t0_capital_paid_d15, 0) AS t0_15_capital_paid_d15,
    COALESCE(s.t30_capital_paid_d30 - s.t0_capital_paid_d30, 0) AS t0_30_capital_paid_d30,

    COALESCE(s.should_capital_d7 - s.t0_capital_paid_d7, 0) AS t0_7_capital_paid_due_d7,
    COALESCE(s.should_capital_d15 - s.t0_capital_paid_d15, 0) AS t0_15_capital_paid_due_d15,
    COALESCE(s.should_capital_d30 - s.t0_capital_paid_d30, 0) AS t0_30_capital_paid_due_d30,
    COALESCE(loan_cycle_amount, 0) AS loan_cycle_amount,
    COALESCE(issue_haircut_amount, 0) AS issue_haircut_amount,
    COALESCE(issue_interest, 0) AS issue_interest,
    COALESCE(issue_revenue, 0) AS issue_revenue,
     total_amt*exchange_rate* 1.00000 / f1.exchange_rate_to_dollar  AS ov_total_amt_usd,
    fl_contract_amt*exchange_rate* 1.00000 / f1.exchange_rate_to_dollar AS fl_total_amt_usd,
    rl_contract_amt*exchange_rate* 1.00000 / f1.exchange_rate_to_dollar AS rl_total_amt_usd,
    month_days, 
    date_month_end_actual ,
    COALESCE(issue_contract_amount_usd_new, 0) AS issue_contract_amount_usd_new,
    COALESCE(issue_contract_amount_usd_old, 0) AS issue_contract_amount_usd_old,
        COALESCE(a.loan_type2, i.loan_type2, s.loan_type2) AS loan_type2


FROM application_metrics a
FULL JOIN issue_metrics i 
    ON a.grant_strategy = i.grant_strategy
    AND a.product_tag = i.product_tag
    AND a.is_reloan2 = i.is_reloan2
    AND a.loan_type2 = i.loan_type2
    AND a.new_grade_level = i.new_grade_level
    AND a.media_source2 = i.media_source2
    AND a.source_channel2 = i.source_channel2 
    AND a.app_week = i.issue_week
    AND a.app_month = i.issue_month
    AND a.user_level = i.user_level
    AND a.if_regular_backup = i.if_regular_backup
    AND a.if_backup_switch = i.if_backup_switch
 


FULL JOIN should_metrics s
    ON COALESCE(a.grant_strategy, i.grant_strategy) = s.grant_strategy
    AND COALESCE(a.product_tag, i.product_tag) = s.product_tag
    AND COALESCE(a.is_reloan2, i.is_reloan2) = s.is_reloan2
    AND COALESCE(a.loan_type2, i.loan_type2) = s.loan_type2
    AND COALESCE(a.new_grade_level, i.new_grade_level) = s.new_grade_level
    AND COALESCE(a.media_source2, i.media_source2) = s.media_source2
    AND COALESCE(a.source_channel2, i.source_channel2) = s.source_channel2 
    AND COALESCE(a.app_week, i.issue_week) = s.should_week
    AND COALESCE(a.app_month, i.issue_month) = s.should_month
    AND COALESCE(a.user_level, i.user_level) = s.user_level
    AND COALESCE(a.if_regular_backup, i.if_regular_backup) = s.if_regular_backup
    AND COALESCE(a.if_backup_switch, i.if_backup_switch) = s.if_backup_switch
 


LEFT JOIN ind.ba_kpi_targets_m b
    ON COALESCE(a.app_month, i.issue_month, s.should_month) = b.month 
left join data_date c
    ON b.month = c.data_month 
LEFT JOIN dim.dim_exchange_rate_cost f1 ON c.date_mon = f1.month_id AND f1.account_currency = 'IDR'
;



 
-- drop table if exists ind.ba_apply_should_result_week;
-- create table
-- if not exists ind.ba_apply_should_result_week as

-- WITH application_metrics AS ( 
--     SELECT 
--         app_week,
--         app_month,
--         grant_strategy,
--         product_tag,
--         is_reloan2,
--         new_grade_level,
--         user_level,
--          loan_type2,
--         media_source2,
--         source_channel2,
--         case when if_regular_backup='1' then 1 else 0 end as if_regular_backup,
--         case when if_backup_switch=1 then 1 else 0 end as if_backup_switch,

--         sum(case when if_recall=0 then if_app end) if_app,
--         sum(case when grant_strategy='OLD' and if_recall=0 then if_external_data_3_passed 
--                  when grant_strategy='NEW' then if_in_confirm_temp end) if_external_3_passed,
--         -- sum(if_in_confirm_final ) AS in_confirm_cnt_final,
--         -- sum(if_in_confirm_temp) AS in_confirm_cnt,
--         -- sum(case when new_grade_level IN ('1','2') then if_in_confirm_temp else 0 end) AS in_confirm_cnt_1_2,
--         -- sum(case when new_grade_level IN ('1','2','3','4') then if_in_confirm_temp else 0 end) AS in_confirm_cnt_1_4,
--         -- sum(case when user_level IN ('1','2') then if_in_confirm_temp else 0 end) AS rl_in_confirm_cnt_1_2,
--         -- sum(case when user_level IN ('1','2','3') then if_in_confirm_temp else 0 end) AS rl_in_confirm_cnt_1_3,
--         -- sum(if_confirm_passed_final) AS confirm_passed_cnt, 
--         -- sum(if_confirm_passed_num_t0) AS if_confirm_passed_num_t0,
--         -- sum(if_confirm_passed_num_t7) AS if_confirm_passed_num_t7,
--         SUM(case when if_in_confirm_final = 1 then grant_amount_max else NULL end) AS in_confirm_grantcredit_amount_total,
--         SUM(case when if_in_confirm_final = 1 then grantcredit_amount else NULL end) AS in_confirm_grantcredit_amount,
--         SUM(case when if_confirm_passed_final= 1 then apply_grantcredit_amount else NULL end) AS confirm_grantcredit_amount,
--         SUM(case when if_confirm_passed_final= 1 then apply_amount else NULL end) AS confirm_apply_amount,
 
--         SUM(case when if_confirm_passed_final= 1 and if_issue=1 then apply_grantcredit_amount else NULL end) AS issue_confirm_grantcredit_amount,
--         SUM(case when if_confirm_passed_final= 1 and if_issue=1 then apply_amount else NULL end) AS issue_confirm_apply_amount,
--         sum(case when grant_strategy='OLD' and if_recall=0 then if_in_external_data_4 
--                  when grant_strategy='NEW' then if_confirm_passed_final end) if_in_external_data_4,

--         sum(if_external_data_4_passed ) as pass_cnt,
--          sum(if_issue) AS issue_cnt_from_app,
--         sum(is_released_within_24h) AS is_released_within_24h
--     FROM ind.ba_asset_base_info
--     WHERE date(app_date) >= DATE('2025-01-01')  
--     AND date(app_date) < CURRENT_DATE
--     -- AND if_app = 1
--     GROUP BY 1,2,3,4,5,6,7,8,9,10,11,12




-- ),


-- confirm_metrics AS ( 
--     SELECT 
--         create_week,
--         create_month,
--         grant_strategy,
--         product_tag,
--         is_reloan2,
--         new_grade_level,
--         user_level,
--          loan_type2,
--         media_source2,
--         source_channel2,
--         case when if_regular_backup='1' then 1 else 0 end as if_regular_backup,
--         case when if_backup_switch=1 then 1 else 0 end as if_backup_switch, 
--         sum(if_in_confirm_final ) AS in_confirm_cnt_final,
--         sum(if_in_confirm_temp) AS in_confirm_cnt, 
--         sum(case when new_grade_level IN ('1','2') then if_in_confirm_temp else 0 end) AS in_confirm_cnt_1_2,
--         sum(case when new_grade_level IN ('1','2','3','4') then if_in_confirm_temp else 0 end) AS in_confirm_cnt_1_4,
--         sum(case when user_level IN ('1','2') then if_in_confirm_temp else 0 end) AS rl_in_confirm_cnt_1_2,
--         sum(case when user_level IN ('1','2','3') then if_in_confirm_temp else 0 end) AS rl_in_confirm_cnt_1_3,
--         sum(if_confirm_passed_final) AS confirm_passed_cnt, 
--         sum(if_confirm_passed_num_t0) AS if_confirm_passed_num_t0,
--         sum(if_confirm_passed_num_t7) AS if_confirm_passed_num_t7 
--     FROM ind.ba_asset_base_info
--     WHERE date(create_date) >= DATE('2025-01-01')  
--     AND date(create_date) < CURRENT_DATE
--      GROUP BY 1,2,3,4,5,6,7,8,9,10,11,12

-- ),

 
-- issue_metrics AS ( 
--     SELECT 
--         issue_week,
--         issue_month,
--         grant_strategy,
--         product_tag,
--         is_reloan2,
--         loan_type2,
--         new_grade_level,
--         user_level,
 
--         media_source2,
--         source_channel2,
--         case when if_regular_backup='1' then 1 else 0 end as if_regular_backup,
--         case when if_backup_switch=1 then 1 else 0 end as if_backup_switch,
--         sum(if_issue) AS issue_cnt_from_issue,
--         sum(case when new_grade_level IN ('1','2') then if_issue else 0 end) AS issue_cnt_1_2,
--         sum(case when new_grade_level IN ('1','2','3','4') then if_issue else 0 end) AS issue_cnt_1_4,
--         sum(case when user_level IN ('1','2') then if_issue else 0 end) AS rl_issue_cnt_1_2,
--         sum(case when user_level IN ('1','2','3') then if_issue else 0 end) AS rl_issue_cnt_1_3,

--         sum(haircut_amount) as issue_haircut_amount,
--         sum(interest) as issue_interest,
--         sum(revenue) as issue_revenue,
--         sum(contract_amount) AS issue_contract_amount,
--         sum(contract_amount_usd1) AS issue_contract_amount_usd,
     
--         sum(case when grant_strategy = 'NEW' then contract_amount_usd1 else 0 end) AS issue_contract_amount_usd_new,
--         sum(case when grant_strategy = 'OLD' then contract_amount_usd1 else 0 end) AS issue_contract_amount_usd_old,
--         sum(overdue_amount_1_0) AS overdue_amount_1_0,
--         sum(should_capital_1_0) AS should_capital_1_0,
--         sum(overdue_amount_1_7) AS overdue_amount_1_7,
--         sum(should_capital_1_7) AS should_capital_1_7,
--         sum(overdue_amount_1_14) AS overdue_amount_1_14,
--         sum(should_capital_1_14) AS should_capital_1_14,
--         sum(overdue_amount_1_30) AS overdue_amount_1_30,
--         sum(should_capital_1_30) AS should_capital_1_30,
--         sum(overdue_amount_2_0) AS overdue_amount_2_0,
--         sum(should_capital_2_0) AS should_capital_2_0,
--         sum(overdue_amount_2_7) AS overdue_amount_2_7,
--         sum(should_capital_2_7) AS should_capital_2_7,
--         sum(overdue_amount_2_14) AS overdue_amount_2_14,
--         sum(should_capital_2_14) AS should_capital_2_14,
--         sum(overdue_amount_2_30) AS overdue_amount_2_30,
--         sum(should_capital_2_30) AS should_capital_2_30,

--         sum(loan_cycle_amount) AS loan_cycle_amount
 

--     FROM ind.ba_asset_base_info
--     WHERE if_issue = 1
--     AND date(issue_date) >= DATE('2025-01-01') 
--     AND date(issue_date) < CURRENT_DATE 
--     GROUP BY 1,2,3,4,5,6,7,8,9,10,11,12 





-- ),



-- should_metrics AS (


--     SELECT
--     to_char(date_trunc('month',a.should_date),'yyyy-mm-dd') as should_month,
-- 	to_char(date_trunc('week', a.should_date),'yyyy-mm-dd') as should_week,
--     c.grant_strategy,
--     c.product_tag,
--     c.is_reloan2,
--     c.loan_type2,
--     c.new_grade_level,
--      c.user_level,
--     c.media_source2,
--     c.source_channel2,  
--     case when c.if_regular_backup='1' then 1 else 0 end as if_regular_backup,
--     case when c.if_backup_switch=1 then 1 else 0 end as if_backup_switch,

--     SUM(a.should_capital) AS should_capital, 
--     SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 1 THEN a.should_capital ELSE null END) AS should_capital_d0, 
--     SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 2 THEN a.should_capital ELSE null END) AS should_capital_d1,
--     SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 8 THEN a.should_capital ELSE null END) AS should_capital_d7,
--     SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 16 THEN a.should_capital ELSE null END) AS should_capital_d15,
--     SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 31 THEN a.should_capital ELSE null END) AS should_capital_d30,
 
 
--     SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 1 THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d0, 
--     SUM(CASE WHEN due_day <= 1  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 2 THEN a.fact_capital ELSE 0 END) AS t1_capital_paid_d1,
--     SUM(CASE WHEN due_day <= 7  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 8 THEN a.fact_capital ELSE 0 END) AS t7_capital_paid_d7,
--     SUM(CASE WHEN due_day <= 15 and DATE_DIFF('day',should_date,CURRENT_DATE) >= 16 THEN a.fact_capital ELSE 0 END) AS t15_capital_paid_d15,
--     SUM(CASE WHEN due_day <= 30 and DATE_DIFF('day',should_date,CURRENT_DATE) >= 31 THEN a.fact_capital ELSE 0 END) AS t30_capital_paid_d30,

--     SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 8  THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d7,
--     SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 16 THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d15,
--     SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 31 THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d30


 
-- FROM (
--     SELECT  
--         customer_id,
--         camera_id AS biz_id, 
--         should_date, 
--         due_day, 
--         SUM(should_amount) AS should_amount,
--         SUM(should_capital) AS should_capital,
--         SUM(should_interest) AS should_interest,
--         SUM(should_fine) AS should_fine,
--         SUM(fact_amount) AS fact_amount,
--         SUM(fact_capital) AS fact_capital,
--         SUM(fact_interest) AS fact_interest,
--         SUM(fact_fine) AS fact_fine
--     FROM ind.gqy_case_info_f
--     WHERE is_due = 0
--         AND should_date >= DATE('2025-01-01') 
--         AND should_date < CURRENT_DATE
--     GROUP BY 
--         1,2,3,4

-- ) a 
-- LEFT JOIN (
--     SELECT 
--         data_date,
--         customer_id,
--         MAX(max_due_day) AS cus_ovd_day
--     FROM ind.gqy_daliy_case
--     GROUP BY 1,2
--     HAVING MAX(max_due_day) >= 1
-- ) b ON a.customer_id = b.customer_id AND should_date = b.data_date
-- left join ind.ba_asset_base_info c 
-- on  TRY_CAST (a.biz_id AS BIGINT) = TRY_CAST (c.biz_id AS BIGINT)
-- WHERE b.customer_id IS NULL 
-- GROUP BY 1,2,3,4,5,6,7,8,9,10,11,12 






-- ),
-- data_date as (
--     select distinct 
--     date_mon,
--     date_format(DATE_PARSE(data_date, '%Y%m%d'), '%Y-%m-01') AS data_month, 
--     month_days,  
--     day(DATE_ADD('day', -1, CURRENT_DATE)) as current_date_day,
--     case when DATE_PARSE(month_end, '%Y%m%d')<DATE_TRUNC('month', CURRENT_DATE) 
--     then day(DATE_PARSE(month_end, '%Y%m%d'))
--     else day(DATE_ADD('day', -1, CURRENT_DATE))
--     end as date_month_end_actual 
--     from dim.dim_data_info
-- )

 


--         SELECT 
--     COALESCE(a.grant_strategy, i.grant_strategy, s.grant_strategy, c.grant_strategy) AS grant_strategy,
--     COALESCE(a.product_tag, i.product_tag, s.product_tag, c.product_tag) AS product_tag,
--     COALESCE(a.is_reloan2, i.is_reloan2, s.is_reloan2, c.is_reloan2) AS is_reloan2,
--     COALESCE(a.new_grade_level, i.new_grade_level, s.new_grade_level, c.new_grade_level) AS new_grade_level,
--     COALESCE(a.user_level, i.user_level, s.user_level, c.user_level) AS user_level,
 

--     COALESCE(a.media_source2, i.media_source2, s.media_source2, c.media_source2) AS media_source,
--     COALESCE(a.source_channel2, i.source_channel2, s.source_channel2, c.source_channel2) AS source_channel2, 
--     COALESCE(a.if_regular_backup,i.if_regular_backup, s.if_regular_backup, c.if_regular_backup) AS if_regular_backup,
--     COALESCE(a.if_backup_switch, i.if_backup_switch, s.if_backup_switch, c.if_backup_switch) AS if_backup_switch,


--     COALESCE(date(a.app_week), date(i.issue_week), date(s.should_week), c.create_week) AS app_week,

--     COALESCE(a.app_month, i.issue_month, s.should_month, c.create_month) AS app_month,  

--     COALESCE(a.if_app, 0) AS if_app,
--     COALESCE(a.if_external_3_passed, 0) AS if_external_3_passed,
--     COALESCE(c.in_confirm_cnt_final, 0) AS in_confirm_cnt_final,
--     COALESCE(c.in_confirm_cnt, 0) AS in_confirm_cnt,
--     COALESCE(c.in_confirm_cnt_1_2, 0) AS in_confirm_cnt_1_2,
--     COALESCE(c.in_confirm_cnt_1_4, 0) AS in_confirm_cnt_1_4,
--     COALESCE(c.rl_in_confirm_cnt_1_2, 0) AS rl_in_confirm_cnt_1_2,
--     COALESCE(c.rl_in_confirm_cnt_1_3, 0) AS rl_in_confirm_cnt_1_3,

--     COALESCE(c.confirm_passed_cnt, 0) AS confirm_passed_cnt,
--     COALESCE(c.if_confirm_passed_num_t0, 0) AS if_confirm_passed_num_t0,
--     COALESCE(c.if_confirm_passed_num_t7, 0) AS if_confirm_passed_num_t7,

--     COALESCE(a.in_confirm_grantcredit_amount_total, 0) AS in_confirm_grantcredit_amount_total,
--     COALESCE(a.in_confirm_grantcredit_amount, 0) AS in_confirm_grantcredit_amount,
--     COALESCE(a.confirm_grantcredit_amount, 0) AS confirm_grantcredit_amount,
--     COALESCE(a.confirm_apply_amount, 0) AS confirm_apply_amount,
--     COALESCE(a.if_in_external_data_4, 0) AS if_in_external_data_4,
--     COALESCE(a.pass_cnt, 0) AS pass_cnt, 
--     COALESCE(a.issue_cnt_from_app, 0) AS issue_cnt_from_app,
--     COALESCE(a.is_released_within_24h, 0) AS is_released_within_24h, 
--     COALESCE(i.issue_cnt_from_issue, 0) AS issue_cnt_from_issue,
--     COALESCE(i.issue_cnt_1_2, 0) AS issue_cnt_1_2,
--     COALESCE(i.issue_cnt_1_4, 0) AS issue_cnt_1_4,
--     COALESCE(i.rl_issue_cnt_1_2, 0) AS rl_issue_cnt_1_2,
--     COALESCE(i.rl_issue_cnt_1_3, 0) AS rl_issue_cnt_1_3,
--     COALESCE(i.issue_contract_amount, 0) AS issue_contract_amount,
--     COALESCE(i.issue_contract_amount_usd, 0) AS issue_contract_amount_usd,
--     SUM(COALESCE(i.issue_contract_amount_usd, 0)) OVER (PARTITION BY COALESCE(a.app_month, i.issue_month, s.should_month)) AS issue_contract_group,
--     SUM(case when COALESCE(a.grant_strategy, i.grant_strategy, s.grant_strategy)='NEW'
--     then COALESCE(i.issue_contract_amount_usd, 0)
--     else 0 end ) OVER (PARTITION BY COALESCE(a.app_month, i.issue_month, s.should_month)) AS issue_contract_new_group,
--     SUM(case when COALESCE(a.grant_strategy, i.grant_strategy, s.grant_strategy)='OLD'
--     then COALESCE(i.issue_contract_amount_usd, 0)
--     else 0 end ) OVER (PARTITION BY COALESCE(a.app_month, i.issue_month, s.should_month)) AS issue_contract_old_group,
    
--     COALESCE(i.overdue_amount_1_0, 0) AS overdue_amount_1_0,
--     COALESCE(i.should_capital_1_0, 0) AS should_capital_1_0,
--     COALESCE(i.overdue_amount_1_7, 0) AS overdue_amount_1_7,
--     COALESCE(i.should_capital_1_7, 0) AS should_capital_1_7,
--     COALESCE(i.overdue_amount_1_14, 0) AS overdue_amount_1_14,
--     COALESCE(i.should_capital_1_14, 0) AS should_capital_1_14,
--     COALESCE(i.overdue_amount_1_30, 0) AS overdue_amount_1_30,
--     COALESCE(i.should_capital_1_30, 0) AS should_capital_1_30, 
--     COALESCE(i.overdue_amount_2_0, 0) AS overdue_amount_2_0,
--     COALESCE(i.should_capital_2_0, 0) AS should_capital_2_0,
--     COALESCE(i.overdue_amount_2_7, 0) AS overdue_amount_2_7,
--     COALESCE(i.should_capital_2_7, 0) AS should_capital_2_7, 
--     COALESCE(i.overdue_amount_2_30, 0) AS overdue_amount_2_30,
--     COALESCE(i.should_capital_2_30, 0) AS should_capital_2_30, 
--     COALESCE(s.should_capital_d0, 0) AS should_capital_d0, 
--     COALESCE(s.should_capital_d1, 0) AS should_capital_d1,
--     COALESCE(s.should_capital_d7, 0) AS should_capital_d7,
--     COALESCE(s.should_capital_d15, 0) AS should_capital_d15,
--     COALESCE(s.should_capital_d30, 0) AS should_capital_d30, 
--     COALESCE(s.should_capital_d0 - s.t0_capital_paid_d0, 0) AS t0_capital_due_d0,
--     COALESCE(s.should_capital_d1 - s.t1_capital_paid_d1, 0) AS t1_capital_due_d1,
--     COALESCE(s.should_capital_d7 - s.t7_capital_paid_d7, 0) AS t7_capital_due_d7,
--     COALESCE(s.should_capital_d15 - s.t15_capital_paid_d15, 0) AS t15_capital_due_d15,
--     COALESCE(s.should_capital_d30 - s.t30_capital_paid_d30, 0) AS t30_capital_due_d30,
--     COALESCE(s.t0_capital_paid_d7, 0) AS t0_capital_paid_d7,
--     COALESCE(s.t0_capital_paid_d15, 0) AS t0_capital_paid_d15,
--     COALESCE(s.t0_capital_paid_d30, 0) AS t0_capital_paid_d30,
--     COALESCE(s.t7_capital_paid_d7 - s.t0_capital_paid_d7, 0) AS t0_7_capital_paid_d7,
--     COALESCE(s.t15_capital_paid_d15 - s.t0_capital_paid_d15, 0) AS t0_15_capital_paid_d15,
--     COALESCE(s.t30_capital_paid_d30 - s.t0_capital_paid_d30, 0) AS t0_30_capital_paid_d30,

--     COALESCE(s.should_capital_d7 - s.t0_capital_paid_d7, 0) AS t0_7_capital_paid_due_d7,
--     COALESCE(s.should_capital_d15 - s.t0_capital_paid_d15, 0) AS t0_15_capital_paid_due_d15,
--     COALESCE(s.should_capital_d30 - s.t0_capital_paid_d30, 0) AS t0_30_capital_paid_due_d30,
--     COALESCE(loan_cycle_amount, 0) AS loan_cycle_amount,
--     COALESCE(issue_haircut_amount, 0) AS issue_haircut_amount,
--     COALESCE(issue_interest, 0) AS issue_interest,
--     COALESCE(issue_revenue, 0) AS issue_revenue,
--      total_amt*exchange_rate* 1.00000 / f1.exchange_rate_to_dollar  AS ov_total_amt_usd,
--     fl_contract_amt*exchange_rate* 1.00000 / f1.exchange_rate_to_dollar AS fl_total_amt_usd,
--     rl_contract_amt*exchange_rate* 1.00000 / f1.exchange_rate_to_dollar AS rl_total_amt_usd,
--     month_days, 
--     date_month_end_actual ,
--     COALESCE(issue_contract_amount_usd_new, 0) AS issue_contract_amount_usd_new,
--     COALESCE(issue_contract_amount_usd_old, 0) AS issue_contract_amount_usd_old,
--         COALESCE(a.loan_type2, i.loan_type2, s.loan_type2,c.loan_type2) AS loan_type2


-- FROM application_metrics a
-- FULL JOIN issue_metrics i 
--     ON a.grant_strategy = i.grant_strategy
--     AND a.product_tag = i.product_tag
--     AND a.is_reloan2 = i.is_reloan2
--     AND a.loan_type2 = i.loan_type2
--     AND a.new_grade_level = i.new_grade_level
--     AND a.media_source2 = i.media_source2
--     AND a.source_channel2 = i.source_channel2 
--     AND a.app_week = i.issue_week
--     AND a.app_month = i.issue_month
--     AND a.user_level = i.user_level
--     AND a.if_regular_backup = i.if_regular_backup
--     AND a.if_backup_switch = i.if_backup_switch
 


-- FULL JOIN should_metrics s
--     ON COALESCE(a.grant_strategy, i.grant_strategy) = s.grant_strategy
--     AND COALESCE(a.product_tag, i.product_tag) = s.product_tag
--     AND COALESCE(a.is_reloan2, i.is_reloan2) = s.is_reloan2
--     AND COALESCE(a.loan_type2, i.loan_type2) = s.loan_type2
--     AND COALESCE(a.new_grade_level, i.new_grade_level) = s.new_grade_level
--     AND COALESCE(a.media_source2, i.media_source2) = s.media_source2
--     AND COALESCE(a.source_channel2, i.source_channel2) = s.source_channel2 
--     AND COALESCE(a.app_week, i.issue_week) = s.should_week
--     AND COALESCE(a.app_month, i.issue_month) = s.should_month
--     AND COALESCE(a.user_level, i.user_level) = s.user_level
--     AND COALESCE(a.if_regular_backup, i.if_regular_backup) = s.if_regular_backup
--     AND COALESCE(a.if_backup_switch, i.if_backup_switch) = s.if_backup_switch
-- full join confirm_metrics c
--     ON COALESCE(a.grant_strategy, i.grant_strategy) = c.grant_strategy
--     AND COALESCE(a.product_tag, i.product_tag) = c.product_tag
--     AND COALESCE(a.is_reloan2, i.is_reloan2) = c.is_reloan2
--     AND COALESCE(a.loan_type2, i.loan_type2) = c.loan_type2
--     AND COALESCE(a.new_grade_level, i.new_grade_level) = c.new_grade_level
--     AND COALESCE(a.media_source2, i.media_source2) = c.media_source2
--     AND COALESCE(a.source_channel2, i.source_channel2) = c.source_channel2 
--     AND COALESCE(date(a.app_week), date(i.issue_week)) = c.create_week

--     AND COALESCE(a.app_month, i.issue_month) = c.create_month
--     AND COALESCE(a.user_level, i.user_level) = c.user_level
--     AND COALESCE(a.if_regular_backup, i.if_regular_backup) = c.if_regular_backup
--     AND COALESCE(a.if_backup_switch, i.if_backup_switch) = c.if_backup_switch
 
-- LEFT JOIN ind.ba_kpi_targets_m b
--     ON COALESCE(a.app_month, i.issue_month, s.should_month) = b.month 
-- left join data_date c
--     ON b.month = c.data_month 
-- LEFT JOIN dim.dim_exchange_rate_cost f1 ON c.date_mon = f1.month_id AND f1.account_currency = 'IDR'
-- ;










 
drop table if exists ind.ba_install_apply_result;
create table
if not exists ind.ba_install_apply_result as

with spend AS (
    select 
        date(ad_date) as ad_date
        ,case when media_source='ASA' then 'IOS_ASA'
                when lower(campaign_name) like  '%ios%'  or lower(media_source) like '%ios%' then 'IOS_OTHER'
                when media_source like '%oogle%' and lower(campaign_name) not like '%ios%' then 'Google'
                when media_source like '%acebook%' and lower(campaign_name) not like '%ios%' then 'Facebook'
                when media_source='organic' then 'Organic'  
                when media_source='Tiktok' then 'Tiktok'
                when media_source='Kwai' then 'Kwai'
                else 'other'
            end as media_source
        ,sum(spend_usd_discount) as spend
        from ind.tyn_ads_cost_discount a
        where ad_date >= date'2025-01-01'
        group by 1,2  
    union all
    select
        distinct
        ad_date,
        'Organic' as media_source,
        0 as spend
        from ind.tyn_ads_cost_discount  
        where ad_date >= date'2025-01-01'
    ),
install_cnt as (
    SELECT install_date,   
     case 
    when media_source in('Google','Facebook','Organic','Tiktok','Kwai') then media_source 
    when media_source='ASA' then 'IOS_ASA'
    when lower(media_source) like '%ios%' then 'IOS_OTHER' 
    else 'other'
    end as media_source,  
    sum(install_cnt) as install_cnt 
    FROM (
    SELECT 
    DATE(event_time + INTERVAL '7' HOUR) AS install_date,
    case 	   		
		when platform = 'ios' and  media_source = 'Apple Search Ads' then 'ASA'
			when platform = 'ios' and  media_source in ('restricted','Facebook Ads') then 'IOS-fb'
			when platform = 'ios' and  media_source = 'tiktokglobal_int' then 'IOS-tt'
			when platform = 'ios' and  media_source = 'googleadwords_int' then 'IOS-gg'
			when platform = 'ios' and  media_source = 'vfine_int' then 'IOS-vfine'
			when platform = 'ios' and  media_source = 'Rupiah Cepat' then 'IOS-RC'
			when platform = 'ios' and  media_source = 'yupaamj_int' then 'IOS-yup'
			when platform = 'ios' and  media_source = 'tangads' then 'IOS-tangads'
			when platform = 'ios' and  media_source = 'Pinjamyuk_ads' then 'IOS-Pinjamyuk'
		  --when platform = 'ios' and  media_source = 'organic' then 'IOS-Organic'	
			when platform = 'ios'  then 'IOS-Organic'	
			when media_source='googleadwords_int' then 'Google'
             when media_source='Facebook Ads' or media_source='restricted' then 'Facebook'
             when media_source='organic' then 'Organic'
             when media_source = 'shareit_int' then 'Shareit'
             when media_source = 'kreditlist_int' or (media_source = 'vfine_int' and partner like '%redi%'  ) 
             or 
             (media_source is null and partner = 'kreditlist')
             then 'kreditlist_int'
			 when media_source = 'vfine_int' or media_source = 'adecentptuo_int' then 'Vfine'
             when media_source in ('bytedanceglobal_int','tiktokglobal_int') then 'Tiktok'
			 when media_source = 'kwaiforbusiness_int' then 'Kwai'
             when media_source = 'cashcashpro' then 'cashcashpro'
			 when media_source = 'cashcerdasid_int' then 'cashcerdas'
			 when media_source = 'kredit pintal' then 'kp'
			 when media_source in ('atomcmkhg_int','atomfinhhl_int') then 'atomcm'
			 when regexp_like(campaign, '^pp') then 'Novabeyond'
			 when media_source = 'pyxis_int' then 'pyxis'
			 when media_source = 'Rupiah Cepat' then 'Rupiah Cepat'
			 when media_source = 'Twitter' then 'twitter'
			 when media_source in ('medproad_int','influencet_int','safmobi_int','brightligkw_int','futuremobxgk_int','cryptosprkw_int','sundvika_int'
,'lianhualu4df_int','mobisummer_int','jmmobied_int','madheadga1ml_int','datagon_int','nzzgmobi_int','wedifice7v_int','qizhimobi_int'
,'zacharyj_int','moreadspdi_int','otterseagv3_int','coooladsi5n_int','wirelesshdk_int','magicmobs_int','inforaftssh_int'
,'adtiming_int','pybzltdio_int','fimobil_int','flashuplt0gh_int','bhglobals7u_int','souththird9_int','dashdigitbj_int','geostar3d_int','nativenation_int'
,'qqiwatx_int','oytexpd_int','boomob_int','acabusoe5i_int','plugcloq6_int','muldigi_int','goatbizeezh_int','lonnimobi_int'
,'jjexany_int','searchus5g_int','callaads_int','signoadsz1_int','yydsmobi_int','cloudappmxx_int','nzxfguide_int'
,'wupenpenpk_int','ralumadsxe_int','netmobile26_int','pearllsns_int','agencyonet_int','appnext_int'
,'nzkamobi_int','polybridges_int','gameappzo45i_int','seoultsy_int','devmobilejw_int','commondex_int'
,'digiwhisk_int','thanhdat_int','grandemedia_int') or lower(campaign) like '%tecdo%' or partner ='appscuckoobd650'then 'Network union'
			when media_source in ('maalook8r_int','oauthhook9o_int','apppro_int','primeadsdr_int','adssharpltd_int','birdpenguin_int','mikkyyw_int','pearllsns_int','citronnn9_int','motechhubkki_int','flybype4_int','ciroocle69_int'
,'applenutsnc_int','jampp_int','thetradedesk_int','beepinkmedia_int','blackteatech_int','oarreal_int','plustep5y_int') or lower(campaign) like '%rainbow%' then 'rainbow'
			when media_source in ('graffitilt_int','flatads_int','onetraffijs_int','desmob_int','goodliveqpf_int') then 'flatads_int'
			when campaign like '%CookeAds_CPI%' then 'CookeAds_CPI'
			when campaign ='CookeAds_CPS' or lower(campaign) like '%cookeads%' then 'CookeAds_CPS'
			when partner = '19mobicn' then '19mobi'
			when campaign = 'Samire_Jan2025youmi' then 'youmi'
			when media_source ='yupaamj_int' then 'yup'
			--when regexp_like(campaign, '^pp') then 'Novabeyond'
			when media_source = 'mintegral_int' then 'mintegral_int'
			when lower(media_source) like '%grab%' then 'Grab'
			when media_source in ('vipmanageb6_int','emilysele_int','icerainbow_int') or lower(campaign) like '%runto%' then 'RUNTOA'
			when lower(campaign) like '%mejoy%'  then 'mejoy'
			when lower(campaign) like '%yolo%'  then 'yolo'
			when media_source ='LinkAja_ads' then 'LinkAja_ads'
			when media_source in ('easycash01','easycashid_int') then 'easycash01'
			when media_source ='xiaomiglobal_int' then 'xiaomiglobal_int'
			when media_source ='tangads' then 'tangads'
			when media_source ='Pinjamyuk_ads' then 'Pinjamyuk_ads'
			when media_source ='oppoglobal_int' then 'oppoglobal_int'
			when media_source like '%_int%' then 'other'
			 else 'Organic'
        end as media_source,
    COUNT(DISTINCT appsflyer_id) AS install_cnt
    FROM ods.s08_appsflyer_push_data
    WHERE  etl_date>='20250101' and event_name='install' 
    and date(event_time + INTERVAL '7' HOUR) >= date'2025-01-01'
    GROUP BY 1,2 
    )t
    GROUP BY 1,2 
     ),

 
reg_cnt as (
    select 
    reg_dt,
    case 
    when media_source in('Google','Facebook','Organic','Tiktok','Kwai') then media_source 
    when media_source='ASA' then 'IOS_ASA'
    when lower(media_source) like '%ios%' then 'IOS_OTHER' 
    else 'other'
    end as media_source, 
    count(distinct mid) reg_cnt
    from ind.tyn_reg_install_new
    where reg_dt >= date'2025-01-01'
    group by 1,2 
     ),
apply_cnt AS ( 
    SELECT
        date(app_date) as app_date,  
        media_source2, 
        sum(if_app) AS if_app  
    FROM ind.ba_asset_base_info 
    WHERE grant_strategy='NEW' 
    and if_app=1
    and if_recall=0
    and date(app_date) >= date'2025-01-01'
    GROUP BY 1,2 

),
issue_cnt AS ( 

    SELECT
        date(issue_date) as issue_date, 
        media_source2, 
        sum(if_issue) AS issue_cnt,
        sum(case when new_grade_level IN ('1','2') then if_issue else 0 end) AS issue_cnt_1_2,
        sum(case when new_grade_level IN ('1','2','3','4') then if_issue else 0 end) AS issue_cnt_1_4,
        sum(contract_amount_usd) as contract_amount_usd
    FROM ind.ba_asset_base_info
    WHERE if_issue = 1
    and grant_strategy='NEW' 
    and date(issue_date) >= date'2025-01-01'
    GROUP BY 1,2
)
 
SELECT
    COALESCE(a.ad_date, b.install_date, c.reg_dt, d.app_date, e.issue_date) AS ad_date,
    to_char(date_trunc('month', COALESCE(a.ad_date, b.install_date, c.reg_dt, d.app_date, e.issue_date)), 'yyyy-mm-dd') AS ad_date_month,
    to_char(date_trunc('week', COALESCE(a.ad_date, b.install_date, c.reg_dt, d.app_date, e.issue_date)), 'yyyy-mm-dd') AS ad_date_week,
    COALESCE(a.media_source, b.media_source, c.media_source, d.media_source2, e.media_source2) AS media_source,
    COALESCE(a.spend, 0) AS spend,
    COALESCE(b.install_cnt, 0) AS install_cnt,
    COALESCE(c.reg_cnt, 0) AS reg_cnt,
    COALESCE(d.if_app, 0) AS if_app,
    COALESCE(e.issue_cnt, 0) AS issue_cnt,
    COALESCE(e.issue_cnt_1_2, 0) AS issue_cnt_1_2,
    COALESCE(e.issue_cnt_1_4, 0) AS issue_cnt_1_4,
    COALESCE(e.contract_amount_usd, 0) AS contract_amount_usd

FROM spend a
FULL OUTER JOIN install_cnt b ON a.ad_date = b.install_date AND a.media_source = b.media_source
FULL OUTER JOIN reg_cnt c ON a.ad_date = c.reg_dt AND a.media_source = c.media_source
FULL OUTER JOIN apply_cnt d ON a.ad_date = d.app_date AND a.media_source = d.media_source2
FULL OUTER JOIN issue_cnt e ON a.ad_date = e.issue_date AND a.media_source = e.media_source2;


  


  






 
-- select * from ind.ba_apply_should_result_week_OLD limit 100000
  drop table if exists ind.ba_apply_should_result_week_OLD;
create table
if not exists ind.ba_apply_should_result_week_OLD as

WITH application_metrics AS ( 
    SELECT 
        app_week,
        app_month,
        grant_strategy,
        product_tag,
        is_reloan2,
        new_grade_level,
        user_level,
        first_loan_grade_level,
        loan_type2, 
        case when if_regular_backup='1' then 1 else 0 end as if_regular_backup,
        case when if_backup_switch=1 then 1 else 0 end as if_backup_switch,

        sum(case when if_recall=0 then if_app end) if_app,
        sum(case when grant_strategy='OLD' and if_recall=0 then if_external_data_3_passed 
                 when grant_strategy='NEW' then if_in_confirm_temp end) if_external_3_passed,

                -- sum(if_in_confirm_final ) AS in_confirm_cnt_final,
        -- sum(if_in_confirm_temp) AS in_confirm_cnt,
        -- sum(case when new_grade_level IN ('1','2') then if_in_confirm_temp else 0 end) AS in_confirm_cnt_1_2,
        -- sum(case when new_grade_level IN ('1','2','3','4') then if_in_confirm_temp else 0 end) AS in_confirm_cnt_1_4,
        -- sum(case when user_level IN ('1','2') then if_in_confirm_temp else 0 end) AS rl_in_confirm_cnt_1_2,
        -- sum(case when user_level IN ('1','2','3') then if_in_confirm_temp else 0 end) AS rl_in_confirm_cnt_1_3,
        -- sum(if_confirm_passed_final) AS confirm_passed_cnt, 
        -- sum(if_confirm_passed_num_t0) AS if_confirm_passed_num_t0,
        -- sum(if_confirm_passed_num_t7) AS if_confirm_passed_num_t7,
        SUM(case when if_in_confirm_final = 1 then grant_amount_max else NULL end) AS in_confirm_grantcredit_amount_total,
        SUM(case when if_in_confirm_final = 1 then grantcredit_amount else NULL end) AS in_confirm_grantcredit_amount,
        SUM(case when if_confirm_passed_final= 1 then apply_grantcredit_amount else NULL end) AS confirm_grantcredit_amount,
        SUM(case when if_confirm_passed_final= 1 then apply_amount else NULL end) AS confirm_apply_amount,
 
        SUM(case when if_confirm_passed_final= 1 and if_issue=1 then apply_grantcredit_amount else NULL end) AS issue_confirm_grantcredit_amount,
        SUM(case when if_confirm_passed_final= 1 and if_issue=1 then apply_amount else NULL end) AS issue_confirm_apply_amount,
        sum(case when grant_strategy='OLD' and if_recall=0 then if_in_external_data_4 
                 when grant_strategy='NEW' then if_confirm_passed_final end) if_in_external_data_4,

        sum(if_external_data_4_passed ) as pass_cnt,
         sum(if_issue) AS issue_cnt_from_app,
        sum(is_released_within_24h) AS is_released_within_24h
    FROM ind.ba_asset_base_info
    WHERE date(app_date) >= DATE('2025-01-01')  
    AND date(app_date) < CURRENT_DATE
    AND grant_strategy = 'OLD'
    GROUP BY 1,2,3,4,5,6,7,8,9,10,11  




),



confirm_metrics AS ( 
    SELECT 
        create_week,
        date_format(create_date, '%Y-%m-01') create_month,
        grant_strategy,
        product_tag,
        is_reloan2,
        new_grade_level,
        user_level,
        first_loan_grade_level,
         loan_type2,
         case when if_regular_backup='1' then 1 else 0 end as if_regular_backup,
        case when if_backup_switch=1 then 1 else 0 end as if_backup_switch, 
        sum(if_in_confirm_final ) AS in_confirm_cnt_final,
        sum(if_in_confirm_temp) AS in_confirm_cnt, 
        sum(case when new_grade_level IN ('1','2') then if_in_confirm_temp else 0 end) AS in_confirm_cnt_1_2,
        sum(case when new_grade_level IN ('1','2','3','4') then if_in_confirm_temp else 0 end) AS in_confirm_cnt_1_4,
        sum(case when user_level IN ('1','2') then if_in_confirm_temp else 0 end) AS rl_in_confirm_cnt_1_2,
        sum(case when user_level IN ('1','2','3') then if_in_confirm_temp else 0 end) AS rl_in_confirm_cnt_1_3,
        sum(if_confirm_passed_final) AS confirm_passed_cnt, 
        sum(if_confirm_passed_num_24h) AS if_confirm_passed_num_24h,

        sum(if_confirm_passed_num_t0) AS if_confirm_passed_num_t0,
        sum(if_confirm_passed_num_t7) AS if_confirm_passed_num_t7 
    FROM ind.ba_asset_base_info
    WHERE date(create_date) >= DATE('2025-01-01')  
    AND date(create_date) < CURRENT_DATE
     GROUP BY 1,2,3,4,5,6,7,8,9,10,11

),
 
 
issue_metrics AS ( 
    SELECT 
        issue_week,
        issue_month,
        grant_strategy,
        product_tag,
        is_reloan2,
        loan_type2,
        new_grade_level,
        user_level,
        first_loan_grade_level,
 
        case when if_regular_backup='1' then 1 else 0 end as if_regular_backup,
        case when if_backup_switch=1 then 1 else 0 end as if_backup_switch,
        sum(if_issue) AS issue_cnt_from_issue,
        sum(case when new_grade_level IN ('1','2') then if_issue else 0 end) AS issue_cnt_1_2,
        sum(case when new_grade_level IN ('1','2','3','4') then if_issue else 0 end) AS issue_cnt_1_4,
        sum(case when user_level IN ('1','2') then if_issue else 0 end) AS rl_issue_cnt_1_2,
        sum(case when user_level IN ('1','2','3') then if_issue else 0 end) AS rl_issue_cnt_1_3,

        sum(haircut_amount) as issue_haircut_amount,
        sum(interest) as issue_interest,
        sum(revenue) as issue_revenue,
        sum(contract_amount) AS issue_contract_amount,
        sum(contract_amount_usd1) AS issue_contract_amount_usd,
     
        sum(case when grant_strategy = 'NEW' then contract_amount_usd1 else 0 end) AS issue_contract_amount_usd_new,
        sum(case when grant_strategy = 'OLD' then contract_amount_usd1 else 0 end) AS issue_contract_amount_usd_old,
        sum(overdue_amount_1_0) AS overdue_amount_1_0,
        sum(should_capital_1_0) AS should_capital_1_0,
        sum(overdue_amount_1_7) AS overdue_amount_1_7,
        sum(should_capital_1_7) AS should_capital_1_7,
        sum(overdue_amount_1_14) AS overdue_amount_1_14,
        sum(should_capital_1_14) AS should_capital_1_14,
        sum(overdue_amount_1_30) AS overdue_amount_1_30,
        sum(should_capital_1_30) AS should_capital_1_30,
        sum(overdue_amount_2_0) AS overdue_amount_2_0,
        sum(should_capital_2_0) AS should_capital_2_0,
        sum(overdue_amount_2_7) AS overdue_amount_2_7,
        sum(should_capital_2_7) AS should_capital_2_7,
        sum(overdue_amount_2_14) AS overdue_amount_2_14,
        sum(should_capital_2_14) AS should_capital_2_14,
        sum(overdue_amount_2_30) AS overdue_amount_2_30,
        sum(should_capital_2_30) AS should_capital_2_30,

        sum(loan_cycle_amount) AS loan_cycle_amount 
 

    FROM ind.ba_asset_base_info
    WHERE if_issue = 1
    AND grant_strategy = 'OLD'

    AND date(issue_date) >= DATE('2025-01-01') 
    AND date(issue_date) < CURRENT_DATE 
    GROUP BY 1,2,3,4,5,6,7,8,9,10,11 





),



should_metrics AS (


    SELECT
    to_char(date_trunc('month',a.should_date),'yyyy-mm-dd') as should_month,
	to_char(date_trunc('week', a.should_date),'yyyy-mm-dd') as should_week,
    c.grant_strategy,
    c.product_tag,
    c.is_reloan2,
    c.loan_type2,
    c.new_grade_level,
    c.first_loan_grade_level,
    c.user_level, 
    case when c.if_regular_backup='1' then 1 else 0 end as if_regular_backup,
    case when c.if_backup_switch=1 then 1 else 0 end as if_backup_switch,

    SUM(a.should_capital) AS should_capital, 
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 1 THEN a.should_capital ELSE null END) AS should_capital_d0, 
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 2 THEN a.should_capital ELSE null END) AS should_capital_d1,
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 8 THEN a.should_capital ELSE null END) AS should_capital_d7,
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 16 THEN a.should_capital ELSE null END) AS should_capital_d15,
    SUM(CASE WHEN DATE_DIFF('day',should_date,CURRENT_DATE) >= 31 THEN a.should_capital ELSE null END) AS should_capital_d30,
 
 
    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 1 THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d0, 
    SUM(CASE WHEN due_day <= 1  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 2 THEN a.fact_capital ELSE 0 END) AS t1_capital_paid_d1,
    SUM(CASE WHEN due_day <= 7  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 8 THEN a.fact_capital ELSE 0 END) AS t7_capital_paid_d7,
    SUM(CASE WHEN due_day <= 15 and DATE_DIFF('day',should_date,CURRENT_DATE) >= 16 THEN a.fact_capital ELSE 0 END) AS t15_capital_paid_d15,
    SUM(CASE WHEN due_day <= 30 and DATE_DIFF('day',should_date,CURRENT_DATE) >= 31 THEN a.fact_capital ELSE 0 END) AS t30_capital_paid_d30,

    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 8  THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d7,
    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 16 THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d15,
    SUM(CASE WHEN due_day <= 0  and DATE_DIFF('day',should_date,CURRENT_DATE) >= 31 THEN a.fact_capital ELSE 0 END) AS t0_capital_paid_d30


 
FROM (
    SELECT  
        customer_id,
        camera_id AS biz_id, 
        should_date, 
        due_day, 
        SUM(should_amount) AS should_amount,
        SUM(should_capital) AS should_capital,
        SUM(should_interest) AS should_interest,
        SUM(should_fine) AS should_fine,
        SUM(fact_amount) AS fact_amount,
        SUM(fact_capital) AS fact_capital,
        SUM(fact_interest) AS fact_interest,
        SUM(fact_fine) AS fact_fine
    FROM ind.gqy_case_info_f
    WHERE is_due = 0
        AND should_date >= DATE('2025-01-01') 
        AND should_date < CURRENT_DATE
    GROUP BY 
        1,2,3,4

) a 
LEFT JOIN (
    SELECT 
        data_date,
        customer_id,
        MAX(max_due_day) AS cus_ovd_day
    FROM ind.gqy_daliy_case
    GROUP BY 1,2
    HAVING MAX(max_due_day) >= 1
) b ON a.customer_id = b.customer_id AND should_date = b.data_date
left join ind.ba_asset_base_info c 
on  TRY_CAST (a.biz_id AS BIGINT) = TRY_CAST (c.biz_id AS BIGINT)
WHERE b.customer_id IS NULL 
AND c.grant_strategy = 'OLD'

GROUP BY 1,2,3,4,5,6,7,8,9,10,11 






),
data_date as (
    select distinct 
    date_mon,
    date_format(DATE_PARSE(data_date, '%Y%m%d'), '%Y-%m-01') AS data_month, 
    month_days,  
    day(DATE_ADD('day', -1, CURRENT_DATE)) as current_date_day,
    case when DATE_PARSE(month_end, '%Y%m%d')<DATE_TRUNC('month', CURRENT_DATE) 
    then day(DATE_PARSE(month_end, '%Y%m%d'))
    else day(DATE_ADD('day', -1, CURRENT_DATE))
    end as date_month_end_actual 
    from dim.dim_data_info
)

 


        SELECT 
    COALESCE(a.grant_strategy, i.grant_strategy, s.grant_strategy, c.grant_strategy) AS grant_strategy,
    COALESCE(a.product_tag, i.product_tag, s.product_tag, c.product_tag) AS product_tag,
    COALESCE(a.is_reloan2, i.is_reloan2, s.is_reloan2, c.is_reloan2) AS is_reloan2,
    COALESCE(a.new_grade_level, i.new_grade_level, s.new_grade_level, c.new_grade_level) AS new_grade_level,
    COALESCE(a.user_level, i.user_level, s.user_level, c.user_level) AS user_level,
    COALESCE(a.first_loan_grade_level, i.first_loan_grade_level, s.first_loan_grade_level, c.first_loan_grade_level) AS first_loan_grade_level,
 
    COALESCE(a.if_regular_backup,i.if_regular_backup, s.if_regular_backup, c.if_regular_backup) AS if_regular_backup,
    COALESCE(a.if_backup_switch, i.if_backup_switch, s.if_backup_switch, c.if_backup_switch) AS if_backup_switch,


    COALESCE(date(a.app_week), date(i.issue_week), date(s.should_week), c.create_week) AS app_week,

    COALESCE(a.app_month, i.issue_month, s.should_month, c.create_month) AS app_month,  
    COALESCE(a.if_app, 0) AS if_app,
    COALESCE(a.if_external_3_passed, 0) AS if_external_3_passed,
    COALESCE(c.in_confirm_cnt_final, 0) AS in_confirm_cnt_final,
    COALESCE(c.in_confirm_cnt, 0) AS in_confirm_cnt,
    COALESCE(c.in_confirm_cnt_1_2, 0) AS in_confirm_cnt_1_2,
    COALESCE(c.in_confirm_cnt_1_4, 0) AS in_confirm_cnt_1_4,
    COALESCE(c.rl_in_confirm_cnt_1_2, 0) AS rl_in_confirm_cnt_1_2,
    COALESCE(c.rl_in_confirm_cnt_1_3, 0) AS rl_in_confirm_cnt_1_3,

    COALESCE(c.confirm_passed_cnt, 0) AS confirm_passed_cnt,
    COALESCE(c.if_confirm_passed_num_24h, 0) AS if_confirm_passed_num_24h,

    COALESCE(c.if_confirm_passed_num_t0, 0) AS if_confirm_passed_num_t0,
    COALESCE(c.if_confirm_passed_num_t7, 0) AS if_confirm_passed_num_t7,

    COALESCE(a.in_confirm_grantcredit_amount_total, 0) AS in_confirm_grantcredit_amount_total,
    COALESCE(a.in_confirm_grantcredit_amount, 0) AS in_confirm_grantcredit_amount,
    COALESCE(a.confirm_grantcredit_amount, 0) AS confirm_grantcredit_amount,
    COALESCE(a.confirm_apply_amount, 0) AS confirm_apply_amount,
    COALESCE(a.if_in_external_data_4, 0) AS if_in_external_data_4,
    COALESCE(a.pass_cnt, 0) AS pass_cnt, 
    COALESCE(a.issue_cnt_from_app, 0) AS issue_cnt_from_app,
    COALESCE(a.is_released_within_24h, 0) AS is_released_within_24h, 
    COALESCE(i.issue_cnt_from_issue, 0) AS issue_cnt_from_issue,
    COALESCE(i.issue_cnt_1_2, 0) AS issue_cnt_1_2,
    COALESCE(i.issue_cnt_1_4, 0) AS issue_cnt_1_4,
    COALESCE(i.rl_issue_cnt_1_2, 0) AS rl_issue_cnt_1_2,
    COALESCE(i.rl_issue_cnt_1_3, 0) AS rl_issue_cnt_1_3,
    COALESCE(i.issue_contract_amount, 0) AS issue_contract_amount,
    COALESCE(i.issue_contract_amount_usd, 0) AS issue_contract_amount_usd,
    SUM(COALESCE(i.issue_contract_amount_usd, 0)) OVER (PARTITION BY COALESCE(a.app_month, i.issue_month, s.should_month)) AS issue_contract_group,
    SUM(case when COALESCE(a.grant_strategy, i.grant_strategy, s.grant_strategy)='NEW'
    then COALESCE(i.issue_contract_amount_usd, 0)
    else 0 end ) OVER (PARTITION BY COALESCE(a.app_month, i.issue_month, s.should_month)) AS issue_contract_new_group,
    SUM(case when COALESCE(a.grant_strategy, i.grant_strategy, s.grant_strategy)='OLD'
    then COALESCE(i.issue_contract_amount_usd, 0)
    else 0 end ) OVER (PARTITION BY COALESCE(a.app_month, i.issue_month, s.should_month)) AS issue_contract_old_group,
    
    COALESCE(i.overdue_amount_1_0, 0) AS overdue_amount_1_0,
    COALESCE(i.should_capital_1_0, 0) AS should_capital_1_0,
    COALESCE(i.overdue_amount_1_7, 0) AS overdue_amount_1_7,
    COALESCE(i.should_capital_1_7, 0) AS should_capital_1_7,
    COALESCE(i.overdue_amount_1_14, 0) AS overdue_amount_1_14,
    COALESCE(i.should_capital_1_14, 0) AS should_capital_1_14,
    COALESCE(i.overdue_amount_1_30, 0) AS overdue_amount_1_30,
    COALESCE(i.should_capital_1_30, 0) AS should_capital_1_30, 
    COALESCE(i.overdue_amount_2_0, 0) AS overdue_amount_2_0,
    COALESCE(i.should_capital_2_0, 0) AS should_capital_2_0,
    COALESCE(i.overdue_amount_2_7, 0) AS overdue_amount_2_7,
    COALESCE(i.should_capital_2_7, 0) AS should_capital_2_7, 
    COALESCE(i.overdue_amount_2_30, 0) AS overdue_amount_2_30,
    COALESCE(i.should_capital_2_30, 0) AS should_capital_2_30, 
    COALESCE(s.should_capital_d0, 0) AS should_capital_d0, 
    COALESCE(s.should_capital_d1, 0) AS should_capital_d1,
    COALESCE(s.should_capital_d7, 0) AS should_capital_d7,
    COALESCE(s.should_capital_d15, 0) AS should_capital_d15,
    COALESCE(s.should_capital_d30, 0) AS should_capital_d30, 
    COALESCE(s.should_capital_d0 - s.t0_capital_paid_d0, 0) AS t0_capital_due_d0,
    COALESCE(s.should_capital_d1 - s.t1_capital_paid_d1, 0) AS t1_capital_due_d1,
    COALESCE(s.should_capital_d7 - s.t7_capital_paid_d7, 0) AS t7_capital_due_d7,
    COALESCE(s.should_capital_d15 - s.t15_capital_paid_d15, 0) AS t15_capital_due_d15,
    COALESCE(s.should_capital_d30 - s.t30_capital_paid_d30, 0) AS t30_capital_due_d30,
    COALESCE(s.t0_capital_paid_d7, 0) AS t0_capital_paid_d7,
    COALESCE(s.t0_capital_paid_d15, 0) AS t0_capital_paid_d15,
    COALESCE(s.t0_capital_paid_d30, 0) AS t0_capital_paid_d30,
    COALESCE(s.t7_capital_paid_d7 - s.t0_capital_paid_d7, 0) AS t0_7_capital_paid_d7,
    COALESCE(s.t15_capital_paid_d15 - s.t0_capital_paid_d15, 0) AS t0_15_capital_paid_d15,
    COALESCE(s.t30_capital_paid_d30 - s.t0_capital_paid_d30, 0) AS t0_30_capital_paid_d30,

    COALESCE(s.should_capital_d7 - s.t0_capital_paid_d7, 0) AS t0_7_capital_paid_due_d7,
    COALESCE(s.should_capital_d15 - s.t0_capital_paid_d15, 0) AS t0_15_capital_paid_due_d15,
    COALESCE(s.should_capital_d30 - s.t0_capital_paid_d30, 0) AS t0_30_capital_paid_due_d30,
    COALESCE(loan_cycle_amount, 0) AS loan_cycle_amount,
    COALESCE(issue_haircut_amount, 0) AS issue_haircut_amount,
    COALESCE(issue_interest, 0) AS issue_interest,
    COALESCE(issue_revenue, 0) AS issue_revenue,
     total_amt*exchange_rate* 1.00000 / f1.exchange_rate_to_dollar  AS ov_total_amt_usd,
    fl_contract_amt*exchange_rate* 1.00000 / f1.exchange_rate_to_dollar AS fl_total_amt_usd,
    rl_contract_amt*exchange_rate* 1.00000 / f1.exchange_rate_to_dollar AS rl_total_amt_usd,
    month_days, 
    date_month_end_actual ,
    COALESCE(issue_contract_amount_usd_new, 0) AS issue_contract_amount_usd_new,
    COALESCE(issue_contract_amount_usd_old, 0) AS issue_contract_amount_usd_old,
        COALESCE(a.loan_type2, i.loan_type2, s.loan_type2) AS loan_type2


FROM application_metrics a
FULL JOIN issue_metrics i 
    ON a.grant_strategy = i.grant_strategy
    AND a.product_tag = i.product_tag
    AND a.is_reloan2 = i.is_reloan2
    AND a.loan_type2 = i.loan_type2
    AND a.new_grade_level = i.new_grade_level 
    AND a.app_week = i.issue_week
    AND a.app_month = i.issue_month
    AND a.user_level = i.user_level
    AND a.if_regular_backup = i.if_regular_backup
    AND a.if_backup_switch = i.if_backup_switch
    AND a.first_loan_grade_level = i.first_loan_grade_level



FULL JOIN should_metrics s
    ON COALESCE(a.grant_strategy, i.grant_strategy) = s.grant_strategy
    AND COALESCE(a.product_tag, i.product_tag) = s.product_tag
    AND COALESCE(a.is_reloan2, i.is_reloan2) = s.is_reloan2
    AND COALESCE(a.loan_type2, i.loan_type2) = s.loan_type2
    AND COALESCE(a.new_grade_level, i.new_grade_level) = s.new_grade_level 
    AND COALESCE(a.app_week, i.issue_week) = s.should_week
    AND COALESCE(a.app_month, i.issue_month) = s.should_month
    AND COALESCE(a.user_level, i.user_level) = s.user_level
    AND COALESCE(a.if_regular_backup, i.if_regular_backup) = s.if_regular_backup
    AND COALESCE(a.if_backup_switch, i.if_backup_switch) = s.if_backup_switch
    AND COALESCE(a.first_loan_grade_level, i.first_loan_grade_level) = s.first_loan_grade_level
full join confirm_metrics c
    ON COALESCE(a.grant_strategy, i.grant_strategy,s.grant_strategy) = c.grant_strategy
    AND COALESCE(a.product_tag, i.product_tag,s.product_tag) = c.product_tag
    AND COALESCE(a.is_reloan2, i.is_reloan2,s.is_reloan2) = c.is_reloan2
    AND COALESCE(a.loan_type2, i.loan_type2,s.loan_type2) = c.loan_type2
    AND COALESCE(a.new_grade_level, i.new_grade_level,s.new_grade_level) = c.new_grade_level
     AND COALESCE(date(a.app_week), date(i.issue_week),date(s.should_week)) = c.create_week

    AND COALESCE(a.app_month, i.issue_month,s.should_month) = c.create_month
    AND COALESCE(a.user_level, i.user_level,s.user_level) = c.user_level
    AND COALESCE(a.if_regular_backup, i.if_regular_backup,s.if_regular_backup) = c.if_regular_backup
    AND COALESCE(a.if_backup_switch, i.if_backup_switch,s.if_backup_switch) = c.if_backup_switch
    AND COALESCE(a.first_loan_grade_level, i.first_loan_grade_level,s.first_loan_grade_level) = c.first_loan_grade_level


LEFT JOIN ind.ba_kpi_targets_m b
    ON COALESCE(a.app_month, i.issue_month, s.should_month) = b.month 
left join data_date cc
    ON b.month = cc.data_month 
LEFT JOIN dim.dim_exchange_rate_cost f1 ON cc.date_mon = f1.month_id AND f1.account_currency = 'IDR'
;





 
DROP TABLE IF EXISTS ind.ba_targets_m;
 
CREATE TABLE ind.ba_targets_m  as 
select a.*,month_days as daily_cnt from ind.ba_kpi_targets_m a
LEFT JOIN dim.dim_data_info b on  date_format(date(a.month),'%Y%m%d')=b.data_date 
union all 
select month,
    ba_type,
    daily_avg_spend,
    cps,
    fl_confirm_1_2_rate,
    fl_issue_1_4_cnt,
    fl_1_4_cps_rate,
    fl_avg_amt,
    fl_issue_cnt,
    fl_pass_rate,
    fl_contract_amt,
    fl_loan_cycle,
    fl_fee_rate,
    fl_bad_rate * (-1) AS fl_bad_rate,

    fl_cust_cost * (-1) AS fl_cust_cost,

    rl_avg_amt,
    rl_issue_cnt,
    rl_pass_rate,
    rl_contract_amt,
    rl_loan_cycle,
    rl_fee_rate,
    rl_bad_rate * (-1) AS rl_bad_rate,
    total_amt,
    rl_amt_ratio,
    lend_biz_ratio,
    lend_biz_amt,
    total_fee_rate,
    total_bad_rate * (-1) AS total_bad_rate,
    total_cust_cost * (-1) AS total_cust_cost,

    exchange_rate_to_dollar,
    daily_cnt 
     from ind.ba_act_targets_process_m ;
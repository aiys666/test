-- 第一段代码

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
   ,a2.fst_loan_cnt
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
    
    (
      SELECT 
    issue_week as release_week,
    sum(if_issue) AS loan_cnt,
    sum(contract_amount_usd1) as contract_amt ,
    SUM(amount/exchange_rate_to_dollar) as release_amt,
 sum(contract_amount_usd1) *1.0 / sum(if_issue) as per_loan,
 SUM(CASE WHEN grant_strategy = 'NEW' THEN if_issue ELSE 0 END) AS fst_loan_cnt,
 SUM(CASE WHEN grant_strategy = 'NEW' THEN contract_amount_usd1 ELSE 0 END) AS fst_contract_amt,
 SUM(CASE WHEN grant_strategy = 'NEW' THEN  loan_cycle_amount ELSE 0 END)/ SUM(CASE WHEN grant_strategy = 'NEW' THEN  contract_amount ELSE 0 END)  AS fst_avg_period,
 SUM(CASE WHEN grant_strategy = 'NEW' THEN  contract_amount_usd1 ELSE 0 END)/ SUM(CASE WHEN grant_strategy = 'NEW' THEN  if_issue ELSE 0 END)  AS fst_per_loan, 
 SUM(CASE WHEN grant_strategy = 'OLD' THEN if_issue ELSE 0 END) AS rl_loan_cnt,
 SUM(CASE WHEN grant_strategy = 'OLD' THEN contract_amount_usd1 ELSE 0 END) AS rl_contract_amt,
 SUM(CASE WHEN grant_strategy = 'OLD' THEN  loan_cycle_amount ELSE 0 END)/ SUM(CASE WHEN grant_strategy = 'OLD' THEN  contract_amount ELSE 0 END)  AS rl_avg_period,
 SUM(CASE WHEN grant_strategy = 'OLD' THEN  contract_amount_usd1 ELSE 0 END)/ SUM(CASE WHEN grant_strategy = 'OLD' THEN  if_issue ELSE 0 END)  AS rl_per_loan, 
 SUM(CASE WHEN grant_strategy = 'OLD' THEN  contract_amount_usd1 ELSE 0 END)/ SUM(contract_amount_usd1)  AS rl_ratio
 
     
FROM ind.ba_asset_base_info
WHERE issue_date > '2024-09-30'  
  AND date(issue_date) < CURRENT_DATE
  AND if_issue = 1
GROUP BY 1 
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
    order by 1 asc


    -- 第二段代码：
    需要改一下data_date按照动态的周一提取数据
        select (amt/exchange_rate_to_dollar) as amt from
    (select sum(a.should_capital  -a.fact_capital) as amt from ods.s02_loan_repayment_his a
    where a.state in (0,2,4) 
    and data_date='20250929')a1
    left JOIN
    (select * from dim.dim_exchange_rate_cost where account_currency = 'IDR'
   and to_char(current_date,'yyyymm') = month_id )b1
    on 1=1
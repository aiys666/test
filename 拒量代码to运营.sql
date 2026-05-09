-我自己推送的表
select
data_date,user_tag,count(distinct mid) 
from ind.fdc_recall
group by 1,2
order by 1 desc


--BI同步的表
select data_date,count(distinct mid)  from dws.dws_fdc_recall
group by 1
order by 1 desc


--开发推送的表用户的查询状态
select
date(create_time)create_time,date(update_time)update_time,count(distinct case when status=1 then mid end) 
from ods.s22_fdc_user_data
group by 1,2
order by 1 desc


select
count(distinct case when status=1 then mid end) 
from ods.s22_fdc_user_data
where update_time>now() - interval '13' hour
--group by 1
order by 1 desc


---短信+push
select data_date,count(distinct mid),
count(distinct case when cast(model_score as decimal(20,17))<=0.215179 and is_not_found='0' then mid end)
--count(distinct case when cast(model_score as decimal(20,17))<=0.215179 and is_not_found='0' and days_since_last_marketing>=8 then mid end)
--count(distinct case when cast(model_score as decimal(20,17))<=0.16588 and is_not_found='0' then mid end)
from dws.dws_fdc_offline_model_score_record
where
user_tag in('NEW')
and model_version in('724') 
and is_loan=0
and days_since_data_date=3
and days_since_last_refuce>=8
group by data_date
order by data_date desc

---IVR+短信
select data_date,count(distinct mid),
count(distinct case when cast(model_score as decimal(20,17))<=0.215179 and is_not_found='0' then mid end)
--count(distinct case when cast(model_score as decimal(20,17))<=0.215179 and is_not_found='0' and days_since_last_marketing>=8 then mid end)
--count(distinct case when cast(model_score as decimal(20,17))<=0.16588 and is_not_found='0' then mid end)
from dws.dws_fdc_offline_model_score_record
where
user_tag in('NEW')
and model_version in('724') 
and is_loan=0
and days_since_data_date=5
and days_since_last_refuce>=8
group by data_date
order by data_date desc



---新客最新营销库表-by模型迭代 0.196122
--注册未进件
select data_date,count(distinct mid),
count(distinct case when cast(model_score as decimal(20,17))<=0.24536 and is_not_found='0' then mid end),
count(distinct case when cast(model_score as decimal(20,17))<=0.24536 and is_not_found='0' and days_since_last_marketing>=8 then mid end)
--count(distinct case when cast(model_score as decimal(20,17))<=0.16588 and is_not_found='0' then mid end)
from dws.dws_fdc_offline_model_score_record
where date(data_date)>=date'2025-05-21'
--(date(data_date)=date'2024-09-18' or date(data_date)=date'2024-09-18' or date(data_date)=date'2024-09-18' )
and user_tag in('NEW_not_apply')
--and model_version in('718')
and model_version in('724') 
and is_loan=0
and days_since_last_refuce>=8
group by data_date
order by data_date desc

---电销
select data_date,count(distinct mid),
count(distinct case when cast(model_score as decimal(20,17))<=0.603 and is_not_found='0' then mid end)
--count(distinct case when cast(model_score as decimal(20,17))<=0.664 and is_not_found='0' then mid end),
count(distinct case when cast(model_score as decimal(20,17))<=0.603 and is_not_found='0' and days_since_last_marketing>=8 then mid end)
--count(distinct case when cast(model_score as decimal(20,17))<=0.16588 and is_not_found='0' then mid end)
from dws.dws_fdc_offline_model_score_record
where user_tag in('NEW')
and model_version in('724_mix') 
and is_loan=0
and days_since_data_date=7
and days_since_last_refuce>=8
group by data_date
order by data_date desc



----结清

select data_date,user_tag,count(distinct mid),count(distinct case when cast(model_score as decimal(20,17))<=0.147269 and is_not_found='0' then mid end)
from dws.dws_fdc_offline_model_score_record
where (date(data_date)=date'2025-05-07' or date(data_date)=date'2025-05-07')
and user_tag in('OLD_SINGLE')
and days_since_last_refuce>=8
--and date(update_time)=date'2024-08-26')
group by 1,2
order by data_date desc


---bin值划分
when is_reloan2 = 'OLD_SINGLE' and pvalue_721oldrh >= 0.000 and pvalue_721oldrh <= 0.0280771 then 1 
when is_reloan2 = 'OLD_SINGLE' and pvalue_721oldrh > 0.0280771 and pvalue_721oldrh <= 0.048442 then 2 
when is_reloan2 = 'OLD_SINGLE' and pvalue_721oldrh > 0.048442 and pvalue_721oldrh <= 0.079801 then 3 
when is_reloan2 = 'OLD_SINGLE' and pvalue_721oldrh > 0.079801 and pvalue_721oldrh <= 0.147269 then 4 
when is_reloan2 = 'OLD_SINGLE' and pvalue_721oldrh > 0.147269 then 5
else 0 end as model_score_721_bin



----加贷
select
data_date,
count(distinct mid)user_num,
count(distinct case when cast(pvalue_new_718_1t7_fdc_offline as decimal(20,17))<=0.0907 and is_not_found='0' then mid end)user_num1,
count(distinct case when cast(pvalue_new_718_1t7_fdc_offline as decimal(20,17))<=0.0907 and is_not_found='0' and days_since_last_marketing>=8 then mid end)user_num2
from
    (
    select a.*,model_score as pvalue_new_718_1t7_fdc_offline
    from dws.dws_fdc_offline_model_score_record a
    where user_tag in('OLD_PLUS')
    and (date(data_date)>=date'2025-04-30' )
    and days_since_last_refuce>=8
    --and date(update_time)=date'2024-08-26')
    )a1
group by 1
order by 1 desc


insert into ind.fdc_recall
    select
    a.cust_id
    ,a.mid
    ,a.tenant_id
    ,'NEW' as user_tag
    , try_cast(b.new_grade_level as bigint) as last_new_grade_level
    , b.mb_phone
    , b.realname
    , 0 as model_score_718fdc_bin5
    , a.status
    , b.latest_apply_days
    , b.finish_time_days
    , b.his_rejected_times
    , b.max_overdue_days
    , b.days_since_last_refuce
    , b.push_token
    ,'0' as tag1
    ,cast((current_date - interval '1' day) as varchar) as data_date
    from
        (select a.*
                ,row_number() over(partition by a.mid order by a.create_time desc) as desc_mid_rn
                ,row_number() over(partition by a.mid order by a.create_time asc) as asc_mid_rn
                from ods.s05_creditx_order a
        )a
        left join
        (select distinct mid
        from ods.s05_creditx_processor_record 
        where current_processor in ('first_loan_strong_rule_set',
            'reloan_strong_rule_set',
            'plus_strong_rule_set',
            'plus_strong_rule_set_circ',
            'm_plus_strong_rule_set',
            'first_loan_strong_rule_set_ios',
            'reloan_strong_rule_set_ios',
            'plus_strong_rule_set_ios')
        and approve_result   ='REFUSED'
        )c
        on try_cast(a.mid as bigint)=try_cast(c.mid as bigint)
        join
        (SELECT 
        distinct mid
        ,days_since_last_refuce
        ,his_rejected_times
        ,rejected_times_near_7d
        ,max_overdue_days
        ,is_finish
        ,finish_time_days
        ,is_whilelist
        ,push_token
        ,mb_phone
        ,realname
        ,new_grade_level
        ,latest_apply_days
        FROM customer_profile.ind_customer_profile_new
        )b
        on try_cast(a.mid as bigint)=try_cast(b.mid as bigint)
        left join
        (select distinct customer_id
         from ods.s02_loan
         where state in (1,2,3,15)
         and create_time < release_time and release_time is not null
        )d
        on try_cast(a.mid as bigint)=try_cast(d.customer_id as bigint)
        left join
        (select distinct list_value,tenant_id from ods.s19_sr_name_list_data t2
        where t2.deleted = 0 AND date(t2.expired_time) > current_date
        AND (t2.type_code like '%creditNo%' or t2.type_code like '%phoneNum%')
        )g
        on a.credit_no=g.list_value and a.tenant_id = g.tenant_id
        left join
        (select * from ods.s05_yn_login_out_record)h
        on try_cast(a.mid as bigint)=try_cast(h.mid as bigint)
        left join ods.s01_mem_member_account m
        on try_cast(a.mid as bigint)=try_cast(m.mid as bigint)
        left join
        (select * from ods.s01_mem_base_info
        where customer_type in(0,1,5)
        )m1
        on try_cast(m.mb_cust_id as bigint)=try_cast(m1.cust_id as bigint)
        left join
        (select distinct mid from ind.fdc_recall
        where cast(data_date as date)<=(current_date - interval '2' day)
        and cast(data_date as date)>=(current_date - interval '15' day)
        --cast(data_date as date)>date'2024-07-31'
        )n
        on try_cast(a.mid as bigint)=try_cast(n.mid as bigint)
        left join
        (select *
         from ods.s02_loan
         where state in (4)
        )d1
        on try_cast(a.biz_id as bigint)=try_cast(d1.camera_id as bigint)
        where g.list_value is null
        and h.mid is null
        and m.mb_phone is not null
        and d.customer_id is null
        --and a.double_loan=0
        and a.desc_mid_rn=1
        --and a.status in(425)
        --and a.status in(421)
        --and a.status in(372) and d.state in(4)
        and (a.status in(421,425) or (a.status in(372) and d1.state in(4)))
        --and cast(days_since_last_refuce as int)<=90
        --and cast(days_since_last_refuce as int)<180
        --and b.latest_apply_days<90
        and b.latest_apply_days>15
        --and b.latest_apply_days<180
        --and b.latest_apply_days>=180
        and b.rejected_times_near_7d=0
        --and cast(his_rejected_times as int)<=3
        and cast(coalesce(b.his_rejected_times,0) as int)<=3
        and n.mid is null
        and c.mid is null
        and m1.cust_id is null
        and b.push_token is not null
        limit 150000;
insert into ind.fdc_recall
    select
    a.cust_id
    ,a.mid
    ,a.tenant_id
    ,'NEW' as user_tag
    , try_cast(b.new_grade_level as bigint) as last_new_grade_level
    , b.mb_phone
    , b.realname
    , 0 as model_score_718fdc_bin5
    , a.status
    , b.latest_apply_days
    , b.finish_time_days
    , b.his_rejected_times
    , b.max_overdue_days
    , b.days_since_last_refuce
    , b.push_token
    ,'0' as tag1
    ,cast((current_date - interval '1' day) as varchar) as data_date
    from
        (select a.*
                ,row_number() over(partition by a.mid order by a.create_time desc) as desc_mid_rn
                ,row_number() over(partition by a.mid order by a.create_time asc) as asc_mid_rn
                from ods.s05_creditx_order a
        )a
        left join
        (select distinct mid
        from ods.s05_creditx_processor_record 
        where current_processor in ('first_loan_strong_rule_set',
            'reloan_strong_rule_set',
            'plus_strong_rule_set',
            'plus_strong_rule_set_circ',
            'm_plus_strong_rule_set',
            'first_loan_strong_rule_set_ios',
            'reloan_strong_rule_set_ios',
            'plus_strong_rule_set_ios')
        and approve_result   ='REFUSED'
        )c
        on try_cast(a.mid as bigint)=try_cast(c.mid as bigint)
        join
        (SELECT 
        distinct mid
        ,days_since_last_refuce
        ,his_rejected_times
        ,rejected_times_near_7d
        ,max_overdue_days
        ,is_finish
        ,finish_time_days
        ,is_whilelist
        ,push_token
        ,mb_phone
        ,realname
        ,new_grade_level
        ,latest_apply_days
        FROM customer_profile.ind_customer_profile_new
        )b
        on try_cast(a.mid as bigint)=try_cast(b.mid as bigint)
        left join
        (select distinct customer_id
         from ods.s02_loan
         where state in (1,2,3,15)
         and create_time < release_time and release_time is not null
        )d
        on try_cast(a.mid as bigint)=try_cast(d.customer_id as bigint)
        left join
        (select distinct list_value,tenant_id from ods.s19_sr_name_list_data t2
        where t2.deleted = 0 AND date(t2.expired_time) > current_date
        AND (t2.type_code like '%creditNo%' or t2.type_code like '%phoneNum%')
        )g
        on a.credit_no=g.list_value and a.tenant_id = g.tenant_id
        left join
        (select * from ods.s05_yn_login_out_record)h
        on try_cast(a.mid as bigint)=try_cast(h.mid as bigint)
        left join ods.s01_mem_member_account m
        on try_cast(a.mid as bigint)=try_cast(m.mid as bigint)
        left join
        (select * from ods.s01_mem_base_info
        where customer_type in(0,1,5)
        )m1
        on try_cast(m.mb_cust_id as bigint)=try_cast(m1.cust_id as bigint)
        left join
        (select distinct mid from ind.fdc_recall
        where cast(data_date as date)<=(current_date - interval '2' day)
        and cast(data_date as date)>=(current_date - interval '15' day)
        --cast(data_date as date)>date'2024-07-31'
        )n
        on try_cast(a.mid as bigint)=try_cast(n.mid as bigint)
        left join
        (select *
         from ods.s02_loan
         where state in (4)
        )d1
        on try_cast(a.biz_id as bigint)=try_cast(d1.camera_id as bigint)
        where g.list_value is null
        and h.mid is null
        and m.mb_phone is not null
        and d.customer_id is null
        --and a.double_loan=0
        and a.desc_mid_rn=1
        --and a.status in(425)
        --and a.status in(421)
        --and a.status in(372) and d.state in(4)
        and (a.status in(421,425) or (a.status in(372) and d1.state in(4)))
        --and cast(days_since_last_refuce as int)<=90
        --and cast(days_since_last_refuce as int)<180
        --and b.latest_apply_days<90
        and b.latest_apply_days>15
        --and b.latest_apply_days<180
        --and b.latest_apply_days>=180
        and b.rejected_times_near_7d=0
        --and cast(his_rejected_times as int)<=3
        and cast(coalesce(b.his_rejected_times,0) as int)<=3
        and n.mid is null
        and c.mid is null
        and m1.cust_id is null
        and b.push_token is null
        limit 0;
insert into ind.fdc_recall
select
    a.cust_id
    ,a.mid
    ,a.tenant_id
    ,'OLD_SINGLE' as user_tag
    , try_cast(b.new_grade_level as bigint) as last_new_grade_level
    , b.mb_phone
    , b.realname
    , 0 as model_score_718fdc_bin5
    , a.status
    , b.latest_apply_days
    , b.finish_time_days
    , b.his_rejected_times
    , b.max_overdue_days
    , b.days_since_last_refuce
    , b.push_token
    , '0' as tag1
    ,cast((current_date - interval '1' day) as varchar) as data_date
    from
        (select a.*
                ,row_number() over(partition by a.mid order by a.create_time desc) as desc_mid_rn
                ,row_number() over(partition by a.mid order by a.create_time asc) as asc_mid_rn
                from ods.s05_creditx_order a
        )a
        left join
        (select distinct mid
        from ods.s05_creditx_processor_record 
        where current_processor in ('first_loan_strong_rule_set','reloan_strong_rule_set','plus_strong_rule_set')
        and approve_result ='REFUSED'
        )c
        on try_cast(a.mid as bigint)=try_cast(c.mid as bigint)
        join
        (SELECT 
        distinct mid
        ,days_since_last_refuce
        ,his_rejected_times
        ,rejected_times_near_7d
        ,max_overdue_days
        ,is_finish
        ,finish_time_days
        ,is_whilelist
        ,push_token
        ,mb_phone
        ,realname
        ,new_grade_level
        ,latest_apply_days
        FROM customer_profile.ind_customer_profile_new
        )b
        on try_cast(a.mid as bigint)=try_cast(b.mid as bigint)
        left join
        /*(select * from
            (select mid,order_no,order_status_code,is_reloan_code,user_confirm_status,create_time as create_time_final
            ,row_number() over(partition by mid order by create_time desc) rf 
            from dwd.dwd_order_info
            ) rc 
            where rc.rf=1
        )d
        on try_cast(a.biz_id as bigint)=try_cast(d.order_no as bigint)*/
        (select distinct customer_id
        from ods.s02_loan
        where state in (1,2,3,15)
        and create_time < release_time and release_time is not null)d
        on try_cast(a.mid as bigint)=try_cast(d.customer_id as bigint)
        left join
        (select distinct list_value,tenant_id from ods.s19_sr_name_list_data t2
        where t2.deleted = 0 AND date(t2.expired_time) > current_date
        AND (t2.type_code like '%creditNo%' or t2.type_code like '%phoneNum%')
        )g
        on a.credit_no=g.list_value and a.tenant_id = g.tenant_id
        left join
        (select * from ods.s05_yn_login_out_record)h
        on try_cast(a.mid as bigint)=try_cast(h.mid as bigint)
        left join ods.s01_mem_member_account m
        on try_cast(a.mid as bigint)=try_cast(m.mid as bigint)
        left join
        (select distinct mid from ind.fdc_recall
        where cast(data_date as date)<=(current_date - interval '2' day)
        and cast(data_date as date)>=(current_date - interval '12' day)
        and cast(data_date as date)>=date'2024-09-10'
        and lower(user_tag) like '%old%')n
        on try_cast(a.mid as bigint)=try_cast(n.mid as bigint) 
        where 
        g.list_value is null
        and h.mid is null
        and m.mb_phone is not null
        --and a.double_loan=1
        and d.customer_id is not null
        and desc_mid_rn=1
        --and a.status in(421,425)
        --and cast(days_since_last_refuce as int)>=15
        and rejected_times_near_7d=0
        and cast(coalesce(b.his_rejected_times,0) as int)<=5
        and n.mid is null
        --and c.mid is null
        and cast(coalesce(b.max_overdue_days,0) as int)<=7
        and cast(b.finish_time_days as int)>15 and b.is_finish='1'
        --and (is_finish='1' or is_whilelist='1')
        --and b.push_token is not null
        limit 0;

insert into ind.fdc_recall
select
    a.cust_id
    ,a.mid
    ,a.tenant_id
    ,'OLD_PLUS' as user_tag
    , try_cast(b.new_grade_level as bigint) as last_new_grade_level
    , b.mb_phone
    , b.realname
    , 0 as model_score_718fdc_bin5
    , a.status
    , b.latest_apply_days
    , b.finish_time_days
    , b.his_rejected_times
    , b.max_overdue_days
    , b.days_since_last_refuce
    , b.push_token
    , '0' as tag1
    ,cast((current_date - interval '1' day) as varchar) as data_date
    from
        (select a.*
                ,row_number() over(partition by a.mid order by a.create_time desc) as desc_mid_rn
                ,row_number() over(partition by a.mid order by a.create_time asc) as asc_mid_rn
                from ods.s05_creditx_order a
        )a
        left join
        (select distinct mid
        from ods.s05_creditx_processor_record 
        where current_processor in ('first_loan_strong_rule_set','reloan_strong_rule_set','plus_strong_rule_set')
        and approve_result ='REFUSED'
        )c
        on try_cast(a.mid as bigint)=try_cast(c.mid as bigint)
        join
        (SELECT 
        distinct mid
        ,days_since_last_refuce
        ,his_rejected_times
        ,rejected_times_near_7d
        ,max_overdue_days
        ,is_finish
        ,finish_time_days
        ,is_whilelist
        ,push_token
        ,mb_phone
        ,realname
        ,new_grade_level
        ,latest_apply_days
        ,is_m_whilelist
        ,is_loop
        FROM customer_profile.ind_customer_profile_new
        )b
        on try_cast(a.mid as bigint)=try_cast(b.mid as bigint)
        left join
        /*(select * from
            (select mid,order_no,order_status_code,is_reloan_code,user_confirm_status,create_time as create_time_final
            ,row_number() over(partition by mid order by create_time desc) rf 
            from dwd.dwd_order_info
            ) rc 
            where rc.rf=1
        )d
        on try_cast(a.biz_id as bigint)=try_cast(d.order_no as bigint)*/
        (select distinct customer_id
        from ods.s02_loan
        where state in (1,2,3,15)
        and create_time < release_time and release_time is not null
        )d
        on try_cast(a.mid as bigint)=try_cast(d.customer_id as bigint)
        left join
        (select distinct list_value,tenant_id from ods.s19_sr_name_list_data t2
        where t2.deleted = 0 AND date(t2.expired_time) > current_date
        AND (t2.type_code like '%creditNo%' or t2.type_code like '%phoneNum%')
        )g
        on a.credit_no=g.list_value and a.tenant_id = g.tenant_id
        left join
        (select * from ods.s05_yn_login_out_record)h
        on try_cast(a.mid as bigint)=try_cast(h.mid as bigint)
        left join ods.s01_mem_member_account m
        on try_cast(a.mid as bigint)=try_cast(m.mid as bigint)
        left join
        (select distinct mid from ind.fdc_recall
        where cast(data_date as date)<=(current_date - interval '2' day)
        and cast(data_date as date)>=(current_date - interval '12' day)
        and lower(user_tag) like '%old%')n
        on try_cast(a.mid as bigint)=try_cast(n.mid as bigint) 
        where 
        g.list_value is null
        and h.mid is null
        and m.mb_phone is not null
        --and a.double_loan=1
        and d.customer_id is not null
        and desc_mid_rn=1
        --and a.status in(421,425)
        --and cast(days_since_last_refuce as int)>=15
        and rejected_times_near_7d=0
        and cast(coalesce(b.his_rejected_times,0) as int)<=5
        and n.mid is null
        --and c.mid is null
        and cast(coalesce(b.max_overdue_days,0) as int)<=7
        and (cast(b.is_m_whilelist as bigint)=1 or cast(b.is_whilelist as bigint)=1 or cast(b.is_loop as bigint)=1)
        --and (is_finish='1' or is_whilelist='1')
        --and b.push_token is not null
        limit 0;

insert into ind.fdc_recall
select
    try_cast(b.cust_id as varchar) as cust_id
    ,try_cast(b.mid as varchar) as mid
    ,b.tenant_id
    ,'NEW' as user_tag
    , 0 as last_new_grade_level
    , b.mb_phone
    , '0' as realname
    , 0 as model_score_718fdc_bin5
    , 0 as status
    , 0 as latest_apply_days
    , 0 as finish_time_days
    , 0 as his_rejected_times
    , 0 as max_overdue_days
    , '0' as days_since_last_refuce
    , '0' as push_token
    , '0' as tag1
    , cast((current_date - interval '1' day) as varchar) as data_date
    from
        ind.wb_1204 n1
        join
        (
        select
        mid,
        mb_cust_id as cust_id,
        1721000000070082 as tenant_id,
        mb_phone
        from ods.s01_mem_member_account
        )b
       on n1.hp_number_t=b.mb_phone
        left join
        (select a.* from
            (select a.*
                ,row_number() over(partition by a.mid order by a.create_time desc) as desc_mid_rn
                ,row_number() over(partition by a.mid order by a.create_time asc) as asc_mid_rn
                from ods.s05_creditx_order a
            )a
            where asc_mid_rn=1
        )a
        on try_cast(b.mid as bigint)=try_cast(a.mid as bigint)
        left join
        (select distinct mid
        from ods.s05_creditx_processor_record 
        where current_processor in ('first_loan_strong_rule_set','reloan_strong_rule_set','plus_strong_rule_set')
        and approve_result   ='REFUSED'
        )c
        on try_cast(a.mid as bigint)=try_cast(c.mid as bigint)  
        left join
        (select * 
        from ods.s02_loan
        )d
        on try_cast(a.biz_id as bigint)=try_cast(d.camera_id as bigint)
        left join
        (select distinct list_value,tenant_id from ods.s19_sr_name_list_data t2
        where t2.deleted = 0 AND date(t2.expired_time) > current_date
        AND (t2.type_code like '%creditNo%' or t2.type_code like '%phoneNum%')
        )g
        on a.credit_no=g.list_value and a.tenant_id = g.tenant_id
        left join
        (select * from ods.s05_yn_login_out_record)h
        on try_cast(a.mid as bigint)=try_cast(h.mid as bigint)
        left join ods.s01_mem_member_account m
        on try_cast(a.mid as bigint)=try_cast(m.mid as bigint)
        left join
        (select * from ods.s01_mem_base_info
        where customer_type in(0,1,5)
        )m1
        on try_cast(m.mb_cust_id as bigint)=try_cast(m1.cust_id as bigint)
        left join
        (select distinct mid from ind.fdc_recall
        where cast(data_date as date)<=(current_date - interval '2' day)
        and cast(data_date as date)>=(current_date - interval '17' day)
        --cast(data_date as date)>date'2024-07-31'
        )n
        on try_cast(a.mid as bigint)=try_cast(n.mid as bigint) 
        limit 0;
insert into ind.fdc_recall
    select
    try_cast(a.cust_id as varchar)cust_id
    ,try_cast(a.mid as varchar)mid
    ,a.tenant_id
    ,'NEW_not_apply' as user_tag
    , try_cast(b.new_grade_level as bigint) as last_new_grade_level
    , a.phone_num as mb_phone
    , a.real_name
    , 0 as model_score_718fdc_bin5
    , m.status
    , b.latest_apply_days
    , b.finish_time_days
    , b.his_rejected_times
    , b.max_overdue_days
    , b.days_since_last_refuce
    , b.push_token
    ,'0' as tag1
    ,cast((current_date - interval '1' day) as varchar) as data_date
    from
        (select * from dwd.dwd_mem_info
        where cust_id is not null and cust_id<>1
        )a
        left join
        (select * from
            (select a.*
                    ,row_number() over(partition by a.mid order by a.create_time desc) as desc_mid_rn
                    ,row_number() over(partition by a.mid order by a.create_time asc) as asc_mid_rn
                    from ods.s05_creditx_order a
            )a
        where a.desc_mid_rn=1
        )m
        on try_cast(a.mid as bigint)=try_cast(m.mid as bigint)
        left join
        (select distinct mid
        from ods.s05_creditx_processor_record 
        where current_processor in ('first_loan_strong_rule_set',
            'reloan_strong_rule_set',
            'plus_strong_rule_set',
            'plus_strong_rule_set_circ',
            'm_plus_strong_rule_set',
            'first_loan_strong_rule_set_ios',
            'reloan_strong_rule_set_ios',
            'plus_strong_rule_set_ios')
        and approve_result   ='REFUSED'
        )c
        on try_cast(a.mid as bigint)=try_cast(c.mid as bigint)
        join
        (SELECT 
        distinct mid
        ,days_since_last_refuce
        ,his_rejected_times
        ,rejected_times_near_7d
        ,max_overdue_days
        ,is_finish
        ,finish_time_days
        ,is_whilelist
        ,push_token
        ,mb_phone
        ,realname
        ,new_grade_level
        ,latest_apply_days
        FROM customer_profile.ind_customer_profile_new
        )b
        on try_cast(a.mid as bigint)=try_cast(b.mid as bigint)
        left join
        (select distinct customer_id
         from ods.s02_loan
         where state in (1,2,3,15)
         and create_time < release_time and release_time is not null
        )d
        on try_cast(a.mid as bigint)=try_cast(d.customer_id as bigint)
        left join
        (select * from ods.s19_sr_name_list_data t2
        where t2.deleted = 0 AND date(t2.expired_time) > current_date
        AND (t2.type_code like '%creditNo%')
        )g
        on a.identity_num=g.list_value and a.tenant_id=g.tenant_id
        left join
        (select * from ods.s19_sr_name_list_data t2
        where t2.deleted = 0 AND date(t2.expired_time) > current_date
        AND (t2.type_code like '%phoneNum%')
        )g1
        on a.phone_num=g1.list_value and a.tenant_id=g1.tenant_id
        left join
        (select * from ods.s05_yn_login_out_record)h
        on try_cast(a.mid as bigint)=try_cast(h.mid as bigint)
        left join
        (select * from ods.s01_mem_base_info
        where customer_type in(0,1,5)
        )m1
        on try_cast(a.cust_id as bigint)=try_cast(m1.cust_id as bigint)
        left join
        (select distinct mid from ind.fdc_recall
        where cast(data_date as date)<=(current_date - interval '2' day)
        and cast(data_date as date)>=(current_date - interval '15' day)
        --cast(data_date as date)>date'2024-07-31'
        )n
        on try_cast(a.mid as bigint)=try_cast(n.mid as bigint)
        left join
        (select *
         from ods.s02_loan
         where state in (4)
        )d1
        on try_cast(m.biz_id as bigint)=try_cast(d1.camera_id as bigint)
        where g.list_value is null
        and g1.list_value is null
        and h.mid is null
        and a.phone_num is not null
        and d.customer_id is null
        --and a.double_loan=0
        --and a.status in(425)
        --and a.status in(421)
        --and a.status in(372) and d.state in(4)
        --and (a.status in(421,425) or (a.status in(372) and d1.state in(4)))
        --and cast(days_since_last_refuce as int)<=90
        --and cast(days_since_laast_refuce as int)<180
        --and b.latest_apply_days<90
        --and b.latest_apply_days>15
        --and b.latest_apply_days<180
        --and b.latest_apply_days>=180
        --and b.rejected_times_near_7d=0
        --and cast(his_rejected_times as int)<=3
        and m.mid is null
        --and cast(coalesce(b.his_rejected_times,0) as int)<=3
        and n.mid is null
        and c.mid is null
        and m1.cust_id is null
        --and b.push_token is not null
        limit 0;


----看板代码
select
to_char(date_trunc('month',date(create_time)),'yyyy-mm-dd') as create_month,
name,
case when branch_num=1 and lower(name) like '%cont%' or lower(name) like '%copy%' then 'control'
when branch_num=1 and (lower(name) not like '%cont%' or lower(name) not like '%copy%') then 'test'
when branch_num=2 and branch_rn=1 then 'control'
when branch_num=2 and branch_rn=2 then 'test'
else 'test'
end as group_tag,
case when activity_id in(20010928,20010929) then 'old'
when lower(name) like '%finish%' then 'old'
when lower(name) like '%old%' then 'old'
when lower(name) like '%fst%' then 'new'
when lower(name) like '%new%' then 'new'
else 'other'
end as user_tag,
create_time,
activity_id,
count(distinct unique_id)user_num,
count(distinct case when ifuse_0=1 then unique_id end)apply_cnt_0,
count(distinct case when ifuse_3=1 then unique_id end)apply_cnt_3,
count(distinct case when ifuse_7=1 then unique_id end)apply_cnt_7,
count(distinct case when ifuse_15=1 then unique_id end)apply_cnt_15,
count(distinct case when ifoan_0=1 then unique_id end)oan_cnt_0,
count(distinct case when ifoan_3=1 then unique_id end)oan_cnt_3,
count(distinct case when ifoan_7=1 then unique_id end)oan_cnt_7,
count(distinct case when ifoan_7=1 then unique_id end)oan_cnt_15,
sum(case when ifoan_0=1 then contract_amount_0 end)contract_amount_0,
sum(case when ifoan_3=1 then contract_amount_3 end)contract_amount_3,
sum(case when ifoan_7=1 then contract_amount_7 end)contract_amount_7,
sum(case when ifoan_7=1 then should_cnt_1_0 end)should_cnt_1_0,
sum(case when ifoan_7=1 then overdue_cnt_1_0 end)overdue_cnt_1_0,
sum(case when ifoan_7=1 then should_capital_1_0 end)should_capital_1_0,
sum(case when ifoan_7=1 then overdue_amount_1_0 end)overdue_amount_1_0,
sum(case when ifoan_7=1 then should_cnt_1_7 end)should_cnt_1_7,
sum(case when ifoan_7=1 then overdue_cnt_1_7 end)overdue_cnt_1_7,
sum(case when ifoan_7=1 then should_capital_1_7 end)should_capital_1_7,
sum(case when ifoan_7=1 then overdue_amount_1_7 end)overdue_amount_1_7,
sum(case when ifoan_7=1 then should_cnt_1_30 end)should_cnt_1_30,
sum(case when ifoan_7=1 then overdue_cnt_1_30 end)overdue_cnt_1_30,
sum(case when ifoan_7=1 then should_capital_1_30 end)should_capital_1_30,
sum(case when ifoan_7=1 then overdue_amount_1_30 end)overdue_amount_1_30,
sum(case when ifoan_7=1 then should_cnt_2_0 end)should_cnt_2_0,
sum(case when ifoan_7=1 then overdue_cnt_2_0 end)overdue_cnt_2_0,
sum(case when ifoan_7=1 then should_capital_2_0 end)should_capital_2_0,
sum(case when ifoan_7=1 then overdue_amount_2_0 end)overdue_amount_2_0,
sum(case when ifoan_7=1 then should_cnt_2_7 end)should_cnt_2_7,
sum(case when ifoan_7=1 then overdue_cnt_2_7 end)overdue_cnt_2_7,
sum(case when ifoan_7=1 then should_capital_2_7 end)should_capital_2_7,
sum(case when ifoan_7=1 then overdue_amount_2_7 end)overdue_amount_2_7,
sum(case when ifoan_7=1 then should_cnt_2_30 end)should_cnt_2_30,
sum(case when ifoan_7=1 then overdue_cnt_2_30 end)overdue_cnt_2_30,
sum(case when ifoan_7=1 then should_capital_2_30 end)should_capital_2_30,
sum(case when ifoan_7=1 then overdue_amount_2_30 end)overdue_amount_2_30,
avg(model_score_718fdc_bin5)model_score_718fdc_bin5
--avg(model_score_721_bin)
from
    (select a.*,row_number() over (partition by biz_id,ifuse_7 order by create_time desc) as rn
    from
        (select *, dense_RANK() OVER (PARTITION BY activity_id ORDER BY branch_id DESC) as branch_rn
                from ind.cyl_user_recall_data
        )a
    )a1
    --where rn=1
    group by 1,2,3,4,5,6
    order by 4,5 asc


drop table if exists ind.cyl_user_recall_data;
create table ind.cyl_user_recall_data as
SELECT distinct DATE(a.create_time)create_time,a.unique_id,a.activity_id,b.biz_id,c.release_time,a.name,a.branch_id,m.branch_num
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 0 then 1 else 0 end as ifuse_0
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 3 then 1 else 0 end as ifuse_3
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 7 then 1 else 0 end as ifuse_7
		,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 15 then 1 else 0 end as ifuse_15
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 0  and state in(1,2,15) and c.release_time is not null then 1 else 0 end as ifoan_0
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 3  and state in(1,2,15) and c.release_time is not null then 1 else 0 end as ifoan_3
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 7  and state in(1,2,15) and c.release_time is not null then 1 else 0 end as ifoan_7
		,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 15  and state in(1,2,15) and c.release_time is not null then 1 else 0 end as ifoan_15
        /*,case when date_diff('day',date(a.create_time),date(b.apply_time)) then greatest(coalesce(p.grantcredit_120d_amount,0),coalesce(p.grantcredit_90d_amount,0),coalesce(p.grantcredit_60d_amount,0),coalesce(p.grantcredit_30d_amount,0))
        else 0 end as as max_credit_amt*/
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 0 then c.contract_amount else 0 end as contract_amount_0
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 3 then c.contract_amount else 0 end as contract_amount_3
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 7 then c.contract_amount else 0 end as contract_amount_7
		,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 15 then c.contract_amount else 0 end as contract_amount_15
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 7  and state in(1,2,15) and c.release_time is not null then should_cnt_1_0 else 0 end as should_cnt_1_0
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 7  and state in(1,2,15) and c.release_time is not null then overdue_cnt_1_0 else 0 end as overdue_cnt_1_0
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 7  and state in(1,2,15) and c.release_time is not null then should_capital_1_0 else 0 end as should_capital_1_0
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 7  and state in(1,2,15) and c.release_time is not null then overdue_amount_1_0 else 0 end as overdue_amount_1_0
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 7  and state in(1,2,15) and c.release_time is not null then should_cnt_1_7 else 0 end as should_cnt_1_7
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 7  and state in(1,2,15) and c.release_time is not null then overdue_cnt_1_7 else 0 end as overdue_cnt_1_7
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 7  and state in(1,2,15) and c.release_time is not null then should_capital_1_7 else 0 end as should_capital_1_7
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 7  and state in(1,2,15) and c.release_time is not null then overdue_amount_1_7 else 0 end as overdue_amount_1_7
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 7  and state in(1,2,15) and c.release_time is not null then should_cnt_1_30 else 0 end as should_cnt_1_30
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 7  and state in(1,2,15) and c.release_time is not null then overdue_cnt_1_30 else 0 end as overdue_cnt_1_30
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 7  and state in(1,2,15) and c.release_time is not null then should_capital_1_30 else 0 end as should_capital_1_30
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 7  and state in(1,2,15) and c.release_time is not null then overdue_amount_1_30 else 0 end as overdue_amount_1_30
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 7  and state in(1,2,15) and c.release_time is not null then should_cnt_2_0 else 0 end as should_cnt_2_0
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 7  and state in(1,2,15) and c.release_time is not null then overdue_cnt_2_0 else 0 end as overdue_cnt_2_0
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 7  and state in(1,2,15) and c.release_time is not null then should_capital_2_0 else 0 end as should_capital_2_0
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 7  and state in(1,2,15) and c.release_time is not null then overdue_amount_2_0 else 0 end as overdue_amount_2_0
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 7  and state in(1,2,15) and c.release_time is not null then should_cnt_2_7 else 0 end as should_cnt_2_7
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 7  and state in(1,2,15) and c.release_time is not null then overdue_cnt_2_7 else 0 end as overdue_cnt_2_7
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 7  and state in(1,2,15) and c.release_time is not null then should_capital_2_7 else 0 end as should_capital_2_7
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 7  and state in(1,2,15) and c.release_time is not null then overdue_amount_2_7 else 0 end as overdue_amount_2_7
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 7  and state in(1,2,15) and c.release_time is not null then should_cnt_2_30 else 0 end as should_cnt_2_30
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 7  and state in(1,2,15) and c.release_time is not null then overdue_cnt_2_30 else 0 end as overdue_cnt_2_30
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 7  and state in(1,2,15) and c.release_time is not null then should_capital_2_30 else 0 end as should_capital_2_30
        ,case when date_diff('day',date(a.create_time),date(b.create_time)) between 0 and 7  and state in(1,2,15) and c.release_time is not null then overdue_amount_2_30 else 0 end as overdue_amount_2_30
        ,model_score_718fdc_bin5
        --,model_score_721_bin
        FROM
            (select distinct a.activity_id,a.create_time,a.unique_id,trim(d.name)name,a.branch_id from
                (select distinct activity_id,create_time,unique_id,branch_id from ods.s10_digital_market_activity_cust) a 
                join 
                (select * from ods.s10_digital_market_activity
                --where name like '%fdcscore%'
                where trim(name) like '%fdc%'
                )d 
                on a.activity_id = d.id
            )a
            left join ods.s05_creditx_order b ON cast(b.mid as bigint) = cast(a.unique_id as bigint) and a.create_time < b.create_time
            left join ods.s02_loan c ON cast(c.camera_id as bigint) = cast(b.biz_id  as bigint)
            left join ind.xly_application_funnel p on cast(p.app_id as decimal)=c.camera_id
            left join 
            (select biz_id,case
            when pvalue_new_718_1t7_fdc_0122_p1<=0.13107 then 1
            when pvalue_new_718_1t7_fdc_0122_p1<=0.18261 then 2
            when pvalue_new_718_1t7_fdc_0122_p1<=0.24536 then 3
            when pvalue_new_718_1t7_fdc_0122_p1<=0.28533 then 4
            when pvalue_new_718_1t7_fdc_0122_p1<=1 then 5
            else -1 end as model_score_718fdc_bin5
            from ind.zx_fdc_sd_score_718
            )d on cast(b.biz_id as bigint)=cast(d.biz_id as bigint)
			left join
			(select activity_id,count(distinct branch_id)branch_num from
                (select distinct activity_id,date(create_time)create_time,unique_id,branch_id from ods.s10_digital_market_activity_cust) a 
                join 
                (select * from ods.s10_digital_market_activity
                --where name like '%fdcscore%'
                where trim(name) like '%fdc%'
                )d 
                on a.activity_id = d.id
				group by 1
            )m on a.activity_id=m.activity_id
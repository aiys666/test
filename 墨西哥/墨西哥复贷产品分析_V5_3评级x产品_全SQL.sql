-- 墨西哥复贷产品分析 v4: V5_3 主资产等级 × 产品 表现总表 (与 .py 同一文本)
-- 口径: 老客复贷(old)+放款(if_issue=1)+有产品名; y.v3_flag='V5_3' 且主等级非空; release 2026-06-09~2026-09-01; 按 biz_id join mx.yj_test_table_250225
-- 税: 仅后收利息计税(E 含税÷1.16), 前砍费/本金不计税; 成熟窗口 vintage T0/T3/T7/T14/T30; t14 无 flag 用金额>1 代理

-- ==== Q1 全期明细(产品×评级) ====
WITH raw AS (
  SELECT f.product_name
        ,CAST(y.android_oldcust_maincreditlevel_charge_v5_3 AS INTEGER) AS grade
        ,if(substr(f.product_name, 1, 1) = 'E', 1, 0) AS is_e
        ,f.biz_id, f.mid
        ,f.contract_amount, f.haircut_amount, f.should_interest
        ,f.release_time
        ,f.is_t0_window ,f.t0_should_amt ,f.t0_overdue_amount
        ,f.is_t3_window ,f.t3_should_amt ,f.t3_overdue_amount
        ,f.is_t7_window ,f.t7_should_amt ,f.t7_overdue_amount
        ,f.is_t14_window,f.t14_should_amt,f.t14_overdue_amount
        ,f.is_t30_window,f.t30_should_amt,f.t30_overdue_amount
        ,f.is_t0_overdue,f.is_t3_overdue,f.is_t7_overdue,f.is_t30_overdue
  FROM mx.wxs_application_funnel f
  JOIN mx.yj_test_table_250225 y ON f.biz_id = y.biz_id
  WHERE f.is_reloan = 'old' AND f.if_issue = 1 AND f.product_name IS NOT NULL AND f.product_name <> '' AND date(f.release_time) >= date '2026-06-09' AND date(f.release_time) < date '2026-09-01' AND y.v3_flag = 'V5_3' AND y.android_oldcust_maincreditlevel_charge_v5_3 IS NOT NULL
)
,g AS (
  SELECT CAST('全期' AS VARCHAR) AS grp
      ,product_name
      ,grade
      ,count(distinct biz_id) AS loans
        ,count(distinct mid)       AS custs
        ,round(sum(contract_amount), 2)  AS ca
        ,round(sum(haircut_amount), 2)   AS ha
        ,round(sum(should_interest), 2)  AS si
        ,round(sum(if(is_e = 1, should_interest / 1.16, should_interest)), 2) AS si_net
        ,sum(if(is_t0_window = 1, 1, 0)) as t0_mature_cnt
      ,sum(if(is_t0_window = 1, t0_should_amt, 0))  as t0_should_amt
      ,sum(if(is_t0_window = 1, t0_overdue_amount, 0)) as t0_overdue_amount
      ,sum(if(is_t0_window = 1 and is_t0_overdue = 1, 1, 0)) as t0_ovd_cnt
      ,sum(if(is_t3_window = 1, 1, 0)) as t3_mature_cnt
      ,sum(if(is_t3_window = 1, t3_should_amt, 0))  as t3_should_amt
      ,sum(if(is_t3_window = 1, t3_overdue_amount, 0)) as t3_overdue_amount
      ,sum(if(is_t3_window = 1 and is_t3_overdue = 1, 1, 0)) as t3_ovd_cnt
      ,sum(if(is_t7_window = 1, 1, 0)) as t7_mature_cnt
      ,sum(if(is_t7_window = 1, t7_should_amt, 0))  as t7_should_amt
      ,sum(if(is_t7_window = 1, t7_overdue_amount, 0)) as t7_overdue_amount
      ,sum(if(is_t7_window = 1 and is_t7_overdue = 1, 1, 0)) as t7_ovd_cnt
      ,sum(if(is_t14_window = 1, 1, 0)) as t14_mature_cnt
      ,sum(if(is_t14_window = 1, t14_should_amt, 0))  as t14_should_amt
      ,sum(if(is_t14_window = 1, t14_overdue_amount, 0)) as t14_overdue_amount
      ,sum(if(is_t14_window = 1 and t14_overdue_amount > 1, 1, 0)) as t14_ovd_cnt
      ,sum(if(is_t30_window = 1, 1, 0)) as t30_mature_cnt
      ,sum(if(is_t30_window = 1, t30_should_amt, 0))  as t30_should_amt
      ,sum(if(is_t30_window = 1, t30_overdue_amount, 0)) as t30_overdue_amount
      ,sum(if(is_t30_window = 1 and is_t30_overdue = 1, 1, 0)) as t30_ovd_cnt
      ,sum(if(is_t7_window = 1, contract_amount, 0))    as t7_mature_ca
      ,sum(if(is_t7_window = 1, haircut_amount, 0))     as t7_mature_ha
      ,sum(if(is_t7_window = 1 and is_e = 1, should_interest / 1.16, if(is_t7_window = 1, should_interest, 0))) as t7_mature_si_net
      ,sum(if(is_t7_window = 1, t7_overdue_amount, 0))  as t7_mature_ovd
  FROM raw
  GROUP BY product_name, grade

)
SELECT grp, product_name, grade
      ,loans, custs, ca, ha, si, si_net
      ,t0_mature_cnt
      ,t0_should_amt
      ,t0_overdue_amount
      ,t0_ovd_cnt
      ,t3_mature_cnt
      ,t3_should_amt
      ,t3_overdue_amount
      ,t3_ovd_cnt
      ,t7_mature_cnt
      ,t7_should_amt
      ,t7_overdue_amount
      ,t7_ovd_cnt
      ,t14_mature_cnt
      ,t14_should_amt
      ,t14_overdue_amount
      ,t14_ovd_cnt
      ,t30_mature_cnt
      ,t30_should_amt
      ,t30_overdue_amount
      ,t30_ovd_cnt
      ,t7_mature_ca
      ,t7_mature_ha
      ,t7_mature_si_net
      ,t7_mature_ovd
       ,round(CAST(ca AS DOUBLE) / nullif(loans, 0), 2)  as avg_ca
      ,round(CAST(loans AS DOUBLE) / nullif(custs, 0), 4) as loans_cust
      ,round(CAST(ha AS DOUBLE) / nullif(ca, 0), 4)          as ha_rate
      ,round(CAST(si AS DOUBLE) / nullif(ca, 0), 4)          as si_rate
      ,round(CAST(si_net AS DOUBLE) / nullif(ca, 0), 4)      as si_net_rate
      ,round(CAST(ha + si_net AS DOUBLE) / nullif(ca, 0), 4) as fee_net_rate
      ,round(CAST(si_net * 0.16 AS DOUBLE) / nullif(ca, 0), 4) as vat_ca_rate
       ,round(CAST(loans AS DOUBLE) / nullif(sum(loans) over (partition by grade), 0), 4) as loans_share_g
      ,round(CAST(ca    AS DOUBLE) / nullif(sum(ca)    over (partition by grade), 0), 4) as ca_share_g
      ,round(CAST(loans AS DOUBLE) / nullif(sum(loans) over (partition by product_name), 0), 4) as loans_share_p
      ,round(CAST(ca    AS DOUBLE) / nullif(sum(ca)    over (partition by product_name), 0), 4) as ca_share_p
      ,round(CAST(t0_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t0_mature_rate,round(CAST(t0_ovd_cnt AS DOUBLE) / nullif(t0_mature_cnt, 0), 4) as t0_cntrate,round(CAST(t0_overdue_amount AS DOUBLE) / nullif(t0_should_amt, 0), 4) as t0_amtrate,round(CAST(t3_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t3_mature_rate,round(CAST(t3_ovd_cnt AS DOUBLE) / nullif(t3_mature_cnt, 0), 4) as t3_cntrate,round(CAST(t3_overdue_amount AS DOUBLE) / nullif(t3_should_amt, 0), 4) as t3_amtrate,round(CAST(t7_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t7_mature_rate,round(CAST(t7_ovd_cnt AS DOUBLE) / nullif(t7_mature_cnt, 0), 4) as t7_cntrate,round(CAST(t7_overdue_amount AS DOUBLE) / nullif(t7_should_amt, 0), 4) as t7_amtrate,round(CAST(t14_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t14_mature_rate,round(CAST(t14_ovd_cnt AS DOUBLE) / nullif(t14_mature_cnt, 0), 4) as t14_cntrate,round(CAST(t14_overdue_amount AS DOUBLE) / nullif(t14_should_amt, 0), 4) as t14_amtrate,round(CAST(t30_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t30_mature_rate,round(CAST(t30_ovd_cnt AS DOUBLE) / nullif(t30_mature_cnt, 0), 4) as t30_cntrate,round(CAST(t30_overdue_amount AS DOUBLE) / nullif(t30_should_amt, 0), 4) as t30_amtrate,round(CAST((t7_mature_ha + t7_mature_si_net - t7_mature_ovd) AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as tr_net7
      ,round(CAST(t7_mature_ovd AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as t7_ovd_amtrate_ca
FROM g
ORDER BY grp, product_name, grade;

-- ==== Q2 评级小计(档1~13) ====
WITH raw AS (
  SELECT f.product_name
        ,CAST(y.android_oldcust_maincreditlevel_charge_v5_3 AS INTEGER) AS grade
        ,if(substr(f.product_name, 1, 1) = 'E', 1, 0) AS is_e
        ,f.biz_id, f.mid
        ,f.contract_amount, f.haircut_amount, f.should_interest
        ,f.release_time
        ,f.is_t0_window ,f.t0_should_amt ,f.t0_overdue_amount
        ,f.is_t3_window ,f.t3_should_amt ,f.t3_overdue_amount
        ,f.is_t7_window ,f.t7_should_amt ,f.t7_overdue_amount
        ,f.is_t14_window,f.t14_should_amt,f.t14_overdue_amount
        ,f.is_t30_window,f.t30_should_amt,f.t30_overdue_amount
        ,f.is_t0_overdue,f.is_t3_overdue,f.is_t7_overdue,f.is_t30_overdue
  FROM mx.wxs_application_funnel f
  JOIN mx.yj_test_table_250225 y ON f.biz_id = y.biz_id
  WHERE f.is_reloan = 'old' AND f.if_issue = 1 AND f.product_name IS NOT NULL AND f.product_name <> '' AND date(f.release_time) >= date '2026-06-09' AND date(f.release_time) < date '2026-09-01' AND y.v3_flag = 'V5_3' AND y.android_oldcust_maincreditlevel_charge_v5_3 IS NOT NULL
)
,g AS (
  SELECT CAST('全期' AS VARCHAR) AS grp
      ,CAST(NULL AS VARCHAR) AS product_name
      ,grade
      ,count(distinct biz_id) AS loans
        ,count(distinct mid)       AS custs
        ,round(sum(contract_amount), 2)  AS ca
        ,round(sum(haircut_amount), 2)   AS ha
        ,round(sum(should_interest), 2)  AS si
        ,round(sum(if(is_e = 1, should_interest / 1.16, should_interest)), 2) AS si_net
        ,sum(if(is_t0_window = 1, 1, 0)) as t0_mature_cnt
      ,sum(if(is_t0_window = 1, t0_should_amt, 0))  as t0_should_amt
      ,sum(if(is_t0_window = 1, t0_overdue_amount, 0)) as t0_overdue_amount
      ,sum(if(is_t0_window = 1 and is_t0_overdue = 1, 1, 0)) as t0_ovd_cnt
      ,sum(if(is_t3_window = 1, 1, 0)) as t3_mature_cnt
      ,sum(if(is_t3_window = 1, t3_should_amt, 0))  as t3_should_amt
      ,sum(if(is_t3_window = 1, t3_overdue_amount, 0)) as t3_overdue_amount
      ,sum(if(is_t3_window = 1 and is_t3_overdue = 1, 1, 0)) as t3_ovd_cnt
      ,sum(if(is_t7_window = 1, 1, 0)) as t7_mature_cnt
      ,sum(if(is_t7_window = 1, t7_should_amt, 0))  as t7_should_amt
      ,sum(if(is_t7_window = 1, t7_overdue_amount, 0)) as t7_overdue_amount
      ,sum(if(is_t7_window = 1 and is_t7_overdue = 1, 1, 0)) as t7_ovd_cnt
      ,sum(if(is_t14_window = 1, 1, 0)) as t14_mature_cnt
      ,sum(if(is_t14_window = 1, t14_should_amt, 0))  as t14_should_amt
      ,sum(if(is_t14_window = 1, t14_overdue_amount, 0)) as t14_overdue_amount
      ,sum(if(is_t14_window = 1 and t14_overdue_amount > 1, 1, 0)) as t14_ovd_cnt
      ,sum(if(is_t30_window = 1, 1, 0)) as t30_mature_cnt
      ,sum(if(is_t30_window = 1, t30_should_amt, 0))  as t30_should_amt
      ,sum(if(is_t30_window = 1, t30_overdue_amount, 0)) as t30_overdue_amount
      ,sum(if(is_t30_window = 1 and is_t30_overdue = 1, 1, 0)) as t30_ovd_cnt
      ,sum(if(is_t7_window = 1, contract_amount, 0))    as t7_mature_ca
      ,sum(if(is_t7_window = 1, haircut_amount, 0))     as t7_mature_ha
      ,sum(if(is_t7_window = 1 and is_e = 1, should_interest / 1.16, if(is_t7_window = 1, should_interest, 0))) as t7_mature_si_net
      ,sum(if(is_t7_window = 1, t7_overdue_amount, 0))  as t7_mature_ovd
  FROM raw
  GROUP BY grade

)
SELECT grp, product_name, grade
      ,loans, custs, ca, ha, si, si_net
      ,t0_mature_cnt
      ,t0_should_amt
      ,t0_overdue_amount
      ,t0_ovd_cnt
      ,t3_mature_cnt
      ,t3_should_amt
      ,t3_overdue_amount
      ,t3_ovd_cnt
      ,t7_mature_cnt
      ,t7_should_amt
      ,t7_overdue_amount
      ,t7_ovd_cnt
      ,t14_mature_cnt
      ,t14_should_amt
      ,t14_overdue_amount
      ,t14_ovd_cnt
      ,t30_mature_cnt
      ,t30_should_amt
      ,t30_overdue_amount
      ,t30_ovd_cnt
      ,t7_mature_ca
      ,t7_mature_ha
      ,t7_mature_si_net
      ,t7_mature_ovd
       ,round(CAST(ca AS DOUBLE) / nullif(loans, 0), 2)  as avg_ca
      ,round(CAST(loans AS DOUBLE) / nullif(custs, 0), 4) as loans_cust
      ,round(CAST(ha AS DOUBLE) / nullif(ca, 0), 4)          as ha_rate
      ,round(CAST(si AS DOUBLE) / nullif(ca, 0), 4)          as si_rate
      ,round(CAST(si_net AS DOUBLE) / nullif(ca, 0), 4)      as si_net_rate
      ,round(CAST(ha + si_net AS DOUBLE) / nullif(ca, 0), 4) as fee_net_rate
      ,round(CAST(si_net * 0.16 AS DOUBLE) / nullif(ca, 0), 4) as vat_ca_rate
       ,CAST(NULL AS DOUBLE) AS loans_share_g
      ,CAST(NULL AS DOUBLE) AS ca_share_g
      ,CAST(NULL AS DOUBLE) AS loans_share_p
      ,CAST(NULL AS DOUBLE) AS ca_share_p
      ,round(CAST(t0_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t0_mature_rate,round(CAST(t0_ovd_cnt AS DOUBLE) / nullif(t0_mature_cnt, 0), 4) as t0_cntrate,round(CAST(t0_overdue_amount AS DOUBLE) / nullif(t0_should_amt, 0), 4) as t0_amtrate,round(CAST(t3_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t3_mature_rate,round(CAST(t3_ovd_cnt AS DOUBLE) / nullif(t3_mature_cnt, 0), 4) as t3_cntrate,round(CAST(t3_overdue_amount AS DOUBLE) / nullif(t3_should_amt, 0), 4) as t3_amtrate,round(CAST(t7_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t7_mature_rate,round(CAST(t7_ovd_cnt AS DOUBLE) / nullif(t7_mature_cnt, 0), 4) as t7_cntrate,round(CAST(t7_overdue_amount AS DOUBLE) / nullif(t7_should_amt, 0), 4) as t7_amtrate,round(CAST(t14_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t14_mature_rate,round(CAST(t14_ovd_cnt AS DOUBLE) / nullif(t14_mature_cnt, 0), 4) as t14_cntrate,round(CAST(t14_overdue_amount AS DOUBLE) / nullif(t14_should_amt, 0), 4) as t14_amtrate,round(CAST(t30_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t30_mature_rate,round(CAST(t30_ovd_cnt AS DOUBLE) / nullif(t30_mature_cnt, 0), 4) as t30_cntrate,round(CAST(t30_overdue_amount AS DOUBLE) / nullif(t30_should_amt, 0), 4) as t30_amtrate,round(CAST((t7_mature_ha + t7_mature_si_net - t7_mature_ovd) AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as tr_net7
      ,round(CAST(t7_mature_ovd AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as t7_ovd_amtrate_ca
FROM g
ORDER BY grp, grade;

-- ==== Q3 产品小计 ====
WITH raw AS (
  SELECT f.product_name
        ,CAST(y.android_oldcust_maincreditlevel_charge_v5_3 AS INTEGER) AS grade
        ,if(substr(f.product_name, 1, 1) = 'E', 1, 0) AS is_e
        ,f.biz_id, f.mid
        ,f.contract_amount, f.haircut_amount, f.should_interest
        ,f.release_time
        ,f.is_t0_window ,f.t0_should_amt ,f.t0_overdue_amount
        ,f.is_t3_window ,f.t3_should_amt ,f.t3_overdue_amount
        ,f.is_t7_window ,f.t7_should_amt ,f.t7_overdue_amount
        ,f.is_t14_window,f.t14_should_amt,f.t14_overdue_amount
        ,f.is_t30_window,f.t30_should_amt,f.t30_overdue_amount
        ,f.is_t0_overdue,f.is_t3_overdue,f.is_t7_overdue,f.is_t30_overdue
  FROM mx.wxs_application_funnel f
  JOIN mx.yj_test_table_250225 y ON f.biz_id = y.biz_id
  WHERE f.is_reloan = 'old' AND f.if_issue = 1 AND f.product_name IS NOT NULL AND f.product_name <> '' AND date(f.release_time) >= date '2026-06-09' AND date(f.release_time) < date '2026-09-01' AND y.v3_flag = 'V5_3' AND y.android_oldcust_maincreditlevel_charge_v5_3 IS NOT NULL
)
,g AS (
  SELECT CAST('全期' AS VARCHAR) AS grp
      ,product_name
      ,CAST(NULL AS INTEGER) AS grade
      ,count(distinct biz_id) AS loans
        ,count(distinct mid)       AS custs
        ,round(sum(contract_amount), 2)  AS ca
        ,round(sum(haircut_amount), 2)   AS ha
        ,round(sum(should_interest), 2)  AS si
        ,round(sum(if(is_e = 1, should_interest / 1.16, should_interest)), 2) AS si_net
        ,sum(if(is_t0_window = 1, 1, 0)) as t0_mature_cnt
      ,sum(if(is_t0_window = 1, t0_should_amt, 0))  as t0_should_amt
      ,sum(if(is_t0_window = 1, t0_overdue_amount, 0)) as t0_overdue_amount
      ,sum(if(is_t0_window = 1 and is_t0_overdue = 1, 1, 0)) as t0_ovd_cnt
      ,sum(if(is_t3_window = 1, 1, 0)) as t3_mature_cnt
      ,sum(if(is_t3_window = 1, t3_should_amt, 0))  as t3_should_amt
      ,sum(if(is_t3_window = 1, t3_overdue_amount, 0)) as t3_overdue_amount
      ,sum(if(is_t3_window = 1 and is_t3_overdue = 1, 1, 0)) as t3_ovd_cnt
      ,sum(if(is_t7_window = 1, 1, 0)) as t7_mature_cnt
      ,sum(if(is_t7_window = 1, t7_should_amt, 0))  as t7_should_amt
      ,sum(if(is_t7_window = 1, t7_overdue_amount, 0)) as t7_overdue_amount
      ,sum(if(is_t7_window = 1 and is_t7_overdue = 1, 1, 0)) as t7_ovd_cnt
      ,sum(if(is_t14_window = 1, 1, 0)) as t14_mature_cnt
      ,sum(if(is_t14_window = 1, t14_should_amt, 0))  as t14_should_amt
      ,sum(if(is_t14_window = 1, t14_overdue_amount, 0)) as t14_overdue_amount
      ,sum(if(is_t14_window = 1 and t14_overdue_amount > 1, 1, 0)) as t14_ovd_cnt
      ,sum(if(is_t30_window = 1, 1, 0)) as t30_mature_cnt
      ,sum(if(is_t30_window = 1, t30_should_amt, 0))  as t30_should_amt
      ,sum(if(is_t30_window = 1, t30_overdue_amount, 0)) as t30_overdue_amount
      ,sum(if(is_t30_window = 1 and is_t30_overdue = 1, 1, 0)) as t30_ovd_cnt
      ,sum(if(is_t7_window = 1, contract_amount, 0))    as t7_mature_ca
      ,sum(if(is_t7_window = 1, haircut_amount, 0))     as t7_mature_ha
      ,sum(if(is_t7_window = 1 and is_e = 1, should_interest / 1.16, if(is_t7_window = 1, should_interest, 0))) as t7_mature_si_net
      ,sum(if(is_t7_window = 1, t7_overdue_amount, 0))  as t7_mature_ovd
  FROM raw
  GROUP BY product_name

)
SELECT grp, product_name, grade
      ,loans, custs, ca, ha, si, si_net
      ,t0_mature_cnt
      ,t0_should_amt
      ,t0_overdue_amount
      ,t0_ovd_cnt
      ,t3_mature_cnt
      ,t3_should_amt
      ,t3_overdue_amount
      ,t3_ovd_cnt
      ,t7_mature_cnt
      ,t7_should_amt
      ,t7_overdue_amount
      ,t7_ovd_cnt
      ,t14_mature_cnt
      ,t14_should_amt
      ,t14_overdue_amount
      ,t14_ovd_cnt
      ,t30_mature_cnt
      ,t30_should_amt
      ,t30_overdue_amount
      ,t30_ovd_cnt
      ,t7_mature_ca
      ,t7_mature_ha
      ,t7_mature_si_net
      ,t7_mature_ovd
       ,round(CAST(ca AS DOUBLE) / nullif(loans, 0), 2)  as avg_ca
      ,round(CAST(loans AS DOUBLE) / nullif(custs, 0), 4) as loans_cust
      ,round(CAST(ha AS DOUBLE) / nullif(ca, 0), 4)          as ha_rate
      ,round(CAST(si AS DOUBLE) / nullif(ca, 0), 4)          as si_rate
      ,round(CAST(si_net AS DOUBLE) / nullif(ca, 0), 4)      as si_net_rate
      ,round(CAST(ha + si_net AS DOUBLE) / nullif(ca, 0), 4) as fee_net_rate
      ,round(CAST(si_net * 0.16 AS DOUBLE) / nullif(ca, 0), 4) as vat_ca_rate
       ,CAST(NULL AS DOUBLE) AS loans_share_g
      ,CAST(NULL AS DOUBLE) AS ca_share_g
      ,CAST(NULL AS DOUBLE) AS loans_share_p
      ,CAST(NULL AS DOUBLE) AS ca_share_p
      ,round(CAST(t0_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t0_mature_rate,round(CAST(t0_ovd_cnt AS DOUBLE) / nullif(t0_mature_cnt, 0), 4) as t0_cntrate,round(CAST(t0_overdue_amount AS DOUBLE) / nullif(t0_should_amt, 0), 4) as t0_amtrate,round(CAST(t3_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t3_mature_rate,round(CAST(t3_ovd_cnt AS DOUBLE) / nullif(t3_mature_cnt, 0), 4) as t3_cntrate,round(CAST(t3_overdue_amount AS DOUBLE) / nullif(t3_should_amt, 0), 4) as t3_amtrate,round(CAST(t7_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t7_mature_rate,round(CAST(t7_ovd_cnt AS DOUBLE) / nullif(t7_mature_cnt, 0), 4) as t7_cntrate,round(CAST(t7_overdue_amount AS DOUBLE) / nullif(t7_should_amt, 0), 4) as t7_amtrate,round(CAST(t14_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t14_mature_rate,round(CAST(t14_ovd_cnt AS DOUBLE) / nullif(t14_mature_cnt, 0), 4) as t14_cntrate,round(CAST(t14_overdue_amount AS DOUBLE) / nullif(t14_should_amt, 0), 4) as t14_amtrate,round(CAST(t30_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t30_mature_rate,round(CAST(t30_ovd_cnt AS DOUBLE) / nullif(t30_mature_cnt, 0), 4) as t30_cntrate,round(CAST(t30_overdue_amount AS DOUBLE) / nullif(t30_should_amt, 0), 4) as t30_amtrate,round(CAST((t7_mature_ha + t7_mature_si_net - t7_mature_ovd) AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as tr_net7
      ,round(CAST(t7_mature_ovd AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as t7_ovd_amtrate_ca
FROM g
ORDER BY grp, product_name;

-- ==== Q4 全量合计 ====
WITH raw AS (
  SELECT f.product_name
        ,CAST(y.android_oldcust_maincreditlevel_charge_v5_3 AS INTEGER) AS grade
        ,if(substr(f.product_name, 1, 1) = 'E', 1, 0) AS is_e
        ,f.biz_id, f.mid
        ,f.contract_amount, f.haircut_amount, f.should_interest
        ,f.release_time
        ,f.is_t0_window ,f.t0_should_amt ,f.t0_overdue_amount
        ,f.is_t3_window ,f.t3_should_amt ,f.t3_overdue_amount
        ,f.is_t7_window ,f.t7_should_amt ,f.t7_overdue_amount
        ,f.is_t14_window,f.t14_should_amt,f.t14_overdue_amount
        ,f.is_t30_window,f.t30_should_amt,f.t30_overdue_amount
        ,f.is_t0_overdue,f.is_t3_overdue,f.is_t7_overdue,f.is_t30_overdue
  FROM mx.wxs_application_funnel f
  JOIN mx.yj_test_table_250225 y ON f.biz_id = y.biz_id
  WHERE f.is_reloan = 'old' AND f.if_issue = 1 AND f.product_name IS NOT NULL AND f.product_name <> '' AND date(f.release_time) >= date '2026-06-09' AND date(f.release_time) < date '2026-09-01' AND y.v3_flag = 'V5_3' AND y.android_oldcust_maincreditlevel_charge_v5_3 IS NOT NULL
)
,g AS (
  SELECT CAST('全期' AS VARCHAR) AS grp
      ,CAST(NULL AS VARCHAR) AS product_name
      ,CAST(NULL AS INTEGER) AS grade
      ,count(distinct biz_id) AS loans
        ,count(distinct mid)       AS custs
        ,round(sum(contract_amount), 2)  AS ca
        ,round(sum(haircut_amount), 2)   AS ha
        ,round(sum(should_interest), 2)  AS si
        ,round(sum(if(is_e = 1, should_interest / 1.16, should_interest)), 2) AS si_net
        ,sum(if(is_t0_window = 1, 1, 0)) as t0_mature_cnt
      ,sum(if(is_t0_window = 1, t0_should_amt, 0))  as t0_should_amt
      ,sum(if(is_t0_window = 1, t0_overdue_amount, 0)) as t0_overdue_amount
      ,sum(if(is_t0_window = 1 and is_t0_overdue = 1, 1, 0)) as t0_ovd_cnt
      ,sum(if(is_t3_window = 1, 1, 0)) as t3_mature_cnt
      ,sum(if(is_t3_window = 1, t3_should_amt, 0))  as t3_should_amt
      ,sum(if(is_t3_window = 1, t3_overdue_amount, 0)) as t3_overdue_amount
      ,sum(if(is_t3_window = 1 and is_t3_overdue = 1, 1, 0)) as t3_ovd_cnt
      ,sum(if(is_t7_window = 1, 1, 0)) as t7_mature_cnt
      ,sum(if(is_t7_window = 1, t7_should_amt, 0))  as t7_should_amt
      ,sum(if(is_t7_window = 1, t7_overdue_amount, 0)) as t7_overdue_amount
      ,sum(if(is_t7_window = 1 and is_t7_overdue = 1, 1, 0)) as t7_ovd_cnt
      ,sum(if(is_t14_window = 1, 1, 0)) as t14_mature_cnt
      ,sum(if(is_t14_window = 1, t14_should_amt, 0))  as t14_should_amt
      ,sum(if(is_t14_window = 1, t14_overdue_amount, 0)) as t14_overdue_amount
      ,sum(if(is_t14_window = 1 and t14_overdue_amount > 1, 1, 0)) as t14_ovd_cnt
      ,sum(if(is_t30_window = 1, 1, 0)) as t30_mature_cnt
      ,sum(if(is_t30_window = 1, t30_should_amt, 0))  as t30_should_amt
      ,sum(if(is_t30_window = 1, t30_overdue_amount, 0)) as t30_overdue_amount
      ,sum(if(is_t30_window = 1 and is_t30_overdue = 1, 1, 0)) as t30_ovd_cnt
      ,sum(if(is_t7_window = 1, contract_amount, 0))    as t7_mature_ca
      ,sum(if(is_t7_window = 1, haircut_amount, 0))     as t7_mature_ha
      ,sum(if(is_t7_window = 1 and is_e = 1, should_interest / 1.16, if(is_t7_window = 1, should_interest, 0))) as t7_mature_si_net
      ,sum(if(is_t7_window = 1, t7_overdue_amount, 0))  as t7_mature_ovd
  FROM raw

)
SELECT grp, product_name, grade
      ,loans, custs, ca, ha, si, si_net
      ,t0_mature_cnt
      ,t0_should_amt
      ,t0_overdue_amount
      ,t0_ovd_cnt
      ,t3_mature_cnt
      ,t3_should_amt
      ,t3_overdue_amount
      ,t3_ovd_cnt
      ,t7_mature_cnt
      ,t7_should_amt
      ,t7_overdue_amount
      ,t7_ovd_cnt
      ,t14_mature_cnt
      ,t14_should_amt
      ,t14_overdue_amount
      ,t14_ovd_cnt
      ,t30_mature_cnt
      ,t30_should_amt
      ,t30_overdue_amount
      ,t30_ovd_cnt
      ,t7_mature_ca
      ,t7_mature_ha
      ,t7_mature_si_net
      ,t7_mature_ovd
       ,round(CAST(ca AS DOUBLE) / nullif(loans, 0), 2)  as avg_ca
      ,round(CAST(loans AS DOUBLE) / nullif(custs, 0), 4) as loans_cust
      ,round(CAST(ha AS DOUBLE) / nullif(ca, 0), 4)          as ha_rate
      ,round(CAST(si AS DOUBLE) / nullif(ca, 0), 4)          as si_rate
      ,round(CAST(si_net AS DOUBLE) / nullif(ca, 0), 4)      as si_net_rate
      ,round(CAST(ha + si_net AS DOUBLE) / nullif(ca, 0), 4) as fee_net_rate
      ,round(CAST(si_net * 0.16 AS DOUBLE) / nullif(ca, 0), 4) as vat_ca_rate
       ,CAST(NULL AS DOUBLE) AS loans_share_g
      ,CAST(NULL AS DOUBLE) AS ca_share_g
      ,CAST(NULL AS DOUBLE) AS loans_share_p
      ,CAST(NULL AS DOUBLE) AS ca_share_p
      ,round(CAST(t0_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t0_mature_rate,round(CAST(t0_ovd_cnt AS DOUBLE) / nullif(t0_mature_cnt, 0), 4) as t0_cntrate,round(CAST(t0_overdue_amount AS DOUBLE) / nullif(t0_should_amt, 0), 4) as t0_amtrate,round(CAST(t3_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t3_mature_rate,round(CAST(t3_ovd_cnt AS DOUBLE) / nullif(t3_mature_cnt, 0), 4) as t3_cntrate,round(CAST(t3_overdue_amount AS DOUBLE) / nullif(t3_should_amt, 0), 4) as t3_amtrate,round(CAST(t7_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t7_mature_rate,round(CAST(t7_ovd_cnt AS DOUBLE) / nullif(t7_mature_cnt, 0), 4) as t7_cntrate,round(CAST(t7_overdue_amount AS DOUBLE) / nullif(t7_should_amt, 0), 4) as t7_amtrate,round(CAST(t14_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t14_mature_rate,round(CAST(t14_ovd_cnt AS DOUBLE) / nullif(t14_mature_cnt, 0), 4) as t14_cntrate,round(CAST(t14_overdue_amount AS DOUBLE) / nullif(t14_should_amt, 0), 4) as t14_amtrate,round(CAST(t30_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t30_mature_rate,round(CAST(t30_ovd_cnt AS DOUBLE) / nullif(t30_mature_cnt, 0), 4) as t30_cntrate,round(CAST(t30_overdue_amount AS DOUBLE) / nullif(t30_should_amt, 0), 4) as t30_amtrate,round(CAST((t7_mature_ha + t7_mature_si_net - t7_mature_ovd) AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as tr_net7
      ,round(CAST(t7_mature_ovd AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as t7_ovd_amtrate_ca
FROM g
ORDER BY grp, 1;

-- ==== Q5 月×评级 ====
WITH raw AS (
  SELECT f.product_name
        ,CAST(y.android_oldcust_maincreditlevel_charge_v5_3 AS INTEGER) AS grade
        ,if(substr(f.product_name, 1, 1) = 'E', 1, 0) AS is_e
        ,f.biz_id, f.mid
        ,f.contract_amount, f.haircut_amount, f.should_interest
        ,f.release_time
        ,f.is_t0_window ,f.t0_should_amt ,f.t0_overdue_amount
        ,f.is_t3_window ,f.t3_should_amt ,f.t3_overdue_amount
        ,f.is_t7_window ,f.t7_should_amt ,f.t7_overdue_amount
        ,f.is_t14_window,f.t14_should_amt,f.t14_overdue_amount
        ,f.is_t30_window,f.t30_should_amt,f.t30_overdue_amount
        ,f.is_t0_overdue,f.is_t3_overdue,f.is_t7_overdue,f.is_t30_overdue
  FROM mx.wxs_application_funnel f
  JOIN mx.yj_test_table_250225 y ON f.biz_id = y.biz_id
  WHERE f.is_reloan = 'old' AND f.if_issue = 1 AND f.product_name IS NOT NULL AND f.product_name <> '' AND date(f.release_time) >= date '2026-06-09' AND date(f.release_time) < date '2026-09-01' AND y.v3_flag = 'V5_3' AND y.android_oldcust_maincreditlevel_charge_v5_3 IS NOT NULL
)
,g AS (
  SELECT date_format(date_trunc('month', date(release_time)), '%Y-%m') AS grp
      ,CAST(NULL AS VARCHAR) AS product_name
      ,grade
      ,count(distinct biz_id) AS loans
        ,count(distinct mid)       AS custs
        ,round(sum(contract_amount), 2)  AS ca
        ,round(sum(haircut_amount), 2)   AS ha
        ,round(sum(should_interest), 2)  AS si
        ,round(sum(if(is_e = 1, should_interest / 1.16, should_interest)), 2) AS si_net
        ,sum(if(is_t0_window = 1, 1, 0)) as t0_mature_cnt
      ,sum(if(is_t0_window = 1, t0_should_amt, 0))  as t0_should_amt
      ,sum(if(is_t0_window = 1, t0_overdue_amount, 0)) as t0_overdue_amount
      ,sum(if(is_t0_window = 1 and is_t0_overdue = 1, 1, 0)) as t0_ovd_cnt
      ,sum(if(is_t3_window = 1, 1, 0)) as t3_mature_cnt
      ,sum(if(is_t3_window = 1, t3_should_amt, 0))  as t3_should_amt
      ,sum(if(is_t3_window = 1, t3_overdue_amount, 0)) as t3_overdue_amount
      ,sum(if(is_t3_window = 1 and is_t3_overdue = 1, 1, 0)) as t3_ovd_cnt
      ,sum(if(is_t7_window = 1, 1, 0)) as t7_mature_cnt
      ,sum(if(is_t7_window = 1, t7_should_amt, 0))  as t7_should_amt
      ,sum(if(is_t7_window = 1, t7_overdue_amount, 0)) as t7_overdue_amount
      ,sum(if(is_t7_window = 1 and is_t7_overdue = 1, 1, 0)) as t7_ovd_cnt
      ,sum(if(is_t14_window = 1, 1, 0)) as t14_mature_cnt
      ,sum(if(is_t14_window = 1, t14_should_amt, 0))  as t14_should_amt
      ,sum(if(is_t14_window = 1, t14_overdue_amount, 0)) as t14_overdue_amount
      ,sum(if(is_t14_window = 1 and t14_overdue_amount > 1, 1, 0)) as t14_ovd_cnt
      ,sum(if(is_t30_window = 1, 1, 0)) as t30_mature_cnt
      ,sum(if(is_t30_window = 1, t30_should_amt, 0))  as t30_should_amt
      ,sum(if(is_t30_window = 1, t30_overdue_amount, 0)) as t30_overdue_amount
      ,sum(if(is_t30_window = 1 and is_t30_overdue = 1, 1, 0)) as t30_ovd_cnt
      ,sum(if(is_t7_window = 1, contract_amount, 0))    as t7_mature_ca
      ,sum(if(is_t7_window = 1, haircut_amount, 0))     as t7_mature_ha
      ,sum(if(is_t7_window = 1 and is_e = 1, should_interest / 1.16, if(is_t7_window = 1, should_interest, 0))) as t7_mature_si_net
      ,sum(if(is_t7_window = 1, t7_overdue_amount, 0))  as t7_mature_ovd
  FROM raw
  GROUP BY date_format(date_trunc('month', date(release_time)), '%Y-%m'), grade

)
SELECT grp, product_name, grade
      ,loans, custs, ca, ha, si, si_net
      ,t0_mature_cnt
      ,t0_should_amt
      ,t0_overdue_amount
      ,t0_ovd_cnt
      ,t3_mature_cnt
      ,t3_should_amt
      ,t3_overdue_amount
      ,t3_ovd_cnt
      ,t7_mature_cnt
      ,t7_should_amt
      ,t7_overdue_amount
      ,t7_ovd_cnt
      ,t14_mature_cnt
      ,t14_should_amt
      ,t14_overdue_amount
      ,t14_ovd_cnt
      ,t30_mature_cnt
      ,t30_should_amt
      ,t30_overdue_amount
      ,t30_ovd_cnt
      ,t7_mature_ca
      ,t7_mature_ha
      ,t7_mature_si_net
      ,t7_mature_ovd
       ,round(CAST(ca AS DOUBLE) / nullif(loans, 0), 2)  as avg_ca
      ,round(CAST(loans AS DOUBLE) / nullif(custs, 0), 4) as loans_cust
      ,round(CAST(ha AS DOUBLE) / nullif(ca, 0), 4)          as ha_rate
      ,round(CAST(si AS DOUBLE) / nullif(ca, 0), 4)          as si_rate
      ,round(CAST(si_net AS DOUBLE) / nullif(ca, 0), 4)      as si_net_rate
      ,round(CAST(ha + si_net AS DOUBLE) / nullif(ca, 0), 4) as fee_net_rate
      ,round(CAST(si_net * 0.16 AS DOUBLE) / nullif(ca, 0), 4) as vat_ca_rate
       ,CAST(NULL AS DOUBLE) AS loans_share_g
      ,CAST(NULL AS DOUBLE) AS ca_share_g
      ,CAST(NULL AS DOUBLE) AS loans_share_p
      ,CAST(NULL AS DOUBLE) AS ca_share_p
      ,round(CAST(t0_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t0_mature_rate,round(CAST(t0_ovd_cnt AS DOUBLE) / nullif(t0_mature_cnt, 0), 4) as t0_cntrate,round(CAST(t0_overdue_amount AS DOUBLE) / nullif(t0_should_amt, 0), 4) as t0_amtrate,round(CAST(t3_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t3_mature_rate,round(CAST(t3_ovd_cnt AS DOUBLE) / nullif(t3_mature_cnt, 0), 4) as t3_cntrate,round(CAST(t3_overdue_amount AS DOUBLE) / nullif(t3_should_amt, 0), 4) as t3_amtrate,round(CAST(t7_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t7_mature_rate,round(CAST(t7_ovd_cnt AS DOUBLE) / nullif(t7_mature_cnt, 0), 4) as t7_cntrate,round(CAST(t7_overdue_amount AS DOUBLE) / nullif(t7_should_amt, 0), 4) as t7_amtrate,round(CAST(t14_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t14_mature_rate,round(CAST(t14_ovd_cnt AS DOUBLE) / nullif(t14_mature_cnt, 0), 4) as t14_cntrate,round(CAST(t14_overdue_amount AS DOUBLE) / nullif(t14_should_amt, 0), 4) as t14_amtrate,round(CAST(t30_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t30_mature_rate,round(CAST(t30_ovd_cnt AS DOUBLE) / nullif(t30_mature_cnt, 0), 4) as t30_cntrate,round(CAST(t30_overdue_amount AS DOUBLE) / nullif(t30_should_amt, 0), 4) as t30_amtrate,round(CAST((t7_mature_ha + t7_mature_si_net - t7_mature_ovd) AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as tr_net7
      ,round(CAST(t7_mature_ovd AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as t7_ovd_amtrate_ca
FROM g
ORDER BY grp, grade;

-- ==== Q6 月小计 ====
WITH raw AS (
  SELECT f.product_name
        ,CAST(y.android_oldcust_maincreditlevel_charge_v5_3 AS INTEGER) AS grade
        ,if(substr(f.product_name, 1, 1) = 'E', 1, 0) AS is_e
        ,f.biz_id, f.mid
        ,f.contract_amount, f.haircut_amount, f.should_interest
        ,f.release_time
        ,f.is_t0_window ,f.t0_should_amt ,f.t0_overdue_amount
        ,f.is_t3_window ,f.t3_should_amt ,f.t3_overdue_amount
        ,f.is_t7_window ,f.t7_should_amt ,f.t7_overdue_amount
        ,f.is_t14_window,f.t14_should_amt,f.t14_overdue_amount
        ,f.is_t30_window,f.t30_should_amt,f.t30_overdue_amount
        ,f.is_t0_overdue,f.is_t3_overdue,f.is_t7_overdue,f.is_t30_overdue
  FROM mx.wxs_application_funnel f
  JOIN mx.yj_test_table_250225 y ON f.biz_id = y.biz_id
  WHERE f.is_reloan = 'old' AND f.if_issue = 1 AND f.product_name IS NOT NULL AND f.product_name <> '' AND date(f.release_time) >= date '2026-06-09' AND date(f.release_time) < date '2026-09-01' AND y.v3_flag = 'V5_3' AND y.android_oldcust_maincreditlevel_charge_v5_3 IS NOT NULL
)
,g AS (
  SELECT date_format(date_trunc('month', date(release_time)), '%Y-%m') AS grp
      ,CAST(NULL AS VARCHAR) AS product_name
      ,CAST(NULL AS INTEGER) AS grade
      ,count(distinct biz_id) AS loans
        ,count(distinct mid)       AS custs
        ,round(sum(contract_amount), 2)  AS ca
        ,round(sum(haircut_amount), 2)   AS ha
        ,round(sum(should_interest), 2)  AS si
        ,round(sum(if(is_e = 1, should_interest / 1.16, should_interest)), 2) AS si_net
        ,sum(if(is_t0_window = 1, 1, 0)) as t0_mature_cnt
      ,sum(if(is_t0_window = 1, t0_should_amt, 0))  as t0_should_amt
      ,sum(if(is_t0_window = 1, t0_overdue_amount, 0)) as t0_overdue_amount
      ,sum(if(is_t0_window = 1 and is_t0_overdue = 1, 1, 0)) as t0_ovd_cnt
      ,sum(if(is_t3_window = 1, 1, 0)) as t3_mature_cnt
      ,sum(if(is_t3_window = 1, t3_should_amt, 0))  as t3_should_amt
      ,sum(if(is_t3_window = 1, t3_overdue_amount, 0)) as t3_overdue_amount
      ,sum(if(is_t3_window = 1 and is_t3_overdue = 1, 1, 0)) as t3_ovd_cnt
      ,sum(if(is_t7_window = 1, 1, 0)) as t7_mature_cnt
      ,sum(if(is_t7_window = 1, t7_should_amt, 0))  as t7_should_amt
      ,sum(if(is_t7_window = 1, t7_overdue_amount, 0)) as t7_overdue_amount
      ,sum(if(is_t7_window = 1 and is_t7_overdue = 1, 1, 0)) as t7_ovd_cnt
      ,sum(if(is_t14_window = 1, 1, 0)) as t14_mature_cnt
      ,sum(if(is_t14_window = 1, t14_should_amt, 0))  as t14_should_amt
      ,sum(if(is_t14_window = 1, t14_overdue_amount, 0)) as t14_overdue_amount
      ,sum(if(is_t14_window = 1 and t14_overdue_amount > 1, 1, 0)) as t14_ovd_cnt
      ,sum(if(is_t30_window = 1, 1, 0)) as t30_mature_cnt
      ,sum(if(is_t30_window = 1, t30_should_amt, 0))  as t30_should_amt
      ,sum(if(is_t30_window = 1, t30_overdue_amount, 0)) as t30_overdue_amount
      ,sum(if(is_t30_window = 1 and is_t30_overdue = 1, 1, 0)) as t30_ovd_cnt
      ,sum(if(is_t7_window = 1, contract_amount, 0))    as t7_mature_ca
      ,sum(if(is_t7_window = 1, haircut_amount, 0))     as t7_mature_ha
      ,sum(if(is_t7_window = 1 and is_e = 1, should_interest / 1.16, if(is_t7_window = 1, should_interest, 0))) as t7_mature_si_net
      ,sum(if(is_t7_window = 1, t7_overdue_amount, 0))  as t7_mature_ovd
  FROM raw
  GROUP BY date_format(date_trunc('month', date(release_time)), '%Y-%m')

)
SELECT grp, product_name, grade
      ,loans, custs, ca, ha, si, si_net
      ,t0_mature_cnt
      ,t0_should_amt
      ,t0_overdue_amount
      ,t0_ovd_cnt
      ,t3_mature_cnt
      ,t3_should_amt
      ,t3_overdue_amount
      ,t3_ovd_cnt
      ,t7_mature_cnt
      ,t7_should_amt
      ,t7_overdue_amount
      ,t7_ovd_cnt
      ,t14_mature_cnt
      ,t14_should_amt
      ,t14_overdue_amount
      ,t14_ovd_cnt
      ,t30_mature_cnt
      ,t30_should_amt
      ,t30_overdue_amount
      ,t30_ovd_cnt
      ,t7_mature_ca
      ,t7_mature_ha
      ,t7_mature_si_net
      ,t7_mature_ovd
       ,round(CAST(ca AS DOUBLE) / nullif(loans, 0), 2)  as avg_ca
      ,round(CAST(loans AS DOUBLE) / nullif(custs, 0), 4) as loans_cust
      ,round(CAST(ha AS DOUBLE) / nullif(ca, 0), 4)          as ha_rate
      ,round(CAST(si AS DOUBLE) / nullif(ca, 0), 4)          as si_rate
      ,round(CAST(si_net AS DOUBLE) / nullif(ca, 0), 4)      as si_net_rate
      ,round(CAST(ha + si_net AS DOUBLE) / nullif(ca, 0), 4) as fee_net_rate
      ,round(CAST(si_net * 0.16 AS DOUBLE) / nullif(ca, 0), 4) as vat_ca_rate
       ,CAST(NULL AS DOUBLE) AS loans_share_g
      ,CAST(NULL AS DOUBLE) AS ca_share_g
      ,CAST(NULL AS DOUBLE) AS loans_share_p
      ,CAST(NULL AS DOUBLE) AS ca_share_p
      ,round(CAST(t0_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t0_mature_rate,round(CAST(t0_ovd_cnt AS DOUBLE) / nullif(t0_mature_cnt, 0), 4) as t0_cntrate,round(CAST(t0_overdue_amount AS DOUBLE) / nullif(t0_should_amt, 0), 4) as t0_amtrate,round(CAST(t3_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t3_mature_rate,round(CAST(t3_ovd_cnt AS DOUBLE) / nullif(t3_mature_cnt, 0), 4) as t3_cntrate,round(CAST(t3_overdue_amount AS DOUBLE) / nullif(t3_should_amt, 0), 4) as t3_amtrate,round(CAST(t7_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t7_mature_rate,round(CAST(t7_ovd_cnt AS DOUBLE) / nullif(t7_mature_cnt, 0), 4) as t7_cntrate,round(CAST(t7_overdue_amount AS DOUBLE) / nullif(t7_should_amt, 0), 4) as t7_amtrate,round(CAST(t14_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t14_mature_rate,round(CAST(t14_ovd_cnt AS DOUBLE) / nullif(t14_mature_cnt, 0), 4) as t14_cntrate,round(CAST(t14_overdue_amount AS DOUBLE) / nullif(t14_should_amt, 0), 4) as t14_amtrate,round(CAST(t30_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t30_mature_rate,round(CAST(t30_ovd_cnt AS DOUBLE) / nullif(t30_mature_cnt, 0), 4) as t30_cntrate,round(CAST(t30_overdue_amount AS DOUBLE) / nullif(t30_should_amt, 0), 4) as t30_amtrate,round(CAST((t7_mature_ha + t7_mature_si_net - t7_mature_ovd) AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as tr_net7
      ,round(CAST(t7_mature_ovd AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as t7_ovd_amtrate_ca
FROM g
ORDER BY grp, 1;

-- ==== Q7 月度明细(月×产品×评级) ====
WITH raw AS (
  SELECT f.product_name
        ,CAST(y.android_oldcust_maincreditlevel_charge_v5_3 AS INTEGER) AS grade
        ,if(substr(f.product_name, 1, 1) = 'E', 1, 0) AS is_e
        ,f.biz_id, f.mid
        ,f.contract_amount, f.haircut_amount, f.should_interest
        ,f.release_time
        ,f.is_t0_window ,f.t0_should_amt ,f.t0_overdue_amount
        ,f.is_t3_window ,f.t3_should_amt ,f.t3_overdue_amount
        ,f.is_t7_window ,f.t7_should_amt ,f.t7_overdue_amount
        ,f.is_t14_window,f.t14_should_amt,f.t14_overdue_amount
        ,f.is_t30_window,f.t30_should_amt,f.t30_overdue_amount
        ,f.is_t0_overdue,f.is_t3_overdue,f.is_t7_overdue,f.is_t30_overdue
  FROM mx.wxs_application_funnel f
  JOIN mx.yj_test_table_250225 y ON f.biz_id = y.biz_id
  WHERE f.is_reloan = 'old' AND f.if_issue = 1 AND f.product_name IS NOT NULL AND f.product_name <> '' AND date(f.release_time) >= date '2026-06-09' AND date(f.release_time) < date '2026-09-01' AND y.v3_flag = 'V5_3' AND y.android_oldcust_maincreditlevel_charge_v5_3 IS NOT NULL
)
,g AS (
  SELECT date_format(date_trunc('month', date(release_time)), '%Y-%m') AS grp
      ,product_name
      ,grade
      ,count(distinct biz_id) AS loans
        ,count(distinct mid)       AS custs
        ,round(sum(contract_amount), 2)  AS ca
        ,round(sum(haircut_amount), 2)   AS ha
        ,round(sum(should_interest), 2)  AS si
        ,round(sum(if(is_e = 1, should_interest / 1.16, should_interest)), 2) AS si_net
        ,sum(if(is_t0_window = 1, 1, 0)) as t0_mature_cnt
      ,sum(if(is_t0_window = 1, t0_should_amt, 0))  as t0_should_amt
      ,sum(if(is_t0_window = 1, t0_overdue_amount, 0)) as t0_overdue_amount
      ,sum(if(is_t0_window = 1 and is_t0_overdue = 1, 1, 0)) as t0_ovd_cnt
      ,sum(if(is_t3_window = 1, 1, 0)) as t3_mature_cnt
      ,sum(if(is_t3_window = 1, t3_should_amt, 0))  as t3_should_amt
      ,sum(if(is_t3_window = 1, t3_overdue_amount, 0)) as t3_overdue_amount
      ,sum(if(is_t3_window = 1 and is_t3_overdue = 1, 1, 0)) as t3_ovd_cnt
      ,sum(if(is_t7_window = 1, 1, 0)) as t7_mature_cnt
      ,sum(if(is_t7_window = 1, t7_should_amt, 0))  as t7_should_amt
      ,sum(if(is_t7_window = 1, t7_overdue_amount, 0)) as t7_overdue_amount
      ,sum(if(is_t7_window = 1 and is_t7_overdue = 1, 1, 0)) as t7_ovd_cnt
      ,sum(if(is_t14_window = 1, 1, 0)) as t14_mature_cnt
      ,sum(if(is_t14_window = 1, t14_should_amt, 0))  as t14_should_amt
      ,sum(if(is_t14_window = 1, t14_overdue_amount, 0)) as t14_overdue_amount
      ,sum(if(is_t14_window = 1 and t14_overdue_amount > 1, 1, 0)) as t14_ovd_cnt
      ,sum(if(is_t30_window = 1, 1, 0)) as t30_mature_cnt
      ,sum(if(is_t30_window = 1, t30_should_amt, 0))  as t30_should_amt
      ,sum(if(is_t30_window = 1, t30_overdue_amount, 0)) as t30_overdue_amount
      ,sum(if(is_t30_window = 1 and is_t30_overdue = 1, 1, 0)) as t30_ovd_cnt
      ,sum(if(is_t7_window = 1, contract_amount, 0))    as t7_mature_ca
      ,sum(if(is_t7_window = 1, haircut_amount, 0))     as t7_mature_ha
      ,sum(if(is_t7_window = 1 and is_e = 1, should_interest / 1.16, if(is_t7_window = 1, should_interest, 0))) as t7_mature_si_net
      ,sum(if(is_t7_window = 1, t7_overdue_amount, 0))  as t7_mature_ovd
  FROM raw
  GROUP BY date_format(date_trunc('month', date(release_time)), '%Y-%m'), product_name, grade

)
SELECT grp, product_name, grade
      ,loans, custs, ca, ha, si, si_net
      ,t0_mature_cnt
      ,t0_should_amt
      ,t0_overdue_amount
      ,t0_ovd_cnt
      ,t3_mature_cnt
      ,t3_should_amt
      ,t3_overdue_amount
      ,t3_ovd_cnt
      ,t7_mature_cnt
      ,t7_should_amt
      ,t7_overdue_amount
      ,t7_ovd_cnt
      ,t14_mature_cnt
      ,t14_should_amt
      ,t14_overdue_amount
      ,t14_ovd_cnt
      ,t30_mature_cnt
      ,t30_should_amt
      ,t30_overdue_amount
      ,t30_ovd_cnt
      ,t7_mature_ca
      ,t7_mature_ha
      ,t7_mature_si_net
      ,t7_mature_ovd
       ,round(CAST(ca AS DOUBLE) / nullif(loans, 0), 2)  as avg_ca
      ,round(CAST(loans AS DOUBLE) / nullif(custs, 0), 4) as loans_cust
      ,round(CAST(ha AS DOUBLE) / nullif(ca, 0), 4)          as ha_rate
      ,round(CAST(si AS DOUBLE) / nullif(ca, 0), 4)          as si_rate
      ,round(CAST(si_net AS DOUBLE) / nullif(ca, 0), 4)      as si_net_rate
      ,round(CAST(ha + si_net AS DOUBLE) / nullif(ca, 0), 4) as fee_net_rate
      ,round(CAST(si_net * 0.16 AS DOUBLE) / nullif(ca, 0), 4) as vat_ca_rate
       ,CAST(NULL AS DOUBLE) AS loans_share_g
      ,CAST(NULL AS DOUBLE) AS ca_share_g
      ,CAST(NULL AS DOUBLE) AS loans_share_p
      ,CAST(NULL AS DOUBLE) AS ca_share_p
      ,round(CAST(t0_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t0_mature_rate,round(CAST(t0_ovd_cnt AS DOUBLE) / nullif(t0_mature_cnt, 0), 4) as t0_cntrate,round(CAST(t0_overdue_amount AS DOUBLE) / nullif(t0_should_amt, 0), 4) as t0_amtrate,round(CAST(t3_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t3_mature_rate,round(CAST(t3_ovd_cnt AS DOUBLE) / nullif(t3_mature_cnt, 0), 4) as t3_cntrate,round(CAST(t3_overdue_amount AS DOUBLE) / nullif(t3_should_amt, 0), 4) as t3_amtrate,round(CAST(t7_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t7_mature_rate,round(CAST(t7_ovd_cnt AS DOUBLE) / nullif(t7_mature_cnt, 0), 4) as t7_cntrate,round(CAST(t7_overdue_amount AS DOUBLE) / nullif(t7_should_amt, 0), 4) as t7_amtrate,round(CAST(t14_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t14_mature_rate,round(CAST(t14_ovd_cnt AS DOUBLE) / nullif(t14_mature_cnt, 0), 4) as t14_cntrate,round(CAST(t14_overdue_amount AS DOUBLE) / nullif(t14_should_amt, 0), 4) as t14_amtrate,round(CAST(t30_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t30_mature_rate,round(CAST(t30_ovd_cnt AS DOUBLE) / nullif(t30_mature_cnt, 0), 4) as t30_cntrate,round(CAST(t30_overdue_amount AS DOUBLE) / nullif(t30_should_amt, 0), 4) as t30_amtrate,round(CAST((t7_mature_ha + t7_mature_si_net - t7_mature_ovd) AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as tr_net7
      ,round(CAST(t7_mature_ovd AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as t7_ovd_amtrate_ca
FROM g
ORDER BY grp, product_name, grade;

-- ==== Q8 月度产品小计(月×产品) ====
WITH raw AS (
  SELECT f.product_name
        ,CAST(y.android_oldcust_maincreditlevel_charge_v5_3 AS INTEGER) AS grade
        ,if(substr(f.product_name, 1, 1) = 'E', 1, 0) AS is_e
        ,f.biz_id, f.mid
        ,f.contract_amount, f.haircut_amount, f.should_interest
        ,f.release_time
        ,f.is_t0_window ,f.t0_should_amt ,f.t0_overdue_amount
        ,f.is_t3_window ,f.t3_should_amt ,f.t3_overdue_amount
        ,f.is_t7_window ,f.t7_should_amt ,f.t7_overdue_amount
        ,f.is_t14_window,f.t14_should_amt,f.t14_overdue_amount
        ,f.is_t30_window,f.t30_should_amt,f.t30_overdue_amount
        ,f.is_t0_overdue,f.is_t3_overdue,f.is_t7_overdue,f.is_t30_overdue
  FROM mx.wxs_application_funnel f
  JOIN mx.yj_test_table_250225 y ON f.biz_id = y.biz_id
  WHERE f.is_reloan = 'old' AND f.if_issue = 1 AND f.product_name IS NOT NULL AND f.product_name <> '' AND date(f.release_time) >= date '2026-06-09' AND date(f.release_time) < date '2026-09-01' AND y.v3_flag = 'V5_3' AND y.android_oldcust_maincreditlevel_charge_v5_3 IS NOT NULL
)
,g AS (
  SELECT date_format(date_trunc('month', date(release_time)), '%Y-%m') AS grp
      ,product_name
      ,CAST(NULL AS INTEGER) AS grade
      ,count(distinct biz_id) AS loans
        ,count(distinct mid)       AS custs
        ,round(sum(contract_amount), 2)  AS ca
        ,round(sum(haircut_amount), 2)   AS ha
        ,round(sum(should_interest), 2)  AS si
        ,round(sum(if(is_e = 1, should_interest / 1.16, should_interest)), 2) AS si_net
        ,sum(if(is_t0_window = 1, 1, 0)) as t0_mature_cnt
      ,sum(if(is_t0_window = 1, t0_should_amt, 0))  as t0_should_amt
      ,sum(if(is_t0_window = 1, t0_overdue_amount, 0)) as t0_overdue_amount
      ,sum(if(is_t0_window = 1 and is_t0_overdue = 1, 1, 0)) as t0_ovd_cnt
      ,sum(if(is_t3_window = 1, 1, 0)) as t3_mature_cnt
      ,sum(if(is_t3_window = 1, t3_should_amt, 0))  as t3_should_amt
      ,sum(if(is_t3_window = 1, t3_overdue_amount, 0)) as t3_overdue_amount
      ,sum(if(is_t3_window = 1 and is_t3_overdue = 1, 1, 0)) as t3_ovd_cnt
      ,sum(if(is_t7_window = 1, 1, 0)) as t7_mature_cnt
      ,sum(if(is_t7_window = 1, t7_should_amt, 0))  as t7_should_amt
      ,sum(if(is_t7_window = 1, t7_overdue_amount, 0)) as t7_overdue_amount
      ,sum(if(is_t7_window = 1 and is_t7_overdue = 1, 1, 0)) as t7_ovd_cnt
      ,sum(if(is_t14_window = 1, 1, 0)) as t14_mature_cnt
      ,sum(if(is_t14_window = 1, t14_should_amt, 0))  as t14_should_amt
      ,sum(if(is_t14_window = 1, t14_overdue_amount, 0)) as t14_overdue_amount
      ,sum(if(is_t14_window = 1 and t14_overdue_amount > 1, 1, 0)) as t14_ovd_cnt
      ,sum(if(is_t30_window = 1, 1, 0)) as t30_mature_cnt
      ,sum(if(is_t30_window = 1, t30_should_amt, 0))  as t30_should_amt
      ,sum(if(is_t30_window = 1, t30_overdue_amount, 0)) as t30_overdue_amount
      ,sum(if(is_t30_window = 1 and is_t30_overdue = 1, 1, 0)) as t30_ovd_cnt
      ,sum(if(is_t7_window = 1, contract_amount, 0))    as t7_mature_ca
      ,sum(if(is_t7_window = 1, haircut_amount, 0))     as t7_mature_ha
      ,sum(if(is_t7_window = 1 and is_e = 1, should_interest / 1.16, if(is_t7_window = 1, should_interest, 0))) as t7_mature_si_net
      ,sum(if(is_t7_window = 1, t7_overdue_amount, 0))  as t7_mature_ovd
  FROM raw
  GROUP BY date_format(date_trunc('month', date(release_time)), '%Y-%m'), product_name

)
SELECT grp, product_name, grade
      ,loans, custs, ca, ha, si, si_net
      ,t0_mature_cnt
      ,t0_should_amt
      ,t0_overdue_amount
      ,t0_ovd_cnt
      ,t3_mature_cnt
      ,t3_should_amt
      ,t3_overdue_amount
      ,t3_ovd_cnt
      ,t7_mature_cnt
      ,t7_should_amt
      ,t7_overdue_amount
      ,t7_ovd_cnt
      ,t14_mature_cnt
      ,t14_should_amt
      ,t14_overdue_amount
      ,t14_ovd_cnt
      ,t30_mature_cnt
      ,t30_should_amt
      ,t30_overdue_amount
      ,t30_ovd_cnt
      ,t7_mature_ca
      ,t7_mature_ha
      ,t7_mature_si_net
      ,t7_mature_ovd
       ,round(CAST(ca AS DOUBLE) / nullif(loans, 0), 2)  as avg_ca
      ,round(CAST(loans AS DOUBLE) / nullif(custs, 0), 4) as loans_cust
      ,round(CAST(ha AS DOUBLE) / nullif(ca, 0), 4)          as ha_rate
      ,round(CAST(si AS DOUBLE) / nullif(ca, 0), 4)          as si_rate
      ,round(CAST(si_net AS DOUBLE) / nullif(ca, 0), 4)      as si_net_rate
      ,round(CAST(ha + si_net AS DOUBLE) / nullif(ca, 0), 4) as fee_net_rate
      ,round(CAST(si_net * 0.16 AS DOUBLE) / nullif(ca, 0), 4) as vat_ca_rate
       ,CAST(NULL AS DOUBLE) AS loans_share_g
      ,CAST(NULL AS DOUBLE) AS ca_share_g
      ,CAST(NULL AS DOUBLE) AS loans_share_p
      ,CAST(NULL AS DOUBLE) AS ca_share_p
      ,round(CAST(t0_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t0_mature_rate,round(CAST(t0_ovd_cnt AS DOUBLE) / nullif(t0_mature_cnt, 0), 4) as t0_cntrate,round(CAST(t0_overdue_amount AS DOUBLE) / nullif(t0_should_amt, 0), 4) as t0_amtrate,round(CAST(t3_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t3_mature_rate,round(CAST(t3_ovd_cnt AS DOUBLE) / nullif(t3_mature_cnt, 0), 4) as t3_cntrate,round(CAST(t3_overdue_amount AS DOUBLE) / nullif(t3_should_amt, 0), 4) as t3_amtrate,round(CAST(t7_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t7_mature_rate,round(CAST(t7_ovd_cnt AS DOUBLE) / nullif(t7_mature_cnt, 0), 4) as t7_cntrate,round(CAST(t7_overdue_amount AS DOUBLE) / nullif(t7_should_amt, 0), 4) as t7_amtrate,round(CAST(t14_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t14_mature_rate,round(CAST(t14_ovd_cnt AS DOUBLE) / nullif(t14_mature_cnt, 0), 4) as t14_cntrate,round(CAST(t14_overdue_amount AS DOUBLE) / nullif(t14_should_amt, 0), 4) as t14_amtrate,round(CAST(t30_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t30_mature_rate,round(CAST(t30_ovd_cnt AS DOUBLE) / nullif(t30_mature_cnt, 0), 4) as t30_cntrate,round(CAST(t30_overdue_amount AS DOUBLE) / nullif(t30_should_amt, 0), 4) as t30_amtrate,round(CAST((t7_mature_ha + t7_mature_si_net - t7_mature_ovd) AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as tr_net7
      ,round(CAST(t7_mature_ovd AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as t7_ovd_amtrate_ca
FROM g
ORDER BY grp, product_name;


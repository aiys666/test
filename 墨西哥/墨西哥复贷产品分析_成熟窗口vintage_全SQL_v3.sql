-- 墨西哥复贷产品分析 v3 全SQL  (与 .py 同一文本, 可独立在 Presto 运行)
-- 口径: 复贷(old)+放款(if_issue=1)+有产品名 2026-05-01~2026-09-01; 税仅对后收利息(E含税÷1.16); 订单级成熟窗口vintage T0/T3/T7/T14/T30
-- 约定镜像参考SQL: 窗口门控 is_t{N}_window=1 / nullif / round(,4); 本端点不支持 GROUPING SETS, 已拆为普通 GROUP BY

-- ==== Q1 月度明细(期×产品) ====
WITH raw AS (
  SELECT product_name
        ,if(substr(product_name, 1, 1) = 'E', 1, 0) AS is_e
        ,camera_id, mid
        ,contract_amount, haircut_amount, should_interest
        ,is_t0_window ,t0_should_amt ,t0_overdue_amount
        ,is_t3_window ,t3_should_amt ,t3_overdue_amount
        ,is_t7_window ,t7_should_amt ,t7_overdue_amount
        ,is_t14_window,t14_should_amt,t14_overdue_amount
        ,is_t30_window,t30_should_amt,t30_overdue_amount
        ,is_t0_overdue,is_t3_overdue,is_t7_overdue,is_t30_overdue
        ,date_format(date_trunc('month', date(release_time)), '%Y-%m') AS grp
  FROM mx.wxs_application_funnel
  WHERE is_reloan = 'old' AND if_issue = 1
    AND product_name IS NOT NULL AND product_name <> ''
    AND date(release_time) >= date '2026-05-01' AND date(release_time) < date '2026-09-01'
)
,g AS (
  SELECT grp, product_name
      ,count(distinct camera_id) AS loans
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
      ,sum(if(is_t7_window = 1, contract_amount, 0))     as t7_mature_ca
      ,sum(if(is_t7_window = 1, haircut_amount, 0))      as t7_mature_ha
      ,sum(if(is_t7_window = 1 and is_e = 1, should_interest / 1.16, if(is_t7_window = 1, should_interest, 0))) as t7_mature_si_net
      ,sum(if(is_t7_window = 1, t7_overdue_amount, 0))   as t7_mature_ovd
  FROM raw
  GROUP BY grp, product_name
)
SELECT grp, product_name
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
      ,round(CAST(loans AS DOUBLE) / nullif(sum(loans) over (partition by grp), 0), 4) as loans_share
      ,round(CAST(ca AS DOUBLE)   / nullif(sum(ca)    over (partition by grp), 0), 4) as ca_share
      ,round(CAST(t0_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t0_mature_rate,round(CAST(t0_ovd_cnt AS DOUBLE) / nullif(t0_mature_cnt, 0), 4) as t0_cntrate,round(CAST(t0_overdue_amount AS DOUBLE) / nullif(t0_should_amt, 0), 4) as t0_amtrate,round(CAST(t3_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t3_mature_rate,round(CAST(t3_ovd_cnt AS DOUBLE) / nullif(t3_mature_cnt, 0), 4) as t3_cntrate,round(CAST(t3_overdue_amount AS DOUBLE) / nullif(t3_should_amt, 0), 4) as t3_amtrate,round(CAST(t7_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t7_mature_rate,round(CAST(t7_ovd_cnt AS DOUBLE) / nullif(t7_mature_cnt, 0), 4) as t7_cntrate,round(CAST(t7_overdue_amount AS DOUBLE) / nullif(t7_should_amt, 0), 4) as t7_amtrate,round(CAST(t14_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t14_mature_rate,round(CAST(t14_ovd_cnt AS DOUBLE) / nullif(t14_mature_cnt, 0), 4) as t14_cntrate,round(CAST(t14_overdue_amount AS DOUBLE) / nullif(t14_should_amt, 0), 4) as t14_amtrate,round(CAST(t30_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t30_mature_rate,round(CAST(t30_ovd_cnt AS DOUBLE) / nullif(t30_mature_cnt, 0), 4) as t30_cntrate,round(CAST(t30_overdue_amount AS DOUBLE) / nullif(t30_should_amt, 0), 4) as t30_amtrate,round(CAST((t7_mature_ha + t7_mature_si_net - t7_mature_ovd) AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as tr_net7
      ,round(CAST(t7_mature_ovd AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as t7_ovd_amtrate_ca
FROM g
ORDER BY grp, product_name;

-- ==== Q2 周度明细(期×产品) ====
WITH raw AS (
  SELECT product_name
        ,if(substr(product_name, 1, 1) = 'E', 1, 0) AS is_e
        ,camera_id, mid
        ,contract_amount, haircut_amount, should_interest
        ,is_t0_window ,t0_should_amt ,t0_overdue_amount
        ,is_t3_window ,t3_should_amt ,t3_overdue_amount
        ,is_t7_window ,t7_should_amt ,t7_overdue_amount
        ,is_t14_window,t14_should_amt,t14_overdue_amount
        ,is_t30_window,t30_should_amt,t30_overdue_amount
        ,is_t0_overdue,is_t3_overdue,is_t7_overdue,is_t30_overdue
        ,date_format(date_trunc('week',  date(release_time)), '%Y-%m-%d') AS grp
  FROM mx.wxs_application_funnel
  WHERE is_reloan = 'old' AND if_issue = 1
    AND product_name IS NOT NULL AND product_name <> ''
    AND date(release_time) >= date '2026-05-01' AND date(release_time) < date '2026-09-01'
)
,g AS (
  SELECT grp, product_name
      ,count(distinct camera_id) AS loans
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
      ,sum(if(is_t7_window = 1, contract_amount, 0))     as t7_mature_ca
      ,sum(if(is_t7_window = 1, haircut_amount, 0))      as t7_mature_ha
      ,sum(if(is_t7_window = 1 and is_e = 1, should_interest / 1.16, if(is_t7_window = 1, should_interest, 0))) as t7_mature_si_net
      ,sum(if(is_t7_window = 1, t7_overdue_amount, 0))   as t7_mature_ovd
  FROM raw
  GROUP BY grp, product_name
)
SELECT grp, product_name
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
      ,round(CAST(loans AS DOUBLE) / nullif(sum(loans) over (partition by grp), 0), 4) as loans_share
      ,round(CAST(ca AS DOUBLE)   / nullif(sum(ca)    over (partition by grp), 0), 4) as ca_share
      ,round(CAST(t0_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t0_mature_rate,round(CAST(t0_ovd_cnt AS DOUBLE) / nullif(t0_mature_cnt, 0), 4) as t0_cntrate,round(CAST(t0_overdue_amount AS DOUBLE) / nullif(t0_should_amt, 0), 4) as t0_amtrate,round(CAST(t3_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t3_mature_rate,round(CAST(t3_ovd_cnt AS DOUBLE) / nullif(t3_mature_cnt, 0), 4) as t3_cntrate,round(CAST(t3_overdue_amount AS DOUBLE) / nullif(t3_should_amt, 0), 4) as t3_amtrate,round(CAST(t7_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t7_mature_rate,round(CAST(t7_ovd_cnt AS DOUBLE) / nullif(t7_mature_cnt, 0), 4) as t7_cntrate,round(CAST(t7_overdue_amount AS DOUBLE) / nullif(t7_should_amt, 0), 4) as t7_amtrate,round(CAST(t14_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t14_mature_rate,round(CAST(t14_ovd_cnt AS DOUBLE) / nullif(t14_mature_cnt, 0), 4) as t14_cntrate,round(CAST(t14_overdue_amount AS DOUBLE) / nullif(t14_should_amt, 0), 4) as t14_amtrate,round(CAST(t30_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t30_mature_rate,round(CAST(t30_ovd_cnt AS DOUBLE) / nullif(t30_mature_cnt, 0), 4) as t30_cntrate,round(CAST(t30_overdue_amount AS DOUBLE) / nullif(t30_should_amt, 0), 4) as t30_amtrate,round(CAST((t7_mature_ha + t7_mature_si_net - t7_mature_ovd) AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as tr_net7
      ,round(CAST(t7_mature_ovd AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as t7_ovd_amtrate_ca
FROM g
ORDER BY grp, product_name;

-- ==== Q3 月度合计(=零差参照) ====
WITH raw AS (
  SELECT product_name
        ,if(substr(product_name, 1, 1) = 'E', 1, 0) AS is_e
        ,camera_id, mid
        ,contract_amount, haircut_amount, should_interest
        ,is_t0_window ,t0_should_amt ,t0_overdue_amount
        ,is_t3_window ,t3_should_amt ,t3_overdue_amount
        ,is_t7_window ,t7_should_amt ,t7_overdue_amount
        ,is_t14_window,t14_should_amt,t14_overdue_amount
        ,is_t30_window,t30_should_amt,t30_overdue_amount
        ,is_t0_overdue,is_t3_overdue,is_t7_overdue,is_t30_overdue
        ,date_format(date_trunc('month', date(release_time)), '%Y-%m') AS grp
  FROM mx.wxs_application_funnel
  WHERE is_reloan = 'old' AND if_issue = 1
    AND product_name IS NOT NULL AND product_name <> ''
    AND date(release_time) >= date '2026-05-01' AND date(release_time) < date '2026-09-01'
)
,g AS (
  SELECT grp
      ,count(distinct camera_id) AS loans
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
      ,sum(if(is_t7_window = 1, contract_amount, 0))     as t7_mature_ca
      ,sum(if(is_t7_window = 1, haircut_amount, 0))      as t7_mature_ha
      ,sum(if(is_t7_window = 1 and is_e = 1, should_interest / 1.16, if(is_t7_window = 1, should_interest, 0))) as t7_mature_si_net
      ,sum(if(is_t7_window = 1, t7_overdue_amount, 0))   as t7_mature_ovd
  FROM raw
  GROUP BY grp
)
SELECT grp, CAST(NULL AS VARCHAR) AS product_name
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
      ,CAST(NULL AS DOUBLE) AS loans_share
      ,CAST(NULL AS DOUBLE) AS ca_share
      ,round(CAST(t0_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t0_mature_rate,round(CAST(t0_ovd_cnt AS DOUBLE) / nullif(t0_mature_cnt, 0), 4) as t0_cntrate,round(CAST(t0_overdue_amount AS DOUBLE) / nullif(t0_should_amt, 0), 4) as t0_amtrate,round(CAST(t3_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t3_mature_rate,round(CAST(t3_ovd_cnt AS DOUBLE) / nullif(t3_mature_cnt, 0), 4) as t3_cntrate,round(CAST(t3_overdue_amount AS DOUBLE) / nullif(t3_should_amt, 0), 4) as t3_amtrate,round(CAST(t7_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t7_mature_rate,round(CAST(t7_ovd_cnt AS DOUBLE) / nullif(t7_mature_cnt, 0), 4) as t7_cntrate,round(CAST(t7_overdue_amount AS DOUBLE) / nullif(t7_should_amt, 0), 4) as t7_amtrate,round(CAST(t14_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t14_mature_rate,round(CAST(t14_ovd_cnt AS DOUBLE) / nullif(t14_mature_cnt, 0), 4) as t14_cntrate,round(CAST(t14_overdue_amount AS DOUBLE) / nullif(t14_should_amt, 0), 4) as t14_amtrate,round(CAST(t30_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t30_mature_rate,round(CAST(t30_ovd_cnt AS DOUBLE) / nullif(t30_mature_cnt, 0), 4) as t30_cntrate,round(CAST(t30_overdue_amount AS DOUBLE) / nullif(t30_should_amt, 0), 4) as t30_amtrate,round(CAST((t7_mature_ha + t7_mature_si_net - t7_mature_ovd) AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as tr_net7
      ,round(CAST(t7_mature_ovd AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as t7_ovd_amtrate_ca
FROM g
ORDER BY grp, product_name;

-- ==== Q4 周度合计(=零差参照) ====
WITH raw AS (
  SELECT product_name
        ,if(substr(product_name, 1, 1) = 'E', 1, 0) AS is_e
        ,camera_id, mid
        ,contract_amount, haircut_amount, should_interest
        ,is_t0_window ,t0_should_amt ,t0_overdue_amount
        ,is_t3_window ,t3_should_amt ,t3_overdue_amount
        ,is_t7_window ,t7_should_amt ,t7_overdue_amount
        ,is_t14_window,t14_should_amt,t14_overdue_amount
        ,is_t30_window,t30_should_amt,t30_overdue_amount
        ,is_t0_overdue,is_t3_overdue,is_t7_overdue,is_t30_overdue
        ,date_format(date_trunc('week',  date(release_time)), '%Y-%m-%d') AS grp
  FROM mx.wxs_application_funnel
  WHERE is_reloan = 'old' AND if_issue = 1
    AND product_name IS NOT NULL AND product_name <> ''
    AND date(release_time) >= date '2026-05-01' AND date(release_time) < date '2026-09-01'
)
,g AS (
  SELECT grp
      ,count(distinct camera_id) AS loans
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
      ,sum(if(is_t7_window = 1, contract_amount, 0))     as t7_mature_ca
      ,sum(if(is_t7_window = 1, haircut_amount, 0))      as t7_mature_ha
      ,sum(if(is_t7_window = 1 and is_e = 1, should_interest / 1.16, if(is_t7_window = 1, should_interest, 0))) as t7_mature_si_net
      ,sum(if(is_t7_window = 1, t7_overdue_amount, 0))   as t7_mature_ovd
  FROM raw
  GROUP BY grp
)
SELECT grp, CAST(NULL AS VARCHAR) AS product_name
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
      ,CAST(NULL AS DOUBLE) AS loans_share
      ,CAST(NULL AS DOUBLE) AS ca_share
      ,round(CAST(t0_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t0_mature_rate,round(CAST(t0_ovd_cnt AS DOUBLE) / nullif(t0_mature_cnt, 0), 4) as t0_cntrate,round(CAST(t0_overdue_amount AS DOUBLE) / nullif(t0_should_amt, 0), 4) as t0_amtrate,round(CAST(t3_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t3_mature_rate,round(CAST(t3_ovd_cnt AS DOUBLE) / nullif(t3_mature_cnt, 0), 4) as t3_cntrate,round(CAST(t3_overdue_amount AS DOUBLE) / nullif(t3_should_amt, 0), 4) as t3_amtrate,round(CAST(t7_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t7_mature_rate,round(CAST(t7_ovd_cnt AS DOUBLE) / nullif(t7_mature_cnt, 0), 4) as t7_cntrate,round(CAST(t7_overdue_amount AS DOUBLE) / nullif(t7_should_amt, 0), 4) as t7_amtrate,round(CAST(t14_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t14_mature_rate,round(CAST(t14_ovd_cnt AS DOUBLE) / nullif(t14_mature_cnt, 0), 4) as t14_cntrate,round(CAST(t14_overdue_amount AS DOUBLE) / nullif(t14_should_amt, 0), 4) as t14_amtrate,round(CAST(t30_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t30_mature_rate,round(CAST(t30_ovd_cnt AS DOUBLE) / nullif(t30_mature_cnt, 0), 4) as t30_cntrate,round(CAST(t30_overdue_amount AS DOUBLE) / nullif(t30_should_amt, 0), 4) as t30_amtrate,round(CAST((t7_mature_ha + t7_mature_si_net - t7_mature_ovd) AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as tr_net7
      ,round(CAST(t7_mature_ovd AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as t7_ovd_amtrate_ca
FROM g
ORDER BY grp, product_name;

-- ==== Q5 产品全期合计 ====
WITH raw AS (
  SELECT product_name
        ,if(substr(product_name, 1, 1) = 'E', 1, 0) AS is_e
        ,camera_id, mid
        ,contract_amount, haircut_amount, should_interest
        ,is_t0_window ,t0_should_amt ,t0_overdue_amount
        ,is_t3_window ,t3_should_amt ,t3_overdue_amount
        ,is_t7_window ,t7_should_amt ,t7_overdue_amount
        ,is_t14_window,t14_should_amt,t14_overdue_amount
        ,is_t30_window,t30_should_amt,t30_overdue_amount
        ,is_t0_overdue,is_t3_overdue,is_t7_overdue,is_t30_overdue
        ,date_format(date_trunc('month', date(release_time)), '%Y-%m') AS grp
  FROM mx.wxs_application_funnel
  WHERE is_reloan = 'old' AND if_issue = 1
    AND product_name IS NOT NULL AND product_name <> ''
    AND date(release_time) >= date '2026-05-01' AND date(release_time) < date '2026-09-01'
)
,g AS (
  SELECT product_name
      ,count(distinct camera_id) AS loans
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
      ,sum(if(is_t7_window = 1, contract_amount, 0))     as t7_mature_ca
      ,sum(if(is_t7_window = 1, haircut_amount, 0))      as t7_mature_ha
      ,sum(if(is_t7_window = 1 and is_e = 1, should_interest / 1.16, if(is_t7_window = 1, should_interest, 0))) as t7_mature_si_net
      ,sum(if(is_t7_window = 1, t7_overdue_amount, 0))   as t7_mature_ovd
  FROM raw
  GROUP BY product_name
)
SELECT CAST(NULL AS VARCHAR) AS grp, product_name
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
      ,CAST(NULL AS DOUBLE) AS loans_share
      ,CAST(NULL AS DOUBLE) AS ca_share
      ,round(CAST(t0_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t0_mature_rate,round(CAST(t0_ovd_cnt AS DOUBLE) / nullif(t0_mature_cnt, 0), 4) as t0_cntrate,round(CAST(t0_overdue_amount AS DOUBLE) / nullif(t0_should_amt, 0), 4) as t0_amtrate,round(CAST(t3_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t3_mature_rate,round(CAST(t3_ovd_cnt AS DOUBLE) / nullif(t3_mature_cnt, 0), 4) as t3_cntrate,round(CAST(t3_overdue_amount AS DOUBLE) / nullif(t3_should_amt, 0), 4) as t3_amtrate,round(CAST(t7_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t7_mature_rate,round(CAST(t7_ovd_cnt AS DOUBLE) / nullif(t7_mature_cnt, 0), 4) as t7_cntrate,round(CAST(t7_overdue_amount AS DOUBLE) / nullif(t7_should_amt, 0), 4) as t7_amtrate,round(CAST(t14_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t14_mature_rate,round(CAST(t14_ovd_cnt AS DOUBLE) / nullif(t14_mature_cnt, 0), 4) as t14_cntrate,round(CAST(t14_overdue_amount AS DOUBLE) / nullif(t14_should_amt, 0), 4) as t14_amtrate,round(CAST(t30_mature_cnt AS DOUBLE) / nullif(loans, 0), 4)  as t30_mature_rate,round(CAST(t30_ovd_cnt AS DOUBLE) / nullif(t30_mature_cnt, 0), 4) as t30_cntrate,round(CAST(t30_overdue_amount AS DOUBLE) / nullif(t30_should_amt, 0), 4) as t30_amtrate,round(CAST((t7_mature_ha + t7_mature_si_net - t7_mature_ovd) AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as tr_net7
      ,round(CAST(t7_mature_ovd AS DOUBLE) / nullif(t7_mature_ca, 0), 4) as t7_ovd_amtrate_ca
FROM g
ORDER BY grp, product_name;

-- ==== Q6 yj_test_table 交叉(参考t1d0/t1d3) ====
select date_format(date_trunc('month', date(release_time)), '%Y-%m') as grp,
       product_name_new as product_name,
       count(*) as cnt,
       round(sum(t0_overdue_amount_1)/nullif(sum(t0_should_amt_1),0), 4) as t1d0_amtrate,
       round(avg(case when is_t0_window_1 = 1 then is_t0_overdue_1 end), 4) as t1d0_cntrate,
       round(sum(t3_overdue_amount_1)/nullif(sum(t3_should_amt_1),0), 4) as t1d3_amtrate,
       round(avg(case when is_t3_window_1 = 1 then is_t3_overdue_1 end), 4) as t1d3_cntrate
from mx.yj_test_table_250225
where 1 = 1
  and product_name_new is not null and product_name_new <> ''
  and date(release_time) >= date '2026-05-01' and date(release_time) < date '2026-09-01'
group by 1, 2
order by 1, 2;


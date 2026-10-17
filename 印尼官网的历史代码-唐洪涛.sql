
DROP TABLE IF EXISTS tmp.tmp_tkb_info ;
CREATE TABLE tmp.tmp_tkb_info as
SELECT  current_date- interval '1' day AS data_date
       ,SUM(CASE WHEN a.lid_status_code = 2 AND c.outstanding > 0 THEN cast(0 AS decimal(38,6)) WHEN (date_diff('day',coalesce(tl.unpaid_due_date,date'2099-01-01'),current_date- interval '1' day) > 90 AND a.lid_status_code NOT IN (1,2)) THEN cast(0 AS decimal(38,6)) ELSE c.outstanding END) os_90
       ,SUM(CASE WHEN a.lid_status_code = 2 AND c.outstanding > 0 THEN cast(0 AS decimal(38,6)) WHEN (date_diff('day',coalesce(tl.unpaid_due_date,date'2099-01-01'),current_date- interval '1' day) > 60 AND a.lid_status_code NOT IN (1,2)) THEN cast(0 AS decimal(38,6)) ELSE c.outstanding END) os_60
       ,SUM(CASE WHEN a.lid_status_code = 2 AND c.outstanding > 0 THEN cast(0 AS decimal(38,6)) WHEN (date_diff('day',coalesce(tl.unpaid_due_date,date'2099-01-01'),current_date- interval '1' day) > 30 AND a.lid_status_code NOT IN (1,2)) THEN cast(0 AS decimal(38,6)) ELSE c.outstanding END) os_30
       ,SUM(CASE WHEN a.lid_status_code = 2 AND c.outstanding > 0 THEN cast(0 AS decimal(38,6)) WHEN (date_diff('day',coalesce(tl.unpaid_due_date,date'2099-01-01'),current_date- interval '1' day) > 0 AND a.lid_status_code NOT IN (1,2)) THEN cast(0 AS decimal(38,6)) ELSE c.outstanding END) os_0
       ,SUM(CASE WHEN a.lid_status_code = 2 AND c.outstanding > 0 THEN cast(0 AS decimal(38,6)) WHEN date_diff('day',coalesce(tl.unpaid_due_date,date'2099-01-01'),current_date- interval '1' day) > 90 THEN cast(0 AS decimal(38,6)) else c.outstanding END) AS os_tkb_90
       ,SUM(CASE WHEN a.lid_status_code = 2 AND c.outstanding > 0 THEN cast(0 AS decimal(38,6)) WHEN date_diff('day',coalesce(tl.unpaid_due_date,date'2099-01-01'),current_date- interval '1' day) > 60 THEN cast(0 AS decimal(38,6)) else c.outstanding END) AS os_tkb_60
       ,SUM(CASE WHEN a.lid_status_code = 2 AND c.outstanding > 0 THEN cast(0 AS decimal(38,6)) WHEN date_diff('day',coalesce(tl.unpaid_due_date,date'2099-01-01'),current_date- interval '1' day) > 30 THEN cast(0 AS decimal(38,6)) else c.outstanding END) AS os_tkb_30
       ,SUM(CASE WHEN a.lid_status_code = 2 AND c.outstanding > 0 THEN cast(0 AS decimal(38,6)) WHEN date_diff('day',coalesce(tl.unpaid_due_date,date'2099-01-01'),current_date- interval '1' day) > 0 THEN cast(0 AS decimal(38,6)) else c.outstanding END) AS os_tkb_0
       ,SUM(CASE WHEN a.lid_status_code = 2 AND c.outstanding > 0 THEN cast(0 AS decimal(38,6)) WHEN date_diff('day',coalesce(tl.unpaid_due_date,date'2099-01-01'),current_date- interval '1' day) > 90 THEN c.outstanding else cast(0 AS decimal(38,6)) END) AS os_tkb_above90_new
       ,SUM(CASE WHEN a.lid_status_code = 2 AND c.outstanding > 0 THEN cast(0 AS decimal(38,6)) WHEN date_diff('day',coalesce(tl.unpaid_due_date,date'2099-01-01'),current_date- interval '1' day) between 61 and 90 THEN c.outstanding else cast(0 AS decimal(38,6)) END) AS os_tkb_90_new
       ,SUM(CASE WHEN a.lid_status_code = 2 AND c.outstanding > 0 THEN cast(0 AS decimal(38,6)) WHEN date_diff('day',coalesce(tl.unpaid_due_date,date'2099-01-01'),current_date- interval '1' day) between 31 and 60 THEN c.outstanding else cast(0 AS decimal(38,6)) END) AS os_tkb_60_new
       ,SUM(CASE WHEN a.lid_status_code = 2 AND c.outstanding > 0 THEN cast(0 AS decimal(38,6)) WHEN date_diff('day',coalesce(tl.unpaid_due_date,date'2099-01-01'),current_date- interval '1' day) between 1 and 30 THEN c.outstanding else cast(0 AS decimal(38,6)) END) AS os_tkb_30_new
       ,SUM(CASE WHEN a.lid_status_code = 2 AND c.outstanding > 0 THEN cast(0 AS decimal(38,6)) WHEN date_diff('day',coalesce(tl.unpaid_due_date,date'2099-01-01'),current_date- interval '1' day) <= 0 THEN c.outstanding else cast(0 AS decimal(38,6)) END) AS os_tkb_0_new
       ,SUM(CASE WHEN a.lid_status_code = 2 AND c.outstanding > 0 THEN cast(0 AS decimal(38,6))  else c.outstanding  END) AS os_total_outstanding_amt
FROM
(
    SELECT  a.release_time
           ,a.lid
           ,a.customer_id
           ,CASE WHEN date(a.finish_time) > current_date- interval '1' day THEN 1  ELSE a.state END AS lid_status_code
    FROM ods.s02_loan a
    WHERE date(a.release_time) <= current_date- interval '1' day and a.state<>15
) a
INNER JOIN
(
    SELECT  t.lid
           ,t.should_capital-t.fact_capital AS outstanding
           ,t.fact_capital
    FROM
    (
        SELECT  t1.lid
               ,SUM(t1.should_capital)                            AS should_capital
               ,SUM(t1.fact_capital -coalesce(t2.fact_capital,0)) AS fact_capital
               ,SUM(fact_penalty)                                 AS fact_penalty
        FROM
        (
            SELECT  lid
                   ,rid
                   ,should_capital
                   ,fact_capital
                   ,CASE WHEN date(lr.fact_time) <= current_date- interval '1' day THEN lr.should_fine + lr.should_overdue_fee  ELSE 0 END AS fact_penalty
            FROM ods.s02_loan_repayment lr
        )t1
        LEFT JOIN
        (
            SELECT  rid
                   ,SUM(fact_capital) AS fact_capital
            FROM ods.s02_loan_repayment_detail
            WHERE date(fact_time) > current_date- interval '1' day
            GROUP BY  1
        )t2
        ON t1.rid = t2.rid
        GROUP BY  1
    )t
) c
ON a.lid = c.lid
LEFT JOIN
(
    SELECT  lr.lid
           ,MIN(date(should_time)) AS unpaid_due_date
    FROM ods.s02_loan_repayment lr
    WHERE fact_time is null or date(fact_time) > current_date- interval '1' day
    GROUP BY  1
) tl
ON c.lid = tl.lid
GROUP BY  1;




DROP TABLE IF EXISTS tmp.tmp_loan_summary_info ;
CREATE TABLE tmp.tmp_loan_summary_info as
SELECT  COUNT(1)  AS his_loan_cnt
       ,COUNT(case WHEN release_time >= date_trunc('year',current_date - interval '1' day) THEN 1 else null end)  AS curr_year_loan_cnt
       ,COUNT(case WHEN date(release_time) = current_date - interval '1'day THEN 1 else null end)  AS curr_day_loan_cnt
       ,COUNT(distinct identity_num) AS his_loan_ktp_cnt
       ,COUNT(distinct case WHEN release_time >= date_trunc('year',current_date - interval '1' day) THEN identity_num else null end)  AS curr_year_loan_ktp_cnt
       ,COUNT(distinct case WHEN date(release_time) = current_date - interval '1'day THEN identity_num else null end)  AS curr_day_loan_ktp_cnt
       ,SUM(contract_amt) AS his_contract_amt
       ,SUM(case WHEN release_time >= date_trunc('year',current_date - interval '1' day) THEN contract_amt else 0 end) AS curr_year_contract_amt
       ,SUM(case WHEN date(release_time) = current_date - interval '1'day THEN contract_amt else 0 end)                                      AS curr_day_contract_amt
       ,sum(case when l.lid_status_code in(1,2,15) then contract_amt else 0 end) AS his_contract_amt_no_writeoff
       ,SUM(case WHEN release_time >= date_trunc('year',current_date - interval '1' day) and l.lid_status_code in(1,2,15) THEN contract_amt else 0 end) AS curr_year_contract_amt_no_writeoff
       ,SUM(case WHEN date(release_time) = current_date - interval '1'day and l.lid_status_code in(1,2,15) THEN contract_amt else 0 end)                                      AS curr_day_contract_amt_no_writeoff
FROM dwd.dwd_loan_info l
JOIN dwd.dwd_mem_info m
ON l.mid = m.mid
WHERE lid_status_code IN (1,2,15);

DROP TABLE IF EXISTS tmp.tmp_repayment_summary_info ;
CREATE TABLE tmp.tmp_repayment_summary_info AS
SELECT  SUM(fact_capital)                                                                                                                        AS his_fact_capital
       ,SUM(case WHEN release_time >= date_trunc('year',current_date- interval '1' day) THEN fact_capital else 0 end)                               AS curr_year_fact_capital
       ,SUM(case WHEN date(release_time) = current_date - interval '1'day THEN fact_capital else 0 end)                                                                    AS curr_day_fact_capital
       ,SUM(case WHEN l.lid_status_code in(1,2) THEN fact_capital else 0 end)                                                                    AS his_fact_capital_no_writeoff
       ,SUM(case WHEN release_time >= date_trunc('year',current_date- interval '1' day) AND l.lid_status_code in(1,2) THEN fact_capital else 0 end) AS curr_year_fact_capital_no_writeoff
       ,SUM(case WHEN date(release_time ) = current_date - interval '1'day AND l.lid_status_code in(1,2) THEN fact_capital else 0 end)                                      AS curr_day_fact_capital_no_writeoff
FROM dwd.dwd_repayment_detail lr
JOIN dwd.dwd_loan_info l
ON lr.lid = l.lid
;

DROP TABLE IF EXISTS tmp.tmp_lend_summary_info ;
CREATE TABLE tmp.tmp_lend_summary_info AS
SELECT  COUNT(distinct ld.lend_customer_id) as total_lender
       ,COUNT(distinct case WHEN ld.buy_time >= date_trunc('year',current_date - interval '1'day) THEN ld.lend_customer_id else null end) AS lender_current_year
       ,COUNT(distinct case WHEN date(ld.buy_time) = current_date - interval '1'day THEN ld.lend_customer_id else null end)  AS lender_current_day
FROM ods.s02_loan l
JOIN ods.s02_lend ld
ON ld.camera_id = l.camera_id
WHERE l.state IN (1, 2)
;

delete from dws.dws_loan_banner_summary ;
insert into dws.dws_loan_banner_summary 
--insert into tmp.tmp_loan_banner_summary
SELECT  t1.data_date        
       ,t1.os_90            
       ,t1.os_60            
       ,t1.os_30            
       ,t1.os_0             
       ,t1.os_tkb_90        
       ,t1.os_tkb_60        
       ,t1.os_tkb_30        
       ,t1.os_tkb_0 
       ,t2.his_loan_cnt as total_loan_transaction
       ,t2.curr_year_loan_cnt as loan_transaction_current_year
       ,t2.curr_day_loan_cnt as loan_transaction_current_day
       ,t2.his_loan_ktp_cnt as total_unique_borrower
       ,t2.curr_year_loan_ktp_cnt as unique_borrower_current_year
       ,t2.curr_day_loan_ktp_cnt as unique_borrower_current_day
       ,t2.his_contract_amt as total_disburs
       ,t2.curr_year_contract_amt as disburs_current_year
       ,t2.curr_day_contract_amt as disburs_current_day
       ,t3.his_fact_capital    as total_repayment  
       ,t3.curr_year_fact_capital as repayment_current_year
       ,t3.curr_day_fact_capital  as repayment_current_day
       ,t2.his_contract_amt_no_writeoff-t3.his_fact_capital_no_writeoff as os
       ,t2.curr_year_contract_amt_no_writeoff-t3.curr_year_fact_capital_no_writeoff as os_current_year
       ,t2.curr_day_contract_amt_no_writeoff-t3.curr_day_fact_capital_no_writeoff as os_current_day
       ,t4.*
       ,t1.os_tkb_90_new
       ,t1.os_tkb_60_new
       ,t1.os_tkb_30_new
       ,t1.os_tkb_0_new
       ,t1.os_tkb_above90_new
       ,t1.os_total_outstanding_amt
FROM tmp.tmp_tkb_info t1
CROSS JOIN tmp.tmp_loan_summary_info t2
CROSS JOIN tmp.tmp_repayment_summary_info t3
CROSS JOIN tmp.tmp_lend_summary_info t4;

delete from dws.dws_loan_banner_summary_his where etl_date='$etl_date';
insert into dws.dws_loan_banner_summary_his select *,'$etl_date' from dws.dws_loan_banner_summary;

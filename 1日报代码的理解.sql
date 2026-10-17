/* ===================================================
 * 印尼现金贷：还款行为分析核心看板
 * 功能：计算每日/周/月的还款表现指标（逾期率/催回率）
 * 关键表： 
 *   - ods.s02_loan_repayment（还款计划明细）
 *   - dwd.dwd_order_info（订单宽表）
 *   - ind.my_all_apply_tags_01（用户标签表）
 * =================================================== */
 
SELECT
  should_date,                          -- 【还款计划】应还款日期
  SUBSTRING(TO_CHAR(should_date, 'yyyy-mm-dd'), 1, 7) AS date_mon,  -- 月份（yyyy-mm）
  TO_CHAR(DATE_TRUNC('week', should_date), 'yyyy-mm-dd') AS date_week, -- 周起始日（周一）
  index AS repayment_index,             -- 【还款计划】还款期次（第几期）
  product_name,                         -- 【订单宽表】产品名称
  a.tenant_id,                          -- 【还款计划】租户ID（独立业务实体标识）
  double_loan,                          -- 【用户标签】贷款类型（0=首贷, 1=复贷）
  CASE 
    WHEN app_channel = '850792dc-e673-4131-8d0f-b0a70b2772be' THEN 'Samir' 
    ELSE 'Other' 
  END AS app_channel,                   -- 【订单宽表】APP渠道（Samir为自营渠道）
  
  -- ========== 本金指标 ==========
  d0, d3, d7, d14, d30,                -- 各时段应还本金（D+0/D+3/...）
  t0, t3, t7, t14, t30,                 -- 各时段逾期本金（T+0/T+3/...）
  fact_amount_t0_midtrans,              -- Midtrans通道实还本金（线上支付）
  fact_amount_t0_offline,               -- 线下实还本金（现金/银行柜台）
  
  -- ========== 还款行为统计 ==========
  tm30_cnt, tm14_cnt, tm7_cnt, tm3_cnt, tm1_cnt, t0_cnt, -- 不同逾期天数内还款人数
  loan_cnt_end,                         -- 当期结束的贷款总笔数
  tm30_amount, tm14_amount, tm7_amount, tm3_amount, tm1_amount, t0_amount, -- 不同逾期天数内还款金额
  loan_amount,                          -- 当期总应还本金
  source                                -- 【用户标签】数据来源标记

FROM (
  SELECT
    should_date,
    dayss,                              -- 星期几（0=周一, 6=周日）
    index AS repayment_index,
    a.tenant_id,
    a.reloan_tag AS double_loan,        -- 首复贷标识（0/1）
    product_name,
    app_channel,                        -- APP渠道ID
    source,                             -- 用户来源渠道
    
    -- ===== 支付通道实还金额 =====
    /* Midtrans通道T+0还款（线上支付） */
    SUM(CASE 
          WHEN fact_date <= should_date 
               AND should_date < CURRENT_DATE 
               AND channel_id = 16      -- 通道ID=16为Midtrans 
          THEN fact_capital 
        END) AS fact_amount_t0_midtrans,
    
    /* 线下还款（无通道记录） */
    SUM(CASE 
          WHEN fact_date IS NULL 
               AND should_date < CURRENT_DATE 
               AND channel_id IS NULL 
          THEN fact_capital 
        END) AS fact_amount_t0_offline,
    
    -- ===== 应还本金累积 =====
    SUM(CASE WHEN should_date < CURRENT_DATE THEN should_capital END) AS d0,
    SUM(CASE WHEN DATE_DIFF('day', should_date, CURRENT_DATE) > 3 THEN should_capital END) AS d3,
    SUM(CASE WHEN DATE_DIFF('day', should_date, CURRENT_DATE) > 7 THEN should_capital END) AS d7,
    SUM(CASE WHEN DATE_DIFF('day', should_date, CURRENT_DATE) > 14 THEN should_capital END) AS d14,
    SUM(CASE WHEN DATE_DIFF('day', should_date, CURRENT_DATE) > 30 THEN should_capital END) AS d30,
    
    -- ===== 逾期本金计算 =====
    /* T+0逾期 = 应还未还 */
    (SUM(CASE WHEN should_date < CURRENT_DATE THEN should_capital END) - 
     SUM(CASE WHEN fact_date <= should_date AND should_date < CURRENT_DATE THEN fact_capital END)
    ) AS t0,
    
    /* T+3逾期 = D+3应还 - 3天内已还 */
    (SUM(CASE WHEN DATE_DIFF('day', should_date, CURRENT_DATE) > 3 THEN should_capital END) - 
     SUM(CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 3 
                   AND DATE_DIFF('day', should_date, CURRENT_DATE) > 3 
              THEN fact_capital END)
    ) AS t3,
    
    -- T+7/T+14/T+30计算逻辑同上...
    
    -- ===== 还款人数统计 =====
    COUNT(DISTINCT camera_id) AS loan_cnt_end,  -- 当期总贷款数
    /* 不同逾期天数内的还款人数 */
    COUNT(DISTINCT CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 30 THEN camera_id END) AS tm30_cnt,
    COUNT(DISTINCT CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 14 THEN camera_id END) AS tm14_cnt,
    COUNT(DISTINCT CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 7 THEN camera_id END) AS tm7_cnt,
    COUNT(DISTINCT CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 3 THEN camera_id END) AS tm3_cnt,
    COUNT(DISTINCT CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 1 THEN camera_id END) AS tm1_cnt,
    COUNT(DISTINCT CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 0 THEN camera_id END) AS t0_cnt,
    
    -- ===== 还款金额统计 =====
    SUM(should_capital) AS loan_amount,  -- 总应还本金
    /* 不同逾期天数内的还款金额 */
    SUM(CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 30 THEN fact_capital END) AS tm30_amount,
    SUM(CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 14 THEN fact_capital END) AS tm14_amount,
    SUM(CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 7 THEN fact_capital END) AS tm7_amount,
    SUM(CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 3 THEN fact_capital END) AS tm3_amount,
    SUM(CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 1 THEN fact_capital END) AS tm1_amount,
    SUM(CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 0 THEN fact_capital END) AS t0_amount
    
  FROM (
    -- ===== 基础数据准备 =====
    SELECT
      a.rid,                            -- 还款计划唯一ID
      a.tenant_id,                      
      a.camera_id,                       -- 进件标识（关联订单）
      a.indexs,                          -- 还款期次
      a.should_time,                     -- 应还款时间
      a.fact_time,                       -- 实际还款时间
      a.should_capital,                  -- 应还本金
      a.fact_capital,                    -- 实还本金
      c.reloan_tag,                      -- 首复贷标签（0/1）
      b.product_name,                    -- 产品名称
      b.app_channel,                     -- APP渠道ID
      DATE(a.should_time) AS should_date,
      a.indexs AS repayment_index,
      DATE(a.fact_time) AS fact_date,
      
      /* 星期几数字映射 */
      CASE 
        WHEN DAY_OF_WEEK(a.should_time) = 1 THEN 0  -- 周日=0
        WHEN DAY_OF_WEEK(a.should_time) = 2 THEN 1  -- 周一=1
        ... -- 完整映射
      END AS dayss,
      
      c.source                           -- 用户来源
    FROM ods.s02_loan_repayment a        -- 还款计划表
    INNER JOIN dwd.dwd_order_info b      -- 订单宽表
      ON TRY_CAST(a.camera_id AS BIGINT) = TRY_CAST(b.order_no AS BIGINT)  -- 通过进件标识关联订单
    LEFT JOIN ind.my_all_apply_tags_01 c -- 用户标签表
      ON TRY_CAST(a.camera_id AS BIGINT) = c.biz_id
    WHERE DATE(a.should_time) >= DATE('2022-01-01')  -- 取2022年后数据
  ) base
  LEFT JOIN (                            -- 还款通道表
    SELECT rid, channel_id 
    FROM ods.s02_loan_repayment_detail
  ) channel ON base.rid = channel.rid
  GROUP BY 1, 2, 3, 4, 5, 6, 7, 8       -- 按日期/期次/产品/租户等分组
) agg;










二、现金贷核心风控引擎​​
/* ===================================================================
 * 印尼现金贷：还款行为分析核心模块
 * 功能：计算本金与利息维度的还款表现指标（逾期率/催回率）
 * 包含两张表：
 *   1. ind.my_repayment_detail        - 本金指标分析
 *   2. ind.my_repayment_detail_02     - 利息指标分析
 * 关键业务逻辑：
 *   - 按日/周/月聚合还款表现
 *   - 区分线上线下还款渠道
 *   - 动态计算不同逾期窗口的指标
 * =================================================================== */

-- ================================================================================
-- 表1：本金指标分析表 (ind.my_repayment_detail)
-- 核心指标：应还本金、实还本金、逾期本金、不同逾期窗口还款人数/金额
-- ================================================================================
SELECT
  should_date,                          -- 【应还款日期】
  SUBSTRING(TO_CHAR(should_date, 'yyyy-mm-dd'), 1, 7) AS date_mon,  -- 月份（yyyy-mm）
  TO_CHAR(DATE_TRUNC('week', should_date), 'yyyy-mm-dd') AS date_week, -- 周起始日
  index AS repayment_index,             -- 【还款期次】
  product_name,                         -- 【产品名称】
  tenant_id,                            -- 【租户ID】
  double_loan,                          -- 【贷款类型】0=首贷,1=复贷
  CASE 
    WHEN app_channel = '850792dc-e673-4131-8d0f-b0a70b2772be' THEN 'Samir' 
    ELSE 'Other' 
  END AS app_channel,                   -- 【APP渠道】
  
  -- ========== 本金指标 ==========
  d0, d3, d7, d14, d30,                -- 各时段应还本金（D+0/D+3/...）
  t0, t3, t7, t14, t30,                 -- 各时段逾期本金（T+0/T+3/...）
  fact_amount_t0_midtrans,              -- Midtrans通道实还本金（线上）
  fact_amount_t0_offline,               -- 线下实还本金
  
  -- ========== 还款行为统计 ==========
  tm30_cnt, tm14_cnt, tm7_cnt, tm3_cnt, tm1_cnt, t0_cnt, -- 不同逾期天数内还款人数
  loan_cnt_end,                         -- 当期结束贷款总数
  tm30_amount, tm14_amount, tm7_amount, tm3_amount, tm1_amount, t0_amount, -- 不同逾期天数内还款金额
  loan_amount,                          -- 总应还本金
  source                                -- 数据来源标记
FROM (
  SELECT
    should_date,
    dayss,                              -- 星期几（0=周一,6=周日）
    index,
    tenant_id,
    a.reloan_tag AS double_loan,
    product_name,
    app_channel,
    source,
    
    -- ===== 支付通道实还金额 =====
    /* Midtrans通道T0还款（线上支付） */
    SUM(CASE 
          WHEN fact_date <= should_date 
               AND should_date < CURRENT_DATE 
               AND channel_id = 16  -- 通道ID=16为Midtrans
          THEN fact_capital 
        END) AS fact_amount_t0_midtrans,
    
    /* 线下还款（无通道记录） */
    SUM(CASE 
          WHEN fact_date IS NULL 
               AND should_date < CURRENT_DATE 
               AND channel_id IS NULL 
          THEN fact_capital 
        END) AS fact_amount_t0_offline,
    
    -- ===== 应还本金累积 =====
    SUM(CASE WHEN should_date < CURRENT_DATE THEN should_capital END) AS d0,
    SUM(CASE WHEN DATE_DIFF('day', should_date, CURRENT_DATE) > 3 THEN should_capital END) AS d3,
    SUM(CASE WHEN DATE_DIFF('day', should_date, CURRENT_DATE) > 7 THEN should_capital END) AS d7,
    SUM(CASE WHEN DATE_DIFF('day', should_date, CURRENT_DATE) > 14 THEN should_capital END) AS d14,
    SUM(CASE WHEN DATE_DIFF('day', should_date, CURRENT_DATE) > 30 THEN should_capital END) AS d30,
    
    -- ===== 逾期本金计算 =====
    /* T0逾期 = 应还未还 */
    (SUM(CASE WHEN should_date < CURRENT_DATE THEN should_capital END) - 
     SUM(CASE WHEN fact_date <= should_date AND should_date < CURRENT_DATE THEN fact_capital END)
    ) AS t0,
    
    /* T3逾期 = D3应还 - 3天内已还 */
    (SUM(CASE WHEN DATE_DIFF('day', should_date, CURRENT_DATE) > 3 THEN should_capital END) - 
     SUM(CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 3 
                   AND DATE_DIFF('day', should_date, CURRENT_DATE) > 3 
              THEN fact_capital END)
    ) AS t3,
    
    -- T7/T14/T30逾期计算逻辑同上...
    
    -- ===== 还款人数统计 =====
    COUNT(DISTINCT camera_id) AS loan_cnt_end,
    COUNT(DISTINCT CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 30 THEN camera_id END) AS tm30_cnt,
    COUNT(DISTINCT CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 14 THEN camera_id END) AS tm14_cnt,
    COUNT(DISTINCT CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 7 THEN camera_id END) AS tm7_cnt,
    COUNT(DISTINCT CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 3 THEN camera_id END) AS tm3_cnt,
    COUNT(DISTINCT CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 1 THEN camera_id END) AS tm1_cnt,
    COUNT(DISTINCT CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 0 THEN camera_id END) AS t0_cnt,
    
    -- ===== 还款金额统计 =====
    SUM(should_capital) AS loan_amount,
    SUM(CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 30 THEN fact_capital END) AS tm30_amount,
    SUM(CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 14 THEN fact_capital END) AS tm14_amount,
    SUM(CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 7 THEN fact_capital END) AS tm7_amount,
    SUM(CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 3 THEN fact_capital END) AS tm3_amount,
    SUM(CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 1 THEN fact_capital END) AS tm1_amount,
    SUM(CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 0 THEN fact_capital END) AS t0_amount
    
  FROM (
    -- ===== 基础数据准备 =====
    SELECT
      a.*,                              -- 还款计划基础字段
      c.reloan_tag,                     -- 首复贷标签
      b.apply_period_code AS product_name, -- 产品名称
      DATE(a.should_time) AS should_date,
      a.indexs AS index,                -- 还款期次
      DATE(a.fact_time) AS fact_date,    -- 实际还款日期
      
      /* 星期几数字映射（0=周一,6=周日） */
      CASE 
        WHEN DAY_OF_WEEK(a.should_time) = 1 THEN 0 
        WHEN DAY_OF_WEEK(a.should_time) = 2 THEN 1 
        WHEN DAY_OF_WEEK(a.should_time) = 3 THEN 2 
        WHEN DAY_OF_WEEK(a.should_time) = 4 THEN 3 
        WHEN DAY_OF_WEEK(a.should_time) = 5 THEN 4 
        WHEN DAY_OF_WEEK(a.should_time) = 6 THEN 5 
        ELSE 6 
      END AS dayss,
      
      c.source                          -- 数据来源
    FROM ods.s02_loan_repayment a        -- 还款计划表
    INNER JOIN dwd.dwd_order_info b     -- 订单宽表
      ON TRY_CAST(a.camera_id AS BIGINT) = TRY_CAST(b.order_no AS BIGINT)
    LEFT JOIN ind.my_all_apply_tags_01 c -- 用户标签表
      ON TRY_CAST(a.camera_id AS BIGINT) = c.biz_id
    WHERE DATE(a.should_time) >= DATE('2022-01-01')  -- 取2022年后数据
  ) base
  LEFT JOIN (                           -- 还款通道表
    SELECT rid, channel_id 
    FROM ods.s02_loan_repayment_detail
  ) channel ON base.rid = channel.rid
  GROUP BY 1, 2, 3, 4, 5, 6, 7, 8      -- 按日期/期次/产品等分组
) agg;

-- ================================================================================
-- 表2：利息指标分析表 (ind.my_repayment_detail_02)
-- 核心指标：应还利息、实还利息、逾期利息
-- 逻辑与本金表完全一致，仅将capital替换为interest
-- ================================================================================
DROP TABLE IF EXISTS ind.my_repayment_detail_02; -- 清理历史表

CREATE TABLE ind.my_repayment_detail_02 AS
SELECT
  should_date,                          
  SUBSTRING(TO_CHAR(should_date, 'yyyy-mm-dd'), 1, 7) AS date_mon,
  TO_CHAR(DATE_TRUNC('week', should_date), 'yyyy-mm-dd') AS date_week,
  index AS repayment_index,
  tenant_id,
  double_loan,
  product_name,
  CASE 
    WHEN app_channel = '850792dc-e673-4131-8d0f-b0a70b2772be' THEN 'Samir' 
    ELSE 'Other' 
  END AS app_channel,
  
  -- ========== 利息指标 ==========
  interest_d0, interest_d3, interest_d7, interest_d14, interest_d30,  -- 应还利息
  interest_t0, interest_t3, interest_t7, interest_t14, interest_t30,  -- 逾期利息
  fact_interest_amount_t0_midtrans,     -- Midtrans通道实还利息
  fact_interest_amount_t0_offline,      -- 线下实还利息
  
  -- ========== 利息还款统计 ==========
  tm30_interest_amount, tm14_interest_amount, tm7_interest_amount, 
  tm3_interest_amount, tm1_interest_amount, t0_interest_amount,
  interest_loan_amount,                 -- 总应还利息
  source
FROM (
  SELECT
    should_date,
    dayss,
    index,
    tenant_id,
    a.reloan_tag AS double_loan,
    product_name,
    app_channel,
    source,
    
    -- ===== 利息支付通道 =====
    SUM(CASE 
          WHEN fact_date <= should_date 
               AND should_date < CURRENT_DATE 
               AND channel_id = 16 
          THEN fact_interest 
        END) AS fact_interest_amount_t0_midtrans,
    
    SUM(CASE 
          WHEN fact_date IS NULL 
               AND should_date < CURRENT_DATE 
               AND channel_id IS NULL 
          THEN fact_interest 
        END) AS fact_interest_amount_t0_offline,
    
    -- ===== 应还利息 =====
    SUM(CASE WHEN should_date < CURRENT_DATE THEN should_interest END) AS interest_d0,
    SUM(CASE WHEN DATE_DIFF('day', should_date, CURRENT_DATE) > 3 THEN should_interest END) AS interest_d3,
    SUM(CASE WHEN DATE_DIFF('day', should_date, CURRENT_DATE) > 7 THEN should_interest END) AS interest_d7,
    SUM(CASE WHEN DATE_DIFF('day', should_date, CURRENT_DATE) > 14 THEN should_interest END) AS interest_d14,
    SUM(CASE WHEN DATE_DIFF('day', should_date, CURRENT_DATE) > 30 THEN should_interest END) AS interest_d30,
    
    -- ===== 逾期利息 =====
    (SUM(CASE WHEN should_date < CURRENT_DATE THEN should_interest END) - 
     SUM(CASE WHEN fact_date <= should_date AND should_date < CURRENT_DATE THEN fact_interest END)
    ) AS interest_t0,
    
    (SUM(CASE WHEN DATE_DIFF('day', should_date, CURRENT_DATE) > 3 THEN should_interest END) - 
     SUM(CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 3 
                   AND DATE_DIFF('day', should_date, CURRENT_DATE) > 3 
              THEN fact_interest END)
    ) AS interest_t3,
    
    -- T7/T14/T30计算逻辑同上...
    
    -- ===== 利息金额统计 =====
    SUM(should_interest) AS interest_loan_amount,
    SUM(CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 30 THEN fact_interest END) AS tm30_interest_amount,
    SUM(CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 14 THEN fact_interest END) AS tm14_interest_amount,
    SUM(CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 7 THEN fact_interest END) AS tm7_interest_amount,
    SUM(CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 3 THEN fact_interest END) AS tm3_interest_amount,
    SUM(CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 1 THEN fact_interest END) AS tm1_interest_amount,
    SUM(CASE WHEN DATE_DIFF('day', should_date, fact_date) <= 0 THEN fact_interest END) AS t0_interest_amount
    
  FROM (
    -- 基础数据准备（同本金表）
    SELECT ... 
    FROM ods.s02_loan_repayment a
    INNER JOIN dwd.dwd_order_info b
      ON TRY_CAST(a.camera_id AS BIGINT) = TRY_CAST(b.order_no AS BIGINT)
    LEFT JOIN ind.my_all_apply_tags_01 c
      ON TRY_CAST(a.camera_id AS BIGINT) = c.biz_id
    WHERE DATE(should_time) >= DATE('2022-01-01')
  ) base
  LEFT JOIN (
    SELECT rid, channel_id 
    FROM ods.s02_loan_repayment_detail
  ) channel ON base.rid = channel.rid
  GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
) agg;





/* ===================================================================
 * 印尼现金贷：短期还款行为分析表
 * 功能：统计应还款日前后4天内的还款情况（本金+利息）
 * 核心价值：监控短期逾期风险与催收效率
 * 业务场景：用于优化前7天催收策略
 * =================================================================== */

-- 清理历史表（确保数据刷新）
DROP TABLE IF EXISTS ind.my_repayment_detail_03;

-- 创建短期还款分析表
CREATE TABLE ind.my_repayment_detail_03 AS
SELECT
  should_date,                          -- 【应还款日期】
  SUBSTRING(TO_CHAR(should_date, 'yyyy-mm-dd'), 1, 7) AS date_mon,  -- 月份（yyyy-mm）
  TO_CHAR(DATE_TRUNC('week', should_date), 'yyyy-mm-dd') AS date_week, -- 周起始日
  index AS repayment_index,             -- 【还款期次】
  tenant_id,                            -- 【租户ID】
  double_loan,                          -- 【贷款类型】0=首贷,1=复贷
  product_name,                         -- 【产品名称】
  CASE 
    WHEN app_channel = '850792dc-e673-4131-8d0f-b0a70b2772be' THEN 'Samir' 
    ELSE 'Other' 
  END AS app_channel,                   -- 【APP渠道】
  
  -- ========== 还款人数统计 ==========
  tm_cnt1,                              -- 应还日+1天内还款人数
  tm_cnt2,                              -- 应还日+2天内还款人数
  tm_cnt3,                              -- 应还日+3天内还款人数
  tm_cnt4,                              -- 应还日+4天内还款人数
  
  -- ========== 本金还款统计 ==========
  tm_amount1,                           -- 应还日+1天内还款本金
  tm_amount2,                           -- 应还日+2天内还款本金
  tm_amount3,                           -- 应还日+3天内还款本金
  tm_amount4,                           -- 应还日+4天内还款本金
  
  -- ========== 利息还款统计 ==========
  tm_interest_amount1,                  -- 应还日+1天内还款利息
  tm_interest_amount2,                  -- 应还日+2天内还款利息
  tm_interest_amount3,                  -- 应还日+3天内还款利息
  tm_interest_amount4,                  -- 应还日+4天内还款利息
  source                                 -- 数据来源标记
FROM (
  SELECT
    should_date,
    dayss,                              -- 星期几（0=周一,6=周日）
    index,
    tenant_id,
    reloan_tag AS double_loan,
    product_name,
    app_channel,
    source,
    
    -- ===== 还款人数统计 =====
    /* 应还日后1天内还款人数 */
    COUNT(DISTINCT CASE WHEN DATE_DIFF('day', fact_date, should_date) <= 1 THEN camera_id END) AS tm_cnt1,
    /* 应还日后2天内还款人数 */
    COUNT(DISTINCT CASE WHEN DATE_DIFF('day', fact_date, should_date) <= 2 THEN camera_id END) AS tm_cnt2,
    /* 应还日后3天内还款人数 */
    COUNT(DISTINCT CASE WHEN DATE_DIFF('day', fact_date, should_date) <= 3 THEN camera_id END) AS tm_cnt3,
    /* 应还日后4天内还款人数 */
    COUNT(DISTINCT CASE WHEN DATE_DIFF('day', fact_date, should_date) <= 4 THEN camera_id END) AS tm_cnt4,
    
    -- ===== 本金还款金额 =====
    /* 应还日后1天内还款本金 */
    SUM(CASE WHEN DATE_DIFF('day', fact_date, should_date) <= 1 THEN fact_capital END) AS tm_amount1,
    /* 应还日后2天内还款本金 */
    SUM(CASE WHEN DATE_DIFF('day', fact_date, should_date) <= 2 THEN fact_capital END) AS tm_amount2,
    /* 应还日后3天内还款本金 */
    SUM(CASE WHEN DATE_DIFF('day', fact_date, should_date) <= 3 THEN fact_capital END) AS tm_amount3,
    /* 应还日后4天内还款本金 */
    SUM(CASE WHEN DATE_DIFF('day', fact_date, should_date) <= 4 THEN fact_capital END) AS tm_amount4,
    
    -- ===== 利息还款金额 =====
    /* 应还日后1天内还款利息 */
    SUM(CASE WHEN DATE_DIFF('day', fact_date, should_date) <= 1 THEN fact_interest END) AS tm_interest_amount1,
    /* 应还日后2天内还款利息 */
    SUM(CASE WHEN DATE_DIFF('day', fact_date, should_date) <= 2 THEN fact_interest END) AS tm_interest_amount2,
    /* 应还日后3天内还款利息 */
    SUM(CASE WHEN DATE_DIFF('day', fact_date, should_date) <= 3 THEN fact_interest END) AS tm_interest_amount3,
    /* 应还日后4天内还款利息 */
    SUM(CASE WHEN DATE_DIFF('day', fact_date, should_date) <= 4 THEN fact_interest END) AS tm_interest_amount4
    
  FROM (
    -- ===== 基础数据准备 =====
    SELECT
      a.*,                              -- 还款计划基础字段
      c.reloan_tag,                     -- 首复贷标签
      DATE(a.should_time) AS should_date,
      a.indexs AS index,                -- 还款期次
      b.apply_period_code AS product_name, -- 产品名称
      DATE(a.fact_time) AS fact_date,    -- 实际还款日期
      
      /* 星期几数字映射（0=周一,6=周日） */
      CASE 
        WHEN DAY_OF_WEEK(a.should_time) = 1 THEN 0  -- 周日=0
        WHEN DAY_OF_WEEK(a.should_time) = 2 THEN 1  -- 周一=1
        WHEN DAY_OF_WEEK(a.should_time) = 3 THEN 2  -- 周二=2
        WHEN DAY_OF_WEEK(a.should_time) = 4 THEN 3  -- 周三=3
        WHEN DAY_OF_WEEK(a.should_time) = 5 THEN 4  -- 周四=4
        WHEN DAY_OF_WEEK(a.should_time) = 6 THEN 5  -- 周五=5
        ELSE 6                                      -- 周六=6
      END AS dayss,
      
      c.source                          -- 数据来源
    FROM ods.s02_loan_repayment a        -- 还款计划表
    INNER JOIN dwd.dwd_order_info b     -- 订单宽表
      ON TRY_CAST(a.camera_id AS BIGINT) = TRY_CAST(b.order_no AS BIGINT)
    LEFT JOIN ind.my_all_apply_tags_01 c -- 用户标签表
      ON TRY_CAST(a.camera_id AS BIGINT) = c.biz_id
    WHERE DATE(a.should_time) >= DATE('2022-01-01')  -- 取2022年后数据
  ) base
  GROUP BY 1, 2, 3, 4, 5, 6, 7, 8      -- 按日期/期次/产品等分组
) agg;








/* =============================================
 * 表名：ind.my_repayment_channels
 * 功能：分析不同支付渠道的还款表现
 * 业务价值：优化支付渠道策略，提升还款成功率
 * 更新频率：每日
 * ============================================= */

DROP TABLE IF EXISTS ind.my_repayment_channels;

CREATE TABLE ind.my_repayment_channels AS
SELECT
  DATE(b.should_time) AS should_date, -- 应还款日期
  c.tenant_id, -- 租户ID
  c.indexs AS repayment_index, -- 还款期次
  e.reloan_tag AS double_loan, -- 贷款类型(0=首贷,1=复贷)
  d.apply_period_code AS product_name, -- 产品名称
  e.source, -- 数据来源
  
  -- 各支付渠道T0还款金额(本金+利息)
  SUM(CASE 
        WHEN DATE(b.fact_time) <= DATE(b.should_time) 
             AND DATE(b.should_time)<CURRENT_DATE 
             AND a.bank_code ='bca' 
        THEN b.fact_capital + b.fact_interest 
      END) AS fact_amount_t0_bca, -- BCA银行还款金额
  
  SUM(CASE 
        WHEN DATE(b.fact_time) <= DATE(b.should_time) 
             AND DATE(b.should_time)<CURRENT_DATE 
             AND a.bank_code ='alfamart' 
        THEN b.fact_capital + b.fact_interest 
      END) AS fact_amount_t0_alfamart, -- Alfamart便利店还款
  
  SUM(CASE 
        WHEN DATE(b.fact_time) <= DATE(b.should_time) 
             AND DATE(b.should_time)<CURRENT_DATE 
             AND a.bank_code ='mandiri' 
        THEN b.fact_capital + b.fact_interest 
      END) AS fact_amount_t0_mandiri, -- Mandiri银行还款
  
  SUM(CASE 
        WHEN DATE(b.fact_time) <= DATE(b.should_time) 
             AND DATE(b.should_time)<CURRENT_DATE 
             AND a.bank_code ='permata' 
        THEN b.fact_capital + b.fact_interest 
      END) AS fact_amount_t0_permata, -- Permata银行还款
  
  SUM(CASE 
        WHEN DATE(b.fact_time) <= DATE(b.should_time) 
             AND DATE(b.should_time)<CURRENT_DATE 
             AND a.bank_code ='bni' 
        THEN b.fact_capital + b.fact_interest 
      END) AS fact_amount_t0_bni, -- BNI银行还款
  
  SUM(CASE 
        WHEN DATE(b.fact_time) <= DATE(b.should_time) 
             AND DATE(b.should_time)<CURRENT_DATE 
             AND b.channel_id IS NULL 
        THEN b.fact_capital + b.fact_interest 
      END) AS fact_amount_t0_offline -- 线下还款金额
FROM
  ods.s04_pmc_abroad_deduct_detail a -- 跨境扣款明细表
  INNER JOIN ods.s02_loan_repayment_detail b -- 还款明细表
    ON a.third_serial_no = b.pay_trade_no -- 通过交易流水号关联
  INNER JOIN ods.s02_loan_repayment c -- 还款计划表
    ON b.rid = c.rid -- 通过还款ID关联
  INNER JOIN dwd.dwd_order_info d -- 订单宽表
    ON TRY_CAST(c.camera_id AS BIGINT) = TRY_CAST(d.order_no AS BIGINT) -- 通过订单号关联
  LEFT JOIN ind.my_all_apply_tags_01 e -- 用户标签表
    ON TRY_CAST(c.camera_id AS BIGINT) = e.biz_id -- 通过业务ID关联
WHERE 
  a.real_amount <> 0 -- 过滤掉金额为0的记录
GROUP BY 
  1,2,3,4,5,6 -- 按日期/租户/期次等分组
;
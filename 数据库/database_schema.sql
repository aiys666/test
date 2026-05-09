-- ================================================
-- 金融风控数据集市 - 数据库架构设计
-- 数据库: YSProd
-- 生成时间: 2026-05-03
-- 设计标准: Kimball维度建模方法论
-- ================================================

-- ================================================
-- 第一部分：维度表 (Dimension Tables)
-- ================================================

-- 1. 时间维度表 (dim_time)
CREATE TABLE IF NOT EXISTS dim_time (
    time_id INT PRIMARY KEY COMMENT '时间ID',
    date_value DATE COMMENT '日期',
    year_num INT COMMENT '年份',
    quarter_num INT COMMENT '季度',
    month_num INT COMMENT '月份',
    month_name VARCHAR(20) COMMENT '月份名称',
    week_num INT COMMENT '周数',
    day_of_month INT COMMENT '月中第几天',
    day_of_week INT COMMENT '周中第几天',
    day_name VARCHAR(20) COMMENT '星期名称',
    is_weekend TINYINT COMMENT '是否周末',
    is_month_start TINYINT COMMENT '是否月初',
    is_month_end TINYINT COMMENT '是否月末',
    is_quarter_start TINYINT COMMENT '是否季度初',
    is_quarter_end TINYINT COMMENT '是否季度末'
) COMMENT '时间维度表';

-- 2. 产品维度表 (dim_product)
CREATE TABLE IF NOT EXISTS dim_product (
    product_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '产品ID',
    product_code VARCHAR(50) NOT NULL COMMENT '产品代码',
    product_name VARCHAR(200) COMMENT '产品名称',
    product_category VARCHAR(50) COMMENT '产品类别',
    product_type VARCHAR(50) COMMENT '产品类型',
    risk_level VARCHAR(20) COMMENT '风险等级',
    interest_rate DECIMAL(8,4) COMMENT '利率',
    min_loan_amount DECIMAL(15,2) COMMENT '最小贷款金额',
    max_loan_amount DECIMAL(15,2) COMMENT '最大贷款金额',
    min_loan_cycle INT COMMENT '最小贷款周期',
    max_loan_cycle INT COMMENT '最大贷款周期',
    loan_currency VARCHAR(10) COMMENT '贷款币种',
    status VARCHAR(20) COMMENT '状态',
    create_date DATE COMMENT '创建日期',
    effective_date DATE COMMENT '生效日期',
    expiry_date DATE COMMENT '失效日期',
    is_active TINYINT COMMENT '是否有效'
) COMMENT '产品维度表';

-- 3. 客户维度表 (dim_customer)
CREATE TABLE IF NOT EXISTS dim_customer (
    customer_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '客户ID',
    customer_code VARCHAR(50) NOT NULL COMMENT '客户代码',
    customer_name VARCHAR(200) COMMENT '客户姓名',
    id_card VARCHAR(50) COMMENT '身份证号',
    phone VARCHAR(50) COMMENT '手机号',
    email VARCHAR(100) COMMENT '邮箱',
    age INT COMMENT '年龄',
    gender VARCHAR(10) COMMENT '性别',
    education VARCHAR(50) COMMENT '学历',
    occupation VARCHAR(100) COMMENT '职业',
    annual_income DECIMAL(15,2) COMMENT '年收入',
    marital_status VARCHAR(20) COMMENT '婚姻状态',
    city VARCHAR(100) COMMENT '城市',
    province VARCHAR(100) COMMENT '省份',
    credit_score INT COMMENT '信用评分',
    risk_level VARCHAR(20) COMMENT '风险等级',
    customer_level VARCHAR(20) COMMENT '客户等级',
    register_date DATE COMMENT '注册日期',
    first_loan_date DATE COMMENT '首次贷款日期',
    is_verified TINYINT COMMENT '是否认证',
    status VARCHAR(20) COMMENT '状态'
) COMMENT '客户维度表';

-- 4. 地域维度表 (dim_location)
CREATE TABLE IF NOT EXISTS dim_location (
    location_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '地域ID',
    country VARCHAR(50) COMMENT '国家',
    province VARCHAR(100) COMMENT '省份',
    city VARCHAR(100) COMMENT '城市',
    district VARCHAR(100) COMMENT '区县',
    city_level VARCHAR(20) COMMENT '城市等级',
    region VARCHAR(50) COMMENT '大区',
    latitude DECIMAL(10,6) COMMENT '纬度',
    longitude DECIMAL(10,6) COMMENT '经度',
    population BIGINT COMMENT '人口数量',
    gdp DECIMAL(20,2) COMMENT 'GDP'
) COMMENT '地域维度表';

-- 5. 机构维度表 (dim_organization)
CREATE TABLE IF NOT EXISTS dim_organization (
    org_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '机构ID',
    org_code VARCHAR(50) NOT NULL COMMENT '机构代码',
    org_name VARCHAR(200) COMMENT '机构名称',
    org_level VARCHAR(20) COMMENT '机构级别',
    org_type VARCHAR(50) COMMENT '机构类型',
    parent_org_id INT COMMENT '上级机构ID',
    manager_name VARCHAR(100) COMMENT '负责人',
    phone VARCHAR(50) COMMENT '联系电话',
    address VARCHAR(500) COMMENT '地址',
    city VARCHAR(100) COMMENT '城市',
    province VARCHAR(100) COMMENT '省份',
    employee_count INT COMMENT '员工数量',
    status VARCHAR(20) COMMENT '状态'
) COMMENT '机构维度表';

-- ================================================
-- 第二部分：事实表 (Fact Tables)
-- ================================================

-- 6. 贷款申请事实表 (fct_loan_application)
CREATE TABLE IF NOT EXISTS fct_loan_application (
    application_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '申请ID',
    application_no VARCHAR(50) NOT NULL COMMENT '申请编号',
    customer_id INT COMMENT '客户ID',
    product_id INT COMMENT '产品ID',
    org_id INT COMMENT '机构ID',
    time_id INT COMMENT '申请时间ID',
    location_id INT COMMENT '地域ID',

    apply_amount DECIMAL(15,2) COMMENT '申请金额',
    apply_cycle INT COMMENT '申请周期',
    apply_term INT COMMENT '申请期限',
    apply_date DATE COMMENT '申请日期',
    approve_date DATE COMMENT '审批日期',
    reject_date DATE COMMENT '拒件日期',

    application_status VARCHAR(20) COMMENT '申请状态',
    approval_status VARCHAR(20) COMMENT '审批状态',
    reject_reason VARCHAR(500) COMMENT '拒件原因',

    risk_score DECIMAL(8,2) COMMENT '风险评分',
    credit_score INT COMMENT '信用评分',
    blacklist_flag TINYINT COMMENT '黑名单标识',

    create_time DATETIME COMMENT '创建时间',
    update_time DATETIME COMMENT '更新时间'
) COMMENT '贷款申请事实表';

-- 7. 贷款发放事实表 (fct_loan_disbursement)
CREATE TABLE IF NOT EXISTS fct_loan_disbursement (
    disbursement_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '发放ID',
    disbursement_no VARCHAR(50) NOT NULL COMMENT '发放编号',
    application_id INT COMMENT '申请ID',
    customer_id INT COMMENT '客户ID',
    product_id INT COMMENT '产品ID',
    org_id INT COMMENT '机构ID',
    time_id INT COMMENT '发放时间ID',
    location_id INT COMMENT '地域ID',

    loan_amount DECIMAL(15,2) COMMENT '贷款金额',
    loan_cycle INT COMMENT '贷款周期',
    loan_term INT COMMENT '贷款期限',
    interest_rate DECIMAL(8,4) COMMENT '贷款利率',
    disbursement_date DATE COMMENT '发放日期',
    maturity_date DATE COMMENT '到期日期',

    contract_amount DECIMAL(15,2) COMMENT '合同金额',
    haircut_amount DECIMAL(15,2) COMMENT '砍头息金额',
    net_amount DECIMAL(15,2) COMMENT '净发放金额',
    service_fee DECIMAL(15,2) COMMENT '服务费',

    disbursement_status VARCHAR(20) COMMENT '发放状态',
    loan_status VARCHAR(20) COMMENT '贷款状态',

    create_time DATETIME COMMENT '创建时间',
    update_time DATETIME COMMENT '更新时间'
) COMMENT '贷款发放事实表';

-- 8. 还款事实表 (fct_repayment)
CREATE TABLE IF NOT EXISTS fct_repayment (
    repayment_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '还款ID',
    repayment_no VARCHAR(50) NOT NULL COMMENT '还款编号',
    disbursement_id INT COMMENT '发放ID',
    customer_id INT COMMENT '客户ID',
    product_id INT COMMENT '产品ID',
    org_id INT COMMENT '机构ID',
    time_id INT COMMENT '还款时间ID',
    location_id INT COMMENT '地域ID',

    repay_date DATE COMMENT '应还日期',
    actual_repay_date DATE COMMENT '实还日期',
    period_no INT COMMENT '期数',
    total_periods INT COMMENT '总期数',

    principal DECIMAL(15,2) COMMENT '本金',
    interest DECIMAL(15,2) COMMENT '利息',
    service_fee DECIMAL(15,2) COMMENT '服务费',
    penalty DECIMAL(15,2) COMMENT '罚息',
    total_amount DECIMAL(15,2) COMMENT '总金额',

    repay_status VARCHAR(20) COMMENT '还款状态',
    overdue_days INT COMMENT '逾期天数',
    overdue_flag TINYINT COMMENT '逾期标识',

    create_time DATETIME COMMENT '创建时间',
    update_time DATETIME COMMENT '更新时间'
) COMMENT '还款事实表';

-- 9. 催收事实表 (fct_collection)
CREATE TABLE IF NOT EXISTS fct_collection (
    collection_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '催收ID',
    collection_no VARCHAR(50) NOT NULL COMMENT '催收编号',
    disbursement_id INT COMMENT '发放ID',
    customer_id INT COMMENT '客户ID',
    repayment_id INT COMMENT '还款ID',
    org_id INT COMMENT '机构ID',
    time_id INT COMMENT '催收时间ID',

    overdue_amount DECIMAL(15,2) COMMENT '逾期金额',
    overdue_days INT COMMENT '逾期天数',
    collection_amount DECIMAL(15,2) COMMENT '催收金额',
    collection_date DATE COMMENT '催收日期',
    collection_method VARCHAR(50) COMMENT '催收方式',
    collection_result VARCHAR(50) COMMENT '催收结果',
    collector_name VARCHAR(100) COMMENT '催收员',
    next_follow_date DATE COMMENT '下次跟进日期',

    create_time DATETIME COMMENT '创建时间',
    update_time DATETIME COMMENT '更新时间'
) COMMENT '催收事实表';

-- 10. 账务事实表 (fct_accounting)
CREATE TABLE IF NOT EXISTS fct_accounting (
    accounting_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '账务ID',
    accounting_no VARCHAR(50) NOT NULL COMMENT '账务编号',
    disbursement_id INT COMMENT '发放ID',
    customer_id INT COMMENT '客户ID',
    product_id INT COMMENT '产品ID',
    org_id INT COMMENT '机构ID',
    time_id INT COMMENT '账务时间ID',

    transaction_date DATE COMMENT '交易日期',
    transaction_type VARCHAR(50) COMMENT '交易类型',
    principal_balance DECIMAL(15,2) COMMENT '本金余额',
    interest_balance DECIMAL(15,2) COMMENT '利息余额',
    fee_balance DECIMAL(15,2) COMMENT '费用余额',

    create_time DATETIME COMMENT '创建时间'
) COMMENT '账务事实表';

-- ================================================
-- 第三部分：索引创建
-- ================================================

-- 为事实表创建常用索引
CREATE INDEX idx_application_customer ON fct_loan_application(customer_id);
CREATE INDEX idx_application_product ON fct_loan_application(product_id);
CREATE INDEX idx_application_date ON fct_loan_application(apply_date);
CREATE INDEX idx_application_status ON fct_loan_application(application_status);

CREATE INDEX idx_disbursement_customer ON fct_loan_disbursement(customer_id);
CREATE INDEX idx_disbursement_product ON fct_loan_disbursement(product_id);
CREATE INDEX idx_disbursement_date ON fct_loan_disbursement(disbursement_date);
CREATE INDEX idx_disbursement_status ON fct_loan_disbursement(loan_status);

CREATE INDEX idx_repayment_disbursement ON fct_repayment(disbursement_id);
CREATE INDEX idx_repayment_date ON fct_repayment(repay_date);
CREATE INDEX idx_repayment_status ON fct_repayment(repay_status);

CREATE INDEX idx_collection_disbursement ON fct_collection(disbursement_id);
CREATE INDEX idx_collection_date ON fct_collection(collection_date);

-- 为维度表创建索引
CREATE INDEX idx_customer_code ON dim_customer(customer_code);
CREATE INDEX idx_customer_phone ON dim_customer(phone);
CREATE INDEX idx_customer_idcard ON dim_customer(id_card);

CREATE INDEX idx_product_code ON dim_product(product_code);
CREATE INDEX idx_product_category ON dim_product(product_category);

CREATE INDEX idx_time_date ON dim_time(date_value);

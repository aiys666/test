# -*- coding: utf-8 -*-
import mysql.connector
import random
from datetime import datetime, timedelta
import os
import time

DB_CONFIG = {
    'host': '47.121.121.48',
    'port': 3306,
    'user': 'yuesong',
    'password': 'yuesongnb',
    'database': 'YSProd'
}

OUT_DIR = r"E:\岳松个人文件\嘉银工作内容的整理\code\权责自动化处理"

random.seed(42)

def connect_db():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        print("数据库连接成功")
        return conn
    except mysql.connector.Error as err:
        print(f"数据库连接失败: {err}")
        return None

def create_tables(conn):
    cursor = conn.cursor()

    tables = [
        """CREATE TABLE IF NOT EXISTS dim_time (
            time_id INT PRIMARY KEY,
            date_value DATE,
            year_num INT,
            quarter_num INT,
            month_num INT,
            month_name VARCHAR(20),
            week_num INT,
            day_of_month INT,
            day_of_week INT,
            day_name VARCHAR(20),
            is_weekend TINYINT,
            is_month_start TINYINT,
            is_month_end TINYINT,
            is_quarter_start TINYINT,
            is_quarter_end TINYINT
        )""",

        """CREATE TABLE IF NOT EXISTS dim_product (
            product_id INT PRIMARY KEY AUTO_INCREMENT,
            product_code VARCHAR(50) NOT NULL,
            product_name VARCHAR(200),
            product_category VARCHAR(50),
            product_type VARCHAR(50),
            risk_level VARCHAR(20),
            interest_rate DECIMAL(8,4),
            min_loan_amount DECIMAL(15,2),
            max_loan_amount DECIMAL(15,2),
            min_loan_cycle INT,
            max_loan_cycle INT,
            loan_currency VARCHAR(10),
            status VARCHAR(20),
            create_date DATE,
            effective_date DATE,
            expiry_date DATE,
            is_active TINYINT
        )""",

        """CREATE TABLE IF NOT EXISTS dim_customer (
            customer_id INT PRIMARY KEY AUTO_INCREMENT,
            customer_code VARCHAR(50) NOT NULL,
            customer_name VARCHAR(200),
            id_card VARCHAR(50),
            phone VARCHAR(50),
            email VARCHAR(100),
            age INT,
            gender VARCHAR(10),
            education VARCHAR(50),
            occupation VARCHAR(100),
            annual_income DECIMAL(15,2),
            marital_status VARCHAR(20),
            city VARCHAR(100),
            province VARCHAR(100),
            credit_score INT,
            risk_level VARCHAR(20),
            customer_level VARCHAR(20),
            register_date DATE,
            first_loan_date DATE,
            is_verified TINYINT,
            status VARCHAR(20)
        )""",

        """CREATE TABLE IF NOT EXISTS dim_location (
            location_id INT PRIMARY KEY AUTO_INCREMENT,
            country VARCHAR(50),
            province VARCHAR(100),
            city VARCHAR(100),
            district VARCHAR(100),
            city_level VARCHAR(20),
            region VARCHAR(50),
            latitude DECIMAL(10,6),
            longitude DECIMAL(10,6),
            population BIGINT,
            gdp DECIMAL(20,2)
        )""",

        """CREATE TABLE IF NOT EXISTS dim_organization (
            org_id INT PRIMARY KEY AUTO_INCREMENT,
            org_code VARCHAR(50) NOT NULL,
            org_name VARCHAR(200),
            org_level VARCHAR(20),
            org_type VARCHAR(50),
            parent_org_id INT,
            manager_name VARCHAR(100),
            phone VARCHAR(50),
            address VARCHAR(500),
            city VARCHAR(100),
            province VARCHAR(100),
            employee_count INT,
            status VARCHAR(20)
        )""",

        """CREATE TABLE IF NOT EXISTS fct_loan_application (
            application_id INT PRIMARY KEY AUTO_INCREMENT,
            application_no VARCHAR(50) NOT NULL,
            customer_id INT,
            product_id INT,
            org_id INT,
            time_id INT,
            location_id INT,
            apply_amount DECIMAL(15,2),
            apply_cycle INT,
            apply_term INT,
            apply_date DATE,
            approve_date DATE,
            reject_date DATE,
            application_status VARCHAR(20),
            approval_status VARCHAR(20),
            reject_reason VARCHAR(500),
            risk_score DECIMAL(8,2),
            credit_score INT,
            blacklist_flag TINYINT,
            create_time DATETIME,
            update_time DATETIME
        )""",

        """CREATE TABLE IF NOT EXISTS fct_loan_disbursement (
            disbursement_id INT PRIMARY KEY AUTO_INCREMENT,
            disbursement_no VARCHAR(50) NOT NULL,
            application_id INT,
            customer_id INT,
            product_id INT,
            org_id INT,
            time_id INT,
            location_id INT,
            loan_amount DECIMAL(15,2),
            loan_cycle INT,
            loan_term INT,
            interest_rate DECIMAL(8,4),
            disbursement_date DATE,
            maturity_date DATE,
            contract_amount DECIMAL(15,2),
            haircut_amount DECIMAL(15,2),
            net_amount DECIMAL(15,2),
            service_fee DECIMAL(15,2),
            disbursement_status VARCHAR(20),
            loan_status VARCHAR(20),
            create_time DATETIME,
            update_time DATETIME
        )"""
    ]

    for i, table_sql in enumerate(tables):
        try:
            table_name = table_sql.split('`')[1] if '`' in table_sql else table_sql.split('NOT EXISTS')[1].split('(')[0].strip()
            cursor.execute(table_sql)
            conn.commit()
            print(f"  创建表成功: {table_name}")
        except mysql.connector.Error as err:
            if 'already exists' not in str(err).lower():
                print(f"  创建表出错: {err}")

    cursor.close()

def insert_dim_time(conn):
    cursor = conn.cursor()
    print("\n插入时间维度表...")

    start_date = datetime(2023, 1, 1)
    end_date = datetime(2025, 12, 31)
    current_date = start_date
    time_id = 1

    batch = []
    while current_date <= end_date:
        year_num = current_date.year
        quarter_num = (current_date.month - 1) // 3 + 1
        month_num = current_date.month
        month_name = current_date.strftime('%B')
        week_num = current_date.isocalendar()[1]
        day_of_month = current_date.day
        day_of_week = current_date.weekday()
        day_name = current_date.strftime('%A')
        is_weekend = 1 if day_of_week >= 5 else 0
        is_month_start = 1 if day_of_month == 1 else 0
        is_month_end = (current_date + timedelta(days=1)).day == 1
        is_quarter_start = 1 if month_num in [1, 4, 7, 10] and day_of_month == 1 else 0
        is_quarter_end = 1 if month_num in [3, 6, 9, 12] and (current_date + timedelta(days=1)).month != month_num else 0

        batch.append((
            time_id, current_date.date(), year_num, quarter_num, month_num,
            month_name, week_num, day_of_month, day_of_week, day_name,
            is_weekend, is_month_start, is_month_end, is_quarter_start, is_quarter_end
        ))

        if len(batch) >= 1000:
            try:
                cursor.executemany("""
                    INSERT INTO dim_time VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, batch)
                conn.commit()
            except mysql.connector.Error as err:
                print(f"  插入错误: {err}")
            batch = []

        current_date += timedelta(days=1)
        time_id += 1

    if batch:
        try:
            cursor.executemany("""
                INSERT INTO dim_time VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, batch)
            conn.commit()
        except mysql.connector.Error as err:
            print(f"  插入错误: {err}")

    cursor.close()
    print(f"  时间维度表完成: {time_id - 1} 条记录")

def insert_dim_product(conn):
    cursor = conn.cursor()
    print("\n插入产品维度表...")

    products = [
        ('P001', '优享贷', '信用贷款', '等本等息', '中', 0.1500, 5000, 50000, 3, 12, 'IDR', 'active', '2023-01-01', '2023-01-01', '2025-12-31', 1),
        ('P002', '无忧贷', '信用贷款', '等本等息', '低', 0.1200, 3000, 30000, 6, 24, 'IDR', 'active', '2023-01-01', '2023-01-01', '2025-12-31', 1),
        ('P003', '放心贷', '信用贷款', '等本等息', '高', 0.1800, 10000, 100000, 12, 36, 'IDR', 'active', '2023-01-01', '2023-01-01', '2025-12-31', 1),
        ('P004', '花式新免息', '现金分期', '等本等息', '中', 0.0000, 1000, 10000, 3, 6, 'IDR', 'active', '2023-01-01', '2023-01-01', '2025-12-31', 1),
        ('P005', '本金前置', '短期贷款', '等本等息', '高', 0.2000, 5000, 20000, 1, 3, 'IDR', 'active', '2023-01-01', '2023-01-01', '2025-12-31', 1),
    ]

    for product in products:
        try:
            cursor.execute("""
                INSERT INTO dim_product (
                    product_code, product_name, product_category, product_type, risk_level,
                    interest_rate, min_loan_amount, max_loan_amount, min_loan_cycle, max_loan_cycle,
                    loan_currency, status, create_date, effective_date, expiry_date, is_active
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, product)
            conn.commit()
        except mysql.connector.Error as err:
            print(f"  插入错误: {err}")

    cursor.close()
    print(f"  产品维度表完成: {len(products)} 条记录")

def insert_dim_customer(conn):
    cursor = conn.cursor()
    print("\n插入客户维度表...")

    cities = ['Jakarta', 'Surabaya', 'Bandung', 'Medan', 'Semarang', 'Makassar', 'Palembang', 'Tangerang', 'Depok', 'Bekasi']
    provinces = ['DKI Jakarta', 'East Java', 'West Java', 'North Sumatra', 'Central Java', 'South Sulawesi', 'South Sumatra', 'Banten', 'West Java', 'West Java']
    educations = ['High School', 'Bachelor', 'Master', 'Doctorate']
    occupations = ['Employee', 'Business Owner', 'Freelancer', 'Government Officer', 'Teacher', 'Engineer']
    marital_statuses = ['Single', 'Married', 'Divorced']

    batch = []
    for i in range(1, 1001):
        customer_code = f'C{str(i).zfill(8)}'
        customer_name = f'Customer_{i}'
        id_card = f'32{str(random.randint(100000000000000, 999999999999999))}'
        phone = f'08{random.randint(100000000, 999999999)}'
        email = f'customer{i}@example.com'
        age = random.randint(21, 55)
        gender = random.choice(['Male', 'Female'])
        education = random.choice(educations)
        occupation = random.choice(occupations)
        annual_income = random.randint(30000000, 200000000)
        marital_status = random.choice(marital_statuses)
        city = random.choice(cities)
        province = provinces[cities.index(city)]
        credit_score = random.randint(300, 850)
        risk_level = 'Low' if credit_score >= 700 else ('Medium' if credit_score >= 500 else 'High')
        customer_level = 'VIP' if credit_score >= 750 else ('Regular' if credit_score >= 600 else 'New')
        register_date = datetime(2023, 1, 1) + timedelta(days=random.randint(0, 730))
        first_loan_date = register_date + timedelta(days=random.randint(0, 30))
        is_verified = random.choice([0, 1])
        status = 'active'

        batch.append((
            customer_code, customer_name, id_card, phone, email, age, gender,
            education, occupation, annual_income, marital_status, city, province,
            credit_score, risk_level, customer_level, register_date.date(),
            first_loan_date.date(), is_verified, status
        ))

        if len(batch) >= 100:
            try:
                cursor.executemany("""
                    INSERT INTO dim_customer (
                        customer_code, customer_name, id_card, phone, email, age, gender,
                        education, occupation, annual_income, marital_status, city, province,
                        credit_score, risk_level, customer_level, register_date,
                        first_loan_date, is_verified, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, batch)
                conn.commit()
            except mysql.connector.Error as err:
                print(f"  插入错误: {err}")
            batch = []

    if batch:
        try:
            cursor.executemany("""
                INSERT INTO dim_customer (
                    customer_code, customer_name, id_card, phone, email, age, gender,
                    education, occupation, annual_income, marital_status, city, province,
                    credit_score, risk_level, customer_level, register_date,
                    first_loan_date, is_verified, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, batch)
            conn.commit()
        except mysql.connector.Error as err:
            print(f"  插入错误: {err}")

    cursor.close()
    print(f"  客户维度表完成: 1000 条记录")

def insert_dim_location(conn):
    cursor = conn.cursor()
    print("\n插入地域维度表...")

    locations = [
        ('Indonesia', 'DKI Jakarta', 'Jakarta Pusat', 'Menteng', 'Tier 1', 'Java', -6.2088, 106.8456, 10562000, 2000000000000),
        ('Indonesia', 'DKI Jakarta', 'Jakarta Selatan', 'Kebayoran', 'Tier 1', 'Java', -6.2615, 106.8113, 10562000, 2000000000000),
        ('Indonesia', 'East Java', 'Surabaya', 'Surabaya Pusat', 'Tier 1', 'Java', -7.2575, 112.7521, 2800000, 150000000000),
        ('Indonesia', 'West Java', 'Bandung', 'Bandung Pusat', 'Tier 2', 'Java', -6.9175, 107.6191, 2500000, 90000000000),
        ('Indonesia', 'North Sumatra', 'Medan', 'Medan Pusat', 'Tier 2', 'Sumatra', 3.5952, 98.6722, 2300000, 80000000000),
        ('Indonesia', 'Central Java', 'Semarang', 'Semarang Pusat', 'Tier 2', 'Java', -6.9667, 110.4206, 1800000, 65000000000),
        ('Indonesia', 'South Sulawesi', 'Makassar', 'Makassar Pusat', 'Tier 2', 'Sulawesi', -5.1429, 119.4123, 1600000, 70000000000),
        ('Indonesia', 'South Sumatra', 'Palembang', 'Palembang Pusat', 'Tier 2', 'Sumatra', -2.9900, 104.7558, 1600000, 60000000000),
        ('Indonesia', 'Banten', 'Tangerang', 'Tangerang Pusat', 'Tier 2', 'Java', -6.1784, 106.6300, 2200000, 85000000000),
        ('Indonesia', 'West Java', 'Bekasi', 'Bekasi Pusat', 'Tier 2', 'Java', -6.2297, 106.9924, 2800000, 95000000000),
    ]

    for loc in locations:
        try:
            cursor.execute("""
                INSERT INTO dim_location (
                    country, province, city, district, city_level, region,
                    latitude, longitude, population, gdp
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, loc)
            conn.commit()
        except mysql.connector.Error as err:
            print(f"  插入错误: {err}")

    cursor.close()
    print(f"  地域维度表完成: {len(locations)} 条记录")

def insert_dim_organization(conn):
    cursor = conn.cursor()
    print("\n插入机构维度表...")

    orgs = [
        ('ORG001', '嘉银科技总部', 'Headquarters', 'Technology', None, 'Zhang Wei', '021-12345678', 'Jakarta Pusat', 'DKI Jakarta', 500, 'active'),
        ('ORG002', '雅加达分部', 'Regional', 'Branch', 1, 'Ahmad Rizki', '021-87654321', 'Jakarta Selatan', 'DKI Jakarta', 120, 'active'),
        ('ORG003', '泗水分部', 'Regional', 'Branch', 1, 'Budi Santoso', '031-12345678', 'Surabaya', 'East Java', 80, 'active'),
        ('ORG004', '万隆分部', 'Regional', 'Branch', 1, 'Dewi Lestari', '022-12345678', 'Bandung', 'West Java', 60, 'active'),
        ('ORG005', '棉兰分部', 'Regional', 'Branch', 1, 'Surya Darma', '061-12345678', 'Medan', 'North Sumatra', 45, 'active'),
    ]

    for org in orgs:
        try:
            cursor.execute("""
                INSERT INTO dim_organization (
                    org_code, org_name, org_level, org_type, parent_org_id,
                    manager_name, phone, address, city, province, employee_count, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, org)
            conn.commit()
        except mysql.connector.Error as err:
            print(f"  插入错误: {err}")

    cursor.close()
    print(f"  机构维度表完成: {len(orgs)} 条记录")

def insert_fact_tables(conn):
    cursor = conn.cursor()
    print("\n插入事实表...")

    cursor.execute("SELECT product_id FROM dim_product")
    product_ids = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT customer_id FROM dim_customer")
    customer_ids = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT org_id FROM dim_organization")
    org_ids = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT time_id FROM dim_time WHERE date_value >= '2024-01-01' AND date_value <= '2024-12-31' LIMIT 365")
    time_ids = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT location_id FROM dim_location")
    location_ids = [row[0] for row in cursor.fetchall()]

    print("\n  插入贷款申请事实表...")
    application_batch = []
    for i in range(1, 501):
        application_no = f'APP{str(i).zfill(10)}'
        customer_id = random.choice(customer_ids)
        product_id = random.choice(product_ids)
        org_id = random.choice(org_ids)
        time_id = random.choice(time_ids)
        location_id = random.choice(location_ids)

        cursor.execute("SELECT date_value FROM dim_time WHERE time_id = %s", (time_id,))
        apply_date = cursor.fetchone()[0]

        apply_amount = random.randint(5000, 100000)
        apply_cycle = random.choice([3, 6, 12, 24, 36])
        apply_term = random.choice([3, 6, 12, 24, 36])

        application_status = random.choice(['approved', 'rejected', 'pending'])
        approval_status = 'approved' if application_status == 'approved' else 'rejected'
        reject_reason = 'Insufficient credit score' if application_status == 'rejected' else None

        risk_score = random.uniform(300, 850)
        credit_score = random.randint(300, 850)
        blacklist_flag = random.choice([0, 0, 0, 1])

        approve_date = apply_date + timedelta(days=random.randint(1, 7)) if approval_status == 'approved' else None
        reject_date = apply_date + timedelta(days=random.randint(1, 3)) if application_status == 'rejected' else None

        application_batch.append((
            application_no, customer_id, product_id, org_id, time_id, location_id,
            apply_amount, apply_cycle, apply_term, apply_date, approve_date, reject_date,
            application_status, approval_status, reject_reason, risk_score, credit_score,
            blacklist_flag, datetime.now(), datetime.now()
        ))

        if len(application_batch) >= 100:
            try:
                cursor.executemany("""
                    INSERT INTO fct_loan_application (
                        application_no, customer_id, product_id, org_id, time_id, location_id,
                        apply_amount, apply_cycle, apply_term, apply_date, approve_date, reject_date,
                        application_status, approval_status, reject_reason, risk_score, credit_score,
                        blacklist_flag, create_time, update_time
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, application_batch)
                conn.commit()
            except mysql.connector.Error as err:
                print(f"  插入错误: {err}")
            application_batch = []

    if application_batch:
        try:
            cursor.executemany("""
                INSERT INTO fct_loan_application (
                    application_no, customer_id, product_id, org_id, time_id, location_id,
                    apply_amount, apply_cycle, apply_term, apply_date, approve_date, reject_date,
                    application_status, approval_status, reject_reason, risk_score, credit_score,
                    blacklist_flag, create_time, update_time
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, application_batch)
            conn.commit()
        except mysql.connector.Error as err:
            print(f"  插入错误: {err}")

    print(f"  贷款申请事实表完成: 500 条记录")

    print("\n  插入贷款发放事实表...")
    cursor.execute("SELECT application_id FROM fct_loan_application WHERE application_status = 'approved' LIMIT 200")
    approved_application_ids = [row[0] for row in cursor.fetchall()]

    disbursement_batch = []
    for i in range(1, 301):
        if not approved_application_ids:
            break

        disbursement_no = f'DIS{str(i).zfill(10)}'
        application_id = random.choice(approved_application_ids)

        cursor.execute("SELECT customer_id, product_id, org_id, time_id, location_id, apply_amount, apply_cycle FROM fct_loan_application WHERE application_id = %s", (application_id,))
        result = cursor.fetchone()
        if not result:
            continue

        customer_id, product_id, org_id, time_id, location_id, loan_amount, loan_cycle = result

        cursor.execute("SELECT date_value FROM dim_time WHERE time_id = %s", (time_id,))
        disbursement_date = cursor.fetchone()[0]
        maturity_date = disbursement_date + timedelta(days=loan_cycle * 30)

        interest_rate = random.uniform(0.10, 0.20)
        contract_amount = loan_amount * 1.15
        haircut_amount = loan_amount * 0.10
        net_amount = loan_amount - haircut_amount
        service_fee = loan_amount * 0.05

        disbursement_batch.append((
            disbursement_no, application_id, customer_id, product_id, org_id, time_id, location_id,
            loan_amount, loan_cycle, loan_cycle * 30, interest_rate, disbursement_date, maturity_date,
            contract_amount, haircut_amount, net_amount, service_fee, 'disbursed', 'active',
            datetime.now(), datetime.now()
        ))

        if len(disbursement_batch) >= 100:
            try:
                cursor.executemany("""
                    INSERT INTO fct_loan_disbursement (
                        disbursement_no, application_id, customer_id, product_id, org_id, time_id, location_id,
                        loan_amount, loan_cycle, loan_term, interest_rate, disbursement_date, maturity_date,
                        contract_amount, haircut_amount, net_amount, service_fee, disbursement_status, loan_status,
                        create_time, update_time
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, disbursement_batch)
                conn.commit()
            except mysql.connector.Error as err:
                print(f"  插入错误: {err}")
            disbursement_batch = []

    if disbursement_batch:
        try:
            cursor.executemany("""
                INSERT INTO fct_loan_disbursement (
                    disbursement_no, application_id, customer_id, product_id, org_id, time_id, location_id,
                    loan_amount, loan_cycle, loan_term, interest_rate, disbursement_date, maturity_date,
                    contract_amount, haircut_amount, net_amount, service_fee, disbursement_status, loan_status,
                    create_time, update_time
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, disbursement_batch)
            conn.commit()
        except mysql.connector.Error as err:
            print(f"  插入错误: {err}")

    print(f"  贷款发放事实表完成")

    cursor.close()

def main():
    print("="*60)
    print("金融风控数据集市 - 数据生成工具")
    print("="*60)

    conn = connect_db()
    if not conn:
        return

    print("\n步骤1: 创建数据库表结构...")
    create_tables(conn)

    print("\n步骤2: 插入维度表数据...")
    insert_dim_time(conn)
    insert_dim_product(conn)
    insert_dim_customer(conn)
    insert_dim_location(conn)
    insert_dim_organization(conn)

    print("\n步骤3: 插入事实表数据...")
    insert_fact_tables(conn)

    conn.close()
    print("\n" + "="*60)
    print("数据生成完成!")
    print("="*60)

if __name__ == "__main__":
    main()

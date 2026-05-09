# -*- coding: utf-8 -*-
"""
补充缺失数据的脚本
"""

import mysql.connector
import random
from datetime import datetime, timedelta

DB_CONFIG = {
    'host': '47.121.121.48',
    'port': 3306,
    'user': 'yuesong',
    'password': 'yuesongnb',
    'database': 'YSProd'
}

def connect_db():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        print("数据库连接成功！")
        return conn
    except mysql.connector.Error as err:
        print(f"数据库连接失败: {err}")
        return None

def insert_organizations(conn):
    print("\n[1] 插入机构维度表数据...")
    
    cursor = conn.cursor()
    
    orgs = [
        ('ORG001', '嘉银科技总部', 'Headquarters', 'Technology', None, 'Zhang Wei', '021-12345678', 'Jakarta Pusat', 'DKI Jakarta', 500, 'active'),
        ('ORG002', '雅加达分部', 'Regional', 'Branch', 1, 'Ahmad Rizki', '021-87654321', 'Jakarta Selatan', 'DKI Jakarta', 120, 'active'),
        ('ORG003', '泗水分部', 'Regional', 'Branch', 1, 'Budi Santoso', '031-12345678', 'Surabaya', 'East Java', 80, 'active'),
        ('ORG004', '万隆分部', 'Regional', 'Branch', 1, 'Dewi Lestari', '022-12345678', 'Bandung', 'West Java', 60, 'active'),
        ('ORG005', '棉兰分部', 'Regional', 'Branch', 1, 'Surya Darma', '061-12345678', 'Medan', 'North Sumatra', 45, 'active'),
    ]
    
    inserted = 0
    for org in orgs:
        try:
            cursor.execute("""
                INSERT INTO dim_organization (
                    org_code, org_name, org_level, org_type, parent_org_id,
                    manager_name, phone, address, city, province, employee_count, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, org)
            inserted += 1
        except mysql.connector.Error as err:
            if "Duplicate" not in str(err):
                print(f"  插入错误: {err}")
    
    conn.commit()
    cursor.close()
    print(f"  机构表插入完成！共插入 {inserted} 条记录")

def get_ids(conn):
    print("\n[2] 获取各表ID列表...")
    
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT product_id FROM dim_product")
    product_ids = [row['product_id'] for row in cursor.fetchall()]
    print(f"  产品ID: {product_ids}")
    
    cursor.execute("SELECT customer_id FROM dim_customer LIMIT 1000")
    customer_ids = [row['customer_id'] for row in cursor.fetchall()]
    print(f"  客户ID: 共 {len(customer_ids)} 个")
    
    cursor.execute("SELECT org_id FROM dim_organization")
    org_ids = [row['org_id'] for row in cursor.fetchall()]
    print(f"  机构ID: {org_ids}")
    
    cursor.execute("SELECT time_id FROM dim_time WHERE date_value >= '2024-01-01' AND date_value <= '2024-12-31' LIMIT 365")
    time_ids = [row['time_id'] for row in cursor.fetchall()]
    print(f"  时间ID: 共 {len(time_ids)} 个")
    
    cursor.execute("SELECT location_id FROM dim_location")
    location_ids = [row['location_id'] for row in cursor.fetchall()]
    print(f"  地域ID: {location_ids}")
    
    cursor.close()
    return product_ids, customer_ids, org_ids, time_ids, location_ids

def insert_loan_applications(conn, product_ids, customer_ids, org_ids, time_ids, location_ids):
    print("\n[3] 插入贷款申请事实表...")
    
    cursor = conn.cursor()
    
    total = 500
    batch_size = 100
    inserted = 0
    application_batch = []
    
    for i in range(1, total + 1):
        application_no = f"APP{str(i).zfill(10)}"
        customer_id = random.choice(customer_ids)
        product_id = random.choice(product_ids)
        org_id = random.choice(org_ids)
        time_id = random.choice(time_ids)
        location_id = random.choice(location_ids)
        
        # 获取申请日期
        cursor.execute("SELECT date_value FROM dim_time WHERE time_id = %s", (time_id,))
        apply_date = cursor.fetchone()[0]
        
        apply_amount = random.randint(5000, 100000)
        apply_cycle = random.choice([3, 6, 12, 24, 36])
        apply_term = apply_cycle
        
        # 随机状态
        rand_val = random.random()
        if rand_val < 0.6:
            application_status = 'approved'
            approval_status = 'approved'
            reject_reason = None
            approve_date = apply_date + timedelta(days=random.randint(1, 7))
        elif rand_val < 0.85:
            application_status = 'rejected'
            approval_status = 'rejected'
            reject_reason = random.choice([
                'Insufficient credit score',
                'High debt-to-income ratio',
                'Incomplete documentation',
                'Previous loan default',
                'Employment verification failed'
            ])
            approve_date = None
        else:
            application_status = 'pending'
            approval_status = 'pending'
            reject_reason = None
            approve_date = None
        
        risk_score = random.uniform(300, 850)
        
        # 获取客户信用分
        cursor.execute("SELECT credit_score FROM dim_customer WHERE customer_id = %s", (customer_id,))
        credit_score = cursor.fetchone()[0]
        
        blacklist_flag = 1 if random.random() < 0.05 else 0
        create_time = datetime.now()
        update_time = datetime.now()
        
        application_batch.append((
            application_no, customer_id, product_id, org_id, time_id, location_id,
            apply_amount, apply_cycle, apply_term, apply_date, approve_date, None,
            application_status, approval_status, reject_reason, risk_score, credit_score,
            blacklist_flag, create_time, update_time
        ))
        
        if len(application_batch) >= batch_size:
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
                inserted += len(application_batch)
                print(f"  已插入 {inserted}/{total} 条...")
                application_batch = []
            except mysql.connector.Error as err:
                print(f"  插入错误: {err}")
                application_batch = []
    
    # 插入剩余的
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
            inserted += len(application_batch)
        except mysql.connector.Error as err:
            print(f"  插入错误: {err}")
    
    cursor.close()
    print(f"  贷款申请表插入完成！共插入 {inserted} 条记录")

def insert_loan_disbursements(conn, product_ids, customer_ids, org_ids, time_ids, location_ids):
    print("\n[4] 插入贷款发放事实表...")
    
    cursor = conn.cursor(dictionary=True)
    
    # 获取已通过的申请
    cursor.execute("""
        SELECT application_id, customer_id, product_id, org_id, apply_amount, apply_cycle
        FROM fct_loan_application
        WHERE application_status = 'approved'
    """)
    approved_applications = cursor.fetchall()
    
    if not approved_applications:
        print("  没有通过的申请，无法生成发放数据")
        cursor.close()
        return
    
    print(f"  找到 {len(approved_applications)} 个已通过的申请")
    
    total = min(300, len(approved_applications))
    batch_size = 100
    inserted = 0
    disbursement_batch = []
    
    for i in range(total):
        app = approved_applications[i]
        disbursement_no = f"DIS{str(i + 1).zfill(10)}"
        application_id = app['application_id']
        customer_id = app['customer_id']
        product_id = app['product_id']
        org_id = app['org_id']
        loan_amount = app['apply_amount']
        loan_cycle = app['apply_cycle']
        
        time_id = random.choice(time_ids)
        location_id = random.choice(location_ids)
        
        # 获取发放日期
        cursor.execute("SELECT date_value FROM dim_time WHERE time_id = %s", (time_id,))
        disbursement_date = cursor.fetchone()[0]
        maturity_date = disbursement_date + timedelta(days=loan_cycle * 30)
        
        # 获取产品信息
        cursor.execute("SELECT interest_rate FROM dim_product WHERE product_id = %s", (product_id,))
        interest_rate = cursor.fetchone()[0]
        
        contract_amount = loan_amount * 1.15
        haircut_amount = loan_amount * 0.10
        net_amount = loan_amount - haircut_amount
        service_fee = loan_amount * 0.05
        disbursement_status = 'disbursed'
        loan_status = 'active'
        create_time = datetime.now()
        update_time = datetime.now()
        
        disbursement_batch.append((
            disbursement_no, application_id, customer_id, product_id, org_id, time_id, location_id,
            loan_amount, loan_cycle, loan_cycle * 30, interest_rate, disbursement_date, maturity_date,
            contract_amount, haircut_amount, net_amount, service_fee, disbursement_status, loan_status,
            create_time, update_time
        ))
        
        if len(disbursement_batch) >= batch_size:
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
                inserted += len(disbursement_batch)
                print(f"  已插入 {inserted}/{total} 条...")
                disbursement_batch = []
            except mysql.connector.Error as err:
                print(f"  插入错误: {err}")
                disbursement_batch = []
    
    # 插入剩余的
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
            inserted += len(disbursement_batch)
        except mysql.connector.Error as err:
            print(f"  插入错误: {err}")
    
    cursor.close()
    print(f"  贷款发放表插入完成！共插入 {inserted} 条记录")

def verify(conn):
    print("\n[5] 验证数据...")
    
    cursor = conn.cursor()
    
    tables = [
        'dim_time',
        'dim_product',
        'dim_customer',
        'dim_location',
        'dim_organization',
        'fct_loan_application',
        'fct_loan_disbursement'
    ]
    
    print("-"*60)
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table:25s} {count:10d} 条记录")
    print("-"*60)
    
    cursor.close()

def main():
    print("="*60)
    print("补充缺失数据")
    print("="*60)
    
    conn = connect_db()
    if not conn:
        return
    
    try:
        insert_organizations(conn)
        product_ids, customer_ids, org_ids, time_ids, location_ids = get_ids(conn)
        insert_loan_applications(conn, product_ids, customer_ids, org_ids, time_ids, location_ids)
        insert_loan_disbursements(conn, product_ids, customer_ids, org_ids, time_ids, location_ids)
        verify(conn)
        
        print("\n" + "="*60)
        print("数据补充完成！")
        print("="*60)
    finally:
        conn.close()

if __name__ == "__main__":
    main()

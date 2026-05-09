# -*- coding: utf-8 -*-
"""
最简单的数据填充脚本
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
    return mysql.connector.connect(**DB_CONFIG)

def main():
    print("="*60)
    print("开始填充数据")
    print("="*60)
    
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    
    # === 1. 插入机构 ===
    print("\n[1] 插入机构...")
    
    # 清空
    cursor.execute("DELETE FROM dim_organization")
    conn.commit()
    
    cursor.execute("""
        INSERT INTO dim_organization 
        (org_code, org_name, org_level, org_type, parent_org_id, manager_name, phone, address, city, province, employee_count, status)
        VALUES ('ORG001', '嘉银科技总部', 'Headquarters', 'Technology', NULL, 'Zhang Wei', '021-12345678', 'Jakarta Pusat', 'DKI Jakarta', 500, 'active')
    """)
    cursor.execute("""
        INSERT INTO dim_organization 
        (org_code, org_name, org_level, org_type, parent_org_id, manager_name, phone, address, city, province, employee_count, status)
        VALUES ('ORG002', '雅加达分部', 'Regional', 'Branch', 1, 'Ahmad Rizki', '021-87654321', 'Jakarta Selatan', 'DKI Jakarta', 120, 'active')
    """)
    cursor.execute("""
        INSERT INTO dim_organization 
        (org_code, org_name, org_level, org_type, parent_org_id, manager_name, phone, address, city, province, employee_count, status)
        VALUES ('ORG003', '泗水分部', 'Regional', 'Branch', 1, 'Budi Santoso', '031-12345678', 'Surabaya', 'East Java', 80, 'active')
    """)
    cursor.execute("""
        INSERT INTO dim_organization 
        (org_code, org_name, org_level, org_type, parent_org_id, manager_name, phone, address, city, province, employee_count, status)
        VALUES ('ORG004', '万隆分部', 'Regional', 'Branch', 1, 'Dewi Lestari', '022-12345678', 'Bandung', 'West Java', 60, 'active')
    """)
    cursor.execute("""
        INSERT INTO dim_organization 
        (org_code, org_name, org_level, org_type, parent_org_id, manager_name, phone, address, city, province, employee_count, status)
        VALUES ('ORG005', '棉兰分部', 'Regional', 'Branch', 1, 'Surya Darma', '061-12345678', 'Medan', 'North Sumatra', 45, 'active')
    """)
    conn.commit()
    
    # === 2. 获取所有需要的ID ===
    print("\n[2] 获取ID...")
    
    cursor.execute("SELECT product_id, interest_rate FROM dim_product")
    products = cursor.fetchall()
    product_ids = [p['product_id'] for p in products]
    product_rate_map = {p['product_id']: p['interest_rate'] for p in products}
    
    cursor.execute("SELECT customer_id, credit_score FROM dim_customer LIMIT 1000")
    customers = cursor.fetchall()
    customer_ids = [c['customer_id'] for c in customers]
    customer_credit_map = {c['customer_id']: c['credit_score'] for c in customers}
    
    cursor.execute("SELECT org_id FROM dim_organization")
    org_ids = [r['org_id'] for r in cursor.fetchall()]
    
    cursor.execute("SELECT time_id, date_value FROM dim_time WHERE date_value >= '2024-01-01' AND date_value <= '2024-12-31' LIMIT 365")
    times = cursor.fetchall()
    time_ids = [t['time_id'] for t in times]
    time_date_map = {t['time_id']: t['date_value'] for t in times}
    
    cursor.execute("SELECT location_id FROM dim_location")
    location_ids = [r['location_id'] for r in cursor.fetchall()]
    
    print(f"  产品: {len(product_ids)}, 客户: {len(customer_ids)}, 机构: {len(org_ids)}, 时间: {len(time_ids)}, 地域: {len(location_ids)}")
    
    # === 3. 清空旧的事实表 ===
    print("\n[3] 清空旧的事实表...")
    cursor.execute("DELETE FROM fct_loan_application")
    cursor.execute("DELETE FROM fct_loan_disbursement")
    conn.commit()
    
    # === 4. 插入贷款申请 ===
    print("\n[4] 插入贷款申请...")
    total = 500
    for i in range(1, total + 1):
        app_no = f"APP{str(i).zfill(10)}"
        cid = random.choice(customer_ids)
        pid = random.choice(product_ids)
        oid = random.choice(org_ids)
        tid = random.choice(time_ids)
        lid = random.choice(location_ids)
        
        apply_date = time_date_map[tid]
        amount = random.randint(5000, 100000)
        cycle = random.choice([3, 6, 12, 24, 36])
        credit = customer_credit_map[cid]
        
        rand_val = random.random()
        if rand_val < 0.6:
            app_status = 'approved'
            approval = 'approved'
            reject_reason = None
            approve_date = apply_date + timedelta(days=random.randint(1, 7))
        elif rand_val < 0.85:
            app_status = 'rejected'
            approval = 'rejected'
            reject_reason = random.choice(['Insufficient credit', 'High debt', 'Incomplete docs'])
            approve_date = None
        else:
            app_status = 'pending'
            approval = 'pending'
            reject_reason = None
            approve_date = None
        
        risk_score = random.uniform(300, 850)
        blacklist = 1 if random.random() < 0.05 else 0
        now = datetime.now()
        
        sql = f"""
            INSERT INTO fct_loan_application 
            (application_no, customer_id, product_id, org_id, time_id, location_id,
             apply_amount, apply_cycle, apply_term, apply_date, approve_date, reject_date,
             application_status, approval_status, reject_reason, risk_score, credit_score,
             blacklist_flag, create_time, update_time)
            VALUES ('{app_no}', {cid}, {pid}, {oid}, {tid}, {lid},
                    {amount}, {cycle}, {cycle}, '{apply_date}', {('NULL' if approve_date is None else f"'{approve_date}'")}, NULL,
                    '{app_status}', '{approval}', {('NULL' if reject_reason is None else f"'{reject_reason}'")}, {risk_score:.2f}, {credit},
                    {blacklist}, '{now}', '{now}')
        """
        cursor.execute(sql)
        
        if i % 100 == 0:
            conn.commit()
            print(f"  {i}/{total}")
    
    conn.commit()
    
    # === 5. 插入贷款发放 ===
    print("\n[5] 插入贷款发放...")
    cursor.execute("""
        SELECT application_id, customer_id, product_id, org_id, apply_amount, apply_cycle
        FROM fct_loan_application
        WHERE application_status = 'approved'
    """)
    apps = cursor.fetchall()
    
    total_dis = min(300, len(apps))
    for i in range(total_dis):
        app = apps[i]
        dis_no = f"DIS{str(i + 1).zfill(10)}"
        tid = random.choice(time_ids)
        lid = random.choice(location_ids)
        dis_date = time_date_map[tid]
        
        amount = app['apply_amount']
        cycle = app['apply_cycle']
        rate = product_rate_map[app['product_id']]
        maturity = dis_date + timedelta(days=cycle * 30)
        now = datetime.now()
        
        contract = amount * 1.15
        haircut = amount * 0.10
        net = amount - haircut
        service_fee = amount * 0.05
        
        sql = f"""
            INSERT INTO fct_loan_disbursement 
            (disbursement_no, application_id, customer_id, product_id, org_id, time_id, location_id,
             loan_amount, loan_cycle, loan_term, interest_rate, disbursement_date, maturity_date,
             contract_amount, haircut_amount, net_amount, service_fee, disbursement_status, loan_status,
             create_time, update_time)
            VALUES ('{dis_no}', {app['application_id']}, {app['customer_id']}, {app['product_id']}, {app['org_id']}, {tid}, {lid},
                    {amount}, {cycle}, {cycle * 30}, {rate}, '{dis_date}', '{maturity}',
                    {contract}, {haircut}, {net}, {service_fee}, 'disbursed', 'active',
                    '{now}', '{now}')
        """
        cursor.execute(sql)
        
        if (i + 1) % 100 == 0:
            conn.commit()
            print(f"  {i + 1}/{total_dis}")
    
    conn.commit()
    
    # === 6. 最终统计 ===
    print("\n[6] 最终数据统计:")
    print("-"*60)
    
    tables = [
        'dim_time', 'dim_product', 'dim_customer', 'dim_location', 
        'dim_organization', 'fct_loan_application', 'fct_loan_disbursement'
    ]
    
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) AS cnt FROM {table}")
        count = cursor.fetchone()['cnt']
        print(f"  {table:25s} {count:10d} 条")
    
    print("-"*60)
    print("\n完成！")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()

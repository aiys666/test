# -*- coding: utf-8 -*-
"""
简单的数据填充脚本
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
    conn = mysql.connector.connect(**DB_CONFIG)
    return conn

def fill_organizations(conn):
    print("[1] 插入机构数据...")
    cursor = conn.cursor()
    
    # 先删除旧数据（如果有）
    cursor.execute("DELETE FROM dim_organization")
    conn.commit()
    
    orgs = [
        ('ORG001', '嘉银科技总部', 'Headquarters', 'Technology', None, 'Zhang Wei', '021-12345678', 'Jakarta Pusat', 'DKI Jakarta', 500, 'active'),
        ('ORG002', '雅加达分部', 'Regional', 'Branch', 1, 'Ahmad Rizki', '021-87654321', 'Jakarta Selatan', 'DKI Jakarta', 120, 'active'),
        ('ORG003', '泗水分部', 'Regional', 'Branch', 1, 'Budi Santoso', '031-12345678', 'Surabaya', 'East Java', 80, 'active'),
        ('ORG004', '万隆分部', 'Regional', 'Branch', 1, 'Dewi Lestari', '022-12345678', 'Bandung', 'West Java', 60, 'active'),
        ('ORG005', '棉兰分部', 'Regional', 'Branch', 1, 'Surya Darma', '061-12345678', 'Medan', 'North Sumatra', 45, 'active'),
    ]
    
    for org in orgs:
        sql = """INSERT INTO dim_organization (
            org_code, org_name, org_level, org_type, parent_org_id,
            manager_name, phone, address, city, province, employee_count, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(sql, org)
    
    conn.commit()
    cursor.close()
    print(f"  插入了 {len(orgs)} 个机构")

def get_data_ids(conn):
    print("\n[2] 获取ID...")
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT product_id FROM dim_product")
    product_ids = [r['product_id'] for r in cursor.fetchall()]
    
    cursor.execute("SELECT customer_id FROM dim_customer LIMIT 1000")
    customer_ids = [r['customer_id'] for r in cursor.fetchall()]
    
    cursor.execute("SELECT org_id FROM dim_organization")
    org_ids = [r['org_id'] for r in cursor.fetchall()]
    
    cursor.execute("SELECT time_id, date_value FROM dim_time WHERE date_value >= '2024-01-01' AND date_value <= '2024-12-31' LIMIT 365")
    time_data = cursor.fetchall()
    time_ids = [t['time_id'] for t in time_data]
    time_date_map = {t['time_id']: t['date_value'] for t in time_data}
    
    cursor.execute("SELECT location_id FROM dim_location")
    location_ids = [r['location_id'] for r in cursor.fetchall()]
    
    cursor.close()
    
    print(f"  产品: {len(product_ids)}个, 客户: {len(customer_ids)}个, 机构: {len(org_ids)}个, 时间: {len(time_ids)}个, 地域: {len(location_ids)}个")
    return product_ids, customer_ids, org_ids, time_ids, time_date_map, location_ids

def fill_loan_applications(conn, product_ids, customer_ids, org_ids, time_ids, time_date_map, location_ids):
    print("\n[3] 插入贷款申请...")
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("DELETE FROM fct_loan_application")
    conn.commit()
    
    # 获取客户信用分
    cursor.execute("SELECT customer_id, credit_score FROM dim_customer LIMIT 1000")
    customer_credit = {r['customer_id']: r['credit_score'] for r in cursor.fetchall()}
    
    total = 500
    inserted = 0
    
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
        
        rand_val = random.random()
        if rand_val < 0.6:
            status = 'approved'
            approval = 'approved'
            reject = None
            approve_date = apply_date + timedelta(days=random.randint(1, 7))
        elif rand_val < 0.85:
            status = 'rejected'
            approval = 'rejected'
            reject = random.choice(['Insufficient credit', 'High debt', 'Incomplete docs'])
            approve_date = None
        else:
            status = 'pending'
            approval = 'pending'
            reject = None
            approve_date = None
        
        risk = random.uniform(300, 850)
        credit = customer_credit[cid]
        blacklist = 1 if random.random() < 0.05 else 0
        now = datetime.now()
        
        sql = """INSERT INTO fct_loan_application (
            application_no, customer_id, product_id, org_id, time_id, location_id,
            apply_amount, apply_cycle, apply_term, apply_date, approve_date, reject_date,
            application_status, approval_status, reject_reason, risk_score, credit_score,
            blacklist_flag, create_time, update_time
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        
        cursor.execute(sql, (
            app_no, cid, pid, oid, tid, lid,
            amount, cycle, cycle, apply_date, approve_date, None,
            status, approval, reject, risk, credit, blacklist, now, now
        ))
        inserted += 1
        
        if inserted % 100 == 0:
            conn.commit()
            print(f"  已插入 {inserted}/{total} 条")
    
    conn.commit()
    cursor.close()
    print(f"  完成！共 {inserted} 条申请")

def fill_loan_disbursements(conn, product_ids, customer_ids, org_ids, time_ids, time_date_map, location_ids):
    print("\n[4] 插入贷款发放...")
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("DELETE FROM fct_loan_disbursement")
    conn.commit()
    
    # 获取已通过的申请
    cursor.execute("""
        SELECT application_id, customer_id, product_id, org_id, apply_amount, apply_cycle
        FROM fct_loan_application
        WHERE application_status = 'approved'
    """)
    apps = cursor.fetchall()
    
    if not apps:
        print("  没有通过的申请")
        cursor.close()
        return
    
    total = min(300, len(apps))
    inserted = 0
    
    # 获取产品利率
    cursor.execute("SELECT product_id, interest_rate FROM dim_product")
    product_rates = {r['product_id']: r['interest_rate'] for r in cursor.fetchall()}
    
    for i in range(total):
        app = apps[i]
        dis_no = f"DIS{str(i + 1).zfill(10)}"
        
        tid = random.choice(time_ids)
        lid = random.choice(location_ids)
        dis_date = time_date_map[tid]
        
        amount = app['apply_amount']
        cycle = app['apply_cycle']
        rate = product_rates[app['product_id']]
        
        contract = amount * 1.15
        haircut = amount * 0.10
        net = amount - haircut
        service_fee = amount * 0.05
        maturity = dis_date + timedelta(days=cycle * 30)
        now = datetime.now()
        
        sql = """INSERT INTO fct_loan_disbursement (
            disbursement_no, application_id, customer_id, product_id, org_id, time_id, location_id,
            loan_amount, loan_cycle, loan_term, interest_rate, disbursement_date, maturity_date,
            contract_amount, haircut_amount, net_amount, service_fee, disbursement_status, loan_status,
            create_time, update_time
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        
        cursor.execute(sql, (
            dis_no, app['application_id'], app['customer_id'], app['product_id'], app['org_id'], tid, lid,
            amount, cycle, cycle * 30, rate, dis_date, maturity,
            contract, haircut, net, service_fee, 'disbursed', 'active', now, now
        ))
        inserted += 1
        
        if inserted % 100 == 0:
            conn.commit()
            print(f"  已插入 {inserted}/{total} 条")
    
    conn.commit()
    cursor.close()
    print(f"  完成！共 {inserted} 条发放")

def show_count(conn):
    print("\n[5] 最终数据统计:")
    print("-"*60)
    cursor = conn.cursor()
    
    tables = [
        'dim_time', 'dim_product', 'dim_customer', 'dim_location', 
        'dim_organization', 'fct_loan_application', 'fct_loan_disbursement'
    ]
    
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table:25s} {count:10d}")
    
    cursor.close()
    print("-"*60)

def main():
    print("="*60)
    print("填充数据库数据")
    print("="*60)
    
    conn = connect_db()
    
    fill_organizations(conn)
    product_ids, customer_ids, org_ids, time_ids, time_date_map, location_ids = get_data_ids(conn)
    fill_loan_applications(conn, product_ids, customer_ids, org_ids, time_ids, time_date_map, location_ids)
    fill_loan_disbursements(conn, product_ids, customer_ids, org_ids, time_ids, time_date_map, location_ids)
    show_count(conn)
    
    conn.close()
    print("\n完成！")

if __name__ == "__main__":
    main()

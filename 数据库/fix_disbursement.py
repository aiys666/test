# -*- coding: utf-8 -*-
"""
修复发放表
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

def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    
    print("获取产品和申请数据...")
    
    # 获取产品
    cursor.execute("SELECT product_id, interest_rate FROM dim_product")
    product_rate_map = {r['product_id']: r['interest_rate'] for r in cursor.fetchall()}
    
    # 获取时间
    cursor.execute("SELECT time_id, date_value FROM dim_time WHERE date_value >= '2024-01-01' AND date_value <= '2024-12-31' LIMIT 365")
    times = cursor.fetchall()
    time_ids = [t['time_id'] for t in times]
    time_date_map = {t['time_id']: t['date_value'] for t in times}
    
    # 获取地域
    cursor.execute("SELECT location_id FROM dim_location")
    location_ids = [r['location_id'] for r in cursor.fetchall()]
    
    # 获取已通过的申请
    cursor.execute("""
        SELECT application_id, customer_id, product_id, org_id, apply_amount, apply_cycle
        FROM fct_loan_application
        WHERE application_status = 'approved'
    """)
    apps = cursor.fetchall()
    
    print(f"已获取 {len(apps)} 个已通过的申请")
    
    # 清空旧数据
    cursor.execute("DELETE FROM fct_loan_disbursement")
    conn.commit()
    
    print("开始插入发放数据...")
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
        
        # 转换 Decimal 为 float
        amount_val = float(amount) if amount else 0
        
        contract = amount_val * 1.15
        haircut = amount_val * 0.10
        net = amount_val - haircut
        service_fee = amount_val * 0.05
        
        sql = f"""
            INSERT INTO fct_loan_disbursement 
            (disbursement_no, application_id, customer_id, product_id, org_id, time_id, location_id,
             loan_amount, loan_cycle, loan_term, interest_rate, disbursement_date, maturity_date,
             contract_amount, haircut_amount, net_amount, service_fee, disbursement_status, loan_status,
             create_time, update_time)
            VALUES ('{dis_no}', {app['application_id']}, {app['customer_id']}, {app['product_id']}, {app['org_id']}, {tid}, {lid},
                    {amount_val}, {cycle}, {cycle * 30}, {float(rate) if rate else 0}, '{dis_date}', '{maturity}',
                    {contract}, {haircut}, {net}, {service_fee}, 'disbursed', 'active',
                    '{now}', '{now}')
        """
        cursor.execute(sql)
        
        if (i + 1) % 100 == 0:
            conn.commit()
            print(f"  {i + 1}/{total_dis}")
    
    conn.commit()
    
    print("\n最终统计:")
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
    
    cursor.close()
    conn.close()
    print("\n完成！")

if __name__ == "__main__":
    main()

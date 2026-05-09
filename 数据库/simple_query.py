# -*- coding: utf-8 -*-
"""
MySQL数据库查询验证脚本 - 简洁版
"""

import mysql.connector
from datetime import datetime

# 数据库配置
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
        print("="*60)
        print("数据库连接成功！")
        print(f"主机: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
        print(f"数据库: {DB_CONFIG['database']}")
        print("="*60)
        print()
        return conn
    except mysql.connector.Error as err:
        print(f"数据库连接失败: {err}")
        return None

def show_tables(conn):
    print("[1] 查看所有表:")
    print("-"*60)
    
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    
    print(f"共找到 {len(tables)} 个表:")
    for i, table in enumerate(tables, 1):
        print(f"  {i}. {table[0]}")
    
    cursor.close()
    print()

def show_table_counts(conn):
    print("[2] 各表数据量统计:")
    print("-"*60)
    
    tables = [
        'dim_time',
        'dim_product',
        'dim_customer',
        'dim_location',
        'dim_organization',
        'fct_loan_application',
        'fct_loan_disbursement'
    ]
    
    cursor = conn.cursor()
    
    for table_name in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  {table_name:25s} {count:10d} 条记录")
        except mysql.connector.Error as err:
            print(f"  {table_name:25s} 查询失败")
    
    cursor.close()
    print()

def show_products(conn):
    print("[3] 产品列表:")
    print("-"*60)
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT product_code, product_name, risk_level, interest_rate, min_loan_amount, max_loan_amount FROM dim_product")
    rows = cursor.fetchall()
    
    if rows:
        for row in rows:
            rate = row['interest_rate'] * 100 if row['interest_rate'] else 0
            print(f"  {row['product_code']} - {row['product_name']} [{row['risk_level']}]")
            print(f"    利率: {rate:.2f}%, 金额范围: {row['min_loan_amount']}-{row['max_loan_amount']}")
    
    cursor.close()
    print()

def show_customers_sample(conn):
    print("[4] 客户样本（前10条）:")
    print("-"*60)
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT customer_code, customer_name, age, city, credit_score, risk_level FROM dim_customer LIMIT 10")
    rows = cursor.fetchall()
    
    if rows:
        for row in rows:
            print(f"  {row['customer_code']} - {row['customer_name']} ({row['age']}岁, {row['city']})")
            print(f"    信用分: {row['credit_score']}, 风险等级: {row['risk_level']}")
    
    cursor.close()
    print()

def show_applications_sample(conn):
    print("[5] 贷款申请样本（前10条）:")
    print("-"*60)
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT a.application_no, p.product_name, a.apply_amount, 
               a.application_status, a.approval_status
        FROM fct_loan_application a
        JOIN dim_product p ON a.product_id = p.product_id
        LIMIT 10
    """)
    rows = cursor.fetchall()
    
    if rows:
        for row in rows:
            status_text = f"申请状态: {row['application_status']}, 审批状态: {row['approval_status']}"
            print(f"  {row['application_no']} - {row['product_name']} - {row['apply_amount']}")
            print(f"    {status_text}")
    
    cursor.close()
    print()

def show_disbursements_sample(conn):
    print("[6] 贷款发放样本（前10条）:")
    print("-"*60)
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT d.disbursement_no, p.product_name, d.loan_amount, 
               d.loan_cycle, d.interest_rate
        FROM fct_loan_disbursement d
        JOIN dim_product p ON d.product_id = p.product_id
        LIMIT 10
    """)
    rows = cursor.fetchall()
    
    if rows:
        for row in rows:
            rate = row['interest_rate'] * 100 if row['interest_rate'] else 0
            print(f"  {row['disbursement_no']} - {row['product_name']}")
            print(f"    金额: {row['loan_amount']}, 周期: {row['loan_cycle']}月, 利率: {rate:.2f}%")
    
    cursor.close()
    print()

def show_statistics(conn):
    print("[7] 统计分析:")
    print("-"*60)
    
    cursor = conn.cursor(dictionary=True)
    
    # 按产品统计
    print("\n[7.1] 按产品统计申请情况:")
    cursor.execute("""
        SELECT p.product_name,
               COUNT(*) as total,
               SUM(CASE WHEN a.application_status = 'approved' THEN 1 ELSE 0 END) as approved
        FROM fct_loan_application a
        JOIN dim_product p ON a.product_id = p.product_id
        GROUP BY p.product_name
    """)
    rows = cursor.fetchall()
    for row in rows:
        approval_rate = row['approved'] * 100.0 / row['total'] if row['total'] > 0 else 0
        print(f"  {row['product_name']}: 总 {row['total']} 件, 通过 {row['approved']} 件, 通过率 {approval_rate:.1f}%")
    
    # 按风险等级统计客户
    print("\n[7.2] 按风险等级统计客户:")
    cursor.execute("""
        SELECT risk_level, COUNT(*) as count
        FROM dim_customer
        GROUP BY risk_level
    """)
    rows = cursor.fetchall()
    for row in rows:
        print(f"  {row['risk_level']}: {row['count']} 人")
    
    cursor.close()
    print()

def main():
    conn = connect_db()
    if not conn:
        return
    
    try:
        show_tables(conn)
        show_table_counts(conn)
        show_products(conn)
        show_customers_sample(conn)
        show_applications_sample(conn)
        show_disbursements_sample(conn)
        show_statistics(conn)
        
        print("="*60)
        print("查询完成！")
        print("="*60)
    finally:
        conn.close()
        print("\n数据库连接已关闭")

if __name__ == "__main__":
    main()

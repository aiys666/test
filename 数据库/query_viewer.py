# -*- coding: utf-8 -*-
"""
MySQL数据库查询验证脚本
用于测试连接并查看查询结果
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
    """连接数据库"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        print("✅ 数据库连接成功！")
        print(f"   主机: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
        print(f"   数据库: {DB_CONFIG['database']}")
        print(f"   用户: {DB_CONFIG['user']}")
        print()
        return conn
    except mysql.connector.Error as err:
        print(f"❌ 数据库连接失败: {err}")
        return None

def show_tables(conn):
    """查看所有表"""
    print("="*60)
    print("📋 一、查看所有表")
    print("="*60)
    
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    
    print(f"   共找到 {len(tables)} 个表:")
    for i, table in enumerate(tables, 1):
        print(f"   {i:2d}. {table[0]}")
    
    cursor.close()
    print()

def show_table_row_counts(conn):
    """查看各表数据量"""
    print("="*60)
    print("📊 二、各表数据量统计")
    print("="*60)
    
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
    
    print(f"   {'表名':<25} {'数据量':>12}")
    print("   " + "-"*37)
    
    for table_name in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"   {table_name:<25} {count:12d}")
        except mysql.connector.Error as err:
            print(f"   {table_name:<25} 查询失败: {err}")
    
    cursor.close()
    print()

def sample_dim_time(conn):
    """查看时间维度表样本数据"""
    print("="*60)
    print("📅 三、时间维度表样本数据")
    print("="*60)
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM dim_time LIMIT 10")
    rows = cursor.fetchall()
    
    if rows:
        print(f"   显示前 {len(rows)} 条记录:")
        print()
        print("   " + "="*120)
        
        # 打印表头
        headers = list(rows[0].keys())
        header_line = "   "
        for h in headers:
            header_line += f"{h:<15} "
        print(header_line)
        
        print("   " + "="*120)
        
        # 打印数据
        for row in rows:
            line = "   "
            for h in headers:
                val = str(row[h]) if row[h] is not None else "NULL"
                line += f"{val:<15} "
            print(line)
        
        print("   " + "="*120)
    else:
        print("   表为空")
    
    cursor.close()
    print()

def sample_dim_product(conn):
    """查看产品维度表数据"""
    print("="*60)
    print("🏦 四、产品维度表数据")
    print("="*60)
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM dim_product")
    rows = cursor.fetchall()
    
    if rows:
        print(f"   共 {len(rows)} 个产品:")
        print()
        print("   " + "="*100)
        print(f"   {'产品代码':<12} {'产品名称':<15} {'风险等级':<8} {'利率':<8} {'最低金额':<12} {'最高金额':<12}")
        print("   " + "="*100)
        
        for row in rows:
            rate = row['interest_rate'] * 100 if row['interest_rate'] else 0
            print(f"   {row['product_code']:<12} {row['product_name']:<15} {row['risk_level']:<8} {rate:6.2f}% {row['min_loan_amount']:<12} {row['max_loan_amount']:<12}")
        
        print("   " + "="*100)
    else:
        print("   表为空")
    
    cursor.close()
    print()

def sample_dim_customer(conn):
    """查看客户维度表样本数据"""
    print("="*60)
    print("👤 五、客户维度表样本数据（前20条）")
    print("="*60)
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT customer_id, customer_code, customer_name, age, gender, city, credit_score, risk_level, customer_level FROM dim_customer LIMIT 20")
    rows = cursor.fetchall()
    
    if rows:
        print(f"   显示前 {len(rows)} 条记录:")
        print()
        print("   " + "="*100)
        print(f"   {'客户ID':<8} {'客户代码':<15} {'姓名':<15} {'年龄':<5} {'性别':<8} {'城市':<12} {'信用分':<8} {'风险等级':<8} {'客户等级':<8}")
        print("   " + "="*100)
        
        for row in rows:
            print(f"   {row['customer_id']:<8} {row['customer_code']:<15} {row['customer_name']:<15} {row['age']:<5} {row['gender']:<8} {row['city']:<12} {row['credit_score']:<8} {row['risk_level']:<8} {row['customer_level']:<8}")
        
        print("   " + "="*100)
    else:
        print("   表为空")
    
    cursor.close()
    print()

def sample_loan_applications(conn):
    """查看贷款申请事实表样本数据"""
    print("="*60)
    print("📝 六、贷款申请事实表样本数据（前10条）")
    print("="*60)
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT a.application_id, a.application_no, p.product_name, a.apply_amount, 
               a.apply_cycle, a.application_status, a.approval_status, a.credit_score
        FROM fct_loan_application a
        JOIN dim_product p ON a.product_id = p.product_id
        LIMIT 10
    """)
    rows = cursor.fetchall()
    
    if rows:
        print(f"   显示前 {len(rows)} 条记录:")
        print()
        print("   " + "="*100)
        print(f"   {'申请ID':<8} {'申请编号':<15} {'产品名称':<15} {'申请金额':<12} {'周期':<6} {'状态':<10} {'审批状态':<10} {'信用分':<8}")
        print("   " + "="*100)
        
        for row in rows:
            print(f"   {row['application_id']:<8} {row['application_no']:<15} {row['product_name']:<15} {row['apply_amount']:<12} {row['apply_cycle']:<6} {row['application_status']:<10} {row['approval_status']:<10} {row['credit_score']:<8}")
        
        print("   " + "="*100)
    else:
        print("   表为空")
    
    cursor.close()
    print()

def sample_loan_disbursements(conn):
    """查看贷款发放事实表样本数据"""
    print("="*60)
    print("💰 七、贷款发放事实表样本数据（前10条）")
    print("="*60)
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT d.disbursement_id, d.disbursement_no, p.product_name, d.loan_amount,
               d.loan_cycle, d.interest_rate, d.contract_amount, d.net_amount
        FROM fct_loan_disbursement d
        JOIN dim_product p ON d.product_id = p.product_id
        LIMIT 10
    """)
    rows = cursor.fetchall()
    
    if rows:
        print(f"   显示前 {len(rows)} 条记录:")
        print()
        print("   " + "="*100)
        print(f"   {'发放ID':<8} {'发放编号':<15} {'产品名称':<15} {'贷款金额':<12} {'周期':<6} {'利率':<8} {'合同金额':<12} {'净发放':<12}")
        print("   " + "="*100)
        
        for row in rows:
            rate = row['interest_rate'] * 100 if row['interest_rate'] else 0
            print(f"   {row['disbursement_id']:<8} {row['disbursement_no']:<15} {row['product_name']:<15} {row['loan_amount']:<12} {row['loan_cycle']:<6} {rate:6.2f}% {row['contract_amount']:<12} {row['net_amount']:<12}")
        
        print("   " + "="*100)
    else:
        print("   表为空")
    
    cursor.close()
    print()

def simple_analysis(conn):
    """简单的统计分析"""
    print("="*60)
    print("📈 八、简单统计分析")
    print("="*60)
    
    cursor = conn.cursor(dictionary=True)
    
    # 按产品统计申请情况
    print("   1. 按产品统计申请情况:")
    cursor.execute("""
        SELECT p.product_name,
               COUNT(*) as total_applications,
               SUM(CASE WHEN a.application_status = 'approved' THEN 1 ELSE 0 END) as approved_count,
               ROUND(SUM(CASE WHEN a.application_status = 'approved' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as approval_rate
        FROM fct_loan_application a
        JOIN dim_product p ON a.product_id = p.product_id
        GROUP BY p.product_name
        ORDER BY total_applications DESC
    """)
    rows = cursor.fetchall()
    
    if rows:
        print("      " + "-"*80)
        print(f"      {'产品名称':<15} {'申请数量':<12} {'通过数量':<12} {'通过率':<10}")
        print("      " + "-"*80)
        for row in rows:
            print(f"      {row['product_name']:<15} {row['total_applications']:<12} {row['approved_count']:<12} {row['approval_rate']:>8}%")
        print("      " + "-"*80)
    else:
        print("      无数据")
    
    print()
    
    # 按风险等级统计客户
    print("   2. 按风险等级统计客户分布:")
    cursor.execute("""
        SELECT risk_level,
               COUNT(*) as customer_count,
               AVG(credit_score) as avg_credit_score
        FROM dim_customer
        GROUP BY risk_level
        ORDER BY customer_count DESC
    """)
    rows = cursor.fetchall()
    
    if rows:
        print("      " + "-"*70)
        print(f"      {'风险等级':<10} {'客户数量':<12} {'平均信用分':<15}")
        print("      " + "-"*70)
        for row in rows:
            print(f"      {row['risk_level']:<10} {row['customer_count']:<12} {row['avg_credit_score']:>15.2f}")
        print("      " + "-"*70)
    else:
        print("      无数据")
    
    cursor.close()
    print()

def main():
    print()
    print("╔" + "═"*58 + "╗")
    print("║" + " " * 15 + "YSProd 数据库查询工具" + " " * 22 + "║")
    print("╚" + "═"*58 + "╝")
    print()
    print(f"⏰ 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 连接数据库
    conn = connect_db()
    if not conn:
        return
    
    try:
        # 执行各种查询
        show_tables(conn)
        show_table_row_counts(conn)
        sample_dim_time(conn)
        sample_dim_product(conn)
        sample_dim_customer(conn)
        sample_loan_applications(conn)
        sample_loan_disbursements(conn)
        simple_analysis(conn)
        
        print("="*60)
        print("✅ 查询完成！")
        print("="*60)
        print()
        print("💡 提示: 如果在IDE中看不到查询结果，")
        print("   可以运行这个Python脚本来查看！")
        print()
    finally:
        conn.close()
        print("🔌 数据库连接已关闭")

if __name__ == "__main__":
    main()

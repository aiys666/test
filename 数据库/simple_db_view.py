# -*- coding: utf-8 -*-
"""
极简版数据库查看器 - 无特殊字符
"""

import mysql.connector

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

    print("="*70)
    print("YSProd 数据库概览")
    print("="*70)
    print()
    print("数据库连接信息:")
    print(f"  主机: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"  数据库: {DB_CONFIG['database']}")
    print(f"  用户: {DB_CONFIG['user']}")
    print()

    print("="*70)
    print("数据表列表")
    print("="*70)
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    for i, row in enumerate(tables, 1):
        print(f"  {i}. {list(row.values())[0]}")
    print()

    print("="*70)
    print("各表数据量")
    print("="*70)
    total = 0
    for row in tables:
        table_name = list(row.values())[0]
        cursor.execute(f"SELECT COUNT(*) as cnt FROM {table_name}")
        count = cursor.fetchone()['cnt']
        total += count
        bar = "#" * int(count / max(1, total / 30))
        print(f"  {table_name:30s} {count:>8,} 条 {bar}")
    print(f"  {'总计':30s} {total:>8,} 条")
    print()

    print("="*70)
    print("数据表结构详情")
    print("="*70)

    for row in tables:
        table_name = list(row.values())[0]
        print(f"\n表名: {table_name}")
        print("-" * 70)

        cursor.execute(f"DESCRIBE {table_name}")
        columns = cursor.fetchall()

        for col in columns:
            field = col['Field']
            col_type = col['Type']
            nullable = 'Y' if col['Null'] == 'YES' else 'N'
            key = 'PK' if col['Key'] else ''
            print(f"    {field:30s} {col_type:20s} Null:{nullable} Key:{key}")

    print()
    print("="*70)
    print("表关系说明")
    print("="*70)
    print("""
    星型模型架构:

         dim_time (时间维度)
              |
    +---------+---------+
    |         |         |
    v         v         v
dim_customer  fct_loan_  dim_product
(客户维度)   application (产品维度)
    |      (贷款申请)     |
    |           |        |
    +----->fct_loan_<-----+
      disbursement
      (贷款发放)
    |           |
    v           v
dim_location  dim_organization
(地域维度)   (机构维度)
    """)

    print("="*70)
    print("查询方法")
    print("="*70)
    print("""
    在Trae IDE中运行SQL查询:
    1. 打开 mysql_queries.sql 文件
    2. 选中要执行的SQL语句
    3. 按 Ctrl+Shift+Enter 执行
    4. 结果会在下方面板显示

    或者在终端中运行:
    python simple_query.py
    python database_viewer.py
    """)

    print("="*70)

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
简洁版数据库查看器
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
    print("YSProd 数据库结构查看器")
    print("="*70)
    print()
    print(f"主机: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"数据库: {DB_CONFIG['database']}")
    print(f"用户: {DB_CONFIG['user']}")
    print()

    # 显示所有表
    print("="*70)
    print("所有数据表:")
    print("="*70)
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    for i, row in enumerate(tables, 1):
        print(f"  {i}. {list(row.values())[0]}")
    print()

    # 显示各表数据量
    print("="*70)
    print("各表数据量统计:")
    print("="*70)
    total = 0
    for row in tables:
        table_name = list(row.values())[0]
        cursor.execute(f"SELECT COUNT(*) as cnt FROM {table_name}")
        count = cursor.fetchone()['cnt']
        total += count
        print(f"  {table_name:30s}: {count:>10,} 条")
    print(f"  {'总计':30s}: {total:>10,} 条")
    print()

    # 显示表结构
    print("="*70)
    print("表结构详情:")
    print("="*70)

    for row in tables:
        table_name = list(row.values())[0]
        print(f"\n【{table_name}】")
        print("-" * 70)

        cursor.execute(f"DESCRIBE {table_name}")
        columns = cursor.fetchall()

        print(f"  {'字段名':25s} {'类型':20s} {'可空':6s} {'主键':6s}")
        print("  " + "-" * 60)

        for col in columns:
            field = col['Field']
            col_type = col['Type']
            nullable = '否' if col['Null'] == 'NO' else '是'
            key = '是' if col['Key'] else '否'
            print(f"  {field:25s} {col_type:20s} {nullable:6s} {key:6s}")

        # 显示前3条数据
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
        sample = cursor.fetchall()
        if sample:
            print(f"\n  数据预览（前3条）:")
            headers = list(sample[0].keys())
            for h in headers[:6]:
                print(f"    {h}")
            print("  ...")

    # 显示ER关系
    print()
    print("="*70)
    print("表关系（星型模型）:")
    print("="*70)
    print("""
                    dim_time
                 (时间维度)
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
   dim_customer   fct_loan_    dim_product
   (客户维度)    application   (产品维度)
        │       (贷款申请)         │
        │            │             │
        │            ▼             │
        │    fct_loan_            │
        └────▶disbursement◀───────┘
           (贷款发放事实表)
        │            │
        ▼            ▼
   dim_location   dim_organization
   (地域维度)    (机构维度)
    """)

    print("="*70)
    print("查看完成!")
    print("="*70)

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()

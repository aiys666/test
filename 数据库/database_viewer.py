# -*- coding: utf-8 -*-
"""
超直观的数据库结构查看器
"""

import mysql.connector
from datetime import datetime

DB_CONFIG = {
    'host': '47.121.121.48',
    'port': 3306,
    'user': 'yuesong',
    'password': 'yuesongnb',
    'database': 'YSProd'
}

def print_banner():
    print()
    print("╔" + "═"*70 + "╗")
    print("║" + " "*15 + "YSProd 数据库结构查看器" + " "*28 + "║")
    print("╚" + "═"*70 + "╝")
    print()

def connect_db():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"连接失败: {err}")
        return None

def show_database_info(conn):
    cursor = conn.cursor(dictionary=True)

    print("┌" + "─"*70 + "┐")
    print("│ 数据库连接信息" + " "*51 + "│")
    print("├" + "─"*70 + "┤")
    print(f"│ 主机: {DB_CONFIG['host']}:{DB_CONFIG['port']}" + " "*37 + "│")
    print(f"│ 数据库: {DB_CONFIG['database']}" + " "*48 + "│")
    print(f"│ 用户: {DB_CONFIG['user']}" + " "*52 + "│")
    print("└" + "─"*70 + "┘")
    print()

    cursor.close()

def show_all_tables(conn):
    cursor = conn.cursor(dictionary=True)

    print("┌" + "═"*70 + "┐")
    print("│ 所有数据表一览" + " "*52 + "│")
    print("╠" + "═"*70 + "╣")
    print("│ 序号  │ 表名                        │ 类型    │ 说明" + " "*21 + "│")
    print("├" + "─"*70 + "┤")

    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()

    table_types = {
        'dim_time': '维度表',
        'dim_product': '维度表',
        'dim_customer': '维度表',
        'dim_location': '维度表',
        'dim_organization': '维度表',
        'fct_loan_application': '事实表',
        'fct_loan_disbursement': '事实表',
    }

    table_desc = {
        'dim_time': '时间维度',
        'dim_product': '产品维度',
        'dim_customer': '客户维度',
        'dim_location': '地域维度',
        'dim_organization': '机构维度',
        'fct_loan_application': '贷款申请',
        'fct_loan_disbursement': '贷款发放',
    }

    for i, row in enumerate(tables, 1):
        table_name = list(row.values())[0]
        table_type = table_types.get(table_name, '未知')
        desc = table_desc.get(table_name, '')
        print(f"│ {i:2d}   │ {table_name:27s} │ {table_type:7s} │ {desc:26s} │")

    print("└" + "─"*70 + "┘")
    print()

    cursor.close()
    return [list(row.values())[0] for row in tables]

def show_table_structure(conn, table_name):
    cursor = conn.cursor()

    print()
    print("┌" + "═"*70 + "┐")
    print(f"│ {table_name} 表结构" + " "* (67 - len(table_name)) + "│")
    print("╠" + "═"*70 + "╣")
    print("│ 字段名                    │ 类型              │ 可空  │ 主键  │ 说明" + " "*17 + "│")
    print("├" + "─"*70 + "┤")

    cursor.execute(f"DESCRIBE {table_name}")
    columns = cursor.fetchall()

    for col in columns:
        field_name = col[0]
        col_type = col[1]
        nullable = '否' if col[2] == 'NO' else '是'
        key = '是' if col[3] else '否'
        extra = col[5] if col[5] else ''

        print(f"│ {field_name:24s} │ {col_type:17s} │ {nullable:5s} │ {key:5s} │ {extra:23s} │")

    print("└" + "─"*70 + "┘")
    print()

    cursor.close()

def show_table_data_preview(conn, table_name, limit=5):
    cursor = conn.cursor(dictionary=True)

    print("┌" + "═"*70 + "┐")
    print(f"│ {table_name} 数据预览（前{limit}条）" + " "* (54 - len(table_name) - len(str(limit))) + "│")
    print("╠" + "═"*70 + "╣")

    cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
    rows = cursor.fetchall()

    if not rows:
        print("│ 无数据" + " "*63 + "│")
        print("└" + "─"*70 + "┘")
        print()
        cursor.close()
        return

    headers = list(rows[0].keys())

    header_line = "│ "
    for h in headers[:5]:
        header_line += f"{h:20s} │ "
    if len(headers) > 5:
        header_line += "..."
    header_line += " " * (69 - len(header_line)) + "│"
    print(header_line)

    print("├" + "─"*70 + "┤")

    for row in rows:
        line = "│ "
        for i, h in enumerate(headers[:5]):
            val = str(row[h])[:20] if row[h] is not None else 'NULL'
            line += f"{val:20s} │ "
        if len(headers) > 5:
            line += "..."
        line += " " * (69 - len(line)) + "│"
        print(line)

    print("└" + "─"*70 + "┘")
    print()

    cursor.close()

def show_row_counts(conn):
    cursor = conn.cursor(dictionary=True)

    print()
    print("┌" + "═"*70 + "┐")
    print("│ 各表数据量统计" + " "*52 + "│")
    print("╠" + "═"*70 + "╣")
    print("│ 表名                        │ 数据量          │ 可视化" + " "*27 + "│")
    print("├" + "─"*70 + "┤")

    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()

    total_rows = 0
    for row in tables:
        table_name = list(row.values())[0]
        cursor.execute(f"SELECT COUNT(*) as cnt FROM {table_name}")
        count = cursor.fetchone()['cnt']
        total_rows += count

        bar_len = int(count / max(1, total_rows / 50)) if total_rows > 0 else 0
        bar = "█" * bar_len

        print(f"│ {table_name:24s} │ {count:>10d} 条    │ {bar:50s} │")

    print("├" + "─"*70 + "┤")
    print(f"│ 总计" + " "*62 + "│")
    print(f"│ 总数据量" + " "*57 + "│")
    print(f"│ {total_rows:>13d} 条" + " "*53 + "│")
    print("└" + "─"*70 + "┘")
    print()

    cursor.close()

def show_relationships(conn):
    print()
    print("┌" + "═"*70 + "┐")
    print("│ 表关系图（星型模型）" + " "*47 + "│")
    print("╠" + "═"*70 + "╣")
    print("│" + " "*70 + "│")
    print("│              ┌─────────────┐" + " "*39 + "│")
    print("│              │  dim_time   │" + " "*39 + "│")
    print("│              │ (时间维度)  │" + " "*39 + "│")
    print("│              └──────┬──────┘" + " "*39 + "│")
    print("│                     │" + " "*49 + "│")
    print("│     ┌───────────────┼───────────────┐" + " "*25 + "│")
    print("│     │               │               │" + " "*25 + "│")
    print("│     ▼               ▼               ▼" + " "*37 + "│")
    print("│ ┌──────────┐ ┌─────────────────┐ ┌──────────────┐" + " "*14 + "│")
    print("│ │dim_customer│ │fct_loan_        │ │dim_product   │" + " "*14 + "│")
    print("│ │(客户维度) │ │application      │ │(产品维度)    │" + " "*14 + "│")
    print("│ └─────┬────┘ │(贷款申请事实表) │ └──────┬───────┘" + " "*14 + "│")
    print("│       │      └────────┬──────────┘        │" + " "*19 + "│")
    print("│       │               │                   │" + " "*19 + "│")
    print("│       │               ▼                   │" + " "*19 + "│")
    print("│       │      ┌────────────────┐           │" + " "*19 + "│")
    print("│       └─────▶│fct_loan_       │           │" + " "*19 + "│")
    print("│              │disbursement     │           │" + " "*19 + "│")
    print("│              │(贷款发放事实表) │           │" + " "*19 + "│")
    print("│              └───────┬─────────┘           │" + " "*19 + "│")
    print("│                      │                    │" + " "*19 + "│")
    print("│              ┌────────┴────────┐          │" + " "*19 + "│")
    print("│              ▼                 ▼          │" + " "*19 + "│")
    print("│       ┌────────────┐   ┌──────────────┐  │" + " "*19 + "│")
    print("│       │dim_location│   │dim_organiza- │  │" + " "*19 + "│")
    print("│       │(地域维度)  │   │tion          │  │" + " "*19 + "│")
    print("│       └────────────┘   │(机构维度)    │  │" + " "*19 + "│")
    print("│                        └──────────────┘  │" + " "*19 + "│")
    print("│" + " "*70 + "│")
    print("└" + "─"*70 + "┘")
    print()

def main():
    print_banner()

    conn = connect_db()
    if not conn:
        return

    try:
        show_database_info(conn)
        tables = show_all_tables(conn)
        show_row_counts(conn)

        print()
        print("按任意键查看各表详细结构（Q退出）...")
        print()

        for table in tables:
            show_table_structure(conn, table)
            show_table_data_preview(conn, table, 3)

        show_relationships(conn)

        print()
        print("="*70)
        print("查看完成！")
        print("="*70)
        print()

    finally:
        conn.close()
        print("数据库连接已关闭")

if __name__ == "__main__":
    main()

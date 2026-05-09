# -*- coding: utf-8 -*-
import mysql.connector
import os

DB_CONFIG = {
    'host': '47.121.121.48',
    'port': 3306,
    'user': 'yuesong',
    'password': 'yuesongnb',
    'database': 'YSProd'
}

OUT_DIR = r"E:\岳松个人文件\嘉银工作内容的整理\code\权责自动化处理"

def connect_db():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        print(f"成功连接到数据库: {DB_CONFIG['database']}")
        return conn
    except mysql.connector.Error as err:
        print(f"数据库连接失败: {err}")
        return None

def get_tables(cursor):
    cursor.execute("SHOW TABLES")
    return [table[0] for table in cursor.fetchall()]

def get_table_schema(cursor, table_name):
    cursor.execute(f"DESCRIBE {table_name}")
    return cursor.fetchall()

def generate_basic_queries(cursor, tables):
    queries = []
    queries.append("-- ================================================")
    queries.append("-- MySQL数据库查询文件")
    queries.append(f"-- 数据库: {DB_CONFIG['database']}")
    queries.append(f"-- 生成时间: 自动生成")
    queries.append("-- ================================================")
    queries.append("")

    queries.append("-- 1. 查询所有表")
    queries.append("SHOW TABLES;\n")

    for table in tables[:10]:
        queries.append(f"-- 2. 查询表 {table} 的前10条记录")
        queries.append(f"SELECT * FROM {table} LIMIT 10;\n")

        queries.append(f"-- 3. 查看表 {table} 的结构")
        queries.append(f"DESCRIBE {table};\n")

    return "\n".join(queries)

def main():
    print("="*60)
    print("MySQL数据库连接工具")
    print("="*60)

    conn = connect_db()
    if not conn:
        return

    cursor = conn.cursor()

    tables = get_tables(cursor)
    print(f"数据库中共有 {len(tables)} 个表")

    if tables:
        print("\n前10个表:")
        for i, table in enumerate(tables[:10], 1):
            print(f"  {i}. {table}")

        queries = generate_basic_queries(cursor, tables)

        sql_file_path = os.path.join(OUT_DIR, "mysql_queries.sql")
        with open(sql_file_path, "w", encoding="utf-8") as f:
            f.write(queries)
        print(f"\nSQL查询文件已生成: {sql_file_path}")
    else:
        print("数据库中没有表")

    cursor.close()
    conn.close()
    print("\n数据库连接已关闭")

if __name__ == "__main__":
    main()
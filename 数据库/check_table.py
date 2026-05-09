# -*- coding: utf-8 -*-
"""
查看表结构
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
    cursor = conn.cursor()
    
    print("dim_organization 表结构:")
    print("="*60)
    cursor.execute("DESCRIBE dim_organization")
    for col in cursor.fetchall():
        print(f"  {col[0]} - {col[1]}")
    print()
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()

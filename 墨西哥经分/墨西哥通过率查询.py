"""墨西哥通过率查询 → Excel"""
import sys, os
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

if __name__ == "__main__":
    pq = PrestoQuery()
    pq.login()
    print("登录成功!")

    sql_path = os.path.join(os.path.dirname(__file__), "墨西哥通过率_前置后置.sql")
    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read().strip()
    
    print("开始执行通过率查询...")
    result = pq.query(sql)

    if isinstance(result, pd.DataFrame):
        print(f"查询成功，共 {len(result)} 行数据")
        
        out_path = os.path.join(os.path.dirname(__file__),
                               f"墨西哥通过率_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        result.to_excel(out_path, index=False)
        print(f"数据已保存到: {out_path}")
    else:
        print(f"查询失败: {result}")

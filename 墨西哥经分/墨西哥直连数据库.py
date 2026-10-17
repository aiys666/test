"""墨西哥 mx.gm_ltv_shou_user_media_source 表查询 → Excel"""
import sys, os
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

if __name__ == "__main__":
    pq = PrestoQuery()
    pq.login()
    print("登录成功!")

    sql = "select * from mx.gm_ltv_shou_user_media_source"
    print(f"查询: {sql}")
    result = pq.query(sql)

    if isinstance(result, pd.DataFrame):
        print(f"成功，{len(result)} 行")
        out = os.path.join(os.path.dirname(__file__),
                           f"gm_ltv_shou_user_media_source_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        result.to_excel(out, index=False)
        print(f"已保存: {out}")
    else:
        print(f"失败: {result}")

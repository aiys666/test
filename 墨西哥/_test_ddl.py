# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery()
pq.login()
print("登录成功\n")

# 测试 DDL/DML 是否可通过 adhoc 接口执行
r = pq.query("DROP TABLE IF EXISTS mx.tmp_effect_decomp_all_dims", wait_sec=3)
print("DROP 结果:", r if not isinstance(r, pd.DataFrame) else "OK(DataFrame)")

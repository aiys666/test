# -*- coding: utf-8 -*-
"""排查 funnel: 评级字段名 + is_t0_overdue_1 填充 + biz_id 类型"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery(); pq.login()
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 300)

def q(sql, tag="", show=30):
    print("="*110)
    print(tag)
    r = pq.query(sql)
    if isinstance(r, str):
        print("[ERR]", r[:500]); return None
    if r is None or len(r) == 0:
        print("[空数据]"); return None
    print(r.head(show).to_string() if len(r) > show else r.to_string())
    print(f"[rows={len(r)}]")
    return r

# 1) funnel 评级相关字段名
r = pq.query("select * from mx.wxs_application_funnel limit 1")
if not isinstance(r, str):
    cols = [c for c in r.columns if 'level' in c.lower() or 'rating' in c.lower() or 'score' in c.lower() or 'grade' in c.lower()]
    print("\nfunnel 含 level/rating/score/grade 的列:")
    for c in cols: print("  ", c)

# 2) is_t0_overdue_1 / is_t0_window_1 样本值 + 类型
q("""
select biz_id, mid, app_time, release_time,
  is_t0_window_1, is_t0_overdue_1, t0_should_amt_1, t0_overdue_amount_1,
  is_t7_window_4, is_t7_overdue_4, t7_should_amt_4, t7_overdue_amount_4,
  typeof(is_t0_window_1) as ty_w, typeof(is_t0_overdue_1) as ty_o
from mx.wxs_application_funnel
where if_issue=1 and is_reloan='old'
  and app_time >= cast('2026-08-10 00:00:00' as timestamp)
  and app_time <  cast('2026-08-17 00:00:00' as timestamp)
limit 15
""", "is_t0_overdue_1 样本+类型")

# 3) biz_id 类型对照
q("""
select typeof(f.biz_id) as f_biz, typeof(u.biz_id) as u_biz
from mx.wxs_application_funnel f
join ods_view_presto.s05_user_creditlimit_used_detail u on 1=0
limit 1
""", "biz_id 类型对照")

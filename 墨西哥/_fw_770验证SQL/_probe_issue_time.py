# -*- coding: utf-8 -*-
"""探测: 在线临额"发放时间"来源字段 (model1386落表 / s21 / yj / funnel)"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 1000)

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)

def q(sql, tag):
    print("=" * 120); print(tag, flush=True)
    for i in range(8):
        try: r = pq.query(sql)
        except Exception:
            time.sleep(6)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]", flush=True); return r
        print(f"[retry {i+1}] {str(r)[:200]}"); time.sleep(6)
    return None

# 1) model1386落表字段
q("""SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema='mx' AND table_name='tmp_darren_temp_limit_table' ORDER BY ordinal_position""",
  "1) mx.tmp_darren_temp_limit_table 字段")

q("""SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema='mx' AND table_name='tmp_darren_new_temp_limit_table' ORDER BY ordinal_position""",
  "1b) mx.tmp_darren_new_temp_limit_table 字段")

# 2) s21 决策流记录字段
q("""SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema='ods' AND table_name='s21_risk_model_record' ORDER BY ordinal_position""",
  "2) ods.s21_risk_model_record 字段")

# 3) yj / funnel 里含 issue/temp/time 的字段
q("""SELECT table_name, column_name, data_type FROM information_schema.columns
WHERE table_schema='mx' AND table_name IN ('yj_test_table_250225','wxs_application_funnel')
  AND (lower(column_name) LIKE '%temp%' OR lower(column_name) LIKE '%issue%')
ORDER BY table_name, column_name""", "3) yj/funnel 临额相关字段")

print("DONE-PROBE")

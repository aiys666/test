# -*- coding: utf-8 -*-
"""新节点探查: 661/1166/1043/1077/1411/1066/694/1505/1504/1441/1747/1016
   Q1 样例时间轴  Q2 661与857全量一致率  Q3 低频节点样例"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 4000)
pd.set_option('display.max_colwidth', 10000); pd.set_option('display.max_rows', 300)
for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)
def q(sql, tag):
    print("=" * 170); print(tag, flush=True)
    for i in range(8):
        try: r = pq.query(sql)
        except Exception as ex:
            print(f"[err] {str(ex)[:200]}"); time.sleep(6)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]", flush=True); return r
        print(f"[retry {i+1}] {str(r)[:220]}"); time.sleep(6)
    return None

NODES = "(1522,1523,1386,1379,857,661,1166,1077,1043,1411,1066,694,1505,1504,1441,1747,1016)"
BIZS = "(1620000462179690,1620000480579892,1620000468511585)"

# Q1 3笔样例的完整节点时间轴
q(f"""
select biz_id, createtime, modelmainid,
  regexp_extract(cast(outputdata as varchar),'"temp_credit_amount":(-?[0-9.]+)',1) temp_amt,
  regexp_extract(cast(outputdata as varchar),'"temp_credit_amount_expired_day":([0-9]+)',1) temp_exp,
  regexp_extract(cast(outputdata as varchar),'"credit_amount":(-?[0-9.]+)',1) credit_amt,
  regexp_extract(cast(outputdata as varchar),'"daily_max_available_limit":(-?[0-9.]+)',1) daily_max,
  regexp_extract(cast(outputdata as varchar),'"fd_single_grantcredit_amount_cap":(-?[0-9.]+)',1) single_cap,
  regexp_extract(cast(outputdata as varchar),'"global_7d_limit":(-?[0-9.]+)',1) g7d,
  regexp_extract(cast(outputdata as varchar),'"fd_global_limit_cap":(-?[0-9.]+)',1) gcap,
  regexp_extract(cast(outputdata as varchar),'"grantcredit_7d_amount":(-?[0-9.]+)',1) gc7,
  regexp_extract(cast(outputdata as varchar),'"grantcredit_30d_amount":(-?[0-9.]+)',1) gc30
from ods.s21_risk_model_record
where strategytype='CHAMPION' and modelmainid in {NODES} and biz_id in {BIZS}
order by biz_id, createtime
""", "Q1 3笔样例节点时间轴(661等新节点 vs 五节点)")

# Q2 661 vs 857 全量一致率
q(f"""
with x as (
  select cast(biz_id as varchar) biz,
    max(case when modelmainid=857 then nullif(cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount":([0-9.]+)',1) as double),0) end) a857,
    max(case when modelmainid=661 then nullif(cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount":([0-9.]+)',1) as double),0) end) a661,
    max(case when modelmainid=1386 then cast(regexp_extract(cast(outputdata as varchar),'"temp_credit_amount_issue_tag":([0-9.]+)',1) as double) end) itag
  from ods.s21_risk_model_record
  where strategytype='CHAMPION' and modelmainid in (857,661,1386)
    and createtime >= timestamp '2026-08-31' and createtime < timestamp '2026-10-17'
  group by 1
)
select count(*) n,
  sum(case when a661 is not null then 1 else 0 end) has661,
  sum(case when itag=1 then 1 else 0 end) tag1,
  sum(case when itag=1 and a661 is not null then 1 else 0 end) tag1_661,
  sum(case when itag=1 and a857 is not null then 1 else 0 end) tag1_857,
  sum(case when itag=1 and a661 is not null and a857 is not null and a661=a857 then 1 else 0 end) eq,
  sum(case when itag=0 and a661 is not null then 1 else 0 end) tag0_661nonzero
from x
""", "Q2 661 vs 857 temp_credit_amount 全量一致率")

# Q3 低频节点全窗口样例
q(f"""
select modelmainid, biz_id, createtime, substr(cast(outputdata as varchar),1,600) sample
from (
  select modelmainid, biz_id, createtime, outputdata,
         row_number() over (partition by modelmainid order by createtime) rn
  from ods.s21_risk_model_record
  where strategytype='CHAMPION' and modelmainid in (694,1505,1504,1441,1747)
    and createtime >= timestamp '2026-08-31' and createtime < timestamp '2026-10-17'
) t where rn=1 order by modelmainid
""", "Q3 低频节点各1条样例output")
print("DONE-PROBE10")

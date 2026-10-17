# -*- coding: utf-8 -*-
"""补充探查: (A)tag1笔在s21中所有含临额/额度key的其他节点(找漏网节点)
   (B)yj宽表344列中评分分量/临额相关列名"""
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

KNOWN = "(1522,1523,1386,1379,857,1067,1500,1542,1635)"

# A: tag1 笔上其他含 credit/temp/quota 相关 key 的节点
q(f"""
select modelmainid, count(distinct biz_id) n_biz, count(*) n_rec,
       min(createtime) t0, max(createtime) t1
from ods.s21_risk_model_record
where strategytype='CHAMPION'
  and createtime >= timestamp '2026-08-31' and createtime < timestamp '2026-10-17'
  and modelmainid not in {KNOWN}
  and (lower(cast(outputdata as varchar)) like '%temp_credit%'
       or lower(cast(outputdata as varchar)) like '%creditamount%'
       or lower(cast(outputdata as varchar)) like '%credit_amount%')
  and biz_id in (
    select distinct biz_id from ods.s21_risk_model_record
    where modelmainid=1386 and strategytype='CHAMPION'
      and outputdata like '%"temp_credit_amount_issue_tag":1%'
      and createtime >= timestamp '2026-08-31' and createtime < timestamp '2026-10-17'
  )
group by 1 order by n_biz desc
""", "A 其他含临额/额度key的节点(tag1笔)")

# A2: 看 top 节点的 key 名样例
q(f"""
select modelmainid,
       array_join(array_agg(distinct regexp_extract(kv, '\"([a-z0-9_]+)\"', 1)), ', ') as keys
from (
  select modelmainid, biz_id,
         regexp_extract_all(cast(outputdata as varchar), '\"[a-z0-9_]*(?:credit|quota|temp|limit)[a-z0-9_]*\"') karr
  from ods.s21_risk_model_record
  where strategytype='CHAMPION'
    and createtime >= timestamp '2026-08-31' and createtime < timestamp '2026-10-17'
    and modelmainid not in {KNOWN}
    and (lower(cast(outputdata as varchar)) like '%temp_credit%'
         or lower(cast(outputdata as varchar)) like '%creditamount%'
         or lower(cast(outputdata as varchar)) like '%credit_amount%')
), unnest(karr) t(kv)
group by 1 order by cardinality(array_agg(distinct kv)) desc
""", "A2 这些节点里的额度相关key名")

# B: yj 表列名中含 credit/quota/finish/score/temp/loan_cnt 的列
q("show columns from mx.yj_test_table_250225", "B yj表全部列(本地过滤)")
print("DONE-PROBE9")

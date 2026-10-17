# -*- coding: utf-8 -*-
"""STEP1~STEP6: 复现"770.4占用来源"的完整推理链, 用户可逐条核验
用法: python _fw_verify_770.py
"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 460)
MID = "1040160040722566"

def q(sql, tag):
    print("=" * 112); print(tag, flush=True)
    for i in range(6):
        try: r = pq.query(sql)
        except Exception:
            print(f"[conn retry {i+1}]"); time.sleep(6)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]\n", flush=True); return r
        print(f"[retry {i+1}] {str(r)[:200]}"); time.sleep(6)
        try: pq.login()
        except Exception: pass
    print(f"[FAIL] {tag}\n"); return None

for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: print("[login retry]"); time.sleep(8)

# STEP1 异常锚点: C010 的 used_grant 恒为 770.4
q(f"""
select create_time, round(change_total_grantamount,1) as grant, round(change_used_grantamount,1) as occupied,
  round(change_total_grantamount - change_used_grantamount,1) as net_avail, expiring_time
from ods_view_presto.s05_user_creditlimit_change_record
where mid={MID} and limit_type='TEMP' and change_event_type='C010'
order by create_time
""", "STEP1 锚点: 每次在线临额发放的 发放额/存量占用/净可用")

# STEP2 TEMP 占用台账(逐笔 FREEZE/UNFREEZE)
q(f"""
select biz_id, change_action, round(risk_credit_limit,1) as amt, create_time
from ods.s05_user_creditlimit_used_detail
where mid={MID} and limit_type='TEMP'
order by create_time
""", "STEP2 TEMP 逐笔占用台账(freeze/unfreeze)")

# STEP3 台账对账: 每笔 biz 的 累计冻结-累计解冻 = 剩余占用
r3 = q(f"""
with d as (
  select biz_id,
    sum(case when change_action='FREEZE_LIMIT'   then risk_credit_limit else 0 end) as frz,
    sum(case when change_action='UNFREEZE_LIMIT' then risk_credit_limit else 0 end) as unfrz
  from ods.s05_user_creditlimit_used_detail
  where mid={MID} and limit_type='TEMP'
  group by biz_id
)
select biz_id, round(frz,1) as frz_sum, round(unfrz,1) as unfrz_sum, round(frz-unfrz,1) as residue
from d where frz-unfrz > 0.01 order by residue desc
""", "STEP3 逐笔剩余占用(>0 即未释放)")
if r3 is not None and len(r3):
    print(f">>> STEP3 剩余占用合计 = {round(float(pd.to_numeric(r3['residue']).sum()),1)}  (应 = 770.4)\n")

# STEP4 交叉验证: 净可用 = 发放 - 770.4  vs  yj 实际用额
q(f"""
select c.create_time, round(c.change_total_grantamount,1) as grant_,
  round(c.change_total_grantamount - c.change_used_grantamount,1) as net_avail,
  round(y.temp_grant_amount/1000.0,1) as yj_used, y.biz_id
from ods_view_presto.s05_user_creditlimit_change_record c
join mx.yj_test_table_250225 y
  on cast(c.external_id as bigint) = cast(y.biz_id as bigint)
where c.mid={MID} and c.limit_type='TEMP' and c.change_event_type='C010'
  and c.external_id is not null and c.external_id <> ''
  and c.create_time >= date'2026-08-01'
order by c.create_time
""", "STEP4 交叉验证: 净可用 = 发放-770.4 与 yj 用额是否一致")

# STEP5 来源两笔是否仍欠款/是否已结清
q("""
select biz_id, app_date, if_issue,
  round(contract_amount,1) as contract_amount,
  round(temp_grant_amount/1000.0,1) as temp_used,
  round(t0_overdue_amount_1,1) as t0_od, round(t3_overdue_amount_1,1) as t3_od,
  t0_should_amt_1, t3_should_amt_1
from mx.yj_test_table_250225
where biz_id in ('1620000395926822','1620000396309679')
  and tenant='yawey'
order by biz_id
""", "STEP5 来源两笔在 yj 的还款/逾期状态")

print("DONE-VERIFY770")

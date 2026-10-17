# -*- coding: utf-8 -*-
"""V1~V9: SKILL.md 1.2节全部校验结论的逐条复跑脚本
用法: python _fw_verify_all.py        # 全跑
      python _fw_verify_all.py V3 V5  # 只跑指定编号
每条独立SQL, 打印结果便于逐项核对; 窗口与B/C系列一致(2026-08-19~10-06)
"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 400)

def q(sql, tag):
    print("=" * 100); print(tag, flush=True)
    for i in range(8):
        try: r = pq.query(sql)
        except Exception:
            print(f"[conn retry {i+1}]"); time.sleep(8)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]\n", flush=True); return r
        print(f"[retry {i+1}] {str(r)[:160]}"); time.sleep(8)
        try: pq.login()
        except Exception: pass
    print(f"[FAIL] {tag}\n"); return None

for _ in range(8):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: print("[login retry]"); time.sleep(10)

W_YJ = "app_date>=date'2026-08-19' and app_date<date'2026-10-06'"      # yj窗口
W_CR = "create_time>=date'2026-08-19' and create_time<date'2026-10-06'" # change_record窗口

CHECKS = {}

# ---------- V1 恒等式: contract_amount = risk_credit_limit(MAIN) + temp_grant_amount ----------
CHECKS['V1'] = ("恒等式 合同额=占用主额+使用临额(案例用户逐笔 + 全窗口误差分布)", f"""
-- A. 案例用户逐笔(mid=1040160040722566)
select y.biz_id, y.app_date, y.contract_amount,
  round(y.temp_grant_amount/1000.0,1) as temp_used,
  d.risk_credit_limit as main_freeze,
  round(d.risk_credit_limit + y.temp_grant_amount/1000.0,1) as main_plus_temp,
  round(y.contract_amount - d.risk_credit_limit - y.temp_grant_amount/1000.0,2) as diff
from mx.yj_test_table_250225 y
join ods.s05_user_creditlimit_used_detail d
  on cast(y.biz_id as bigint) = d.biz_id and d.change_action='FREEZE_LIMIT' and d.limit_type='MAIN'
where y.mid=1040160040722566 and y.if_issue=1 and y.temp_grant_amount>0
order by y.app_date
""")
CHECKS['V1b'] = ("恒等式全窗口: 用临额放款中 |合同额-主额-临额|<1 的占比", f"""
select count(*) as used_loans,
  sum(if(abs(y.contract_amount - d.risk_credit_limit - y.temp_grant_amount/1000.0) < 1, 1, 0)) as match_cnt,
  round(sum(if(abs(y.contract_amount - d.risk_credit_limit - y.temp_grant_amount/1000.0) < 1, 1, 0))*100.0/count(*),2) as match_pct
from mx.yj_test_table_250225 y
join ods.s05_user_creditlimit_used_detail d
  on cast(y.biz_id as bigint) = d.biz_id and d.change_action='FREEZE_LIMIT' and d.limit_type='MAIN'
where y.is_reloan='old' and y.if_issue=1 and y.temp_grant_amount>0 and {W_YJ}
""")

# ---------- V2 事件码×动作映射(解冻=C004+C008) ----------
CHECKS['V2'] = ("事件码×change_action×limit_type 映射(2026-07起)", """
select change_event_type as evt, change_action, limit_type, count(*) as c
from ods_view_presto.s05_user_creditlimit_change_record
where create_time >= date'2026-07-01'
group by 1,2,3 order by c desc limit 30
""")

# ---------- V3 C010语义: change_desc=确认借款页创建 ----------
CHECKS['V3'] = ("C010 change_desc 分布(验证=实际领取/使用)", f"""
select change_desc, count(*) as c
from ods_view_presto.s05_user_creditlimit_change_record
where change_event_type='C010' and {W_CR}
group by 1 order by c desc limit 5
""")

# ---------- V4 C010 vs yj 对账(笔数/mid/biz) ----------
CHECKS['V4'] = ("C010 vs yj(tag=1且使用) 笔级对账", f"""
with y as (
  select cast(biz_id as varchar) as bid, mid from mx.yj_test_table_250225
  where is_reloan='old' and if_issue=1 and temp_credit_amount_issue_tag=1 and temp_grant_amount>0 and {W_YJ}
),
c as (
  select cast(external_id as varchar) as bid, mid from ods_view_presto.s05_user_creditlimit_change_record
  where change_event_type='C010' and {W_CR}
)
select (select count(*) from y) as y_used_cnt, (select count(*) from c) as c010_cnt,
  (select count(distinct mid) from y) as y_mid, (select count(distinct mid) from c) as c010_mid,
  count(*) as matched_biz
from y join c on y.bid=c.bid
""")
CHECKS['V4b'] = ("yj tag=1(弹窗展示) 全量 vs 实际使用占比", f"""
select sum(if(temp_credit_amount_issue_tag=1,1,0)) as tag1_cnt,
  sum(if(temp_credit_amount_issue_tag=1 and temp_grant_amount>0,1,0)) as tag1_used_cnt,
  round(sum(if(temp_credit_amount_issue_tag=1 and temp_grant_amount>0,1,0))*100.0
        /nullif(sum(if(temp_credit_amount_issue_tag=1,1,0)),0),1) as used_pct
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1 and {W_YJ}
""")

# ---------- V5 金额: C010发放上限 vs 实际支用 vs yj ----------
CHECKS['V5'] = ("金额三口径对比(C010上限/C010支用/C003冻结/yj用额)", f"""
select
  round(sum(if(c.change_event_type='C010', c.change_total_grantamount, 0)),1) as c010_grant_amt,
  round(sum(if(c.change_event_type='C010', c.change_used_grantamount, 0)),1) as c010_used_amt,
  round(sum(if(c.change_event_type='C003', c.change_total_grantamount, 0)),1) as c003_freeze_amt
from ods_view_presto.s05_user_creditlimit_change_record c
where c.limit_type='TEMP' and c.change_event_type in ('C010','C003') and {W_CR}
""")
CHECKS['V5b'] = ("yj 实际使用临额总额(对照)", f"""
select round(sum(temp_grant_amount/1000.0),1) as yj_used_amt
from mx.yj_test_table_250225
where is_reloan='old' and if_issue=1 and temp_credit_amount_issue_tag=1 and temp_grant_amount>0 and {W_YJ}
""")

# ---------- V6 在线+离线双路径 ----------
CHECKS['V6'] = ("双路径mid(同窗口两事件都有的客户占比)", f"""
with y as (
  select distinct mid from mx.yj_test_table_250225
  where is_reloan='old' and if_issue=1 and {W_YJ}
),
e as (
  select mid,
    max(if(change_event_type='C010',1,0)) as has_online,
    max(if(change_event_type in ('C013','C015'),1,0)) as has_offline
  from ods_view_presto.s05_user_creditlimit_change_record
  where limit_type='TEMP' and create_time>=date'2026-07-01'
  group by 1
)
select count(*) as yj_mids,
  sum(if(e.has_online=1 and e.has_offline=1,1,0)) as both_path_mids,
  round(sum(if(e.has_online=1 and e.has_offline=1,1,0))*100.0/count(*),1) as both_pct
from y join e on y.mid=e.mid
""")

# ---------- V7 冲突扫描(change_action判定, 2026-07起TEMP账户) ----------
CONFLICT_BASE = """
with e as (
  select mid, create_time, change_event_type as evt, change_action,
    max(case when change_action='UNFREEZE_LIMIT' then create_time end)
      over (partition by mid order by create_time rows between unbounded preceding and 1 preceding) as last_unfz,
    max(case when change_action='FREEZE_LIMIT' then create_time end)
      over (partition by mid order by create_time rows between unbounded preceding and 1 preceding) as last_frz
  from ods_view_presto.s05_user_creditlimit_change_record
  where create_time >= date'2026-07-01' and limit_type='TEMP'
    and (change_event_type in ('C010','C013','C015') or change_action in ('FREEZE_LIMIT','UNFREEZE_LIMIT'))
)
"""
COND = "evt in ('C010','C013','C015') and last_frz is not null and (last_unfz is null or last_frz>last_unfz)"
CHECKS['V7'] = ("冲突扫描: 未解冻即再调额 总规模", f"""{CONFLICT_BASE}
select count(if(evt in ('C010','C013','C015'),1,null)) as grant_total,
  count(if({COND},1,null)) as conflict_cnt,
  round(count(if({COND},1,null))*100.0/count(if(evt in ('C010','C013','C015'),1,null)),2) as conflict_pct,
  count(distinct mid) as mid_total,
  count(distinct if({COND},mid,null)) as conflict_mids
from e
""")
CHECKS['V7b'] = ("冲突按调额类型拆分", f"""{CONFLICT_BASE}
select evt as grant_evt, count(*) as conflict_cnt, count(distinct mid) as conflict_mids
from e where {COND} group by 1 order by conflict_cnt desc
""")

# ---------- V8 冲突样例事件流(验证替换/续期非叠加) ----------
CHECKS['V8'] = ("冲突样例TEMP事件流(取2个冲突mid)", f"""{CONFLICT_BASE}
select e2.mid, e2.create_time, e2.change_action,
  round(e2.change_total_grantamount,1) as total_grant, round(e2.change_used_grantamount,1) as used_grant,
  e2.expiring_time, e2.change_event_type as evt
from ods_view_presto.s05_user_creditlimit_change_record e2
where e2.limit_type='TEMP' and e2.mid in (
  select distinct mid from e where {COND} order by mid limit 2
)
order by e2.mid, e2.create_time
""")

# ---------- V9 案例用户完整TEMP事件流(展示C010→C003→C004/C008循环+limit_main_id) ----------
CHECKS['V9'] = ("案例用户TEMP事件流(mid=1040160040722566)", """
select limit_main_id, create_time, change_event_type as evt, change_action,
  round(change_total_grantamount,1) as total_grant, expiring_time
from ods_view_presto.s05_user_creditlimit_change_record
where mid=1040160040722566 and limit_type='TEMP'
order by create_time
""")

# ---------- 执行 ----------
todo = [a for a in sys.argv[1:] if a.upper() in CHECKS] or list(CHECKS.keys())
for k in todo:
    tag, sql = CHECKS[k]
    q(sql, f"[{k}] {tag}")
print("ALL DONE:", ",".join(todo))

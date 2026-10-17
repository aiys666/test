# -*- coding: utf-8 -*-
"""墨西哥临额分析脚本模板: 登录/查询双层重试 + 四组打标 + 周度指标
用法: 修改 WEEKS 列表后直接运行。依赖 code/mexico_presto.py（sys.path 指向 code 目录）。
"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

# ---- 登录重试（网络波动时连接 data.tengoprestamos.com 可能超时）----
for _i in range(8):
    try:
        pq = PrestoQuery(); pq.login(); break
    except Exception as e:
        print(f"[login retry {_i+1}] {type(e).__name__}"); time.sleep(15)
else:
    raise SystemExit("登录失败，请检查网络/VPN")

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 460)


def q(sql, tag="", show=300, retry=8):
    """执行SQL；query() 返回 DataFrame 或错误字符串。连接/查询双层重试。"""
    print("=" * 120)
    print(tag)
    for i in range(retry):
        try:
            r = pq.query(sql)
        except Exception as e:
            print(f"[conn retry {i+1}] {type(e).__name__}"); time.sleep(10)
            try:
                pq.login()
            except Exception:
                pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0:
                print("[空]"); return None
            print(r.to_string() if len(r) <= show else r.head(show).to_string())
            print(f"[rows={len(r)}]")
            return r
        print(f"[sql retry {i+1}] {r[:200]}"); time.sleep(10)
        try:
            pq.login()
        except Exception:
            pass
    return None


# ---- 配置: 按进件周切片（change_record 关联重，大区间易超时，必须逐周跑）----
WEEKS = [
    ('2026-08-04', '2026-08-11', 'w0803'),
    ('2026-08-11', '2026-08-18', 'w0810'),
    ('2026-08-18', '2026-08-25', 'w0817'),
    ('2026-08-25', '2026-09-01', 'w0824'),
    ('2026-09-01', '2026-09-08', 'w0831'),
    ('2026-09-08', '2026-09-15', 'w0907'),
]

SQL_WEEKLY = """
with evt_last as (
  select biz_id, change_event_type,
    row_number() over (partition by biz_id order by create_time desc) as rn
  from (
    select y.biz_id, e.change_event_type, e.create_time
    from mx.yj_test_table_250225 y
    join ods_view_presto.s05_user_creditlimit_change_record e
      on y.mid = e.mid and e.create_time <= y.release_time
    where y.if_issue=1 and y.is_reloan='old'
      and y.app_date >= date'{w0}' and y.app_date < date'{w1}'
      and e.limit_type='TEMP' and e.change_event_type in ('C010','C013','C015')
  ) x
)
select '{wn}' as awk,
  case when el.change_event_type in ('C013','C015') then 'offline'
       when el.change_event_type = 'C010' then
         case when y.temp_credit_amount_issue_tag=1 then 'online_tag1' else 'online_tag0' end
       else 'none' end as tl_grp,
  count(*) as loan_cnt,
  round(sum(if(y.t0_should_amt_1>0, y.t0_overdue_amount_1, null))
       /nullif(sum(if(y.t0_should_amt_1>0, y.t0_should_amt_1, null)),0)*100,2) as t0_rate,
  round(sum(if(y.t0_should_amt_1>0, y.t0_should_amt_1, null))/1000.0,0) as should_k,
  round(sum(if(y.t0_should_amt_1>0, y.t0_overdue_amount_1, null))/1000.0,0) as od_k,
  -- 在线临额四指标（对全部四组都算，仅在线组有意义）
  round(avg(if(y.temp_grant_amount!=0, y.temp_grant_amount/1000.0, null)),1) as use_avg_k,
  count(distinct if(y.temp_grant_amount>0, y.biz_id, null)) as use_cnt,
  round(sum(y.temp_grant_amount/1000.0),0) as use_sum_k,
  count(distinct if(y.temp_grant_amount=0, y.biz_id, null)) as no_use_cnt
from mx.yj_test_table_250225 y
left join evt_last el on y.biz_id = el.biz_id and el.rn=1
where y.if_issue=1 and y.is_reloan='old'
  and y.app_date >= date'{w0}' and y.app_date < date'{w1}'
group by 2 order by 2
"""

if __name__ == '__main__':
    frames = []
    for w0, w1, wn in WEEKS:
        df = q(SQL_WEEKLY.format(w0=w0, w1=w1, wn=wn), f"{wn} 复贷临额四组周度指标")
        if df is not None:
            frames.append(df)
    if frames:
        all_df = pd.concat(frames, ignore_index=True)
        print("\n汇总：\n", all_df.to_string())

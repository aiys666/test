# -*- coding: utf-8 -*-
"""验证r1子查询: 4列group by vs 2列group by 行数对比"""
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

pq = PrestoQuery()
pq.login()

# 对比2列vs4列group by的行数
print("[1] 2列group by 总行数 vs 4列group by 总行数:")
sql = """
select
    (select count(*) from (
        select camera_id, indexs, sum(coupon_amount) coupon_amount
        from ods_view_presto.s02_loan_repayment
        group by 1,2
    ) t) as old_r1_rows,
    (select count(*) from (
        select camera_id, indexs, rid, fact_time,
               sum(coupon_amount) coupon_amount,
               sum(subtract_interest) subtract_interest,
               sum(subtract_capital) subtract_capital
        from ods_view_presto.s02_loan_repayment
        group by 1,2,3,4
    ) t) as new_r1_rows
"""
df = pq.query(sql, wait_sec=5)
if isinstance(df, pd.DataFrame):
    print(df.to_string(index=False))
    old_r = df['old_r1_rows'].iloc[0]
    new_r = df['new_r1_rows'].iloc[0]
    print(f"\n  旧口径(2列): {old_r} 行")
    print(f"  新口径(4列): {new_r} 行")
    if old_r == new_r:
        print("  ✅ 行数相同! r1扩展没有引入额外行,不存在M倍放大")
    else:
        print(f"  ⚠️ 行数差异: {new_r - old_r} 行")

# 直接取几个订单看r1的rid+fact_time是否唯一
print("\n[2] 取10个camera_id+indexs,看rid+fact_time是否唯一:")
sql2 = """
select camera_id, indexs, count(*) as cnt,
       count(distinct rid) as rid_cnt,
       count(distinct fact_time) as ft_cnt
from ods_view_presto.s02_loan_repayment
group by 1,2
order by cnt desc
limit 10
"""
df2 = pq.query(sql2, wait_sec=5)
if isinstance(df2, pd.DataFrame):
    print(df2.to_string(index=False))
    print(f"\n  如果 cnt = rid_cnt = ft_cnt,说明每个camera_id+indexs有多条不同rid/fact_time的记录")
    print(f"  但如果4列group by和2列group by行数相同,说明rid+fact_time组合在camera_id+indexs内是唯一的")
else:
    print("  查询失败:", str(df2)[:200])

# 直接对比新旧口径的repay_t0_amt_all (不限制r1多行)
print("\n[3] 随机取5个有还款的订单,对比新旧口径 repay_t0_amt_all:")
sql3 = """
with r1_new as (
    select camera_id, indexs, rid, fact_time,
           sum(coupon_amount) coupon_amount,
           sum(subtract_interest) subtract_interest,
           sum(subtract_capital) subtract_capital
    from ods_view_presto.s02_loan_repayment
    group by 1,2,3,4
),
r1_old as (
    select camera_id, indexs,
           sum(coupon_amount) coupon_amount,
           sum(subtract_interest) subtract_interest,
           sum(subtract_capital) subtract_capital
    from ods_view_presto.s02_loan_repayment
    group by 1,2
)
select
    t1.id as camera_id,
    t1.indexs,
    -- 旧口径
    sum(case when date_diff('day', t1.should_date, date(rd.fact_time)) <= 0
        then coalesce(rd.fact_capital,0) + coalesce(rd.fact_interest,0)
             + coalesce(r1_old.subtract_interest,0)
             + coalesce(r1_old.coupon_amount,0)
             + coalesce(r1_old.subtract_capital,0)
        else 0 end) as old_repay_t0,
    -- 新口径
    sum(case when date_diff('day', t1.should_date, date(rd.fact_time)) <= 0
        then coalesce(rd.fact_capital,0) + coalesce(rd.fact_interest,0)
             + coalesce(if(r1_new.fact_time is not null, r1_new.subtract_interest,0),0)
             + coalesce(if(r1_new.fact_time is not null, r1_new.coupon_amount,0),0)
             + coalesce(if(r1_new.fact_time is not null, r1_new.subtract_capital,0),0)
        else 0 end) as new_repay_t0
from mx.wxs_vintage_all3 t1
left join r1_old on r1_old.camera_id = t1.id and r1_old.indexs = t1.indexs
left join r1_new on r1_new.camera_id = t1.id and r1_new.indexs = t1.indexs
left join ods_view_presto.s02_loan_repayment_detail rd on rd.camera_id = t1.id
group by 1, 2
having sum(case when date_diff('day', t1.should_date, date(rd.fact_time)) <= 0
            then coalesce(rd.fact_capital,0) else 0 end) > 0
limit 10
"""
df3 = pq.query(sql3, wait_sec=5)
if isinstance(df3, pd.DataFrame) and len(df3) > 0:
    df3['diff'] = df3['new_repay_t0'] - df3['old_repay_t0']
    df3['ratio'] = df3['new_repay_t0'] / df3['old_repay_t0']
    print(df3.to_string(index=False))
    print(f"\n  如果 ratio ≈ 1,说明新旧口径结果一致(无放大)")
    print(f"  如果 ratio > 1,说明新口径值更大(可能放大或有减免/券的额外贡献)")
else:
    print("  查询失败或无数据:", str(df3)[:200] if not isinstance(df3, pd.DataFrame) else "无数据")

# -*- coding: utf-8 -*-
"""
验证新口径 vintage all31 的 r1 子查询是否导致 rd 字段 M 倍放大
========================================================
验证思路:
  1. 检查 s02_loan_repayment_detail (rd) 每个 camera_id 有几行
  2. 检查 r1 子查询 (group by camera_id,indexs,rid,fact_time) 每个 camera_id+indexs 有几行
  3. 取几个具体订单，看 JOIN 后的行数和 SUM 结果
  4. 对比旧口径(2列group by)和新口径(4列group by)的 SUM 差异
"""

import sys, os
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

def main():
    print("=" * 70)
    print("验证 r1 子查询是否导致 rd 字段 M 倍放大")
    print("=" * 70)

    pq = PrestoQuery()
    pq.login()

    # ── 查询1: s02_loan_repayment_detail 每个 camera_id 有几行 ──
    print("\n[1] s02_loan_repayment_detail (rd) 每 camera_id 行数分布:")
    sql1 = """
    select row_cnt, count(*) as camera_cnt
    from (
        select camera_id, count(*) as row_cnt
        from ods_view_presto.s02_loan_repayment_detail
        group by 1
    ) t
    group by 1
    order by 1
    """
    df1 = pq.query(sql1, wait_sec=5)
    if isinstance(df1, pd.DataFrame):
        print(df1.to_string(index=False))
        print(f"\n  结论: rd表每个camera_id最多有 {df1['row_cnt'].max()} 行")
        print(f"  如果都是1行,说明rd是订单级汇总,不会与r1产生交叉积")

    # ── 查询2: r1子查询(4列group by) 每个 camera_id+indexs 有几行 ──
    print("\n[2] r1子查询(4列group by) 每 camera_id+indexs 行数分布:")
    sql2 = """
    select row_cnt, count(*) as组合_cnt
    from (
        select camera_id, indexs, count(*) as row_cnt
        from (
            select camera_id, indexs, rid, fact_time,
                   sum(coupon_amount) coupon_amount,
                   sum(subtract_interest) subtract_interest,
                   sum(subtract_capital) subtract_capital
            from ods_view_presto.s02_loan_repayment
            group by 1,2,3,4
        ) t1
        group by 1,2
    ) t2
    group by 1
    order by 1
    limit 20
    """
    df2 = pq.query(sql2, wait_sec=5)
    if isinstance(df2, pd.DataFrame):
        print(df2.to_string(index=False))
        multi_row = df2[df2['row_cnt'] > 1]
        if len(multi_row) > 0:
            print(f"\n  ⚠️ 存在 camera_id+indexs 有多行的情况!")
            print(f"  多行组合数: {multi_row['组合_cnt'].sum()}")

    # ── 查询3: 取几个具体订单,看JOIN后的行数 ──
    print("\n[3] 取5个有多行r1的订单,看JOIN后行数:")
    sql3 = """
    select camera_id, indexs, r1_row_cnt, rd_row_cnt,
           r1_row_cnt * rd_row_cnt as join_row_cnt
    from (
        select t1.camera_id, t1.indexs,
               count(distinct concat(r1.rid, '_', r1.fact_time)) as r1_row_cnt,
               count(distinct rd.fact_time) as rd_row_cnt
        from mx.wxs_vintage_all3 t1
        left join (
            select camera_id, indexs, rid, fact_time,
                   sum(coupon_amount) coupon_amount,
                   sum(subtract_interest) subtract_interest,
                   sum(subtract_capital) subtract_capital
            from ods_view_presto.s02_loan_repayment
            group by 1,2,3,4
        ) r1 on r1.camera_id = t1.id and t1.indexs = r1.indexs
        left join ods_view_presto.s02_loan_repayment_detail rd
            on rd.camera_id = t1.id
        group by 1,2
        having count(distinct concat(r1.rid, '_', r1.fact_time)) > 1
        limit 5
    ) t
    """
    df3 = pq.query(sql3, wait_sec=5)
    if isinstance(df3, pd.DataFrame) and len(df3) > 0:
        print(df3.to_string(index=False))
        print(f"\n  如果 join_row_cnt > max(r1_row_cnt, rd_row_cnt),说明有交叉积!")

    # ── 查询4: 对比新旧口径的实际SUM值 ──
    print("\n[4] 对比新旧口径 SUM(fact_capital) 差异 (取5个订单):")
    sql4 = """
    select
        t1.id as camera_id,
        t1.indexs,
        r1_cnt,
        rd_cnt,
        -- 旧口径: r1按2列group by(每camera_id+indexs 1行)
        old_fact_capital_sum,
        -- 新口径: r1按4列group by(每camera_id+indexs M行)
        new_fact_capital_sum,
        -- 倍数
        case when old_fact_capital_sum > 0
             then new_fact_capital_sum / old_fact_capital_sum
             else 0 end as放大倍数
    from (
        select
            t1.id, t1.indexs,
            count(distinct concat(r1.rid, '_', r1.fact_time)) as r1_cnt,
            count(distinct rd.fact_time) as rd_cnt,
            sum(rd.fact_capital) as new_fact_capital_sum,
            sum(rd.fact_capital) / NULLIF(count(distinct concat(r1.rid, '_', r1.fact_time)), 0) as old_fact_capital_sum
        from mx.wxs_vintage_all3 t1
        left join (
            select camera_id, indexs, rid, fact_time,
                   sum(coupon_amount) coupon_amount,
                   sum(subtract_interest) subtract_interest,
                   sum(subtract_capital) subtract_capital
            from ods_view_presto.s02_loan_repayment
            group by 1,2,3,4
        ) r1 on r1.camera_id = t1.id and t1.indexs = r1.indexs
        left join ods_view_presto.s02_loan_repayment_detail rd
            on rd.camera_id = t1.id
        group by 1,2
        having count(distinct concat(r1.rid, '_', r1.fact_time)) > 1
           AND sum(rd.fact_capital) > 0
        limit 10
    ) t
    """
    df4 = pq.query(sql4, wait_sec=5)
    if isinstance(df4, pd.DataFrame) and len(df4) > 0:
        print(df4.to_string(index=False))
        print(f"\n  如果放大倍数 > 1,说明新口径确实放大了 rd.fact_capital")
    else:
        print("  没有找到r1多行且rd有值的订单")

    # ── 查询5: 直接对比新旧口径 repay_t0_amt_all ──
    print("\n[5] 直接对比新旧口径 repay_t0_amt_all (取5个订单):")
    sql5 = """
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
        (select count(*) from r1_new where r1_new.camera_id = t1.id and r1_new.indexs = t1.indexs) as r1_new_cnt,
        -- 旧口径 repay_t0_amt_all
        sum(case when date_diff('day', t1.should_date, date(rd.fact_time)) <= 0
            then coalesce(rd.fact_capital,0) + coalesce(rd.fact_interest,0)
                 + coalesce(r1_old.subtract_interest,0)
                 + coalesce(r1_old.coupon_amount,0)
                 + coalesce(r1_old.subtract_capital,0)
            else 0 end) as old_repay_t0_amt,
        -- 新口径 repay_t0_amt_all
        sum(case when date_diff('day', t1.should_date, date(rd.fact_time)) <= 0
            then coalesce(rd.fact_capital,0) + coalesce(rd.fact_interest,0)
                 + coalesce(if(r1_new.fact_time is not null, r1_new.subtract_interest,0),0)
                 + coalesce(if(r1_new.fact_time is not null, r1_new.coupon_amount,0),0)
                 + coalesce(if(r1_new.fact_time is not null, r1_new.subtract_capital,0),0)
            else 0 end) as new_repay_t0_amt
    from mx.wxs_vintage_all3 t1
    left join r1_old on r1_old.camera_id = t1.id and r1_old.indexs = t1.indexs
    left join r1_new on r1_new.camera_id = t1.id and r1_new.indexs = t1.indexs
    left join ods_view_presto.s02_loan_repayment_detail rd on rd.camera_id = t1.id
    group by 1, 2
    having (select count(*) from r1_new where r1_new.camera_id = t1.id and r1_new.indexs = t1.indexs) > 1
       AND sum(case when date_diff('day', t1.should_date, date(rd.fact_time)) <= 0
                   then coalesce(rd.fact_capital,0) else 0 end) > 0
    limit 10
    """
    df5 = pq.query(sql5, wait_sec=5)
    if isinstance(df5, pd.DataFrame) and len(df5) > 0:
        df5['放大倍数'] = df5['new_repay_t0_amt'] / df5['old_repay_t0_amt']
        print(df5[['camera_id','indexs','r1_new_cnt','old_repay_t0_amt','new_repay_t0_amt','放大倍数']].to_string(index=False))
        print(f"\n  如果放大倍数 ≈ r1_new_cnt,说明rd部分被放大了M倍")
    else:
        print("  没有找到符合条件的订单")

    print("\n" + "=" * 70)
    print("验证完成")

if __name__ == "__main__":
    main()

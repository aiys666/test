# -*- coding: utf-8 -*-
"""LTV v2 跑数验证: 对账 + 两处修复的生效证据 + 新旧口径可加性检验。

注意: 盘古 Presto 解析器不接受中文列别名, SQL 里一律用英文别名。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
sys.path.insert(0, HERE)
from mexico_presto import PrestoQuery  # noqa: E402


def show(pq, title, sql):
    print(f"\n### {title}")
    r = pq.query(sql)
    if isinstance(r, str):
        print("  !! " + r[:220])
        return None
    print(r.to_string(index=False))
    return r


def main():
    pq = PrestoQuery()
    pq.login()

    print("=" * 78)
    print("一、可加性检验: 新表按「旧维度」汇总后是否等于旧口径")
    print("=" * 78)

    show(pq, "首贷底表总数", """
        select count(*) as loan_cnt, count(distinct biz_id) as order_cnt,
               count(distinct mid) as cust_cnt, sum(contract_amount) as amount
        from mx.ys_ltv_v2_first_loan""")

    show(pq, "月版首贷CAC(全维度) 汇总", """
        select count(*) as row_cnt, sum(frs_cnt) as loan_cnt, sum(contract_amount) as amount
        from mx.ys_ltv_v2_m_first_loan_cac""")

    show(pq, "月版首贷CAC 收敛回旧3维(月×渠道×等级) 后的行数", """
        select count(*) as old_dim_rows, sum(frs_cnt) as loan_cnt
        from (select ltv_month, app_channel_name, new_grade_level,
                     sum(frs_cnt) as frs_cnt
              from mx.ys_ltv_v2_m_first_loan_cac
              group by 1,2,3) t""")

    show(pq, "周版首贷CAC(全维度) 汇总", """
        select count(*) as row_cnt, sum(frs_cnt) as loan_cnt, sum(contract_amount) as amount
        from mx.ys_ltv_v2_w_first_loan_cac""")

    show(pq, "周版首贷CAC 收敛回旧4维(周×渠道×等级×小金额) 后的行数", """
        select count(*) as old_dim_rows, sum(frs_cnt) as loan_cnt
        from (select ltv_week, app_channel_name, new_grade_level, is_low_amount_flag,
                     sum(frs_cnt) as frs_cnt
              from mx.ys_ltv_v2_w_first_loan_cac
              group by 1,2,3,4) t""")

    print("\n" + "=" * 78)
    print("二、复贷对账")
    print("=" * 78)

    show(pq, "复贷原始口径(未关联首贷 cohort)", """
        select count(*) as loan_cnt, count(distinct biz_id) as order_cnt,
               count(distinct mid) as cust_cnt, sum(contract_amount) as amount
        from mx.wxs_application_funnel
        where is_reloan='old' and if_issue=1""")

    show(pq, "月版/周版复贷明细 + 聚合 + final", """
        select 'm_detail' as stage, count(*) as row_cnt, count(distinct biz_id) as order_cnt,
               sum(contract_amount) as amount from mx.ys_ltv_v2_m_double_loan
        union all
        select 'm_group', count(*), sum(double_cnt), sum(contract_amount)
        from mx.ys_ltv_v2_m_double_group
        union all
        select 'm_final', count(*), sum(double_cnt), sum(contract_amount)
        from mx.ys_ltv_v2_m_final
        union all
        select 'w_detail', count(*), count(distinct biz_id), sum(contract_amount)
        from mx.ys_ltv_v2_w_double_loan
        union all
        select 'w_group', count(*), sum(double_cnt), sum(contract_amount)
        from mx.ys_ltv_v2_w_double_group
        union all
        select 'w_final', count(*), sum(double_cnt), sum(contract_amount)
        from mx.ys_ltv_v2_w_final""")

    show(pq, "月版final 月度跨度与复贷笔数", """
        select min(ltv_month) as min_month, max(ltv_month) as max_month,
               max(wob) as max_wob, sum(double_cnt) as re_loan_cnt,
               sum(frs_cnt) as frs_cnt
        from mx.ys_ltv_v2_m_final""")

    print("\n" + "=" * 78)
    print("三、FIX-1 媒体来源关联键 (cast(cust_id as bigint) -> r.mid)")
    print("=" * 78)

    show(pq, "修复后 register_media_source 分布", """
        select register_media_source as media_source, count(*) as loan_cnt
        from mx.ys_ltv_v2_first_loan
        group by 1 order by 2 desc""")

    show(pq, "两种关联键的命中行数对比", """
        select 'cust_id 关联(原写法)' as join_key, count(*) as hit_rows
        from mx.wxs_application_funnel r
        join mx.gm_attribution_detail att on cast(r.cust_id as bigint) = att.mid
        where r.is_reloan='new' and r.if_issue=1
        union all
        select 'r.mid 关联(修复后)', count(*)
        from mx.wxs_application_funnel r
        join mx.gm_attribution_detail att on r.mid = att.mid
        where r.is_reloan='new' and r.if_issue=1""")

    print("\n" + "=" * 78)
    print("四、FIX-2 new_grade_level_main 分支顺序")
    print("=" * 78)

    show(pq, "修复后 new_grade_level_main 分布", """
        select new_grade_level_main as grade, count(*) as loan_cnt
        from mx.ys_ltv_v2_first_loan group by 1 order by 1""")

    show(pq, "2026-06-02 起 V5_2 / V4_1 实际启用规模", """
        select case when t.android_newcust_maincreditlevel_charge_v5_2 is not null then 'v5_2_used'
                    when t.sd_creditlevel_main_v4_1 is not null then 'v5_2_null_fallback_v4_1'
                    else 'both_null_9999' end as source,
               count(*) as row_cnt
        from mx.wxs_application_funnel r
        left join (select externalid7, sd_creditlevel_main_v4_1,
                          android_newcust_maincreditlevel_charge_v5_2
                   from mx.wenj_sd_market) t on r.biz_id = t.externalid7
        where r.is_reloan='new' and r.if_issue=1 and r.app_time >= date '2026-06-02'
        group by 1 order by 2 desc""")

    print("\n" + "=" * 78)
    print("五、维度膨胀明细 (月版首贷 cohort 组合数)")
    print("=" * 78)

    show(pq, "各维度层级的 cohort 组合数", """
        select 'old_3dims(month,channel,grade)' as dim_level, count(*) as combos
        from (select ltv_month, app_channel_name, new_grade_level
              from mx.ys_ltv_v2_first_loan group by 1,2,3) a
        union all
        select 'plus_media_grade_main', count(*)
        from (select ltv_month, app_channel_name, new_grade_level,
                     register_media_source, new_grade_level_main
              from mx.ys_ltv_v2_first_loan group by 1,2,3,4,5) b
        union all
        select 'all_9_dims', count(*)
        from (select ltv_month, app_channel_name, new_grade_level, product_name,
                     app_version, channel_category, new_grade_level_main,
                     register_media_source, is_low_amount_flag
              from mx.ys_ltv_v2_first_loan group by 1,2,3,4,5,6,7,8,9) c""")

    print("\n" + "=" * 78)
    print("六、汇率覆盖")
    print("=" * 78)
    show(pq, "月版首贷CAC 中汇率缺失的月份", """
        select ltv_month, count(*) as row_cnt
        from mx.ys_ltv_v2_m_first_loan_cac
        where exchange_rate_to_dollar is null
        group by 1 order by 1""")

    print("\n验证结束")


if __name__ == "__main__":
    main()

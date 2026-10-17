# -*- coding: utf-8 -*-
"""
还原「海外_墨西哥_复贷_资产等级v6_1策略.xlsx」的审批策略效果
=========================================================
文档口径:
  - 进件样本: 2026-06-10 至 2026-07-26 老客复贷进件
  - 新策略(V6_1): 资产等级 11 级拒尾 → 等级<=10 通过
  - 原策略(V5_2): 线上实际通过率(if_sx_passed)
  - 交叉表: V6_1等级(1-11) × V5_2等级

数据源说明(口径差异):
  - mx.yj_test_table_250225: 老客进件宽表(最接近进件全集)
  - mx.tracedata_v6_1_level: V6_1回测等级(仅放款样本,非全进件)
  - mx.android_oldcust_main_creditlevel_charge_v5_2_param_table: V5_2等级
  ⚠️ 文档进件样本=65122，但现有数据源对不上(见输出注释)，此处为最接近还原
"""
import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery
import pandas as pd

if sys.stdout.encoding and 'utf' not in sys.stdout.encoding.lower():
    sys.stdout.reconfigure(encoding='utf-8')


def main():
    pq = PrestoQuery()
    pq.login()
    print('墨西哥连接成功\n')

    # ============================================================
    # 1. 整体效果表还原（按 V6_1 等级）
    # 进件样本: yj_test_table 老客 6/10-7/26，关联 V6_1 等级
    # ============================================================
    print('=== 整体效果（进件=老客进件 且 有V6_1等级）===')
    df = pq.query('''
    select t.v6_level,
      count(*) as app_cnt,
      count_if(y.if_sx_passed=1) as old_pass_cnt,
      count_if(y.if_sx_passed=1)*1.0/count(*) as old_pass_rate,
      count_if(try_cast(t.v6_level as int) <= 10) as new_pass_cnt,
      count_if(try_cast(t.v6_level as int) <= 10)*1.0/count(*) as new_pass_rate
    from mx.yj_test_table_250225 y
    join mx.tracedata_v6_1_level t
      on replace(t.id_id,'id','') = cast(y.biz_id as varchar)
    where y.app_date >= date '2026-06-10' and y.app_date <= date '2026-07-26'
      and y.is_reloan = 'old'
      and try_cast(t.v6_level as int) is not null
    group by 1 order by 1
    ''', wait_sec=5)
    if isinstance(df, str):
        print(f'查询失败: {df}')
        return
    # 转数值
    for c in ['app_cnt','old_pass_cnt','new_pass_cnt']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df['old_pass_rate'] = pd.to_numeric(df['old_pass_rate'], errors='coerce')
    df['new_pass_rate'] = pd.to_numeric(df['new_pass_rate'], errors='coerce')
    # 总计行
    total_app = df['app_cnt'].sum()
    total_old = df['old_pass_cnt'].sum()
    total_new = df['new_pass_cnt'].sum()
    print(df.to_string(index=False))
    print(f'总计: 进件={total_app}, 原策略通过率={total_old/total_app:.4f}, 新策略通过率={total_new/total_app:.4f}')
    print(f'（文档: 进件=65122, 原策略通过率=0.9187, 新策略通过率=0.9127）')

    # ============================================================
    # 2. 交叉表还原（V6_1等级 × V5_2等级）
    # ============================================================
    print('\n=== 交叉表：V6_1等级(行) × V5_2等级(列) ===')
    df2 = pq.query('''
    select t.v6_level,
      y.android_oldcust_maincreditlevel_charge_v5_2 as v52_level,
      count(*) as cnt
    from mx.yj_test_table_250225 y
    join mx.tracedata_v6_1_level t
      on replace(t.id_id,'id','') = cast(y.biz_id as varchar)
    where y.app_date >= date '2026-06-10' and y.app_date <= date '2026-07-26'
      and y.is_reloan = 'old'
      and try_cast(t.v6_level as int) is not null
    group by 1,2
    ''', wait_sec=5)
    if isinstance(df2, str):
        print(f'查询失败: {df2}')
        return
    # 转数值排序再透视
    df2['v6_level'] = pd.to_numeric(df2['v6_level'], errors='coerce')
    df2['v52_level'] = pd.to_numeric(df2['v52_level'], errors='coerce')
    df2['cnt'] = pd.to_numeric(df2['cnt'], errors='coerce')
    pivot = df2.pivot_table(index='v6_level', columns='v52_level', values='cnt',
                            aggfunc='sum', fill_value=0)
    pivot = pivot.sort_index()
    print(pivot.to_string())
    print('（文档: V5_2列是1-7级；表里V5_2是1-16级，口径差异）')

    # ============================================================
    # 3. 拒尾 swap 还原
    # ============================================================
    print('\n=== 拒尾 swap（新策略 vs 原策略）===')
    df3 = pq.query('''
    select
      case when try_cast(t.v6_level as int) <= 10 then '新pass' else '新refuse' end as new_flag,
      case when y.if_sx_passed = 1 then '原pass' else '原refuse' end as old_flag,
      count(*) as cnt
    from mx.yj_test_table_250225 y
    join mx.tracedata_v6_1_level t
      on replace(t.id_id,'id','') = cast(y.biz_id as varchar)
    where y.app_date >= date '2026-06-10' and y.app_date <= date '2026-07-26'
      and y.is_reloan = 'old'
      and try_cast(t.v6_level as int) is not null
    group by 1,2
    ''', wait_sec=5)
    if not isinstance(df3, str):
        pivot3 = df3.pivot_table(index='new_flag', columns='old_flag', values='cnt',
                                 aggfunc='sum', fill_value=0)
        print(pivot3.to_string())
        print('（文档: 新策略refuse=5684=V6_1等级11全部拒）')


if __name__ == '__main__':
    main()

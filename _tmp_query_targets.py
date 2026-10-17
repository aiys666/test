# -*- coding: utf-8 -*-
"""临时脚本：查询 ind.ba_kpi_targets_m 表结构与目标数据。"""
import sys
import pandas as pd

sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from indonesia_presto import PrestoQuery

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)
pd.set_option('display.max_colwidth', 50)


def run_query(pq, sql, title):
    print('=' * 80)
    print(f'【{title}】')
    print(f'SQL: {sql}')
    print('-' * 80)
    try:
        result = pq.submit_query(sql)
    except Exception as e:
        print(f'查询异常: {e}')
        return None

    if result is None:
        print('查询返回 None（可能 statementType 非 select 或获取结果失败）')
        return None

    if isinstance(result, tuple):
        # (query, errorMsg) 形式的错误返回
        print(f'查询错误: {result}')
        return None

    if isinstance(result, str):
        # DDL / 其他语句的字符串返回
        print(f'返回字符串: {result}')
        return None

    if isinstance(result, pd.DataFrame):
        if result.empty:
            print('查询成功，但结果为空 DataFrame（无数据）')
        else:
            print(f'查询成功，共 {len(result)} 行 x {len(result.columns)} 列')
            print(result.to_string(index=False))
        return result

    print(f'未知返回类型: {type(result)} -> {result}')
    return None


def main():
    pq = PrestoQuery()
    print('开始登录...')
    pq.login_process()
    print('登录完成。\n')

    # 1) 表结构 —— show columns
    run_query(
        pq,
        'show columns from ind.ba_kpi_targets_m',
        '1. 表结构 (show columns)',
    )

    # 1.1) 兜底：用 information_schema 再查一次字段（show 可能不被识别为 select）
    run_query(
        pq,
        "select column_name, data_type, comment "
        "from information_schema.columns "
        "where table_schema = 'ind' and table_name = 'ba_kpi_targets_m' "
        "order by ordinal_position",
        '1.1 表结构 (information_schema.columns)',
    )

    # 2) 8 月份目标数据
    run_query(
        pq,
        "select * from ind.ba_kpi_targets_m where month = '2026-08-01'",
        '2. 8月份目标数据 (month = 2026-08-01)',
    )

    # 3) 全部数据
    run_query(
        pq,
        'select * from ind.ba_kpi_targets_m',
        '3. 全部数据',
    )


if __name__ == '__main__':
    main()

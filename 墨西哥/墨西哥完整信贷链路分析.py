# -*- coding: utf-8 -*-
"""
墨西哥完整信贷链路分析（最终版）
=============================
数据源: mx.wxs_application_funnel (墨西哥完整宽表)
时间线: 2026-01-01 起
维度:   月度 × 新老客(grant_strategy)

【链路设计说明】
墨西哥风控是"前置并行评估 + 授信主链路"：
- 反欺诈/模型/外部数据 是前置评估分支，触发率随策略/月份变化，不能当主漏斗
- 真正的授信主链路：进件 → 授信(sx) → 通过(pass) → 放款(issue)

主漏斗（单调递减，不会倒挂）：
进件 → 授信进入(sx_in) → 授信通过(sx_pass) → 通过(pass) → 放款(issue)

辅助评估环节（单独展示，不进主漏斗）：
- 反欺诈进入/通过（首贷shou_ / 复贷fu_）
- 模型进入/通过
- 外部数据进入/通过
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
    print('墨西哥连接成功')

    # ============================================================
    # 主查询（月度 × 新老客）
    # ============================================================
    sql = """
    SELECT
        date_format(app_date, '%Y-%m') AS month,
        grant_strategy,
        -- ===== 主漏斗 =====
        count_if(if_app = 1)                    AS app_cnt,          -- 进件
        count_if(if_in_sx = 1)                  AS sx_in_cnt,        -- 授信进入
        count_if(if_sx_passed = 1)              AS sx_pass_cnt,      -- 授信通过
        count_if(if_pass = 1)                   AS pass_cnt,         -- 最终通过
        count_if(if_issue = 1)                  AS issue_cnt,        -- 放款
        sum(case when if_issue=1 then issue_amount else 0 end) AS issue_amt,
        -- ===== 辅助评估环节 =====
        count_if(CASE WHEN grant_strategy='首贷' THEN if_in_shou_anti_fraud=1
                      WHEN grant_strategy='复贷' THEN if_in_fu_anti_fraud=1 END) AS af_in_cnt,
        count_if(CASE WHEN grant_strategy='首贷' THEN if_shou_anti_fraud_passed=1
                      WHEN grant_strategy='复贷' THEN if_fu_anti_fraud_passed=1 END) AS af_pass_cnt,
        count_if(CASE WHEN grant_strategy='首贷' THEN if_in_shou_model=1
                      WHEN grant_strategy='复贷' THEN if_in_fu_model=1 END) AS model_in_cnt,
        count_if(CASE WHEN grant_strategy='首贷' THEN if_shou_model_passed=1
                      WHEN grant_strategy='复贷' THEN if_fu_model_passed=1 END) AS model_pass_cnt,
        count_if(CASE WHEN grant_strategy='首贷' THEN if_in_shou_external_data=1
                      WHEN grant_strategy='复贷' THEN if_in_fu_external_data=1 END) AS ext_in_cnt,
        count_if(CASE WHEN grant_strategy='首贷' THEN if_shou_external_data_passed=1
                      WHEN grant_strategy='复贷' THEN if_fu_external_data_passed=1 END) AS ext_pass_cnt,
        -- ===== 贷后逾期 =====
        count_if(if_issue=1 AND is_t7_overdue=1)  AS t7_ovd_cnt,
        count_if(if_issue=1 AND is_t7_window=1)   AS t7_win_cnt,
        count_if(if_issue=1 AND is_t30_overdue=1) AS t30_ovd_cnt,
        count_if(if_issue=1 AND is_t30_window=1)  AS t30_win_cnt,
        sum(case when if_issue=1 AND is_t30_overdue=1 then t30_overdue_amount else 0 end) AS t30_ovd_amt
    FROM mx.wxs_application_funnel
    WHERE app_date >= date '2026-01-01'
      AND grant_strategy in ('首贷', '复贷')
    GROUP BY 1, 2
    ORDER BY 1, 2
    """
    print('正在跑完整链路主查询（数据量大，请稍候）...')
    df = pq.query(sql, wait_sec=5)
    if isinstance(df, str):
        print(f'主查询失败: {df}')
        return
    print(f'主查询完成: {df.shape[0]} 行')

    num_cols = ['app_cnt', 'sx_in_cnt', 'sx_pass_cnt', 'pass_cnt', 'issue_cnt', 'issue_amt',
                'af_in_cnt', 'af_pass_cnt', 'model_in_cnt', 'model_pass_cnt',
                'ext_in_cnt', 'ext_pass_cnt', 't7_ovd_cnt', 't7_win_cnt',
                't30_ovd_cnt', 't30_win_cnt', 't30_ovd_amt']
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce')

    # ============================================================
    # 主漏斗转化率（单调递减）
    # ============================================================
    df['sx_in_rate'] = df['sx_in_cnt'] / df['app_cnt'].replace(0, pd.NA)       # 进件→授信进入
    df['sx_pass_rate'] = df['sx_pass_cnt'] / df['sx_in_cnt'].replace(0, pd.NA) # 授信进入→授信通过(用信率)
    df['pass/sx'] = df['pass_cnt'] / df['sx_pass_cnt'].replace(0, pd.NA)       # 授信通过→最终通过
    df['issue/pass'] = df['issue_cnt'] / df['pass_cnt'].replace(0, pd.NA)      # 通过→放款
    df['issue/app'] = df['issue_cnt'] / df['app_cnt'].replace(0, pd.NA)        # 进件→放款 总转化
    df['avg_loan_amt'] = df['issue_amt'] / df['issue_cnt'].replace(0, pd.NA)   # 件均
    df['t7_ovd_rate'] = df['t7_ovd_cnt'] / df['t7_win_cnt'].replace(0, pd.NA)
    df['t30_ovd_rate'] = df['t30_ovd_cnt'] / df['t30_win_cnt'].replace(0, pd.NA)

    # 辅助环节触发率（进入/进件）
    df['af_trigger'] = df['af_in_cnt'] / df['app_cnt'].replace(0, pd.NA)
    df['model_trigger'] = df['model_in_cnt'] / df['app_cnt'].replace(0, pd.NA)
    df['ext_trigger'] = df['ext_in_cnt'] / df['app_cnt'].replace(0, pd.NA)

    # ============================================================
    # 汇总（全部新老客）
    # ============================================================
    agg_cols = ['app_cnt', 'sx_in_cnt', 'sx_pass_cnt', 'pass_cnt', 'issue_cnt', 'issue_amt',
                'af_in_cnt', 'af_pass_cnt', 'model_in_cnt', 'model_pass_cnt',
                'ext_in_cnt', 'ext_pass_cnt', 't7_ovd_cnt', 't7_win_cnt',
                't30_ovd_cnt', 't30_win_cnt', 't30_ovd_amt']
    summ = df.groupby('month')[agg_cols].sum().reset_index()
    summ['grant_strategy'] = '全部'
    for rate_col, a, b in [('sx_in_rate','sx_in_cnt','app_cnt'), ('sx_pass_rate','sx_pass_cnt','sx_in_cnt'),
                           ('pass/sx','pass_cnt','sx_pass_cnt'), ('issue/pass','issue_cnt','pass_cnt'),
                           ('issue/app','issue_cnt','app_cnt'), ('avg_loan_amt','issue_amt','issue_cnt'),
                           ('t7_ovd_rate','t7_ovd_cnt','t7_win_cnt'), ('t30_ovd_rate','t30_ovd_cnt','t30_win_cnt'),
                           ('af_trigger','af_in_cnt','app_cnt'), ('model_trigger','model_in_cnt','app_cnt'),
                           ('ext_trigger','ext_in_cnt','app_cnt')]:
        summ[rate_col] = summ[a] / summ[b].replace(0, pd.NA)

    df_all = pd.concat([df, summ], ignore_index=True).sort_values(['month', 'grant_strategy'])

    # ============================================================
    # 输出 Excel
    # ============================================================
    out = r'E:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\墨西哥完整信贷链路_2026_v2.xlsx'
    with pd.ExcelWriter(out, engine='openpyxl') as writer:
        df_all.to_excel(writer, sheet_name='完整链路明细', index=False)

        rate_cols = ['sx_in_rate', 'sx_pass_rate', 'pass/sx', 'issue/pass', 'issue/app',
                     'avg_loan_amt', 't7_ovd_rate', 't30_ovd_rate']
        pivot = df_all[df_all['grant_strategy'] == '全部'][['month'] + rate_cols]
        pivot.to_excel(writer, sheet_name='转化率矩阵', index=False)

    print(f'\n已输出: {out}')
    print()
    show = df_all[['month', 'grant_strategy', 'app_cnt', 'sx_in_cnt', 'sx_pass_cnt',
                   'pass_cnt', 'issue_cnt', 'issue_amt',
                   'sx_in_rate', 'sx_pass_rate', 'pass/sx', 'issue/pass', 'issue/app',
                   'avg_loan_amt', 't7_ovd_rate', 't30_ovd_rate']]
    print(show.to_string(index=False))


if __name__ == '__main__':
    main()

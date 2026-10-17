#!/usr/bin/env python3
"""
客群质量多期追踪工具
====================
用途：追踪不同渠道/不同批次客群的 FPD、多期逾期率、LTV 回收曲线
输入：各渠道的分期表现数据
输出：客群质量排名、回收曲线、质量趋势

输入格式（CSV）：
    channel,cohort_month,disbursals,fpd_1,fpd_2,fpd_3,ltv_30,ltv_60,ltv_90
    facebook,2026-01,500,0.12,0.18,0.22,15.0,28.0,38.0
    facebook,2026-02,550,0.10,0.16,0.20,18.0,32.0,42.0
    tiktok,2026-01,300,0.15,0.22,0.28,12.0,22.0,30.0
    tiktok,2026-02,350,0.13,0.20,0.25,14.0,25.0,34.0

使用方法：
    python cohort_analysis.py --file cohort_data.csv
    echo "channel,cohort_month,...\n..." | python cohort_analysis.py
"""

import json
import sys
import csv
import math


def read_data(input_source):
    reader = csv.DictReader(input_source)
    cohorts = []
    for row in reader:
        entry = {
            'channel': row['channel'],
            'cohort_month': row['cohort_month'],
            'disbursals': int(float(row.get('disbursals', 0))),
        }
        # 读取逾期率字段
        for period in range(1, 7):
            key = f'fpd_{period}'
            if key in row and row[key].strip():
                entry[key] = float(row[key])
        # 读取 LTV 字段
        for period in [30, 60, 90, 120, 180]:
            key = f'ltv_{period}'
            if key in row and row[key].strip():
                entry[key] = float(row[key])
        cohorts.append(entry)
    return cohorts


def analyze_quality(cohorts):
    """
    分析客群质量：
    1. 按渠道聚合，计算加权平均 FPD 和 LTV
    2. 质量排名
    3. 回收曲线
    4. 质量趋势（月度变化）
    """
    if not cohorts:
        return {'error': '无数据'}

    # 按渠道聚合
    by_channel = {}
    for c in cohorts:
        channel = c['channel']
        if channel not in by_channel:
            by_channel[channel] = {'cohorts': [], 'total_disbursals': 0}
        by_channel[channel]['cohorts'].append(c)
        by_channel[channel]['total_disbursals'] += c['disbursals']

    channel_summary = {}
    for channel, data in by_channel.items():
        cohort_list = data['cohorts']
        total_dis = data['total_disbursals']

        # 加权平均 FPD
        weighted_fpd = {}
        fpd_keys = [k for k in cohort_list[0].keys() if k.startswith('fpd_')]
        for fk in sorted(fpd_keys):
            weighted_sum = sum(c[fk] * c['disbursals'] for c in cohort_list if fk in c)
            dis_sum = sum(c['disbursals'] for c in cohort_list if fk in c)
            weighted_fpd[fk] = round(weighted_sum / max(dis_sum, 1), 4) if dis_sum > 0 else None

        # 最新一期 FPD
        latest = cohort_list[-1]
        latest_fpd = {fk: latest.get(fk, None) for fk in sorted(fpd_keys)}

        # 加权平均 LTV
        weighted_ltv = {}
        ltv_keys = [k for k in cohort_list[0].keys() if k.startswith('ltv_')]
        for lk in sorted(ltv_keys):
            weighted_sum = sum(c[lk] * c['disbursals'] for c in cohort_list if lk in c)
            dis_sum = sum(c['disbursals'] for c in cohort_list if lk in c)
            weighted_ltv[lk] = round(weighted_sum / max(dis_sum, 1), 2) if dis_sum > 0 else None

        # 趋势判断
        trend = 'stable'
        if len(cohort_list) >= 3:
            fpd1_values = [c.get('fpd_1', 0) for c in cohort_list if 'fpd_1' in c]
            if len(fpd1_values) >= 3:
                first_half = sum(fpd1_values[:len(fpd1_values)//2]) / (len(fpd1_values)//2)
                second_half = sum(fpd1_values[-len(fpd1_values)//2:]) / (len(fpd1_values)//2)
                if second_half > first_half * 1.2:
                    trend = '恶化'
                elif second_half < first_half * 0.8:
                    trend = '改善'

        channel_summary[channel] = {
            'total_disbursals': total_dis,
            'cohort_count': len(cohort_list),
            'weighted_fpd': weighted_fpd,
            'latest_fpd': latest_fpd,
            'weighted_ltv': weighted_ltv,
            'trend': trend,
            'quality_score': _calc_quality_score(weighted_fpd, weighted_ltv)
        }

    # 按质量评分排序
    ranked = sorted(channel_summary.items(), key=lambda x: x[1]['quality_score'], reverse=True)
    ranking = []
    for i, (channel, info) in enumerate(ranked, 1):
        ranking.append({
            'rank': i,
            'channel': channel,
            'quality_score': info['quality_score'],
            'total_disbursals': info['total_disbursals'],
            'fpd_1': info['weighted_fpd'].get('fpd_1', None),
            'trend': info['trend']
        })

    # 整体趋势
    all_months = sorted(set(c['cohort_month'] for c in cohorts))
    monthly_trend = []
    for month in all_months:
        month_cohorts = [c for c in cohorts if c['cohort_month'] == month]
        if month_cohorts:
            total_dis = sum(c['disbursals'] for c in month_cohorts)
            avg_fpd1 = sum(c.get('fpd_1', 0) * c['disbursals'] for c in month_cohorts if 'fpd_1' in c)
            fpd_dis = sum(c['disbursals'] for c in month_cohorts if 'fpd_1' in c)
            monthly_trend.append({
                'month': month,
                'total_disbursals': total_dis,
                'avg_fpd_1': round(avg_fpd1 / max(fpd_dis, 1), 4) if fpd_dis > 0 else None
            })

    result = {
        'channels': channel_summary,
        'ranking': ranking,
        'monthly_trend': monthly_trend,
        'recommendation': _generate_quality_recommendation(ranking, monthly_trend)
    }

    return result


def _calc_quality_score(weighted_fpd, weighted_ltv):
    """
    质量评分：综合 FPD 和 LTV
    分数越高表示质量越好
    """
    score = 50.0  # 基础分

    # FPD 扣分
    fpd_1 = weighted_fpd.get('fpd_1', None)
    if fpd_1 is not None:
        score -= fpd_1 * 100  # FPD 10% 扣10分

    # LTV 加分
    ltv_30 = weighted_ltv.get('ltv_30', None)
    if ltv_30 is not None:
        score += ltv_30 * 2  # LTV30 每1刀加2分

    ltv_90 = weighted_ltv.get('ltv_90', None)
    if ltv_90 is not None:
        score += ltv_90 * 1  # LTV90 每1刀加1分

    return round(score, 2)


def _generate_quality_recommendation(ranking, monthly_trend):
    """生成质量优化建议"""
    parts = []

    if not ranking:
        return "缺乏数据，无法生成建议"

    best = ranking[0]
    worst = ranking[-1]

    # 质量差距
    if len(ranking) >= 2:
        gap = best['quality_score'] - worst['quality_score']
        if gap > 30:
            parts.append(f"各渠道质量差距较大（{best['channel']} vs {worst['channel']} 分差{gap}），建议缩减{worst['channel']}预算")

    # FPD 趋势
    if len(monthly_trend) >= 2:
        first_fpd = monthly_trend[0].get('avg_fpd_1', 0) or 0
        last_fpd = monthly_trend[-1].get('avg_fpd_1', 0) or 0
        if last_fpd > first_fpd * 1.3:
            parts.append(f"⚠️ FPD 呈上升趋势（{monthly_trend[0]['month']}: {first_fpd*100:.1f}% → {monthly_trend[-1]['month']}: {last_fpd*100:.1f}%），需关注客群质量")

    # 质量恶化渠道
    bad_trend = [r for r in ranking if r.get('trend') == '恶化']
    if bad_trend:
        names = [r['channel'] for r in bad_trend]
        parts.append(f"渠道{', '.join(names)}质量趋势恶化，建议排查定向策略")

    return '；'.join(parts) if parts else "客群质量总体稳定"


def format_output(result):
    """格式化为易读的输出"""
    if 'error' in result:
        return {'error': result['error']}

    lines = []
    lines.append("客群质量多期追踪报告")
    lines.append(f"{'='*60}")
    lines.append("")

    lines.append("渠道质量排名:")
    lines.append(f"{'排名':<6} {'渠道':<15} {'放款数':>10} {'FPD1':>8} {'质量趋势':>10} {'评分':>8}")
    lines.append(f"{'-'*6} {'-'*15} {'-'*10} {'-'*8} {'-'*10} {'-'*8}")
    for r in result['ranking']:
        fpd_str = f"{r.get('fpd_1', 0)*100:.1f}%" if r.get('fpd_1') else "N/A"
        trend_emoji = '🔴' if r['trend'] == '恶化' else ('🟢' if r['trend'] == '改善' else '➡️')
        lines.append(f"#{r['rank']:<4} {r['channel']:<15} {r['total_disbursals']:>8,} {fpd_str:>8} {trend_emoji}{r['trend']:>8} {r['quality_score']:>6.1f}")
    lines.append("")

    lines.append("月度 FPD 趋势:")
    for t in result['monthly_trend']:
        fpd_str = f"{t['avg_fpd_1']*100:.1f}%" if t['avg_fpd_1'] else "N/A"
        lines.append(f"  {t['month']}: 放款{t['total_disbursals']:>6,}人 | 加权FPD1 {fpd_str}")
    lines.append("")

    lines.append(f"策略建议：{result['recommendation']}")

    return '\n'.join(lines)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--file':
        idx = sys.argv.index('--file')
        filepath = sys.argv[idx + 1]
        with open(filepath, 'r', encoding='utf-8') as f:
            cohorts = read_data(f)
    else:
        cohorts = read_data(sys.stdin)

    if not cohorts:
        print(json.dumps({'error': '无法从输入解析客群数据。需要的CSV格式: channel,cohort_month,disbursals,fpd_1'}, ensure_ascii=False))
        sys.exit(1)

    result = analyze_quality(cohorts)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

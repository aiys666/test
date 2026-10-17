#!/usr/bin/env python3
"""
渠道效率矩阵评估工具
====================
用途：基于 CPS 和 Grade 1-2 占比，将渠道划分为四象限并输出策略建议
输入：各渠道名称、CPS、Grade 1-2占比
输出：四象限分类 + 策略推荐 + 可视化数据

输入格式（CSV）：
    channel,cps,grade12_pct,category
    facebook,18.0,0.65,main
    tiktok,22.0,0.55,main
    google_uac,25.0,0.70,secondary
    audience_network,12.0,0.30,fill
    affiliate,15.0,0.35,fill

使用方法：
    python channel_matrix.py --file channels.csv [--target-cps 20]
    echo "channel,cps,grade12_pct\n..." | python channel_matrix.py
"""

import json
import sys
import csv
import math


def read_data(input_source):
    reader = csv.DictReader(input_source)
    channels = []
    for row in reader:
        entry = {
            'name': row['channel'],
            'cps': float(row['cps']),
            'grade12_pct': float(row['grade12_pct']),
            'category': row.get('category', 'main'),
        }
        # 可选字段
        for field in ['spend', 'disbursals', 'fpd', 'impressions', 'ctr']:
            if field in row and row[field].strip():
                entry[field] = float(row[field])
        channels.append(entry)
    return channels


def classify_channels(channels, target_cps=None):
    """
    将渠道分为四象限：
    - 🟢 明星渠道：低CPS × 高Grade1-2 → 优先放量
    - 🔵 规模渠道：低CPS × 低Grade1-2 → 控制占比
    - 🟡 品质渠道：高CPS × 高Grade1-2 → 维持预算
    - 🔴 优化渠道：高CPS × 低Grade1-2 → 缩减或优化

    如果没有 target_cps，使用所有渠道 CPS 的中位数作为分界线
    """
    if not channels:
        return {'error': '无渠道数据'}

    # 确定 CPS 分界线
    if target_cps:
        cps_threshold = target_cps
    else:
        cps_values = sorted([c['cps'] for c in channels])
        mid = len(cps_values) // 2
        cps_threshold = cps_values[mid] if len(cps_values) % 2 else (cps_values[mid-1] + cps_values[mid]) / 2

    # Grade 1-2 分界线：建议 ≥ 50% 为高
    grade12_threshold = 0.50

    quadrants = {
        'star': {'label': '🟢 明星渠道', 'strategy': '优先放量，最大化预算', 'channels': []},
        'scale': {'label': '🔵 规模渠道', 'strategy': '控制占比，用于冲量不冲质', 'channels': []},
        'quality': {'label': '🟡 品质渠道', 'strategy': '维持预算，优化客群结构', 'channels': []},
        'optimize': {'label': '🔴 优化渠道', 'strategy': '缩减预算或优化后重新评估', 'channels': []},
    }

    for c in channels:
        is_low_cps = c['cps'] <= cps_threshold
        is_high_quality = c['grade12_pct'] >= grade12_threshold

        if is_low_cps and is_high_quality:
            quadrant = 'star'
        elif is_low_cps and not is_high_quality:
            quadrant = 'scale'
        elif not is_low_cps and is_high_quality:
            quadrant = 'quality'
        else:
            quadrant = 'optimize'

        entry = {
            'name': c['name'],
            'cps': c['cps'],
            'grade12_pct': c['grade12_pct'],
            'cps_vs_threshold': round(c['cps'] - cps_threshold, 2),
            'quality_gap': round(c['grade12_pct'] - grade12_threshold, 4),
        }
        if 'spend' in c:
            entry['spend'] = c['spend']
        if 'fpd' in c:
            entry['fpd'] = c['fpd']

        quadrants[quadrant]['channels'].append(entry)

    # 添加全局排序
    all_ranked = sorted(channels, key=lambda c: (c['cps'], -c['grade12_pct']))
    ranking = []
    for i, c in enumerate(all_ranked, 1):
        ranking.append({
            'rank': i,
            'channel': c['name'],
            'cps': c['cps'],
            'grade12_pct': c['grade12_pct'],
            'composite_score': round(1.0 / max(c['cps'], 0.01) * c['grade12_pct'] * 10000, 2)
        })

    # 统计
    total_channels = len(channels)
    quadrant_counts = {k: len(v['channels']) for k, v in quadrants.items()}
    star_pct = round(quadrant_counts['star'] / max(total_channels, 1) * 100, 1)

    result = {
        'cps_threshold': round(cps_threshold, 2),
        'grade12_threshold': round(grade12_threshold, 2),
        'total_channels': total_channels,
        'star_ratio': f"{star_pct}%",
        'quadrants': quadrants,
        'ranking': ranking,
        'recommendation': _generate_recommendation(quadrants, total_channels)
    }

    return result


def _generate_recommendation(quadrants, total):
    """生成策略建议"""
    star_count = len(quadrants['star']['channels'])
    scale_count = len(quadrants['scale']['channels'])
    optimize_count = len(quadrants['optimize']['channels'])

    parts = []
    if star_count >= 2:
        parts.append(f"有{star_count}个明星渠道，建议集中预算放量")
    elif star_count == 1:
        parts.append("只有1个明星渠道，需注意集中度风险，培育第二渠道")
    elif star_count == 0:
        parts.append("⚠️ 目前没有明星渠道，需要先优化出价或素材来降低CPS")

    if optimize_count > 0:
        parts.append(f"有{optimize_count}个优化渠道，建议缩减或暂停后重新评估")

    if scale_count > total * 0.5:
        parts.append("⚠️ 规模渠道占比过高（>50%），整体客群质量可能偏低，建议关注FPD趋势")

    return '；'.join(parts) if parts else "渠道结构健康，按当前策略执行"


def format_output(result):
    """格式化为易读的输出"""
    if 'error' in result:
        return {'error': result['error']}

    lines = []
    lines.append("渠道效率四象限评估")
    lines.append(f"{'='*60}")
    lines.append(f"CPS分界线: ${result['cps_threshold']} | Grade1-2分界线: {result['grade12_threshold']*100}%")
    lines.append("")

    for q_key in ['star', 'scale', 'quality', 'optimize']:
        q = result['quadrants'][q_key]
        lines.append(f"{q['label']} — {q['strategy']}")
        if not q['channels']:
            lines.append("  (无)")
        else:
            for c in q['channels']:
                lines.append(f"  ├ {c['name']}: CPS ${c['cps']} | Grade1-2 {c['grade12_pct']*100:.0f}%")
        lines.append("")

    # 排名
    lines.append("综合效率排名 (CPS×质量):")
    lines.append(f"{'排名':<6} {'渠道':<15} {'CPS':>8} {'Grade1-2':>10} {'综合分':>10}")
    lines.append(f"{'-'*6} {'-'*15} {'-'*8} {'-'*10} {'-'*10}")
    for r in result['ranking'][:8]:
        lines.append(f"#{r['rank']:<4} {r['channel']:<15} ${r['cps']:>5.1f} {r['grade12_pct']*100:>8.0f}% {r['composite_score']:>8.2f}")

    lines.append("")
    lines.append(f"策略建议：{result['recommendation']}")

    return '\n'.join(lines)


def main():
    target_cps = None
    if '--target-cps' in sys.argv:
        idx = sys.argv.index('--target-cps')
        target_cps = float(sys.argv[idx + 1])

    if len(sys.argv) > 1 and sys.argv[1] == '--file':
        idx = sys.argv.index('--file')
        filepath = sys.argv[idx + 1]
        with open(filepath, 'r', encoding='utf-8') as f:
            channels = read_data(f)
    else:
        channels = read_data(sys.stdin)

    if not channels:
        print(json.dumps({'error': '无法从输入解析渠道数据。需要的CSV格式: channel,cps,grade12_pct'}, ensure_ascii=False))
        sys.exit(1)

    result = classify_channels(channels, target_cps)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

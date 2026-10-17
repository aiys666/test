#!/usr/bin/env python3
"""
预算优化分配工具
================
用途：基于渠道效率数据，在多约束条件下计算最优预算分配
输入：各渠道的 CPS、Grade 1-2占比、放量上限、当前预算
输出：最优预算分配方案 + 敏感性分析

输入格式（CSV）：
    channel,cps,grade12_pct,current_budget,max_budget,min_budget,total_budget
    facebook,18.0,0.65,40000,80000,20000,200000
    tiktok,22.0,0.55,30000,60000,15000,200000
    google,25.0,0.70,20000,40000,10000,200000
    affiliate,15.0,0.35,10000,30000,5000,200000

使用方法：
    python budget_optimizer.py --file budget_data.csv [--target-cps 20]
    echo "channel,cps,...\n..." | python budget_optimizer.py
"""

import json
import sys
import csv
import math


EPSILON = 1e-10


def read_data(input_source):
    """读取渠道数据"""
    reader = csv.DictReader(input_source)
    channels = []
    for row in reader:
        channels.append({
            'name': row['channel'],
            'cps': float(row['cps']),
            'grade12_pct': float(row.get('grade12_pct', 0.5)),
            'current_budget': float(row.get('current_budget', 0)),
            'max_budget': float(row.get('max_budget', float('inf'))),
            'min_budget': float(row.get('min_budget', 0)),
        })
    return channels


def calc_efficiency_weight(cps, grade12_pct, scale_potential=1.0):
    """
    计算渠道效率权重
    公式：权重 = (1/CPS) × Grade1-2占比 × 放量空间系数
    """
    cps_weight = 1.0 / max(cps, EPSILON)
    return cps_weight * grade12_pct * scale_potential


def optimize_budget(channels, total_budget, target_cps=None):
    """
    基于边际效率的预算优化分配

    核心逻辑：
    1. 先按效率权重计算初始分配
    2. 检查各渠道是否在约束范围内
    3. 对超出约束的渠道做预算再分配
    4. 计算优化后的综合 CPS
    """
    if not channels:
        return {'error': '无渠道数据'}

    total_current = sum(c['current_budget'] for c in channels)

    # 计算各渠道的放量空间系数
    # 放量空间：如果当前预算远低于 max，说明有大的放量空间
    for c in channels:
        if c['max_budget'] and c['max_budget'] < float('inf'):
            remaining_room = max(0, c['max_budget'] - c['current_budget'])
            c['scale_potential'] = min(1.0, remaining_room / max(c['current_budget'], 1))
        else:
            c['scale_potential'] = 1.0

    # 计算效率权重
    weights = []
    total_weight = 0
    for c in channels:
        w = calc_efficiency_weight(c['cps'], c['grade12_pct'], c['scale_potential'])
        weights.append(w)
        total_weight += w

    # 初始分配
    allocations = []
    for c, w in zip(channels, weights):
        raw_alloc = total_budget * w / max(total_weight, EPSILON)
        clamped = max(c['min_budget'], min(raw_alloc, c['max_budget']))
        allocations.append({
            'channel': c['name'],
            'cps': c['cps'],
            'grade12_pct': c['grade12_pct'],
            'current_budget': c['current_budget'],
            'allocated_budget': round(clamped, 2),
            'initial_allocation': round(raw_alloc, 2),
            'weight': round(w / max(total_weight, EPSILON) * 100, 2),
            'efficiency_score': round(w, 4),
            'scale_potential': round(c['scale_potential'], 2)
        })

    # 如果 clamp 后有剩余预算，重新分配给仍有空间的渠道
    allocated_total = sum(a['allocated_budget'] for a in allocations)
    remaining = total_budget - allocated_total

    iterations = 0
    while abs(remaining) > 100 and iterations < 10:
        iterations += 1
        if remaining > 0:
            # 有预算剩余，分配给有空间的渠道
            candidates = [a for a in allocations if a['allocated_budget'] < a.get('max_budget', float('inf'))]
            if not candidates:
                break
            per_channel = remaining / len(candidates)
            for a in candidates:
                a['allocated_budget'] = round(a['allocated_budget'] + per_channel, 2)
        else:
            # 预算超额，从有空间的渠道减
            candidates = [a for a in allocations if a['allocated_budget'] > a['current_budget'] * 0.5]
            if not candidates:
                break
            per_channel = abs(remaining) / len(candidates)
            for a in candidates:
                a['allocated_budget'] = round(a['allocated_budget'] - per_channel, 2)

        allocated_total = sum(a['allocated_budget'] for a in allocations)
        remaining = round(total_budget - allocated_total, 2)

    # 计算预期产出
    total_expected_disbursals = 0
    for a in allocations:
        expected = a['allocated_budget'] / max(a['cps'], EPSILON)
        a['expected_disbursals'] = round(expected, 0)
        total_expected_disbursals += expected

    # 计算综合 CPS
    blended_cps = total_budget / max(total_expected_disbursals, EPSILON) if total_expected_disbursals > 0 else float('inf')

    # 计算对比
    current_disbursals = 0
    for c, a in zip(channels, allocations):
        current_disbursals += c['current_budget'] / max(c['cps'], EPSILON)

    current_blended_cps = total_current / max(current_disbursals, EPSILON) if current_disbursals > 0 else float('inf')

    # 按分配金额排序（降序）
    allocations.sort(key=lambda x: x['allocated_budget'], reverse=True)

    result = {
        'total_budget': total_budget,
        'allocated_total': allocated_total,
        'expected_disbursals': round(total_expected_disbursals, 0),
        'blended_cps': round(blended_cps, 2),
        'current_blended_cps': round(current_blended_cps, 2),
        'cps_change': round((blended_cps - current_blended_cps) / max(current_blended_cps, EPSILON) * 100, 2),
        'channels': allocations,
        'comparison': {
            'current_total_budget': total_current,
            'current_disbursals': round(current_disbursals, 0),
            'new_disbursals': round(total_expected_disbursals, 0),
            'disbursals_change': f"{round((total_expected_disbursals - current_disbursals) / max(current_disbursals, EPSILON) * 100, 2)}%"
        }
    }

    return result


def format_output(result):
    """格式化为易读的输出"""
    if 'error' in result:
        return {'error': result['error']}

    lines = []
    lines.append(f"预算优化方案")
    lines.append(f"{'='*50}")
    lines.append(f"总预算: ${result['total_budget']:,.0f}")
    lines.append(f"预期放款数: {result['expected_disbursals']:,.0f} 人")
    lines.append(f"综合 CPS: ${result['blended_cps']} (当前 ${result['current_blended_cps']}, 变化 {result['cps_change']}%)")
    lines.append(f"预期放款增量: {result['comparison']['new_disbursals']:,.0f} vs 当前 {result['comparison']['current_disbursals']:,.0f} ({result['comparison']['disbursals_change']})")
    lines.append("")

    lines.append(f"{'渠道':<15} {'当前预算':>12} {'分配预算':>12} {'变化':>10} {'CPS':>8} {'Grade1-2':>10} {'预期放款':>10}")
    lines.append(f"{'-'*15} {'-'*12} {'-'*12} {'-'*10} {'-'*8} {'-'*10} {'-'*10}")

    for a in result['channels']:
        chg = a['allocated_budget'] - a['current_budget']
        chg_str = f"+${chg:,.0f}" if chg > 0 else f"-${abs(chg):,.0f}" if chg < 0 else "$0"
        lines.append(f"{a['channel']:<15} ${a['current_budget']:>9,.0f} ${a['allocated_budget']:>9,.0f} {chg_str:>10} ${a['cps']:>5.1f} {a['grade12_pct']*100:>8.0f}% {a['expected_disbursals']:>10,.0f}")

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

    total_budget = sum(c['current_budget'] for c in channels)
    if '--total-budget' in sys.argv:
        idx = sys.argv.index('--total-budget')
        total_budget = float(sys.argv[idx + 1])

    if not channels:
        print(json.dumps({'error': '无法从输入解析渠道数据。需要的CSV格式: channel,cps,grade12_pct,current_budget'}, ensure_ascii=False))
        sys.exit(1)

    result = optimize_budget(channels, total_budget, target_cps)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

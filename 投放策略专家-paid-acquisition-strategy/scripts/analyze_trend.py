#!/usr/bin/env python3
"""
投放数据趋势分析工具
====================
用途：对时间序列数据进行趋势检测、异常波动识别、环比/同比变化计算
输入：CSV 格式的时间序列数据（从标准输入或文件读取）
输出：JSON 格式的趋势分析报告

输入格式（CSV，支持 piped 或文件）：
    date,metric,value
    2026-01-01,spend,5000
    2026-01-01,disbursals,250
    2026-01-01,cps,20.0

支持两种模式：
1. 通用趋势分析：传入时间序列数据，输出趋势方向和异常点
2. 对比分析：传入两期数据，输出 WoW/MoM 变化

使用方法：
    python analyze_trend.py --file data.csv [--period daily|weekly|monthly]
    echo "date,metric,value\n..." | python analyze_trend.py
"""

import json
import sys
import csv
import math
from collections import defaultdict
from datetime import datetime, timedelta


def read_data(input_source):
    """从文件或 stdin 读取 CSV 数据"""
    reader = csv.DictReader(input_source)
    data = defaultdict(list)
    for row in reader:
        try:
            val = float(row['value'])
            data[row['metric']].append({
                'date': row['date'],
                'value': val
            })
        except (ValueError, KeyError) as e:
            continue
    return data


def calc_change(current, previous):
    """计算变化率和变化方向"""
    if previous == 0 or previous is None:
        return {'change_pct': None, 'direction': 'no_previous'}
    change_pct = (current - previous) / previous * 100
    direction = 'up' if change_pct > 0 else ('down' if change_pct < 0 else 'flat')
    return {
        'change_pct': round(change_pct, 2),
        'direction': direction,
        'absolute_change': round(current - previous, 2)
    }


def detect_anomaly(values, threshold=2.0):
    """
    基于移动平均 + 标准差检测异常点
    原理：如果某个点偏离移动平均值超过 threshold 个标准差，标记为异常
    """
    if len(values) < 4:
        return [False] * len(values)

    n = min(3, len(values) - 1)
    results = []
    for i in range(len(values)):
        # 用前 n 个点做基线（不含当前点）
        if i < n:
            results.append(False)
            continue
        window = values[i-n:i]
        mean = sum(window) / len(window)
        variance = sum((x - mean) ** 2 for x in window) / len(window)
        std = math.sqrt(variance) if variance > 0 else 0.001

        if std > 0 and abs(values[i] - mean) > threshold * std:
            results.append(True)
        else:
            results.append(False)
    return results


def split_periods(data, freq='weekly'):
    """按周期聚合数据"""
    periods = defaultdict(lambda: defaultdict(list))
    for metric, points in data.items():
        for p in points:
            dt = datetime.strptime(p['date'], '%Y-%m-%d')
            if freq == 'weekly':
                # 按 ISO 周聚合
                key = f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}"
            elif freq == 'monthly':
                key = f"{dt.year}-{dt.month:02d}"
            else:
                key = p['date']
            periods[metric][key].append(p['value'])

    aggregated = {}
    for metric, period_data in periods.items():
        aggregated[metric] = []
        for period_key, values in sorted(period_data.items()):
            aggregated[metric].append({
                'period': period_key,
                'value': round(sum(values) / len(values), 2) if metric != 'spend' else round(sum(values), 2)
            })
    return aggregated


def analyze_trend(data, freq='daily'):
    """
    主分析函数
    - 对每个指标计算环比变化
    - 检测异常波动
    - 判断趋势方向
    """
    result = {}
    for metric, points in data.items():
        points_sorted = sorted(points, key=lambda x: x['date'])
        values = [p['value'] for p in points_sorted]
        dates = [p['date'] for p in points_sorted]

        if len(values) < 2:
            result[metric] = {
                'error': '数据点不足（至少需要2个点）',
                'values': values,
                'dates': dates
            }
            continue

        # 环比变化
        changes = []
        for i in range(1, len(values)):
            chg = calc_change(values[i], values[i-1])
            changes.append({
                'period': f"{dates[i-1]} → {dates[i]}",
                **chg
            })

        # WoW 变化（如果有足够数据）
        wow = None
        if len(values) >= 8:
            recent_7 = sum(values[-7:]) / min(7, len(values[-7:]))
            prev_7 = sum(values[-14:-7]) / min(7, len(values[-14:-7])) if len(values) >= 14 else None
            if prev_7 and prev_7 > 0:
                wow = calc_change(recent_7, prev_7)
                wow['recent_7_avg'] = round(recent_7, 2)
                wow['prev_7_avg'] = round(prev_7, 2)

        # 异常点检测
        anomaly_flags = detect_anomaly(values)

        # 整体趋势判断（用线性回归斜率的符号）
        trend = 'unknown'
        if len(values) >= 3:
            x = list(range(len(values)))
            n = len(values)
            slope = (n * sum(x[i] * values[i] for i in range(n)) - sum(x) * sum(values)) / \
                    (n * sum(xi*xi for xi in x) - sum(x) ** 2) if n > 1 else 0
            if slope > 0.01:
                trend = '上升'
            elif slope < -0.01:
                trend = '下降'
            else:
                trend = '持平'

        # 统计
        total = sum(values)
        avg = round(total / len(values), 2)
        min_val = min(values)
        max_val = max(values)
        latest = values[-1]
        first = values[0]

        result[metric] = {
            'latest': round(latest, 2),
            'avg': avg,
            'min': round(min_val, 2),
            'max': round(max_val, 2),
            'total': round(total, 2),
            'trend': trend,
            'data_points': len(values),
            'changes': changes[-5:],  # 最近5期变化
            'anomalies': [{'date': dates[i], 'value': values[i]} for i, flag in enumerate(anomaly_flags) if flag],
            'wow': wow
        }

    return result


def format_output(result):
    """格式化为易读的输出"""
    output = {'summary': {}, 'details': result}

    # 生成摘要
    summary_lines = []
    for metric, info in result.items():
        if 'error' in info:
            summary_lines.append(f"⚠️ {metric}: {info['error']}")
            continue

        metric_names = {
            'cps': 'CPS', 'spend': '消耗', 'disbursals': '放款数',
            'ctr': 'CTR', 'cpm': 'CPM', 'cpi': 'CPI',
            'cpr': 'CPR', 'fpd': 'FPD', 'installs': '安装数',
            'registrations': '注册数', 'applications': '进件数',
            'approvals': '授信数', 'impressions': '曝光数',
            'clicks': '点击数'
        }
        name = metric_names.get(metric, metric)

        parts = [f"{name}: 最新{info['latest']} (avg:{info['avg']})"]
        parts.append(f"趋势{info['trend']}")

        if info['wow']:
            wow = info['wow']
            emoji = '📈' if wow['direction'] == 'up' else ('📉' if wow['direction'] == 'down' else '➡️')
            parts.append(f"近7日均{wow['recent_7_avg']} 上7日{wow['prev_7_avg']} WoW{emoji}{wow['change_pct']}%")

        if info['anomalies']:
            for a in info['anomalies']:
                parts.append(f"⚠️ {a['date']}异常({a['value']})")

        summary_lines.append(" | ".join(parts))

    output['summary'] = summary_lines
    return output


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--file':
        idx = sys.argv.index('--file')
        filepath = sys.argv[idx + 1]
        with open(filepath, 'r', encoding='utf-8') as f:
            data = read_data(f)
    else:
        data = read_data(sys.stdin)

    # 周期参数
    freq = 'daily'
    if '--period' in sys.argv:
        idx = sys.argv.index('--period')
        freq = sys.argv[idx + 1]

    if not data:
        print(json.dumps({'error': '无法从输入解析数据。需要的CSV格式: date,metric,value'}, ensure_ascii=False))
        sys.exit(1)

    result = analyze_trend(data, freq)
    output = format_output(result)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

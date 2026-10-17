"""
测试修复后的MA转化率计算
"""

def calc_ma_simple(rates, window=3):
    """简单移动平均（修复后）"""
    if not rates:
        return 0.0
    recent = rates[:window]
    return round(sum(recent) / len(recent), 6)

def calc_ma_old_trend(rates, window=3):
    """带趋势外推的MA（修复前，有问题的版本）"""
    if not rates:
        return 0.0
    recent = rates[:window]
    ma_val = sum(recent) / len(recent)
    if len(recent) >= 3:
        trend = (recent[0] - recent[-1]) / len(recent)
        projected = recent[0] + trend
        projected = max(0.0, min(1.0, projected))
        return round((ma_val + projected) / 2, 6)
    return round(ma_val, 6)

# 测试数据：MOB1的历史转化率（最新→最老）
test_rates = [0.38, 0.40, 0.42]  # 最新期是38%，前两期是40%和42%

print("=" * 60)
print("MA转化率计算对比")
print("=" * 60)
print(f"历史转化率序列（最新→最老）: {test_rates}")
print(f"\n【修复前】带趋势外推的MA: {calc_ma_old_trend(test_rates):.4%}")
print(f"   → 问题：趋势外推会让下降趋势继续，导致结果偏低")
print(f"\n【修复后】简单移动平均(SMA): {calc_ma_simple(test_rates):.4%}")
print(f"   → 正确：直接取3期平均值")
print("\n" + "=" * 60)

# 再测试一个上升趋势的情况
test_rates_up = [0.45, 0.42, 0.38]  # 上升趋势：38%→42%→45%
print(f"\n历史转化率序列（上升趋势）: {test_rates_up}")
print(f"【修复前】带趋势外推的MA: {calc_ma_old_trend(test_rates_up):.4%}")
print(f"【修复后】简单移动平均(SMA): {calc_ma_simple(test_rates_up):.4%}")
print("\n" + "=" * 60)
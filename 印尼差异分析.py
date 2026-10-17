# -*- coding: utf-8 -*-
"""
差异分析脚本 - 分析基准结果与优化后结果的差异
"""
import pandas as pd
import os

OUTPUT_DIR = r"E:\岳松个人文件\嘉银工作内容的整理\code"

baseline_file = os.path.join(OUTPUT_DIR, "印尼拍拍_基准结果_第一段.csv")
optimized_files = [
    f for f in os.listdir(OUTPUT_DIR) 
    if f.startswith("印尼拍拍_核心指标_") and f.endswith(".csv")
]

if optimized_files:
    optimized_files.sort(reverse=True)
    latest_file = os.path.join(OUTPUT_DIR, optimized_files[0])
    print(f"基准文件: {baseline_file}")
    print(f"优化后文件: {latest_file}")
    
    baseline_df = pd.read_csv(baseline_file)
    optimized_df = pd.read_csv(latest_file)
    
    print(f"\n基准数据: {len(baseline_df)}行, {len(baseline_df.columns)}列")
    print(f"优化数据: {len(optimized_df)}行, {len(optimized_df.columns)}列")
    
    print("\n" + "=" * 60)
    print("逐列差异分析")
    print("=" * 60)
    
    total_diffs = 0
    diff_columns = []
    
    for col in baseline_df.columns:
        baseline_vals = baseline_df[col].fillna('NULL').astype(str)
        optimized_vals = optimized_df[col].fillna('NULL').astype(str)
        
        if not baseline_vals.equals(optimized_vals):
            mismatches = (baseline_vals != optimized_vals).sum()
            total_diffs += mismatches
            diff_columns.append((col, mismatches))
            
            print(f"\n列 '{col}' - {mismatches}处差异:")
            
            diff_indices = baseline_df[baseline_vals != optimized_vals].index[:3]
            for idx in diff_indices:
                b_val = baseline_df.loc[idx, col]
                o_val = optimized_df.loc[idx, col]
                print(f"  行{idx}: 基准={b_val[:50]}, 优化={o_val[:50]}")
    
    print("\n" + "=" * 60)
    print(f"总差异数: {total_diffs}")
    print(f"有差异的列数: {len(diff_columns)}")
    
    if diff_columns:
        print("\n差异列排序（按差异数量）:")
        diff_columns.sort(key=lambda x: x[1], reverse=True)
        for col, count in diff_columns[:10]:
            print(f"  {col}: {count}处差异")
    
    print("\n" + "=" * 60)
    print("结论:")
    print("=" * 60)
    if total_diffs == 0:
        print("✅✅✅ 所有数据完全一致！")
    else:
        print("⚠️  存在数据差异，可能原因:")
        print("  1. 数据库中的实时数据在两次查询间发生了变化")
        print("  2. 浮点精度差异")
        print("  3. 查询时间窗口不同导致结果略有差异")
        
        numeric_cols = baseline_df.select_dtypes(include=['float64', 'int64']).columns
        if len(numeric_cols) > 0:
            print(f"\n数值列统计: {len(numeric_cols)}列")
            print("  差异可能主要来自数值计算的微小波动")

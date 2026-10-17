# -*- coding: utf-8 -*-
"""
配置加载模块 - 从 config.yaml 加载配置
从印尼 pipeline 的 core/config.py 改编
"""
import os
import yaml
from pathlib import Path

# 配置单例
_config = None

def load_config():
    """
    加载 config.yaml 配置文件
    使用单例模式避免重复加载
    """
    global _config
    if _config is not None:
        return _config
    
    # 配置文件路径
    config_path = Path(__file__).parent.parent / "config.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        _config = yaml.safe_load(f)
    
    return _config

def get_country_config():
    """获取墨西哥国家配置"""
    cfg = load_config()
    return cfg.get('MEXICO', {})

def get_db_config():
    """获取数据库配置"""
    cfg = load_config()
    return cfg.get('DB', {})

def get_analysis_config():
    """获取分析配置"""
    cfg = load_config()
    return cfg.get('ANALYSIS', {})

def get_output_dir():
    """获取输出目录"""
    cfg = load_config()
    return cfg.get('OUTPUT_DIR', './output')

def get_data_dir():
    """获取数据目录"""
    cfg = load_config()
    return cfg.get('DATA_DIR', './data')

if __name__ == "__main__":
    cfg = load_config()
    print(f"墨西哥国家: {cfg.get('MEXICO', {}).get('country_code', 'N/A')}")
    print(f"货币: {cfg.get('MEXICO', {}).get('currency', 'N/A')}")
    print(f"产品数: {len(cfg.get('MEXICO', {}).get('products', []))}")
    print(f"渠道数: {len(cfg.get('MEXICO', {}).get('channels', []))}")

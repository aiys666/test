# -*- coding: utf-8 -*-
"""
经营计划自动化 — 配置加载器
从 config.yaml 加载所有参数，支持占位符替换和参数校验
"""

import os
import yaml
from datetime import datetime
from typing import Any, Dict


# ═══════════════════════════════════════════════════════════════
# 配置加载
# ═══════════════════════════════════════════════════════════════

def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    加载 YAML 配置文件
    如果指定了路径则加载指定文件，否则在同目录下查找 config.yaml
    """
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
        config_path = os.path.normpath(config_path)

    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"配置文件不存在: {config_path}\n"
            f"请在 权责自动化处理/ 目录下创建 config.yaml"
        )

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # 处理占位符 {month}
    cfg = _resolve_placeholders(cfg)

    return cfg


def _resolve_placeholders(cfg: Dict) -> Dict:
    """递归替换配置中的 {month} 等占位符"""
    month = cfg.get("months", {}).get("current", datetime.now().strftime("%Y-%m"))

    def _resolve(val):
        if isinstance(val, str):
            return val.replace("{month}", month)
        elif isinstance(val, dict):
            return {k: _resolve(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [_resolve(v) for v in val]
        return val

    return _resolve(cfg)


# ═══════════════════════════════════════════════════════════════
# 配置校验
# ═══════════════════════════════════════════════════════════════

def validate_config(cfg: Dict) -> list:
    """
    校验配置完整性，返回缺失/错误列表
    返回空列表表示校验通过
    """
    errors = []

    # 必需顶层 key
    required_keys = ["months", "database", "first_loan", "reloan_forecast",
                     "accrual_app_cnt", "accrual_rates", "paths"]
    for key in required_keys:
        if key not in cfg:
            errors.append(f"缺少顶层配置项: {key}")

    # 月份配置
    months = cfg.get("months", {})
    for k in ["current", "next", "label_current", "label_next"]:
        if k not in months:
            errors.append(f"months 缺少: {k}")

    # 数据库配置
    db = cfg.get("database", {})
    for k in ["username", "password"]:
        if k not in db:
            errors.append(f"database 缺少: {k}")

    # 首贷参数
    fl = cfg.get("first_loan", {})
    for k in ["daily_spend", "cpi", "install_register_rate",
              "pass_rate", "sign_loan_rate", "avg_amount"]:
        if k not in fl:
            errors.append(f"first_loan 缺少: {k}")

    # 进件量
    app_cnt = cfg.get("accrual_app_cnt", {})
    for biz in ["首贷", "复贷-循环贷", "复贷-非循环贷"]:
        if biz not in app_cnt:
            errors.append(f"accrual_app_cnt 缺少业务: {biz}")
        else:
            for m_label in [months.get("label_current", ""), months.get("label_next", "")]:
                if m_label and m_label not in app_cnt[biz]:
                    errors.append(f"accrual_app_cnt.{biz} 缺少月份: {m_label}")

    # 文件路径
    paths = cfg.get("paths", {})
    for k in ["accrual_template", "accrual_source"]:
        if k not in paths:
            errors.append(f"paths 缺少: {k}")

    return errors


# ═══════════════════════════════════════════════════════════════
# 辅助方法
# ═══════════════════════════════════════════════════════════════

def get_rate(cfg: Dict, month_label: str, biz: str, product: str, term: int) -> dict:
    """
    从 accrual_rates 中获取指定维度的风险参数
    返回 {"K": ..., "L": ..., "M": ..., "S": ..., "V": ...}
    """
    rates = cfg.get("accrual_rates", {})
    key = f"{month_label}_{biz}_{product}_{term}"
    return rates.get(key, {})


def get_q_dist(cfg: Dict, month_label: str, biz: str, product: str, term: int) -> float:
    """
    从 accrual_q_dist 获取 Q 分布系数
    优先当月，否则回退到上月
    """
    q_dist = cfg.get("accrual_q_dist", {})
    key = f"{month_label}_{biz}_{product}_{term}"
    if key in q_dist:
        return q_dist[key]

    # 回退逻辑：尝试其他月份标签
    for fallback_key in q_dist:
        if fallback_key.endswith(f"_{biz}_{product}_{term}"):
            return q_dist[fallback_key]

    return 0.0


def get_step_enabled(cfg: Dict, step_num: int) -> bool:
    """检查某步骤是否启用"""
    enabled = cfg.get("pipeline", {}).get("enabled_steps", [1, 2, 3, 4, 5])
    return step_num in enabled

# -*- coding: utf-8 -*-
"""
墨西哥经分自动化 Pipeline - 主入口
===================================
用途: 墨西哥现金贷业务经营分析自动化

流程:
  Step 0: 数据准备 - 从Excel读取墨西哥历史数据
  Step 1: 周度指标计算 - 计算进件量/CPI/CPR/CPA/CPS/T3转化率
  Step 2: 月度预测 - 生成7月-12月预测数据
  Step 3: LTV模型 - 计算Lifetime Value
  Step 4: 模板输出 - 生成Excel权责经分模板

使用方法:
  python mexico_pipeline.py              # 运行全流程
  python mexico_pipeline.py --step 0      # 仅运行 Step 0
  python mexico_pipeline.py --steps 0 1  # 运行 Step 0 和 Step 1
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.config import load_config, get_output_dir
from core.db import connect_db, get_tables, close_db

# ===================== 日志配置 =====================
def setup_logging():
    """配置日志"""
    import sys
    # 设置控制台输出编码为UTF-8 (避免PowerShell GBK乱码)
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    
    log_format = '[%(asctime)s] %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 文件日志
    log_dir = PROJECT_ROOT / 'logs'
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f'mexico_pipeline_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    logging.getLogger().addHandler(file_handler)
    
    return logging.getLogger(__name__)

logger = setup_logging()

# ===================== 版本信息 =====================
VERSION = 'v1.0.0'
BUILD_DATE = '2026-06-30'

# ===================== Step 入口函数 =====================

def step0_data_prep(logger):
    """
    Step 0: 数据准备
    从 Excel 文件读取墨西哥历史数据，解析各 sheet 内容
    """
    logger.info("=" * 60)
    logger.info("Step 0: 数据准备 - 读取墨西哥历史Excel")
    logger.info("=" * 60)
    
    from steps.step0_data_prep import load_historical_data
    
    # PROJECT_ROOT = 墨西哥经分/, 父级 = code/, 上级 = 嘉银工作内容的整理/
    data_dir = PROJECT_ROOT.parent.parent / '01工作内容' / '权责分析' / '墨西哥'
    excel_file = data_dir / '墨西哥经营计划_26年6月及7月预估V4.xlsx'
    
    logger.info(f"数据文件: {excel_file}")
    logger.info(f"文件存在: {excel_file.exists()}")
    
    if not excel_file.exists():
        logger.error(f"数据文件不存在: {excel_file}")
        logger.info("尝试查找其他版本...")
        xlsx_files = list(data_dir.glob('*.xlsx'))
        for f in xlsx_files:
            logger.info(f"  找到: {f.name}")
        return False
    
    try:
        result = load_historical_data(str(excel_file))
        
        if result:
            # 列出所有加载的 sheet
            sheet_names = list(result.keys())
            logger.info(f"加载了 {len(result)} 个数据集:")
            for name in sheet_names:
                df_or_list = result[name]
                if hasattr(df_or_list, 'shape'):
                    logger.info(f"  - {name}: {df_or_list.shape[0]}行 x {df_or_list.shape[1]}列")
                elif isinstance(df_or_list, list):
                    logger.info(f"  - {name}: {len(df_or_list)}条记录")
                else:
                    logger.info(f"  - {name}: {type(df_or_list)}")
            logger.info("Step 0 完成")
            return result
        else:
            logger.error("Step 0 失败: result 为空")
            return False
    except Exception as e:
        import traceback
        logger.error(f"Step 0 异常: {e}")
        logger.error(traceback.format_exc())
        return False


def step1_weekly_metrics(logger, historical_data=None):
    """
    Step 1: 周度指标计算
    从历史数据中提取并计算周度经营指标
    """
    logger.info("=" * 60)
    logger.info("Step 1: 周度指标计算")
    logger.info("=" * 60)
    
    if historical_data is None:
        logger.warning("未提供历史数据，Step 1 需要先运行 Step 0")
        return False
    
    from steps.step1_weekly_metrics import calculate_weekly_metrics
    
    result = calculate_weekly_metrics(historical_data)
    
    if result:
        logger.info(f"✅ Step 1 完成 - 计算了 {len(result)} 周的数据")
    else:
        logger.error("❌ Step 1 失败")
    
    return result is not False


def step2_monthly_forecast(logger, weekly_data=None):
    """
    Step 2: 月度预测
    基于历史数据生成未来6个月的预测
    """
    logger.info("=" * 60)
    logger.info("Step 2: 月度预测")
    logger.info("=" * 60)
    
    if weekly_data is None:
        logger.warning("未提供周度数据，Step 2 需要先运行 Step 1")
        return False
    
    from steps.step2_monthly_forecast import generate_monthly_forecast
    
    result = generate_monthly_forecast(weekly_data)
    
    if result:
        logger.info(f"✅ Step 2 完成 - 生成了 {len(result)} 个月的预测")
    else:
        logger.error("❌ Step 2 失败")
    
    return result is not False


def step3_ltv_model(logger, historical_data=None):
    """
    Step 3: LTV模型
    计算Lifetime Value模型数据
    """
    logger.info("=" * 60)
    logger.info("Step 3: LTV模型计算")
    logger.info("=" * 60)
    
    if historical_data is None:
        logger.warning("未提供历史数据，Step 3 需要先运行 Step 0")
        return False
    
    from steps.step3_ltv_model import calculate_ltv_model
    
    result = calculate_ltv_model(historical_data)
    
    if result:
        logger.info(f"✅ Step 3 完成 - LTV模型计算完成")
    else:
        logger.error("❌ Step 3 失败")
    
    return result is not False


def step4_template_output(logger, all_results=None):
    """
    Step 4: 模板输出
    生成Excel权责经分模板
    """
    logger.info("=" * 60)
    logger.info("Step 4: Excel模板输出")
    logger.info("=" * 60)
    
    from steps.step4_template_output import generate_report_template
    
    output_dir = Path(get_output_dir())
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        result = generate_report_template(all_results, str(output_dir))
        if result:
            logger.info(f"Step 4 完成 - 报告已输出到: {result}")
            return result
        else:
            logger.error("Step 4 失败: generate_report_template 返回空")
            return False
    except Exception as e:
        import traceback
        logger.error(f"Step 4 异常: {e}")
        logger.error(traceback.format_exc())
        return False


def check_database(logger):
    """检查数据库连接"""
    logger.info("=" * 60)
    logger.info("检查数据库连接")
    logger.info("=" * 60)
    
    try:
        conn = connect_db()
        if conn:
            tables = get_tables()
            logger.info(f"✅ 数据库连接成功，共 {len(tables)} 个表")
            
            # 查找墨西哥相关表
            mexico_related = [t for t in tables if 'mx' in t.lower()]
            if mexico_related:
                logger.info(f"墨西哥相关表: {mexico_related}")
            else:
                logger.warning("未找到明确的墨西哥相关表(mx.*)")
            
            close_db()
            return True
        else:
            logger.error("❌ 数据库连接失败")
            return False
    except Exception as e:
        logger.error(f"❌ 数据库检查失败: {e}")
        return False


# ===================== 主函数 =====================

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description='墨西哥经分自动化 Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python mexico_pipeline.py              # 运行全流程
  python mexico_pipeline.py --step 0     # 仅运行 Step 0
  python mexico_pipeline.py --steps 0 1 2 # 运行 Step 0-2
  python mexico_pipeline.py --check       # 检查数据库连接
  python mexico_pipeline.py --version     # 显示版本信息
        """
    )
    parser.add_argument('--step', type=int, choices=[0, 1, 2, 3, 4],
                        help='运行指定的 Step')
    parser.add_argument('--steps', type=int, nargs='+', choices=[0, 1, 2, 3, 4],
                        help='运行指定的多个 Steps')
    parser.add_argument('--check', action='store_true',
                        help='检查数据库连接')
    parser.add_argument('--version', action='store_true',
                        help='显示版本信息')
    
    args = parser.parse_args()
    
    # 显示版本
    if args.version:
        print(f"墨西哥经分自动化 Pipeline {VERSION} ({BUILD_DATE})")
        return
    
    # 检查数据库
    if args.check:
        check_database(logger)
        return
    
    logger.info("=" * 60)
    logger.info(f"墨西哥经分自动化 Pipeline {VERSION}")
    logger.info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    # 确定要运行的 Steps
    if args.step is not None:
        steps_to_run = [args.step]
    elif args.steps is not None:
        steps_to_run = args.steps
    else:
        steps_to_run = [0, 1, 2, 3, 4]  # 默认运行全部
    
    logger.info(f"将运行 Steps: {steps_to_run}")
    
    # 运行结果存储
    results = {}
    
    # Step 0: 数据准备
    if 0 in steps_to_run:
        historical_data = step0_data_prep(logger)
        if historical_data:
            results['historical_data'] = historical_data
            results['weekly_data'] = historical_data.get('weekly_parsed', [])
        if not historical_data and 0 in steps_to_run and len(steps_to_run) > 1:
            logger.warning("Step 0 失败，后续 Steps 可能受影响")
    
    # Step 1: 周度指标
    if 1 in steps_to_run:
        weekly = step1_weekly_metrics(logger, results.get('historical_data'))
        if weekly:
            results['weekly_data'] = weekly
        else:
            logger.warning("Step 1 返回空数据")
            results['weekly_data'] = []
    
    # Step 2: 月度预测
    if 2 in steps_to_run:
        step2_ok = step2_monthly_forecast(logger, results.get('weekly_data'))
    
    # Step 3: LTV模型
    if 3 in steps_to_run:
        ltv = step3_ltv_model(logger, results.get('historical_data'))
        if ltv:
            results['ltv_data'] = ltv
    
    # Step 4: 模板输出
    if 4 in steps_to_run:
        output_ok = step4_template_output(logger, results)
        if output_ok:
            results['output_path'] = output_ok
    
    logger.info("=" * 60)
    logger.info(f"Pipeline 执行完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

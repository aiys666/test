# -*- coding: utf-8 -*-
import sys, re, time
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery
import pandas as pd

SQL_PATH = r'E:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\22.墨西哥逾期率效果排查.sql'

pq = PrestoQuery()
pq.login()
print("登录成功\n")

with open(SQL_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

# 提取三个 INSERT 块
insert_blocks = re.findall(
    r'(INSERT INTO mx\.tmp_effect_decomp_all_dims\b.*?;)\s*\n\s*\n(?=-- =|-- 最后|SELECT \* FROM)',
    content, re.DOTALL
)
print(f"提取到 {len(insert_blocks)} 个 INSERT 块")

# 每批的首个维度名（用于验证该批是否已落地）
batch_first_dim = ['V5.3行为子分', '687模型分', 'AMLBA21天B类数']

drop_sql = 'DROP TABLE IF EXISTS mx.tmp_effect_decomp_all_dims;'
create_m = re.search(
    r'CREATE TABLE mx\.tmp_effect_decomp_all_dims\s*\(.*?\);',
    content, re.DOTALL
)
if not create_m:
    print("未找到 CREATE TABLE，退出")
    sys.exit(1)
create_sql = create_m.group(0)


def execute(sql, tag, retries=6):
    for i in range(retries):
        try:
            t0 = time.time()
            ok, msg = pq.execute(sql, wait_sec=3)
            dt = time.time() - t0
            print(f"  {tag}: {'OK' if ok else 'FAIL'} ({msg})  耗时 {dt:.1f}s", flush=True)
            if ok:
                return True
            # SQL检查/任务失败这类确定性错误不再重试
            if '检查' in msg or '任务失败' in msg:
                return False
        except Exception as e:
            print(f"  {tag}: 第{i+1}次连接异常 -> {type(e).__name__}: {e}", flush=True)
        time.sleep(3)
        try:
            pq.login()
        except Exception as le:
            print(f"    重登失败: {le}", flush=True)
    return False


def batch_landed(dim):
    df = pq.query(f"SELECT COUNT(*) AS c FROM mx.tmp_effect_decomp_all_dims WHERE dim_name = '{dim}'")
    if isinstance(df, pd.DataFrame) and len(df) > 0:
        return int(df.iloc[0]['c']) > 0
    return False


# 执行 DROP + CREATE
print("执行 DROP ...")
if not execute(drop_sql, "DROP"):
    sys.exit(1)
print("执行 CREATE ...")
if not execute(create_sql, "CREATE"):
    sys.exit(1)

# 依次执行 INSERT
for i, blk in enumerate(insert_blocks, 1):
    dim = batch_first_dim[i-1]
    print(f"执行 INSERT 第{i}批（{dim} ...）", flush=True)
    for attempt in range(3):
        if batch_landed(dim):
            print(f"  第{i}批已存在，跳过", flush=True)
            break
        if execute(blk, f"INSERT{i}"):
            if batch_landed(dim):
                print(f"  第{i}批落地成功", flush=True)
                break
            else:
                print(f"  第{i}批执行完成但未检测到 {dim}，重试", flush=True)
        else:
            print(f"  第{i}批执行失败，重试", flush=True)
    else:
        print(f"  第{i}批重试耗尽，终止", flush=True)
        sys.exit(1)

# 查询结果表概览
print("\n查询结果表 ...")
r = pq.query("SELECT COUNT(*) AS row_cnt, COUNT(DISTINCT dim_name) AS dim_cnt, COUNT(DISTINCT week) AS week_cnt FROM mx.tmp_effect_decomp_all_dims")
print(r if isinstance(r, pd.DataFrame) else r)

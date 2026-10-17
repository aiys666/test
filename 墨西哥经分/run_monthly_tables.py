"""跑 ltv_repurchase_monthly.sql 三张月度表"""
import sys
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery

SQL_FILE = r"E:\岳松个人文件\嘉银工作内容的整理\code\墨西哥经分\ltv_repurchase_monthly.sql"

# 从 SQL 文件里提取每条独立语句（跳过注释和空行）
def parse_statements(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    stmts = []
    buf = []
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("--") or stripped == "":
            continue
        buf.append(line)
        if stripped.endswith(";"):
            stmts.append("\n".join(buf))
            buf = []
    return stmts


if __name__ == "__main__":
    print("🔗 连接墨西哥盘古...")
    pq = PrestoQuery()
    pq.login()
    print("✅ 登录成功\n")

    stmts = parse_statements(SQL_FILE)
    print(f"📋 共 {len(stmts)} 条语句\n")

    for i, sql in enumerate(stmts, 1):
        # 提取第一行做摘要
        first_line = sql.strip().split("\n")[0][:80]
        print(f"[{i}/{len(stmts)}] {first_line}...", end=" ", flush=True)

        result = pq.query(sql)

        if isinstance(result, str):
            print(f"❌ {result}")
        else:
            rows = len(result) if hasattr(result, "__len__") else "?"
            print(f"✅ 完成（返回 {rows} 行）")

    print("\n🎉 全部执行完毕！")

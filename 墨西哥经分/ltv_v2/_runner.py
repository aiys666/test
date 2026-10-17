"""LTV v2 SQL 执行器：按 ; 切分语句，逐条 execute，报告耗时。"""
import sys, os, re, time
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery

HERE = os.path.dirname(os.path.abspath(__file__))


def split_sql(text):
    """去掉 -- 注释后按 ; 切分。"""
    lines = []
    for ln in text.splitlines():
        # 保留 -- 之后的内容（Presto 中 -- 到行尾都是注释）
        lines.append(ln)
    body = "\n".join(lines)
    # 逐行剥掉行注释
    stripped = []
    for ln in body.splitlines():
        i = ln.find("--")
        stripped.append(ln[:i] if i >= 0 else ln)
    body = "\n".join(stripped)
    parts = [p.strip() for p in body.split(";")]
    return [p for p in parts if p and not p.isspace()]


def main(sql_file):
    path = sql_file if os.path.isabs(sql_file) else os.path.join(HERE, sql_file)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    stmts = split_sql(text)
    print(f"[{os.path.basename(path)}] {len(stmts)} 条语句")

    pq = PrestoQuery()
    pq.login()
    print("登录成功")

    for i, s in enumerate(stmts, 1):
        head = re.sub(r"\s+", " ", s)[:110]
        # 提取产出的表名
        m = re.search(r"create\s+table\s+([\w\.]+)", s, re.I)
        target = m.group(1) if m else "(非建表)"
        print(f"\n--- [{i}/{len(stmts)}] {target}")
        print(f"    {head}...")
        t0 = time.time()
        ok, msg = pq.execute(s, wait_sec=3, timeout=1800)
        dt = time.time() - t0
        print(f"    {'OK ' if ok else 'FAIL'} {msg}  ({dt:.1f}s)")
        if not ok:
            print("!! 中断")
            return 1
    print("\n全部完成")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))

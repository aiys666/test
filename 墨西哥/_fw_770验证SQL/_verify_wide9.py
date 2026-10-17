# -*- coding: utf-8 -*-
"""宽表v9回归: 离线批量推荐额1504 抽查 + 全量对账(C015 vs 推荐额) + 行数/在线列回归"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 4200)
pd.set_option('display.max_colwidth', 10000); pd.set_option('display.max_rows', 200)
for _ in range(6):
    try: pq = PrestoQuery(); pq.login(); break
    except Exception: time.sleep(8)
def q(sql, tag):
    print("=" * 170); print(tag, flush=True)
    for i in range(8):
        try: r = pq.query(sql)
        except Exception as ex:
            print(f"[err] {str(ex)[:200]}"); time.sleep(6)
            try: pq.login()
            except Exception: pass
            continue
        if not isinstance(r, str):
            if r is None or len(r) == 0: print("[空]"); return None
            print(r.to_string()); print(f"[rows={len(r)}]", flush=True); return r
        print(f"[retry {i+1}] {str(r)[:220]}"); time.sleep(6)
    return None

sqlp = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_fw_770验证SQL\11_在线离线临额区分逻辑.sql"
txt = open(sqlp, encoding='utf-8').read()
mk = '-- 【时间轴宽表】'
i0 = txt.index(mk); ws = txt.index('with', i0)
we = txt.index("f.tenant='yawey';", ws) + len("f.tenant='yawey';")
WIDE = txt[ws:we].strip().rstrip(';').rstrip()
print(f"[宽表段 {len(WIDE)} 字符]")

BIZ = "('1620000482922458','1620000463039322','1620000474757589','1620000476073204',\
'1620000462179690','1620000483074755','1620000480579892','1620000468511585')"

q(f"""
{WIDE}
where a.biz_id in {BIZ}
order by a.biz_id
""", "Q1 8笔: 离线发放额 vs 1504推荐额 + 在线列回归")

q(f"""
select count(*) n,
  sum(case when t."离线发放金额" is not null then 1 else 0 end) n_offline,
  sum(case when t."离线发放金额" is not null and t."离线批量推荐额_1504" is not null then 1 else 0 end) off_cov_rec,
  sum(case when t."离线发放金额" is not null and t."离线批量推荐额_1504" is not null
        and t."离线发放金额"=t."离线批量推荐额_1504" then 1 else 0 end) off_eq,
  sum(case when t."离线发放金额" is not null and t."离线批量推荐额_1504" is not null
        and abs((t."离线发放金额"-t."离线批量推荐额_1504") % 50) < 0.01 then 1 else 0 end) off_diff50,
  sum(case when t."弹窗发放tag_1386"=1 then 1 else 0 end) tag1_regress,
  sum(case when t."弹窗发放tag_1386"=1
        and round(t."理论算额_1379_取整前"/50.0)*50=t."在线临额发放金额_857" then 1 else 0 end) round50_regress,
  sum(case when abs(coalesce(t."合同金额_放款金额",0)-coalesce(t."占用主额金额",0)
        -coalesce(t."临额最终使用金额",0))<0.01 then 1 else 0 end) identity_regress
from (
{WIDE}
) t
""", "Q2 全量: 离线推荐额覆盖/同额/50倍数差 + 在线指标回归")
print("DONE-VERIFY9")

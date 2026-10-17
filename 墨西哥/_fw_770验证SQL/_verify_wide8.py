# -*- coding: utf-8 -*-
"""宽表v8回归: 决策链底数新字段 14笔抽查 + 全量断言(覆盖率/算额公式/round50/恒等式)"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd
pd.set_option('display.max_columns', None); pd.set_option('display.width', 4000)
pd.set_option('display.max_colwidth', 10000); pd.set_option('display.max_rows', 400)
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

# ---- 从权威SQL文件提取【时间轴宽表】段 ----
sqlp = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥\_fw_770验证SQL\11_在线离线临额区分逻辑.sql"
txt = open(sqlp, encoding='utf-8').read()
mk = '-- 【时间轴宽表】'
i0 = txt.index(mk)
ws = txt.index('with', i0)
we = txt.index("f.tenant='yawey';", ws) + len("f.tenant='yawey';")
WIDE = txt[ws:we].strip().rstrip(';').rstrip()
print(f"[宽表段长度 {len(WIDE)} 字符]")

BIZ = "('1620000479377160','1620000474757589','1620000483074755',\
'1620000462179690','1620000462287861','1620000463039322','1620000464027012','1620000482922458',\
'1620000463197032','1620000466574256','1620000480579892','1620000468511585','1620000482684370',\
'1620000476073204')"

# Q1 14笔抽查: 决策链底数新列
q(f"""
{WIDE}
where a.biz_id in {BIZ}
order by a.biz_id
""", "Q1 14笔宽表全字段(决策链底数)")

# Q2 全量断言
q(f"""
select count(*) n,
  sum(case when t."授信额度_credit_amount_1067" is not null then 1 else 0 end) cov_credit,
  sum(case when t."主额评级_V5_2_1500" is not null then 1 else 0 end) cov_g52,
  sum(case when t."主额评级_V5_3_1542" is not null then 1 else 0 end) cov_g53,
  sum(case when t."主额评级_V6_1_1635" is not null then 1 else 0 end) cov_g61,
  sum(case when t."用信评分_score_v1_1522" is not null then 1 else 0 end) cov_score,
  sum(case when t."用信临额类型_type_1523" is not null then 1 else 0 end) cov_type,
  sum(case when t."弹窗发放tag_1386"=1 then 1 else 0 end) n_tag1,
  sum(case when t."弹窗发放tag_1386"=1 and t."在线临额发放金额_857" is not null then 1 else 0 end) tag1_has857,
  sum(case when t."弹窗发放tag_1386"=1 and t."理论算额_1379_取整前" is not null then 1 else 0 end) tag1_has1379,
  sum(case when t."弹窗发放tag_1386"=1 and t."理论发放比例" is not null then 1 else 0 end) tag1_hasratio,
  sum(case when t."弹窗发放tag_1386"=1
            and round(t."理论算额_1379_取整前"/50.0)*50 = t."在线临额发放金额_857" then 1 else 0 end) round50_hit,
  sum(case when t."弹窗发放tag_1386"=1 and t."用信临额类型_type_1523" in (1,2,3)
            and abs(t."理论算额_1379_取整前" - t."算额底数_占用主额floor20"*t."理论发放比例")<0.01
       then 1 else 0 end) formula_hit,
  sum(case when t."弹窗发放tag_1386"=1 and t."用信临额类型_type_1523" in (1,2,3) then 1 else 0 end) formula_base,
  sum(case when t."在线临额有效期天数_1379"=3 then 1 else 0 end) exp3_hit,
  sum(case when abs(coalesce(t."合同金额_放款金额",0)
        - coalesce(t."占用主额金额",0) - coalesce(t."临额最终使用金额",0))<0.01 then 1 else 0 end) identity_hit
from (
{WIDE}
) t
""", "Q2 全量断言(覆盖率/公式/round50/恒等式)")
print("DONE-VERIFY8")

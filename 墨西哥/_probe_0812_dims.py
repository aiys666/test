# -*- coding: utf-8 -*-
"""0812 脉冲定位：按天 x 产品 / 评级 / 渠道 拆解 8/9~8/15"""
import sys, io, os, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
import pandas as pd

OUT = r"e:\岳松个人文件\嘉银工作内容的整理\code\墨西哥"
pq = PrestoQuery(); pq.login()

def q(sql, retry=4):
    for i in range(retry):
        r = pq.query(sql)
        if isinstance(r, str) and ("login" in r.lower() or "数据格式错误" in r):
            print(f"  [重登{i+1}]"); pq.login(); continue
        return r
    raise SystemExit(f"[失败] {r}")

def _num(df):
    for c in df.columns:
        if c not in ('d','dim'): df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def piv(df):
    df["1t0本金%"] = (df.t0_overdue_capit_1 / df.t0_should_capit_1 * 100).round(2)
    df["1t3本金%"] = (df.t3_overdue_capit_1 / df.t3_should_capit_1 * 100).round(2)
    p = df.pivot_table(index="dim", columns="d", values="1t0本金%", aggfunc="mean")
    return p

def dim_sql(dim_expr, dim_name):
    return f"""
select date(f.app_time) as d, {dim_expr} as dim,
  sum(f.if_app) as app_cnt,
  sum(f.contract_amount) as contract_amount,
  sum(f.t0_overdue_capit_1) as t0_overdue_capit_1,
  sum(f.t0_should_capit_1) as t0_should_capit_1,
  sum(f.t3_overdue_capit_1) as t3_overdue_capit_1,
  sum(f.t3_should_capit_1) as t3_should_capit_1
from mx.wxs_application_funnel f
LEFT JOIN (
  SELECT biz_id, android_oldcust_maincreditlevel_charge_v5_3,
    ROW_NUMBER() OVER(PARTITION BY biz_id ORDER BY update_time DESC NULLS LAST) rn
  FROM mx.yj_test_table_250225
) y ON f.biz_id = y.biz_id AND y.rn = 1
where f.is_reloan='old' and f.tenant='yawey'
  and date(f.create_time) >= date '2026-08-08'
  and date(f.create_time) <= date '2026-08-16'
group by 1, 2 order by 1, 2
"""

dims = {
 "product_name": "f.product_name",
 "app_group": "f.app_group",
 "channel_category": "f.channel_category",
 "loan_cycle": "cast(f.loan_cycle as varchar)",
 "reloan_num": "case when f.reloan_num=2 then '2贷' when f.reloan_num=3 then '3贷' when f.reloan_num<=5 then '4-5贷' when f.reloan_num<=9 then '6-9贷' else '10+贷' end",
 "评级两档": "case when try_cast(y.android_oldcust_maincreditlevel_charge_v5_3 as double) is null then '空' when try_cast(y.android_oldcust_maincreditlevel_charge_v5_3 as double)<=5 then '1-5级' when try_cast(y.android_oldcust_maincreditlevel_charge_v5_3 as double)<=12 then '6-12级' else '13级参照' end",
 "评级子段": "case when try_cast(y.android_oldcust_maincreditlevel_charge_v5_3 as double) between 6 and 9 then '6-9级' when try_cast(y.android_oldcust_maincreditlevel_charge_v5_3 as double) between 10 and 12 then '10-12级' else '其他' end",
}

results = {}
for name, expr in dims.items():
    r = q(dim_sql(expr, name))
    if isinstance(r, str):
        print(f"[FAIL] {name}: {r[:200]}"); continue
    r = _num(r)
    results[name] = r
    p = piv(r)
    print("\n" + "="*110)
    print(f"【{name}】 1t0本金% 逐日 (进件日 8/8~8/16)")
    print(p.to_string())
    # 量
    qq = r.pivot_table(index="dim", columns="d", values="app_cnt", aggfunc="sum")
    print(f"\n【{name}】 进件笔数 逐日")
    print(qq.to_string())

import pickle
with open(os.path.join(OUT, "_probe_0812_dims.pkl"), "wb") as f:
    pickle.dump(results, f)
print("\n\n保存完成: _probe_0812_dims.pkl")

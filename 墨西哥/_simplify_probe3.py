# -*- coding: utf-8 -*-
"""探针: 1) 验证各前缀产品 DB 后收/前砍 相对名义费率的含税方向(税前50% vs 税后58)
2) 哪些产品有 期2~期4 次列(多期)  3) 抽样多期产品看 t0/t3/t7 各期应还本金结构与窗口门控。"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import pandas as pd
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery

W = ("f.tenant='yawey' and f.is_reloan='old' and f.if_issue=1 "
     "and f.release_time>=date'2026-06-09' and f.release_time<date'2026-09-01'")
pq = PrestoQuery(); pq.login()

def q(sql):
    r = pq.query(sql)
    if isinstance(r, str):
        raise RuntimeError(r[:500])
    return r

PRODS = "('B_07_02_00_50','C_07_03_00_85','B_07_03_00_60','A_07_01_50_00','C_07_04_00_75','E_07_02_62_50X2','E_07_04_31_35X2_20_10','E_07_01_80_100','E_07_02_70_50X2','E_07_03_41_40X2_20')"

# 1) 每产品 应还后收/合同 vs 名义(代码末段可解读) —— 看存的是净额还是含税毛额
r1 = q(f"""
select y.product_name_new p,
 count(distinct f.biz_id) n,
 round(sum(cast(f.contract_amount as double)),0) ca,
 round(sum(cast(f.haircut_amount as double)),0) ha,
 round(sum(cast(f.should_interest as double)),0) si,
 round(sum(cast(f.should_interest as double))/sum(cast(f.contract_amount as double))*100,4) si_rate,
 round(sum(cast(f.haircut_amount as double))/sum(cast(f.contract_amount as double))*100,4) ha_rate,
 round(sum(cast(f.contract_amount as double)*cast(f.loan_cycle as double))/sum(cast(f.contract_amount as double)),2) term,
 sum(if(t0_should_capit_2>0,1,0)) J2, sum(if(t0_should_capit_3>0,1,0)) J3, sum(if(t0_should_capit_4>0,1,0)) J4
from mx.wxs_application_funnel f
join mx.yj_test_table_250225 y on f.biz_id=y.biz_id
where {W} and y.product_name_new in {PRODS}
group by 1 order by si_rate desc""")
print("\n== 各产品 raw: 后收率(si/ca) 前收率(ha/ca) 期限 有期2/3/4的笔数 ==")
print(r1.to_string(index=False))

# 2) 全产品里 有任一期>=2的贷款占比 —— 看多期产品分布(取8月)
r2 = q(f"""
with b as (
 select y.product_name_new p,
  count(distinct f.biz_id) n,
  sum(if(coalesce(t0_should_capit_2,0)>0,1,0)) j2,
  sum(if(coalesce(t0_should_capit_3,0)>0,1,0)) j3,
  sum(if(coalesce(t0_should_capit_4,0)>0,1,0)) j4
 from mx.wxs_application_funnel f
 join mx.yj_test_table_250225 y on f.biz_id=y.biz_id
 where f.release_time>=date'2026-08-01' and f.release_time<date'2026-09-01' and f.is_reloan='old' and f.if_issue=1
 group by 1)
select p,n,j2,j3,j4 from b where j2+j3+j4>0 order by j2 desc limit 20""")
print("\n== 8月有 期2/3/4 的贷款 产品分布 ==")
print(r2.to_string(index=False))

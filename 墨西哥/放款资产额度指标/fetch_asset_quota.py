# -*- coding: utf-8 -*-
"""
放款资产额度指标逐笔表（2026-09-01 起）
按用户框架：主额 / 离线临额 / 在线临额 三组额度列 + 三套逻辑可用额度
输出：逐笔 CSV + Excel（含字段字典）

注意：Presto 客户端单次结果集上限 10000 行，故按 issue_date 分片循环取数，
      单个分片一旦返回 10000 行即判定为「疑似截断」，自动拆成更小分片重跑。
"""
import os, sys, io, time
from datetime import datetime, timedelta
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r'e:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(OUT_DIR, '_out')
os.makedirs(RAW_DIR, exist_ok=True)

START = "2026-09-01"
END = "2026-10-20"   # 上界，落库到 T-1

# 分片步长（天）：先用 7 天，命中截断则依次降级到 3 天、1 天
STEPS = [7, 3, 1]
TRUNC_ROWS = 10000   # 单次结果集上限；等于该值即判为「疑似截断」
SAFE_ROWS = 9500     # 期望每片不超过该值


def _d(s):
    return datetime.strptime(s, '%Y-%m-%d').date()


def date_chunks(d1, d2, step_days):
    """把 [d1, d2] 按 step_days 天切成若干左闭右闭区间。"""
    a, b = _d(d1), _d(d2)
    out = []
    cur = a
    while cur <= b:
        end = min(cur + timedelta(days=step_days - 1), b)
        out.append((cur.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')))
        cur = end + timedelta(days=1)
    return out


def build_sql(d1, d2):
    """按分片日期区间 [d1, d2] 生成取数 SQL；各 CTE 时间窗随分片收窄，避免全表扫描/超时。"""
    D1, D2 = _d(d1), _d(d2)
    # yj_test_table_250225（复贷老客宽表，app_time 为进件/申请时刻，早于放款 0~2 天）
    yj_lo = (D1 - timedelta(days=7)).strftime('%Y-%m-%d') + ' 00:00:00'
    yj_hi = (D2 + timedelta(days=1)).strftime('%Y-%m-%d') + ' 00:00:00'
    # c010 (create_time 为 timestamp)
    c_lo = (D1 - timedelta(days=1)).strftime('%Y-%m-%d') + ' 00:00:00'
    c_hi = (D2 + timedelta(days=1)).strftime('%Y-%m-%d') + ' 23:59:59'
    # c003 主额冻结台账（external_id = biz_id）
    f_lo = (D1 - timedelta(days=2)).strftime('%Y-%m-%d') + ' 00:00:00'
    f_hi = (D2 + timedelta(days=1)).strftime('%Y-%m-%d') + ' 23:59:59'

    return f"""
with base as (
  select cast(biz_id as bigint) as biz_id,
         mid,
         issue_date,
         release_time,
         cast(product_level as varchar) as product_level,
         cast(contract_amount as double) as contract_amount,
         cast(coalesce(temp_grant_amount,0) as double)/1000.0 as temp_used,
         cast(credit_amount as double)                    as main_grant,
         cast(coalesce(change_used_grantamount,0) as double) as main_used,
         cast(daily_max_available_limit as double)        as main_daily_max
  from mx.report_application_funnel7_table
  where issue_date >= date'{d1}' and issue_date <= date'{d2}'
    and if_issue = 1 and is_reloan = 'old' and biz_id is not null
),
yj as (
  select cast(biz_id as bigint) as biz_id,
         max(cast(android_oldcust_maincreditlevel_charge_v6_1 as double)) as lvl
  from mx.yj_test_table_250225
  where app_time >= timestamp'{yj_lo}' and app_time < timestamp'{yj_hi}'
    and biz_id is not null
  group by 1
),
c010 as (
  select mid, dt, g, u from (
    select mid, date(create_time) as dt,
           cast(change_total_grantamount as double) as g,
           cast(change_used_grantamount as double)  as u,
           row_number() over(partition by mid, date(create_time) order by create_time desc) rn
    from ods_view_presto.s05_user_creditlimit_change_record
    where limit_type='TEMP' and change_event_type='C010'
      and create_time >= timestamp'{c_lo}' and create_time <= timestamp'{c_hi}'
  ) t where rn=1
),
c003 as (
  select biz_id, delta_used from (
    select b.biz_id,
           cast(c.change_used_grantamount as double)
             - cast(coalesce(c.old_used_grantamount,0) as double) as delta_used,
           row_number() over(partition by b.biz_id
                            order by abs(date_diff('second', c.create_time, b.release_time))) rn
    from base b
    join ods_view_presto.s05_user_creditlimit_change_record c
      on cast(c.external_id as varchar) = cast(b.biz_id as varchar)
     and c.limit_type = 'MAIN' and c.change_action = 'FREEZE_LIMIT'
     and c.create_time >= timestamp'{f_lo}' and c.create_time <= timestamp'{f_hi}'
  ) t where rn = 1
),
off as (
  select biz_id, g, u from (
    select f.biz_id,
           cast(o.temp_limit_issue_amount as double)     as g,
           cast(o.curr_temp_used_credit_limit as double) as u,
           row_number() over(partition by f.biz_id order by o.data_date desc) rn
    from base f
    join mx.yuhan_temp_limit_base_table_his_20260924 o
      on o.mid = f.mid
     and o.data_date <= date_format(f.issue_date,'%Y%m%d')
     and o.data_date >= date_format(date_add('day',-5,f.issue_date),'%Y%m%d')
  ) t where rn=1
)
select b.biz_id, b.mid, b.issue_date, b.product_level, b.release_time,
       y.lvl as v6_1_credit_level,
       b.main_grant, b.main_used, b.main_daily_max, b.contract_amount, b.temp_used,
       k.delta_used as c003_main_used_this,
       c.g as online_g, c.u as online_u,
       o.g as offline_g, o.u as offline_u,
       case when b.issue_date >= date'2026-10-19' and b.product_level='D_1_03' then 15000 else 10000 end as product_limit_max
from base b
left join yj      y  on y.biz_id = b.biz_id
left join c003    k  on k.biz_id = b.biz_id
left join c010    c  on c.mid = b.mid and c.dt = b.issue_date
left join off     o  on o.biz_id = b.biz_id
"""


def fetch_shard(q, d1, d2, step_idx=0):
    """取 [d1, d2] 分片，返回 DataFrame 列表；命中 10000 行（疑似截断）则自动拆小重跑。"""
    sql = build_sql(d1, d2)
    df = None
    for attempt in range(2):
        try:
            r = q.query(sql)
        except Exception as e:
            r = f'异常: {e}'
        if hasattr(r, 'to_string'):
            df = r
            break
        print(f'    [失败] {d1}~{d2} 第{attempt+1}次查询未成功: {str(r)[:200]}')
        time.sleep(2)

    nxt_idx = min(step_idx + 1, len(STEPS) - 1)

    if df is None:
        # 查询失败：能拆则拆小重试，否则报错
        if d1 < d2:
            nxt = STEPS[nxt_idx]
            print(f'    [拆分] {d1}~{d2} 查询失败，按 {nxt} 天拆分重试')
            out = []
            for (a, b) in date_chunks(d1, d2, nxt):
                out += fetch_shard(q, a, b, nxt_idx)
            return out
        raise RuntimeError(f'分片 {d1} 查询失败')

    n = len(df)

    # 行数正好等于 10000 -> 疑似截断，必须拆
    if n == TRUNC_ROWS and step_idx < len(STEPS) - 1 and d1 < d2:
        nxt = STEPS[nxt_idx]
        print(f'    [截断] {d1}~{d2} 返回 {n} 行 (=10000)，按 {nxt} 天拆分重跑')
        out = []
        for (a, b) in date_chunks(d1, d2, nxt):
            out += fetch_shard(q, a, b, nxt_idx)
        return out

    if n == TRUNC_ROWS:
        print(f'    [警告] {d1}~{d2} 返回 {n} 行，已达最小粒度仍疑似截断，请人工检查')
    elif n > SAFE_ROWS:
        print(f'    [注意] {d1}~{d2} 返回 {n} 行 (> {SAFE_ROWS})，未达截断上限但偏大')
    else:
        print(f'    -> {n} 行')
    return [df]


def main():
    q = PrestoQuery(); q.login()
    t0 = time.time()

    plan = date_chunks(START, END, STEPS[0])
    print(f'分片计划: {len(plan)} 个 {STEPS[0]} 天分片，{START} ~ {END}')
    frames = []
    for i, (a, b) in enumerate(plan, 1):
        print(f'[{i}/{len(plan)}] {a} ~ {b}')
        try:
            frames += fetch_shard(q, a, b, 0)
        except Exception as e:
            print(f'    [致命] 分片 {a}~{b} 取数失败: {e}')
            raise
        time.sleep(1)

    if not frames:
        print('未取到任何数据，终止'); return
    df = pd.concat(frames, ignore_index=True)

    raw_n = len(df)
    df = df.drop_duplicates(subset=['biz_id']).reset_index(drop=True)
    print(f'\n合并: {raw_n} 行 -> 去重(subset=biz_id)后 {len(df)} 行, 用时 {time.time()-t0:.1f}s')

    raw = os.path.join(RAW_DIR, 'query_result_raw.csv')
    df.to_csv(raw, index=False, encoding='utf-8-sig')
    print('原始结果 ->', raw)

    # ---------- 派生列 ----------
    d = df.copy()
    # 注意：客户端把缺失数值返回为空串 ''，直接 notna() 会误判为「有值」，
    # 故所有数值列（含评级）统一 to_numeric(coerce)，空串 -> NaN，保证验证口径真实。
    for c in ['v6_1_credit_level',
              'main_grant','main_used','main_daily_max','contract_amount','temp_used',
              'c003_main_used_this',
              'online_g','online_u','offline_g','offline_u','product_limit_max']:
        d[c] = pd.to_numeric(d[c], errors='coerce')

    # 本笔占用主额：优先用 C003(MAIN FREEZE) 台账增量（external_id=biz_id），
    # 台账缺失时用恒等式回退（合同金额 - 本笔临额使用额）。
    # 含前砍费的 A 类产品合同额 > 真实主额占用，故必须以台账为准。
    d['main_used_this']       = d['c003_main_used_this'].fillna(
        d['contract_amount'] - d['temp_used'].fillna(0))
    d['main_available_amount']= d['main_grant'] - d['main_used']

    # 临额归属：本笔存在 C010（同日在线临额）-> 在线；否则 -> 离线
    d['is_online'] = d['online_g'].notna()

    d['offline_grant_amount']    = d['offline_g'].fillna(0)
    d['offline_used_amount']     = d['offline_u'].fillna(0)
    d['offline_available_amount']= d['offline_grant_amount'] - d['offline_used_amount']
    d['offline_used_this']       = d['temp_used'].fillna(0).where(~d['is_online'], 0)

    d['online_grant_amount']     = d['online_g'].fillna(0)
    d['online_used_amount']      = d['online_u'].fillna(0)
    d['online_available_amount'] = d['online_grant_amount'] - d['online_used_amount']
    d['online_used_this']        = d['temp_used'].fillna(0).where(d['is_online'], 0)

    base_avail = (d[['main_available_amount','main_daily_max']].min(axis=1, skipna=True)
                  + d['offline_available_amount'])
    uncapped   = d['main_available_amount'] + d['offline_available_amount']
    d['avail_tochange_logic'] = base_avail
    d['avail_current_logic']  = base_avail.combine(d['product_limit_max'], min)
    d['avail_future_logic']   = uncapped

    cols = ['biz_id','mid','issue_date','product_level',
            'v6_1_credit_level',
            'main_grant','main_used','main_available_amount','main_daily_max','main_used_this',
            'offline_grant_amount','offline_used_amount','offline_available_amount','offline_used_this',
            'product_limit_max','online_grant_amount','online_used_amount','online_available_amount','online_used_this',
            'avail_current_logic','avail_tochange_logic','avail_future_logic']
    out = d[cols].copy()
    out.columns = ['biz_id','mid','issue_date','product_level',
                   'v6_1_credit_level',
                   'main_grant_amount','main_used_amount','main_available_amount','main_daily_max','main_used_this',
                   'offline_grant_amount','offline_used_amount','offline_available_amount','offline_used_this',
                   'product_limit_max','online_grant_amount','online_used_amount','online_available_amount','online_used_this',
                   'avail_current_logic','avail_tochange_logic','avail_future_logic']

    csv_path = os.path.join(OUT_DIR, f'放款资产额度指标_逐笔_20260901起.csv')
    out.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print('明细 CSV ->', csv_path)

    # ---------- 验证 ----------
    print('\n===== 验证 =====')
    print('总笔数:', len(out))
    print('列数:', out.shape[1])
    print('复贷老客(is_reloan=old)笔数:', len(out))
    print('V6_1评级覆盖率: %.2f%%' % (out['v6_1_credit_level'].notna().mean()*100))
    hit_c003 = d['c003_main_used_this'].notna().mean()*100
    print('本笔主额支用来源: C003台账 %.2f%% / 恒等式回退 %.2f%%' % (hit_c003, 100-hit_c003))

    cap = out[['main_available_amount','main_daily_max']].min(axis=1, skipna=True)
    valid = cap.notna()
    # decimal/double 混算会产生 1e-16 量级噪声，故用 1e-6 容差判定越界
    over = (out['main_used_this'] > cap + 1e-6) & valid
    print('主额 越界率(支用 > min(可用,单日上限)+1e-6): %.4f%%' % (over.sum() / max(valid.sum(),1) * 100))
    print('主额 精确命中率(支用 == min(可用,单日上限)): %.2f%%  (参考值，未满额支用天然不等)'
          % ((out['main_used_this'] - cap).abs().le(1e-6)[valid].mean() * 100))
    if over.sum() > 0:
        print('越界样本(前10行):')
        print(out.loc[over, ['biz_id','mid','issue_date','product_level','main_grant_amount','main_used_amount',
                             'main_available_amount','main_daily_max','main_used_this']].head(10).to_string())

    trio = out[['avail_current_logic','avail_tochange_logic','avail_future_logic']]
    trio_valid = trio.notna().all(axis=1)
    mono = ((out.loc[trio_valid,'avail_current_logic'] <= out.loc[trio_valid,'avail_tochange_logic']+1e-6) &
            (out.loc[trio_valid,'avail_tochange_logic'] <= out.loc[trio_valid,'avail_future_logic']+1e-6)).mean()
    print('三套逻辑单调性命中率(仅取三列均非空): %.2f%%  有效行 %d / 总行 %d'
          % (mono*100, int(trio_valid.sum()), len(out)))
    if not trio_valid.all():
        print('  三列含空值的行数(多因主额授予额度缺失):', int((~trio_valid).sum()))
    print('在线临额笔数(本笔有C010):', int((out['online_used_this'] > 0).sum()))
    print('离线临额笔数:', int((out['offline_used_this'] > 0).sum()))
    print('产品上限=15000笔数:', int((out['product_limit_max'] == 15000).sum()))

    # ---------- Excel ----------
    try:
        dict_rows = [
            ('biz_id','业务号','funnel7.biz_id（一笔放款一行）'),
            ('mid','用户号','funnel7.mid'),
            ('issue_date','放款日期','funnel7.issue_date'),
            ('product_level','产品','funnel7.product_level'),
            ('v6_1_credit_level','V6_1评级','mx.yj_test_table_250225.android_oldCust_mainCreditLevel_charge_V6_1（按 biz_id 关联）'),
            ('main_grant_amount','主额-授予额度','funnel7.credit_amount（放款时授信额度）'),
            ('main_used_amount','主额-历史已占用','funnel7.change_used_grantamount（放款前存量占用）'),
            ('main_available_amount','主额-当前可用额度','main_grant_amount - main_used_amount'),
            ('main_daily_max','主额-单日可借上限','funnel7.daily_max_available_limit'),
            ('main_used_this','主额-当前支用额度','C003(MAIN FREEZE)台账增量 external_id=biz_id；缺失时回退 contract_amount - temp_grant_amount/1000'),
            ('offline_grant_amount','离线临额-授予额度','离线临额底表最近一批(5天有效)temp_limit_issue_amount'),
            ('offline_used_amount','离线临额-历史已占用','离线临额底表 curr_temp_used_credit_limit'),
            ('offline_available_amount','离线临额-当前可用额度','授予-已占用'),
            ('offline_used_this','离线临额-当前支用额度','本笔临额使用且来源为离线'),
            ('product_limit_max','产品上限','产品级单笔上限（常态1万；D_1_03默认产品 2026-10-19 起测试1.5万）'),
            ('online_grant_amount','在线临额-授予额度','本笔 C010(TEMP) change_total_grantamount'),
            ('online_used_amount','在线临额-历史已占用','本笔 C010 change_used_grantamount'),
            ('online_available_amount','在线临额-当前可用额度','授予-已占用'),
            ('online_used_this','在线临额-当前支用额度','本笔临额使用且来源为在线'),
            ('avail_current_logic','当前逻辑（含产品上限1万）可用额度','min(min(主额可用,单日上限)+离线临额可用, 产品上限)'),
            ('avail_tochange_logic','要改的逻辑（去除产品上限1万）可用额度','min(主额可用,单日上限)+离线临额可用'),
            ('avail_future_logic','未来的逻辑（去产品上限+去单日上限）可用额度','主额可用+离线临额可用'),
        ]
        dd = pd.DataFrame(dict_rows, columns=['字段','中文名','口径'])
        xlsx = os.path.join(OUT_DIR, f'放款资产额度指标_逐笔_20260901起.xlsx')
        with pd.ExcelWriter(xlsx, engine='openpyxl') as w:
            out.to_excel(w, sheet_name='逐笔明细', index=False)
            dd.to_excel(w, sheet_name='字段字典', index=False)
        print('Excel ->', xlsx)
    except Exception as e:
        print('Excel 生成失败:', e)


if __name__ == '__main__':
    main()

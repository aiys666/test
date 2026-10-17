import sys
sys.path.insert(0, r'E:\岳松个人文件\嘉银工作内容的整理\code')
from mexico_presto import PrestoQuery

pq = PrestoQuery()
pq.login()

# 1) 维度数与总行数
r = pq.query("""
SELECT COUNT(DISTINCT dim_name) AS n_dims, COUNT(*) AS n_rows
FROM mx.tmp_effect_decomp_all_dims
""")
print('=== 维度数/总行数 ===')
print(r.to_string())

# 2) 新增维度是否出现
r2 = pq.query("""
SELECT dim_name, COUNT(*) AS n
FROM mx.tmp_effect_decomp_all_dims
WHERE dim_name IN (
  '30天多头V6','730天多头V6','上次还款间隔天数V6','问卷3-V6','问卷6-V6',
  '全局逾期天数V6','近30天逾期天数V6','最近结清距今天数V6','邮箱数量V6',
  '近30天卸载次数V6','还款计划停留时长V6','年龄V6','学历V6',
  'B320长窗细分15档','1.8倍cap测试分组','发临额测试分组','策略发临额测试',
  '临额金额策略分组','临额间隔策略分组','紧急联系人逾期标识',
  '0819离线发临额在贷','0826离线发临额在贷','0902离线发临额在贷','0909离线发临额在贷',
  '0819发临额标签','0820发临额标签','0826发临额标签','0827发临额标签',
  '0902发临额标签','0903发临额标签','0909发临额标签','0910发临额标签',
  '产品/最大额度变更标签','结清次数分档','结清次数指数分档','其他包放款标签',
  '其他包在逾标签','其他包在逾区间','上笔产品来源','转产标记','24H复贷','产品名称','全局额度'
)
GROUP BY dim_name
ORDER BY dim_name
""")
print('=== 新增维度统计 ===')
print(r2.to_string())

# 3) 全市场总量锚定（8/3 与 8/10 出账笔数，用某稳定维度求和核对）
r3 = pq.query("""
SELECT week, SUM(billed_cnt) AS billed_cnt, SUM(overdue_cnt) AS overdue_cnt
FROM mx.tmp_effect_decomp_all_dims
WHERE dim_name = '是否复贷'
GROUP BY week
ORDER BY week
""")
print('=== 是否复贷维度锚定总量 ===')
print(r3.to_string())

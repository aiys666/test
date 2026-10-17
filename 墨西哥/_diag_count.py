# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"E:\岳松个人文件\嘉银工作内容的整理\code")
from mexico_presto import PrestoQuery
pq = PrestoQuery(); pq.login()

sqls = {
"8/03片总行数(if_app=1)": "select count(*) c from mx.wxs_application_funnel where is_reloan='old' and tenant='yawey' and if_app=1 and date(create_time)>=date '2026-08-03' and date(create_time)<date '2026-08-10'",
"8/03片总行数(不过滤if_app)": "select count(*) c from mx.wxs_application_funnel where is_reloan='old' and tenant='yawey' and date(create_time)>=date '2026-08-03' and date(create_time)<date '2026-08-10'",
"全期总行数(if_app=1)": "select count(*) c from mx.wxs_application_funnel where is_reloan='old' and tenant='yawey' and if_app=1 and date(create_time)>=date '2026-06-29'",
}
for k, s in sqls.items():
    r = pq.query(s)
    print(k, "=>", r.to_string(index=False) if not isinstance(r, str) else r)

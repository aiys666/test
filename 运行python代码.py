# -*- coding: utf-8 -*-
import openpyxl, os, csv, sys, io

SRC = r"E:/岳松个人文件/嘉银工作内容的整理/01工作内容/权责分析/202605月预估/风险产品坏账.xlsx"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

wb = openpyxl.load_workbook(SRC, data_only=True)
ws = wb["Sheet1"]

COLUMN_RANGES = [
    (2,7,"常规产品（等本等息+老免息）","NEW","15D"),
    (8,11,"常规产品（等本等息+老免息）","NEW","30D"),
    (12,14,"花式-新免息","NEW","F"),
    (15,19,"本金前置","NEW","M"),
    (20,22,"无忧贷","NEW","NR"),
    (23,26,"优享贷","NEW","NF"),
    (27,29,"放心贷","NEW","NW"),
    (30,35,"常规产品（等本等息+老免息）","OLD","15D"),
    (36,39,"常规产品（等本等息+老免息）","OLD","30D"),
    (40,45,"花式-新免息","OLD","F"),
    (46,50,"本金前置","OLD","M"),
    (51,54,"无忧贷","OLD","NR"),
    (55,59,"优享贷","OLD","NF"),
    (60,62,"放心贷","OLD","NW"),
]

PRODUCT_TAG = {
    "常规产品（等本等息+老免息）": "R",
    "花式-新免息": "F",
    "本金前置":    "M",
    "无忧贷":      "NR",
    "优享贷":      "NF",
    "放心贷":      "NW",
}

records = []
HEJI_CYCLE = 9999

for data_row in range(4, ws.max_row + 1):
    month_raw = ws.cell(data_row, 1).value
    if not month_raw:
        continue
    month_str = str(month_raw).strip()[:10]

    for col_s, col_e, product_cn, grant, period in COLUMN_RANGES:
        pt = PRODUCT_TAG[product_cn]
        tenure_list = []
        for c in range(col_s, col_e + 1):
            v3 = ws.cell(3, c).value
            if v3 is None:
                continue
            val3 = str(v3).strip()
            if val3 == "":
                continue
            if val3 in ("合计","总计","合计_1","合计_2"):
                tenure_list.append((c, HEJI_CYCLE))
            else:
                num = "".join(ch for ch in val3 if ch.isdigit())
                if num:
                    tenure_list.append((c, int(num)))

        for t_col, t_days in tenure_list:
            cell_val = ws.cell(data_row, t_col).value
            if cell_val is None:
                bdr = "NULL"
            elif isinstance(cell_val, (int, float)):
                bdr = str(round(float(cell_val), 10))
            else:
                cs = str(cell_val).strip()
                if cs in ("/","") or cs == "-":
                    bdr = "NULL"
                else:
                    try:
                        bdr = str(round(float(cs), 10))
                    except:
                        bdr = "NULL"

            records.append({
                "grant_month":    month_str,
                "product_tag":    pt,
                "period_tag":     period,
                "grant_strategy": grant,
                "loan_cycle":    t_days,
                "bad_debt_rate": bdr,
            })

# NO deduplication - keep ALL records exactly as extracted
# (user wants all data, no removal)
total = len(records)
null_count = sum(1 for r in records if r["bad_debt_rate"] == "NULL")
zero_count = sum(1 for r in records if r["bad_debt_rate"] in ("0","0.0"))
num_count = total - null_count - zero_count
print(f"Total records (no dedup): {total}")
print(f"  NULL: {null_count}, =0: {zero_count}, non-zero: {num_count}")

# Distribution check
dist = {}
for r in records:
    k = (r["product_tag"], r["period_tag"], r["grant_strategy"])
    dist[k] = dist.get(k, 0) + 1
for k, cnt in sorted(dist.items()):
    print(f"  {k}: {cnt}")

# =0 rows
zero_rows = [r for r in records if r["bad_debt_rate"] in ("0","0.0")]
print(f"\n=0 rows ({len(zero_rows)}):")
for r in zero_rows:
    print(f"  {r}")

# Write CSV
csv_path = os.path.join(OUT_DIR, "risk_bad_debt_v3.csv")
with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=["grant_month","product_tag","period_tag","grant_strategy","loan_cycle","bad_debt_rate"])
    writer.writeheader()
    writer.writerows(records)
print(f"CSV: {csv_path}")

# Write SQL
sql_path = os.path.join(OUT_DIR, "risk_bad_debt_insert_v3.sql")
with open(sql_path, "w", encoding="utf-8") as f:
    f.write("-- ind.ba_bad_debt_rate_lookup\n")
    f.write("-- grant_month | product_tag | period_tag | grant_strategy | loan_cycle | bad_debt_rate\n")
    f.write("-- product_tag: R/F/M/NR/NF/NW\n")
    f.write("-- period_tag: 15D/30D/F/M/NR/NF/NW\n")
    f.write("-- grant_strategy: NEW/OLD\n")
    f.write("-- bad_debt_rate: NULL=no data, 0~1=actual\n\n")
    f.write("DELETE from ind.ba_bad_debt_rate_lookup;\n\n")
    f.write("INSERT INTO ind.ba_bad_debt_rate_lookup\n  (grant_month, product_tag, period_tag, grant_strategy, loan_cycle, bad_debt_rate)\nVALUES\n")
    rows_sql = []
    for rec in records:
        lc = rec["loan_cycle"]
        bdr = rec["bad_debt_rate"]
        rows_sql.append(
            f"  ('{rec['grant_month']}','{rec['product_tag']}','{rec['period_tag']}',"
            f"'{rec['grant_strategy']}',{lc},{bdr})"
        )
    f.write(",\n".join(rows_sql))
    f.write(";\n")
print(f"SQL: {sql_path}")

# Write mapping
mapping_path = os.path.join(OUT_DIR, "risk_bad_debt_mapping.csv")
with open(mapping_path, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["field","value_en","value_cn","note"])
    for row in [
        ("product_tag","R","常规产品（等本等息+老免息）","Regular"),
        ("product_tag","F","花式-新免息","Fee-based new"),
        ("product_tag","M","本金前置","Money first"),
        ("product_tag","NR","无忧贷","No risk"),
        ("product_tag","NF","优享贷","New feature"),
        ("product_tag","NW","放心贷","No worry"),
        ("period_tag","15D","15天账期","15-day"),
        ("period_tag","30D","30天账期","30-day"),
        ("period_tag","F","花式账期","Fee-based"),
        ("period_tag","M","本金前置账期","Money first"),
        ("period_tag","NR","无忧贷账期","No risk"),
        ("period_tag","NF","优享贷账期","New feature"),
        ("period_tag","NW","放心贷账期","No worry"),
        ("grant_strategy","NEW","首贷/新客","First-time"),
        ("grant_strategy","OLD","复贷/老客","Repeat"),
        ("loan_cycle","30","30天","30-day"),
        ("loan_cycle","60","60天","60-day"),
        ("loan_cycle","90","90天","90-day"),
        ("loan_cycle","120","120天","120-day"),
        ("loan_cycle","150","150天","150-day"),
        ("loan_cycle","180","180天","180-day"),
        ("loan_cycle","210","210天","210-day"),
        ("loan_cycle","9999","合计列","Heji/total columns — all map to 9999"),
    ]:
        w.writerow(row)
print(f"Mapping: {mapping_path}")
print("=== DONE ===")

#!/usr/bin/env python3
"""全类型收入流水的一次完整拉取(只读密钥), 给 cash_identity_usd.py 用。
为什么【全类型】而不是按类型: 恒等式要把每一笔改变钱包的流水都算进去; 按类型拉就得先假设账户只有哪些类型 ——
那正是会静默漏项的地方。全类型拉一次, 在本地分类, 未知类型会以名字出现在产物里。
节流: fetch_income_paged 自带 0.35 s 间隔; income 端点权重 30, 1 分钟上限 2400 ⇒ 这里每次再多等 0.5 s(≈70 次/分 ≈ 2100 权重/分)。
usage: pull_income_all.py <startUTC YYYY-MM-DD> <out.json>"""
import calendar, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import fetch_income_paged as FI

_orig = FI.get


def _slow(params):
    time.sleep(0.5)
    return _orig(params)


FI.get = _slow
s = calendar.timegm(time.strptime(sys.argv[1], "%Y-%m-%d")) * 1000; e = int(time.time() * 1000); out = sys.argv[2]
pages, rows, st, why, nsub = FI.run(s, e, "all")
doc = {"endpoint": "/fapi/v1/income", "incomeType": "ALL", "device": "pull_income_all.py -> fetch_income_paged.run (v2 + income_type)",
       "startTime": s, "endTime": e, "fetched_utc": time.strftime("%FT%TZ", time.gmtime()), "completeness": st, "incomplete_reason": why,
       "n_boundary_rows_subtracted": nsub, "n_pages": len(pages), "n_rows": len(rows),
       "max_weight_seen": max((int(p.get("weight") or 0) for p in pages), default=None), "pages": pages, "body": rows}
with open(out + ".part", "w") as fh: json.dump(doc, fh)
os.replace(out + ".part", out)
types = {}
for r in rows: types[r["incomeType"]] = types.get(r["incomeType"], 0) + 1
print(st, why, "rows", len(rows), "pages", len(pages), "max weight", doc["max_weight_seen"], types)
sys.exit(0 if st == "COMPLETE" else 3)

#!/usr/bin/env python3
"""T3c 首锚验收器(PREREG_deploy_modulation §3)— 只读。用法: t3c_first_anchor_check.py <anchor_ts>"""
import json, os, sys, time, numpy as np
A=int(sys.argv[1]); WS=os.path.expanduser("~/wide_shadow"); ok_all=True
def chk(n,c,d=""):
    global ok_all; ok_all&=bool(c); print(f"  {'PASS' if c else 'FAIL'} {n} {d}")
d=json.load(open(f"{WS}/state/target_combo/{A}.json")); m=d.get("modulation")
print(f"T3c 首锚验收 anchor {A} ({time.strftime('%m-%dT%H:%MZ',time.gmtime(A))})")
chk("modulation 字段存在", m is not None, m)
if m:
    chk("factor 范围 ⊂ [0.75, 1.25]", 0.75-1e-9<=m["factor_min"] and m["factor_max"]<=1.25+1e-9, f"{m['factor_min']}..{m['factor_max']} 均 {m['factor_mean']}")
    chk("n_finite ≥ 380/400", m["n_finite"]>=380, f"{m['n_finite']}/{m['n_members']}")
w=json.load(open(f"{WS}/state/target_live/{A}.json"))["weights"]; wp=json.load(open(f"{WS}/state/target_live/{A-14400}.json"))["weights"]; names=set(w)|set(wp); g=sum(abs(v) for v in w.values())
dw=sum(abs(w.get(n,0)-wp.get(n,0)) for n in names)/g; chk("Σ|Δw|/gross vs 上锚 ≤ 30%", dw<=0.30, f"{dw:.3f}")
chk("FTRIM 记录仍在", "ftrim" in d and d["ftrim"]["n_kc"]>=0, d.get("ftrim",{}).get("n_kc"))
print("RESULT:", "PASS" if ok_all else "FAIL(见上)")

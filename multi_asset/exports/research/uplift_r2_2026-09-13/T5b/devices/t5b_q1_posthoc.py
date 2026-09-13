#!/usr/bin/env python3
"""t5b_q1_posthoc.py — POST-HOC descriptive split of the Q1 frozen-residual carry (not in SPEC_T5b; written after the Q1 readings were seen).
Reads receipts/T5b_q1_instances.json (sha asserted against RECEIPT_T5b_q1.json). Splits C_tl^FROZ and C_tl^RES by residual sign, lists per-name
contributions (sum over included anchors / n anchors) and the anchors with the largest |C_tl^FROZ|. Bootstrap k = 701.. (post-hoc labels). Changes no reading.
Launch: env -i PATH=/usr/bin:/bin HOME=$HOME /usr/bin/python3 devices/t5b_q1_posthoc.py <T5b dir> CPATH,HOME,LC_CTYPE,LIBRARY_PATH,MANPATH,PATH,SDKROOT,__CF_USER_TEXT_ENCODING
"""
import os, sys, json, collections
T5B = os.path.abspath(sys.argv[1]); WHITE = set(x for x in sys.argv[2].split(",") if x)
assert WHITE and sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
sys.path.insert(0, T5B + "/devices")
import numpy as np
import t5b_common as TC
Q1 = json.load(open(T5B + "/receipts/RECEIPT_T5b_q1.json")); IP = T5B + "/receipts/T5b_q1_instances.json"; assert TC.sha(IP) == Q1["instances_sha256"]
inst = json.load(open(IP)); rows = {r["A"]: r for r in Q1["rows"]}
incA = sorted(A for A, r in rows.items() if r.get("included", {}).get("tl"))
n = len(incA); days = np.array([A // 86400 for A in incA])
split = {k: np.zeros(n) for k in ("FROZ_short", "FROZ_long", "RES_short", "RES_long")}
per_name = collections.defaultdict(lambda: dict(froz=0.0, res=0.0, n_froz=0, n_res=0, signs=set()))
pos = {A: q for q, A in enumerate(incA)}
for e in inst:
    A = e["A"]
    if A not in pos or not e["included_tl"]: continue
    w = e["w_tl"]; g = rows[A]["tl"]["gross"]
    if abs(w) <= 1e-6: continue
    c = w * e["c4"] / g * 1e4; side = "short" if w < 0 else "long"
    split["RES_" + side][pos[A]] += c; per_name[e["symbol"]]["res"] += c; per_name[e["symbol"]]["n_res"] += 1; per_name[e["symbol"]]["signs"].add(side)
    if e["frozen_tl"]:
        split["FROZ_" + side][pos[A]] += c; per_name[e["symbol"]]["froz"] += c; per_name[e["symbol"]]["n_froz"] += 1
chk = max(abs(split["FROZ_short"][pos[A]] + split["FROZ_long"][pos[A]] - rows[A]["tl"]["C_FROZ"]) for A in incA)
chk2 = max(abs(split["RES_short"][pos[A]] + split["RES_long"][pos[A]] - rows[A]["tl"]["C_RES"]) for A in incA)
assert chk <= 1e-12 and chk2 <= 1e-12, (chk, chk2)
out = dict(label="POST-HOC descriptive; does not alter SPEC readings", n_anchors=n, closure_maxabs=[chk, chk2])
for q, (k, v) in enumerate(split.items()):
    ci = TC.boot_ratio(v, np.ones(n), days, 701 + q); out[k] = dict(mean=float(v.mean()), ci95=[ci[1], ci[2]], cumulative=float(v.sum()), k=701 + q)
names = sorted(per_name.items(), key=lambda kv: -abs(kv[1]["froz"]))
out["per_name_froz_top"] = [dict(symbol=s, froz_mean_contrib=v["froz"] / n, res_mean_contrib=v["res"] / n, n_froz=v["n_froz"], n_res=v["n_res"], sides=sorted(v["signs"])) for s, v in names[:20]]
tlF = [(A, rows[A]["tl"]["C_FROZ"]) for A in incA]
out["top_anchors_abs_C_FROZ"] = [dict(utc=TC.utc(A), C_FROZ=c, names=[dict(symbol=e["symbol"], w_tl=e["w_tl"], c4_bps=e["c4"] * 1e4, age_tl=e["age_tl"]) for e in inst if e["A"] == A and e["frozen_tl"]]) for A, c in sorted(tlF, key=lambda x: -abs(x[1]))[:6]]
excl_top = [A for A, _ in sorted(tlF, key=lambda x: -abs(x[1]))[:3]]
rest = np.array([c for A, c in tlF if A not in excl_top]); out["mean_C_FROZ_without_top3_abs_anchors"] = float(rest.mean())
out["G_RN8_non_match"] = Q1["gates"]["G_RN8"]["non_match_examples"]
out["self_sha256"] = TC.sha(os.path.abspath(__file__))
json.dump(out, open(T5B + "/receipts/RECEIPT_T5b_q1_posthoc.json", "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k not in ("per_name_froz_top", "top_anchors_abs_C_FROZ")}, indent=0)[:2500])
print("PER_NAME", json.dumps(out["per_name_froz_top"][:12]))
print("TOP_ANCHORS", json.dumps(out["top_anchors_abs_C_FROZ"])[:3000])
print("DONE_t5b_q1_posthoc")

#!/usr/bin/env python3
"""t8_postfreeze_calendar.py <T8 dir> <env whitelist> — POST-FREEZE DESCRIPTIVE (lead request 2026-09-13, after RESULT db99f6b9; NOT a gate,
cannot change the T8 verdict): calendar-only sign reading = per cell, the out-of-sample fold Pearson r in the four calendar test years
2023/2024/2025/2026 (folds F2..F5 of RECEIPT_T8_fit.json), count positive / negative, and whether >= 3 of 4 share one sign; also the already
stored pooled r on 2023-26 rows (r_2326). No statistic is recomputed from data; inputs are read with a guarded read (refuses APFS dataless /
short reads) and checked against SHA256SUMS.txt. Writes receipts/POSTFREEZE_calendar_T8.json and .md."""
import os, sys, json, stat, hashlib, time
WHITE = set(x for x in sys.argv[2].split(",") if x) if len(sys.argv) > 2 else None
assert WHITE, "launch with an env whitelist as argv[2]"
extra = sorted(k for k in os.environ if k not in WHITE); assert extra == [], ("ENV WHITELIST VIOLATION", extra)
T8 = os.path.abspath(sys.argv[1]); SF_DATALESS = getattr(stat, "SF_DATALESS", 0x40000000)
def guarded_bytes(p):
    st = os.stat(p)
    assert not (st.st_flags & SF_DATALESS), ("REFUSE dataless", p)
    with open(p, "rb") as f:
        b = f.read()
    assert len(b) == st.st_size and st.st_size > 0, ("REFUSE short/empty read", p, len(b), st.st_size)
    return b
sums = {}
for line in guarded_bytes(T8 + "/SHA256SUMS.txt").decode().splitlines():
    if line.strip() and not line.startswith("#") and "  ./" in line:
        d, p = line.split("  ", 1); sums[p] = d
def load(rel):
    b = guarded_bytes(T8 + "/" + rel); h = hashlib.sha256(b).hexdigest()
    assert sums.get("./" + rel) == h, ("sha differs from SHA256SUMS.txt", rel, h)
    return json.loads(b), h
F, hF = load("receipts/pod2/RECEIPT_T8_fit.json"); J, hJ = load("receipts/pod2/RECEIPT_T8_judge.json")
SELF = hashlib.sha256(guarded_bytes(os.path.abspath(__file__))).hexdigest()
CAL = ("F2", "F3", "F4", "F5"); YEARS = {"F2": 2023, "F3": 2024, "F4": 2025, "F5": 2026}
cells = {}
for key, o in F["cells"].items():
    fr = {f["fold"]: f["r"] for f in o["folds"]}
    rs = [fr[k] for k in CAL]
    npos = sum(1 for r in rs if r is not None and r > 0); nneg = sum(1 for r in rs if r is not None and r < 0)
    sign = "+" if npos >= 3 else ("-" if nneg >= 3 else None)
    cells[key] = dict(model=o["model"], target=o["target"], seed=o["seed"], r_by_year={str(YEARS[k]): fr[k] for k in CAL}, n_pos=npos, n_neg=nneg,
                      calendar_3of4_same_sign=sign is not None, sign=sign, r_2326_pooled=o["r_2326"], r_pool_W_ALPHA=o["pool"]["r"],
                      frozen_cell_PASS=J["criteria"][key].get("PASS_cell"))
agg = {}
for t in ("NET", "LONG", "SHORT", "CARRY"):
    for m in ("R", "L"):
        cs = [cells[f"{m}_{t}_s{s}"] for s in ("42", "2027")]
        agg[f"{m}_{t}"] = dict(both_seeds_3of4_positive=all(c["sign"] == "+" for c in cs), both_seeds_3of4_negative=all(c["sign"] == "-" for c in cs),
                               r_2326=[c["r_2326_pooled"] for c in cs], frozen_verdict=(J["model_target"].get(f"{m}_{t}", {}).get("verdict") if t != "CARRY" else "positive control"))
R = dict(device="t8_postfreeze_calendar.py", label="POST-FREEZE DESCRIPTIVE (not a gate; T8 verdict unchanged)", self_sha256=SELF,
         fit_receipt_sha256=hF, judge_receipt_sha256=hJ, T8_frozen_verdict=J["T8"], cells=cells, model_target=agg, utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(R, open(T8 + "/receipts/POSTFREEZE_calendar_T8.json", "w"), indent=1)
L = ["> **POST-FREEZE DESCRIPTIVE** —— 应 lead 于结果之后要求; 不是门, 不改变 T8 冻结判决(" + J["T8"] + ")。数字取自 `receipts/pod2/RECEIPT_T8_fit.json`(sha `" + hF[:16] + "…`), 装置 `devices/t8_postfreeze_calendar.py`。", "",
     "| 格 | 2023 | 2024 | 2025 | 2026 | 正 / 负 | 日历 ≥3/4 同号 | 2023–26 合并 r | 冻结格判决 |", "|---|---|---|---|---|---|---|---|---|"]
for key in F["cells"]:
    c = cells[key]
    L.append(f"| {key} | " + " | ".join(f"{c['r_by_year'][y]:+.4f}" for y in ("2023", "2024", "2025", "2026")) + f" | {c['n_pos']} / {c['n_neg']} | {('是(' + c['sign'] + ')') if c['sign'] else '否'} | {c['r_2326_pooled']:+.4f} | " + ("PASS" if c["frozen_cell_PASS"] else ("FAIL" if c["frozen_cell_PASS"] is False else "正控")) + " |")
L += ["", "| 模型 × 目标 | 两种子都 ≥3/4 为正 | 两种子都 ≥3/4 为负 | 2023–26 合并 r(s42 / s2027) | 冻结判决 |", "|---|---|---|---|---|"]
for k, a in agg.items():
    L.append(f"| {k} | {'是' if a['both_seeds_3of4_positive'] else '否'} | {'是' if a['both_seeds_3of4_negative'] else '否'} | {a['r_2326'][0]:+.4f} / {a['r_2326'][1]:+.4f} | {a['frozen_verdict']} |")
open(T8 + "/receipts/POSTFREEZE_calendar_T8.md", "w").write("\n".join(L) + "\n")
print("T8_POSTFREEZE_CALENDAR_DONE " + " ".join(f"{k}:{'+' if a['both_seeds_3of4_positive'] else ('-' if a['both_seeds_3of4_negative'] else 'x')}" for k, a in agg.items()) + f" T8_verdict_unchanged={J['T8']}")

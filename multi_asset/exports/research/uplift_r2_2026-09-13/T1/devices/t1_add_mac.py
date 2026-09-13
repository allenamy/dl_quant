#!/usr/bin/env python3
"""t1_add_mac.py — Mac, ADDENDUM 1 X1.1: the unit definitions behind P1's 1.371 (ledger) and r18's carry_ex 0.4797 (replay),
read from the source lines (asserted to contain the expected expressions) and written to a receipt."""
import os, sys, json, hashlib, time
T1 = os.path.abspath(sys.argv[1]); WHITE = set(x for x in sys.argv[2].split(",") if x)
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
assert sha(T1 + "/ADDENDUM_1_SPEC_T1_2026-09-13.md") == "79b7c067aaddd63691111809e27f35564fc32c231f7b618b9cedc59ac47f0c4f"
U = os.path.abspath(T1 + "/../../uplift_2026-09-11")
CHECKS = [
    (U + "/r18_foundation/devices/w10_sleeve_r18.py", "car_r = float((smr[m] * fnow * (4.0 / ivv)).sum() * 1e4)", "replay executor-caliber carry: position x current settled rate x 4/interval, bps, positive = paid"),
    (U + "/r18_foundation/devices/w10_sleeve_r18.py", "gt = float(np.abs(sm).sum())", "replay gross_total = sum |position| (unit gross denominator)"),
    (U + "/r18_foundation/devices/w10_sleeve_r18.py", "fnow = np.nan_to_num(FN[j, m], nan=0.0); ivv = IV[j, m]; ivv = np.where(np.isfinite(ivv) & (ivv > 0), ivv, 8.0)", "fnow = panel f_fund_now (per-settlement rate), iv = f_fund_iv hours"),
    (U + "/judge1_r6/j1_realized.py", "fund = float(fpd[(fts > g) & (fts <= g2)].sum())", "ledger funding: settlements in (E, E+4h], venue P&L sign (negative = paid)"),
    (U + "/judge1_r6/j1_realized.py", "gross = A[g]['gross'] or cov", "ledger denominator: anchors.jsonl realized_gross (USD), fallback covered notional"),
    (U + "/judge1_r6/j1_realized.py", "fund_bps=fund / gross * 1e4", "ledger funding in bps of gross per 4h anchor"),
    (T1 + "/devices/t1_realized.py", "tot = dict(price=0.0, fund=float(fpd[sel].sum()), fee=0.0, timing=0.0, cov=0.0, unc=0.0)", "T1 re-extraction uses the same settlement window"),
]
rows = []
for path, needle, meaning in CHECKS:
    lines = open(path).read().split("\n"); hits = [i + 1 for i, l in enumerate(lines) if needle in l]
    assert len(hits) >= 1, (path, needle)
    rows.append(dict(file=os.path.relpath(path, T1), sha256=sha(path), line=hits, text=needle, meaning=meaning))
RC = dict(self_sha256=sha(os.path.abspath(__file__)), label="ADDENDUM 1 X1.1", checks=rows,
          reading="both are bps per 4h anchor per unit gross; replay carry is MODELLED (rate at E x 4/iv on target positions, positive = paid), ledger funding is REALIZED (settlements in (E,E+4h] on read-back positions, negative = paid)",
          env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(RC, open(T1 + "/receipts/RECEIPT_T1_addendum1_mac.json", "w"), indent=1)
print(json.dumps([(r["file"], r["line"]) for r in rows]))

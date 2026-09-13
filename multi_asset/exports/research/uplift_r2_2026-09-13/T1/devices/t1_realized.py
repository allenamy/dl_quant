#!/usr/bin/env python3
"""t1_realized.py — Mac, READ-ONLY copies under T1/private (PREREG_T1 §2.4 REAL, GATE L).
Per (anchor, symbol) realized decomposition of the live book, same formulas as r6 judge1 (j1_realized.py / j1_fee_fix.py / j1_symret.py):
  price_s   = q_s(post-anchor readback at E) * (mid_s(E+4h) - mid_s(E))
  funding_s = sum funding_paid, settlements in (E, E+4h], dedupe (symbol, settlement_ts)
  fee_s     = - sum commission * USD price of commission_asset (same-anchor mid, else first anchor within +-4 anchors in ascending order), dedupe trade_id
  timing_s  = signed traded qty * (mid_s(E) - notional-weighted avg fill px)
  gross     = anchors.jsonl realized_gross (last row per floored anchor), as r6.
Also rn8 at E per symbol from the PRODUCER ledger copy (aux ledger_tail: last row with ft <= E, fresh <= 12h): rate * 8/iv.
GATE L: per-anchor totals equal r6 j1_realized.json rows (price/fund/fee/timing) on r6's anchors to 1e-6 USD; mismatches listed.
Launch: env -i PATH=/usr/bin:/bin HOME=$HOME /usr/bin/python3 devices/t1_realized.py <T1 dir> PATH,HOME,LC_CTYPE
"""
import os, sys, json, time, hashlib, collections
T1 = os.path.abspath(sys.argv[1]); WHITE = set(x for x in sys.argv[2].split(",") if x)
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
PREREG_SHA = "9548214267b5a44900ba90fee6b2fb2bbeb77964d562628b77678b16c56777f6"; AMEND_SHA = "a7628a7268cad50976470e5b6334c9086af9805bf786dac0ed51f496374da373"
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
assert sha(T1 + "/PREREG_T1_edge_diagnosis_2026-09-13.md") == PREREG_SHA and sha(T1 + "/PREREG_AMENDMENT_1_T1_2026-09-13.md") == AMEND_SHA
BASE = T1 + "/private/pilot_log"; AUX = T1 + "/private/aux_20260913.json"
R6 = os.path.abspath(T1 + "/../../uplift_2026-09-11/judge1_r6/j1_realized.json")
LIVE0 = 1787716800   # 2026-08-26 04Z
LIVE1 = 1789156800   # 2026-09-11 20Z
def G(t): return int(float(t) // 14400) * 14400
days = sorted(d for d in os.listdir(BASE) if d.isdigit())
A = {}; raw = 0
for d in days:
    p = f"{BASE}/{d}/anchors.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        ln = ln.strip()
        if not ln: continue
        try: r = json.loads(ln)
        except Exception: continue
        if r.get("anchor_ts") is None: continue
        raw += 1
        mv = r.get("mid_at_anchor_vector"); mids = {}
        if isinstance(mv, str):
            try: mids = json.loads(mv)
            except Exception: mids = {}
        elif isinstance(mv, dict): mids = mv
        A[G(r["anchor_ts"])] = dict(gross=float(r.get("realized_gross") or 0.0), mids=mids)
POS = collections.defaultdict(dict)
for d in days:
    p = f"{BASE}/{d}/position_readback.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        ln = ln.strip()
        if not ln: continue
        try: r = json.loads(ln)
        except Exception: continue
        if r.get("anchor_ts") is None or r.get("venue_position_qty") is None: continue
        POS[G(r["anchor_ts"])][r["symbol"]] = (float(r["venue_position_qty"]), float(r.get("venue_position_notional") or 0.0))
MIDS = {g: a["mids"] for g, a in A.items() if a["mids"]}
anchors_sorted = sorted(MIDS)
def px_asset(asset, g):
    if asset == "USDT": return 1.0
    sym = f"{asset}USDT"
    for cand in [g] + [a for a in anchors_sorted if abs(a - g) <= 4 * 14400]:
        v = MIDS.get(cand, {}).get(sym)
        if v: return float(v)
    return None
FEE = collections.defaultdict(lambda: collections.defaultdict(float)); TRDQ = collections.defaultdict(lambda: collections.defaultdict(float))
FILLPX = collections.defaultdict(lambda: collections.defaultdict(list)); seen = set(); unres = 0; nfill = 0
for d in days:
    p = f"{BASE}/{d}/fills.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        ln = ln.strip()
        if not ln: continue
        try: r = json.loads(ln)
        except Exception: continue
        tid = r.get("trade_id")
        if tid is not None:
            if tid in seen: continue
            seen.add(tid)
        if r.get("anchor_ts") is None: continue
        g = G(r["anchor_ts"]); s = r["symbol"]; nfill += 1
        a = r.get("commission_asset") or "USDT"; c = float(r.get("commission") or 0.0)
        P = px_asset(a, g)
        if P is None: unres += 1; P = 1.0
        FEE[g][s] += c * P
        sgn = 1.0 if r.get("side") == "buy" else -1.0; notl = float(r.get("fill_notional") or 0.0); fpx = float(r.get("fill_px") or 0.0)
        if fpx > 0: TRDQ[g][s] += sgn * notl / fpx
        FILLPX[g][s].append((fpx, notl))
FUND = []; seenf = set()
for d in days:
    p = f"{BASE}/{d}/funding.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        ln = ln.strip()
        if not ln: continue
        try: r = json.loads(ln)
        except Exception: continue
        k = (r["symbol"], r["settlement_ts"])
        if k in seenf: continue
        seenf.add(k)
        FUND.append((float(r["settlement_ts"]), r["symbol"], float(r.get("funding_paid") or 0.0), r.get("funding_interval_h"), float(r.get("funding_rate") or 0.0)))
FUND.sort()
fts = np.array([x[0] for x in FUND]); fsym = np.array([x[1] for x in FUND]); fpd = np.array([x[2] for x in FUND]); fiv = [x[3] for x in FUND]
aux = json.load(open(AUX)); LED = aux["ledger_tail"]
LEDT = {s: np.array([float(r[0]) for r in rows]) for s, rows in LED.items() if rows}
def rn8_at(s, g):
    rows = LED.get(s)
    if not rows: return np.nan, "no_ledger"
    t = LEDT[s]; k = int(np.searchsorted(t, g, side="right")) - 1
    if k < 0: return np.nan, "before_tail"
    if g - t[k] > 12 * 3600: return np.nan, "stale"
    iv = float(rows[k][2]) if (len(rows[k]) > 2 and rows[k][2]) else 8.0
    return float(rows[k][1]) * (8.0 / (iv if iv > 0 else 8.0)), "ok"
rows_out = []; anchor_rows = []
cov_reason = collections.Counter()
for g in sorted(A):
    g2 = g + 14400
    if g2 not in A: continue
    m1 = A[g]["mids"]; m2 = A[g2]["mids"]; pos = POS.get(g)
    if not pos or not m1 or not m2: continue
    gross = A[g]["gross"]
    syms = set(s for s, (q, n) in pos.items() if abs(n) >= 1e-9) | set(FEE.get(g, {}).keys()) | set(TRDQ.get(g, {}).keys())
    sel = (fts > g) & (fts <= g2)
    fund_by = collections.defaultdict(float)
    for s, v in zip(fsym[sel], fpd[sel]): fund_by[s] += v
    syms |= set(fund_by.keys())
    tot = dict(price=0.0, fund=float(fpd[sel].sum()), fee=0.0, timing=0.0, cov=0.0, unc=0.0)
    _start = len(rows_out)
    for s in sorted(syms):
        q, notl = pos.get(s, (0.0, 0.0))
        held = abs(notl) >= 1e-9
        p1 = m1.get(s); p2 = m2.get(s)
        price = 0.0; priced = False
        if held:
            if p1 and p2: price = q * (float(p2) - float(p1)); priced = True; tot["cov"] += abs(notl)
            else: tot["unc"] += abs(notl)
        tot["price"] += price
        fee = -FEE.get(g, {}).get(s, 0.0); tot["fee"] += fee
        tim = 0.0
        if s in TRDQ.get(g, {}) and p1:
            legs = FILLPX[g][s]; tn = sum(n for _, n in legs)
            if tn > 0:
                avg = sum(x * n for x, n in legs) / tn
                tim = TRDQ[g][s] * (float(p1) - avg)
        tot["timing"] += tim
        side = np.sign(q) if (held and q != 0) else (np.sign(-TRDQ.get(g, {}).get(s, 0.0)) if s in TRDQ.get(g, {}) else 0.0)
        rn, why = rn8_at(s, g); cov_reason[why] += 1
        rows_out.append((g, s, q, (q * float(p1)) if (held and p1) else np.nan, float(p1) if p1 else np.nan, float(p2) if p2 else np.nan, price, fund_by.get(s, 0.0), fee, tim, float(side), float(held), float(priced), rn))
    gross = gross or tot["cov"]          # r6: gross = realized_gross or covered notional; skip if <= 0
    if gross <= 0:
        del rows_out[_start:]          # (fixed: del rows_out[-len(syms):] wiped the whole list when syms was empty)
        continue
    anchor_rows.append(dict(A=g, gross=gross, **tot))
# ---------------- GATE L ----------------
r6 = json.load(open(R6))["rows"]; mine = {r["A"]: r for r in anchor_rows}
mism = []; n_cmp = 0
for r in r6:
    m = mine.get(r["A"])
    if m is None: mism.append(dict(A=r["A"], reason="anchor missing in T1 extraction")); continue
    n_cmp += 1
    d = {k: abs(m[k2] - r[k]) for k, k2 in (("price", "price"), ("fund", "fund"), ("fee", "fee"), ("timing", "timing"), ("gross", "gross"))}
    if max(d.values()) > 1e-6: mism.append(dict(A=r["A"], utc=r["utc"], diffs=d, r6=dict(price=r["price"], fund=r["fund"], fee=r["fee"], timing=r["timing"], gross=r["gross"]), t1=dict(price=m["price"], fund=m["fund"], fee=m["fee"], timing=m["timing"], gross=m["gross"])))
GL = dict(n_r6_rows=len(r6), n_compared=n_cmp, n_mismatch=len(mism), mismatches=mism[:40], PASS=bool(len(mism) == 0))
print("GATE_L", json.dumps(dict(n_r6_rows=GL["n_r6_rows"], n_compared=n_cmp, n_mismatch=len(mism), PASS=GL["PASS"])), flush=True)
# ---------------- outputs ----------------
names = np.array([r[1] for r in rows_out])
arr = np.array([[r[0], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10], r[11], r[12], r[13]] for r in rows_out], dtype=np.float64)
cols = ["A", "q", "notional_at_mid", "p1", "p2", "price_usd", "funding_usd", "fee_usd", "timing_usd", "side", "held", "priced", "rn8_producer"]
arows = np.array([[r["A"], r["gross"], r["price"], r["fund"], r["fee"], r["timing"], r["cov"], r["unc"]] for r in anchor_rows])
out = T1 + "/receipts/T1_real_names.npz"
np.savez_compressed(out, names=names, cols=np.array(cols), rows=arr, anchor_cols=np.array(["A", "gross", "price", "fund", "fee", "timing", "cov", "unc"]), anchors=arows)
live = arows[(arows[:, 0] >= LIVE0) & (arows[:, 0] <= LIVE1)]
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, amendment1_sha256=AMEND_SHA, copy_utc=open(T1 + "/private/COPY_UTC.txt").read().strip(), copy_utc_earlydays=open(T1 + "/private/COPY_UTC_earlydays.txt").read().strip(), copy_sha256_manifest=sha(T1 + "/private/COPY_SHA256.txt"),
          aux_sha256=sha(AUX), r6_realized_sha256=sha(R6), anchors_raw_rows=raw, anchors_canonical=len(A), fills_dedup_kept=nfill, fee_unresolved_price=unres, funding_rows_dedup=len(FUND),
          n_anchor_rows=len(anchor_rows), n_live_anchor_rows=int(len(live)), live_first=int(live[0, 0]) if len(live) else None, live_last=int(live[-1, 0]) if len(live) else None,
          rn8_producer_coverage=dict(cov_reason), gate_L=GL, out=out, out_sha256=sha(out),
          env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(RC, open(T1 + "/receipts/RECEIPT_T1_realized.json", "w"), indent=1, default=str)
print("DONE_t1_realized rows", len(rows_out), "anchors", len(anchor_rows), "live anchors", len(live))

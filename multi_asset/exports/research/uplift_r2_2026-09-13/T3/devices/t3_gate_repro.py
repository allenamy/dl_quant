#!/usr/bin/python3
"""T3 gate G1 / G2 (PREREG_T3_markout_curve_2026-09-13.md §2).

G1: re-run trackB_realized_cost_2026-09-11.py's per-anchor logic VERBATIM on the ledger snapshot, with the
    ledger state rebuilt as of the moment trackB wrote its rows file (T_cut = 2026-09-11T07:32:03Z), and
    compare row by row against trackB_realized_cost_rows.json (sha256 8ae867eb...). Then the critic's
    aggregates (-2.6573 bps, 27.5 % favourable anchors) are recomputed from the rebuilt rows.
G2: same cut state, the executor's own collapse rule (pilot_log.collapse_supersedes: last row per trade_id
    wins, file position = chronology) versus trackB's rule (keep the row carrying the 60 s mark).
Read-only on every input. ENV WHITELIST = EMPTY SET (asserted; os.environ.get / os.getenv raise after import).
"""
import calendar, hashlib, json, math, os, sys, time
from collections import defaultdict

T3 = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_r2_2026-09-13/T3"
PREREG = f"{T3}/PREREG_T3_markout_curve_2026-09-13.md"
PREREG_SHA = "c7be850055160d7eeafe10fb859470f442d3f0552333ba290d9496357be8f8f6"
LOG = f"{T3}/private/ledger_snap_20260913T0455Z"
ROWS = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/trackB_realized_cost_rows.json"
ROWS_SHA = "8ae867eb3c1e47cffa1c5514ad28bb76b8aa9add45d59bbeecf82d2103d29f05"
TRACKB_PY = "/Users/haosiyu/Desktop/quant_research/multi_asset/exports/research/uplift_2026-09-11/trackB_realized_cost_2026-09-11.py"
TRACKB_SHA = "9eb531f4269ed2ae4bc246ff5ad55b97f156facd021c51fd2cf13c2f4bab4406"
T_CUT_ISO = "2026-09-11T07:32:03Z"
T_CUT = float(calendar.timegm(time.strptime(T_CUT_ISO, "%Y-%m-%dT%H:%M:%SZ")))

_FORBID = ("CAL", "JUDGE", "PANEL", "W10_", "POD_", "DLW_", "KING_", "SEAT_", "UMASK", "LEGS", "FTRIM", "R12_", "R21_", "PHI", "CEM_Q", "LIVE_MODE")
_hit = sorted(k for k in os.environ if any(k.startswith(p) for p in _FORBID))
assert not _hit, f"E-0826-D: forbidden env present {_hit}"
def _no_env(*a, **k):
    raise RuntimeError("E-0826-D: this device reads no environment variable (whitelist = empty set)")
os.environ.get = _no_env; os.getenv = _no_env

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""): h.update(c)
    return h.hexdigest()

assert sha256(PREREG) == PREREG_SHA, "prereg sha mismatch"
assert sha256(ROWS) == ROWS_SHA, "trackB rows sha mismatch"
assert sha256(TRACKB_PY) == TRACKB_SHA, "trackB script sha mismatch"
SELF_SHA = sha256(os.path.abspath(__file__))

def iso_to_epoch(s):
    return float(calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ")))

def read_jsonl(p):
    out = []
    with open(p) as f:
        lines = f.readlines()
    for i, ln in enumerate(lines):
        ln = ln.strip()
        if not ln: continue
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            if i == len(lines) - 1: continue
            raise
    return out

def fill_row_in_cut(r):
    b = r.get("backfilled_utc")
    if b is not None:
        return iso_to_epoch(b) <= T_CUT
    ft = r.get("fill_ts")
    return ft is not None and float(ft) <= T_CUT

days = sorted(d for d in os.listdir(LOG) if d.isdigit())

# ---------------- trackB logic, verbatim port (only LOG and the time cut differ) ----------------
def build_state(cut=True):
    anch = {}
    for d in days:
        p = f"{LOG}/{d}/anchors.jsonl"
        if not os.path.exists(p): continue
        for r in read_jsonl(p):
            ts = r.get("anchor_ts")
            if ts is None: continue
            if cut and ts > T_CUT: continue
            mid = r.get("mid_at_anchor_vector")
            if isinstance(mid, str): mid = json.loads(mid)
            anch[ts] = dict(day=d, realized_gross=r.get("realized_gross"), target_gross=r.get("target_gross"),
                            mid=mid or {}, regime=r.get("regime_at_anchor"))
    pbg = defaultdict(float)
    for d in days:
        p = f"{LOG}/{d}/position_readback.jsonl"
        if not os.path.exists(p): continue
        for r in read_jsonl(p):
            ts = r["anchor_ts"]
            if cut and ts > T_CUT: continue
            v = float(r.get("venue_position_notional") or 0.0)
            pbg[ts] += abs(v)
    fills_raw = []
    for d in days:
        p = f"{LOG}/{d}/fills.jsonl"
        if not os.path.exists(p): continue
        for r in read_jsonl(p):
            if cut and not fill_row_in_cut(r): continue
            fills_raw.append(r)
    orders = []
    for d in days:
        p = f"{LOG}/{d}/orders.jsonl"
        if not os.path.exists(p): continue
        for r in read_jsonl(p):
            ts = r.get("anchor_ts")
            if ts is None: continue
            if cut and ts > T_CUT: continue
            orders.append(r)
    return anch, pbg, fills_raw, orders

def dedupe_trackB(fills_raw):
    F = {}; same = diff = 0
    for r in fills_raw:
        k = (r["symbol"], r["trade_id"])
        cur = F.get(k)
        if cur is None:
            F[k] = r; continue
        s_ = (cur.get("fill_notional") == r.get("fill_notional") and cur.get("commission") == r.get("commission")
              and cur.get("fill_px") == r.get("fill_px"))
        same += s_; diff += (not s_)
        if r.get("mid_at_fill_plus_60s") is not None and cur.get("mid_at_fill_plus_60s") is None:
            F[k] = r
    return list(F.values()), same, diff

def collapse_supersedes(rows):
    """pilot_log.collapse_supersedes (dl_quant_live live/pilot_log.py L452, sha f02baa69...), verbatim semantics."""
    seen_last = {}
    for i, f in enumerate(rows):
        tid = f.get("trade_id")
        if tid is not None: seen_last[tid] = i
    return [f for i, f in enumerate(rows) if f.get("trade_id") is None or seen_last.get(f.get("trade_id")) == i]

def per_anchor_rows(anch, pbg, fills, orders):
    ats = sorted(anch)
    def bnb_mid(ts):
        c = [t for t in ats if anch[t]["mid"].get("BNBUSDT")]
        if not c: return None
        t = min(c, key=lambda t: abs(t - ts)); return anch[t]["mid"]["BNBUSDT"]
    BNB = {t: bnb_mid(t) for t in ats}
    A = defaultdict(lambda: dict(fee=0.0, fee_bnb_usdt=0.0, notional=0.0, mk_notional=0.0, tk_notional=0.0,
                                 mk_fee=0.0, tk_fee=0.0, mo_wn=0.0, mo_w=0.0, n=0, n_mo=0))
    for r in fills:
        ts = r.get("anchor_ts")
        if ts is None: continue
        a = A[ts]
        c = float(r.get("commission") or 0.0); ca = r.get("commission_asset") or "USDT"
        cu = c * (BNB.get(ts) or 1.0) if ca == "BNB" else c
        if ca == "BNB": a["fee_bnb_usdt"] += cu
        nz = abs(float(r.get("fill_notional") or 0.0))
        mk = bool(r.get("venue_maker_flag")) if r.get("venue_maker_flag") is not None else (r.get("order_type") == "maker")
        a["fee"] += cu; a["notional"] += nz; a["n"] += 1
        if mk: a["mk_notional"] += nz; a["mk_fee"] += cu
        else: a["tk_notional"] += nz; a["tk_fee"] += cu
        m60 = r.get("mid_at_fill_plus_60s"); px = float(r.get("fill_px") or 0.0)
        if m60 is not None and px > 0:
            sgn = 1.0 if r.get("side") == "buy" else -1.0
            mo = sgn * (float(m60) - px) / px
            a["mo_wn"] += mo * nz; a["mo_w"] += nz; a["n_mo"] += 1
    O = defaultdict(lambda: dict(intended=0.0, filled=0.0))
    for r in orders:
        ts = r.get("anchor_ts")
        if ts is None: continue
        o = O[ts]
        o["intended"] += abs(float(r.get("intended_notional") or 0.0)); o["filled"] += abs(float(r.get("filled_notional") or 0.0))
    rows = []
    for ts in sorted(set(list(A) + list(O))):
        G = pbg.get(ts, 0.0)
        if G <= 0: G = anch.get(ts, {}).get("target_gross") or 0.0
        a = A.get(ts, {})
        if G <= 0: continue
        fee = a.get("fee", 0.0); nz = a.get("notional", 0.0)
        mo = (a["mo_wn"] / a["mo_w"]) if a.get("mo_w", 0) > 0 else float("nan")
        rows.append(dict(ts=ts, traded_notional=nz, fee_usdt=fee, adv_cost_usdt=-(a.get("mo_wn", 0.0)),
                         mo_cov=(a.get("mo_w", 0.0) / nz if nz > 0 else float("nan")),
                         markout60_bps=mo * 1e4 if mo == mo else float("nan")))
    return rows

def critic(rows):
    ok = lambda v: v == v
    tn = sum(r["traded_notional"] for r in rows if ok(r["traded_notional"]))
    fee = sum(r["fee_usdt"] for r in rows if ok(r["fee_usdt"]))
    adv = sum(r["adv_cost_usdt"] for r in rows if ok(r["adv_cost_usdt"]))
    mo = [r["markout60_bps"] for r in rows if ok(r["markout60_bps"])]
    return dict(n_anchor_rows=len(rows), n_rows_with_finite_markout60=len(mo), traded_notional_usdt=round(tn, 2),
                fee_bps_of_traded=round(fee / tn * 1e4, 4), markout60_bps_notional_weighted=round(-adv / tn * 1e4, 4),
                anchors_with_favourable_markout_pct=round(100.0 * sum(1 for v in mo if v > 0) / len(mo), 1),
                anchors_adverse_pct_strict_lt0=round(100.0 * sum(1 for v in mo if v < 0) / len(mo), 1),
                markout60_bps_raw=(-adv / tn * 1e4))

OUT = {"device": os.path.abspath(__file__), "self_sha256": SELF_SHA, "prereg_sha256": PREREG_SHA, "env_whitelist": [],
       "python": sys.version.split()[0], "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "inputs": {"ledger_snapshot": LOG, "ledger_manifest_sha256": sha256(f"{LOG}/MANIFEST_sha256.txt"),
                  "trackB_rows": {"path": ROWS, "sha256": ROWS_SHA}, "trackB_script": {"path": TRACKB_PY, "sha256": TRACKB_SHA}},
       "T_cut": T_CUT_ISO}

# ---------------- G1 ----------------
anch, pbg, fills_raw, orders = build_state(cut=True)
fills_tb, same, diff = dedupe_trackB(fills_raw)
mine = per_anchor_rows(anch, pbg, fills_tb, orders)
ref = json.load(open(ROWS))
ref_by = {r["ts"]: r for r in ref}; mine_by = {r["ts"]: r for r in mine}
set_equal = set(ref_by) == set(mine_by)
worst = {"traded_notional": 0.0, "fee_usdt": 0.0, "adv_cost_usdt": 0.0, "mo_cov": 0.0}
bad_rows = []
for ts in sorted(set(ref_by) | set(mine_by)):
    a = ref_by.get(ts); b = mine_by.get(ts)
    if a is None or b is None:
        bad_rows.append({"ts": ts, "why": "missing in " + ("reference" if a is None else "rebuild")}); continue
    for k in worst:
        x, y = a[k], b[k]
        if (isinstance(x, float) and math.isnan(x)) or (isinstance(y, float) and math.isnan(y)):
            if not ((isinstance(x, float) and math.isnan(x)) and (isinstance(y, float) and math.isnan(y))):
                bad_rows.append({"ts": ts, "field": k, "ref": x, "rebuild": y})
            continue
        d = abs(x - y); worst[k] = max(worst[k], d)
        tol = 1e-9 if k == "mo_cov" else 1e-6
        if d > tol: bad_rows.append({"ts": ts, "field": k, "ref": x, "rebuild": y, "abs_diff": d})
c_ref = critic(ref); c_mine = critic(mine)
g1_pass = (set_equal and not bad_rows and c_mine["markout60_bps_notional_weighted"] == -2.6573
           and c_mine["anchors_with_favourable_markout_pct"] == 27.5 and c_mine["n_anchor_rows"] == 243)
OUT["G1"] = {"rule": "rows ts-set equal; per-row |d| <= 1e-6 USDT (traded, fee, adv) and <= 1e-9 (mo_cov); aggregates -2.6573 and 27.5",
             "raw_fill_rows_in_cut": len(fills_raw), "deduped_trackB_rule": len(fills_tb),
             "dupes_identical_payload": same, "dupes_differing_payload": diff,
             "rows_ts_set_equal": set_equal, "n_rows_reference": len(ref), "n_rows_rebuild": len(mine),
             "worst_abs_diff": worst, "n_bad": len(bad_rows), "bad_rows_first20": bad_rows[:20],
             "critic_from_reference_rows": c_ref, "critic_from_rebuild": c_mine, "PASS": bool(g1_pass)}
print(json.dumps(OUT["G1"], indent=1, default=str))
if not g1_pass:
    json.dump(OUT, open(f"{T3}/receipts/GATE_repro.json", "w"), indent=1, default=str)
    print("G1 FAIL -> STOP (prereg §2)"); sys.exit(2)

# ---------------- G2 ----------------
fills_ex = collapse_supersedes(fills_raw)
by_tb = {(r["symbol"], r["trade_id"]): r for r in fills_tb}
by_ex = {(r["symbol"], r["trade_id"]): r for r in fills_ex}
assert set(by_tb) == set(by_ex)
ndiff = {"mid_at_fill_plus_60s": 0, "fill_notional": 0, "commission": 0}
for k in by_tb:
    for f in ndiff:
        if by_tb[k].get(f) != by_ex[k].get(f): ndiff[f] += 1
tid_symbols = defaultdict(set)
for r in fills_raw: tid_symbols[r["trade_id"]].add(r["symbol"])
rows_ex = per_anchor_rows(anch, pbg, fills_ex, orders)
c_ex = critic(rows_ex)
# full snapshot, no cut
_, _, fills_all, _ = build_state(cut=False)
coll_all = collapse_supersedes(fills_all)
by_type = defaultdict(lambda: [0, 0.0])
for r in coll_all:
    t = (r.get("order_type"), r.get("venue_maker_flag"))
    by_type[str(t)][0] += 1; by_type[str(t)][1] += abs(float(r.get("fill_notional") or 0.0))
OUT["G2"] = {"cut_state": {"trade_ids_differing_between_rules": ndiff, "trade_ids_shared_by_two_symbols": sum(1 for v in tid_symbols.values() if len(v) > 1),
                           "critic_under_executor_collapse": c_ex},
             "full_snapshot_no_cut": {"raw_fill_rows": len(fills_all), "collapsed_by_trade_id": len(coll_all),
                                      "collapsed_by_order_type_and_maker_flag": {k: {"n": v[0], "notional_usdt": round(v[1], 2)} for k, v in sorted(by_type.items())}}}
print(json.dumps(OUT["G2"], indent=1, default=str))
json.dump(OUT, open(f"{T3}/receipts/GATE_repro.json", "w"), indent=1, default=str)
print("G1 PASS; G2 written")

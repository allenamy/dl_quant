#!/usr/bin/env python3
"""parabolic_onset_forward_log.py — ZERO-TOUCH forward offline log for the parabolic-name intra-anchor continuation hypothesis
(PREREG_crash_continuation_parabolic_stratum_2026-09-06 commit 26aeb23; RESULT_crash_risk_long_end §Phase 2c = UNDECIDED, 5/6 conditions; the
missing one is the per-year significance, so this log accumulates the 2026-09+ forward sample).

READ-ONLY on the producer: reads ~/wide_shadow/state/rolling.npz (producer 5m cache), ~/wide_shadow/shadow_bundle/config.json (symbols_panel,
params.cap_mult) and ~/wide_shadow/state/target_live_king/<A>.json (king-form book target weights). It calls NO API and writes NOTHING under
~/wide_shadow or ~/dl_quant_live. Output is appended only under the research repo: multi_asset/exports/live/parabolic_onset_forward/events.jsonl
(append-only records) and run_log.jsonl (one line per run).

Cache layout (asserted at run time, verified against shadow_loop_v3.py 2026-09-06): ts = bar CLOSE times (open_time+5min), step 300 s, 40-day tail;
data (T, 829, 7) float16 with channels [ret5, rng, cpos, lqv, lcnt, lasz, tbf] and clips CHN_CLIPS — identical to the pod ext cache used by the
event study (crash_continuation.py / crash_stratum.py), so the same detection code applies.

Per run: every anchor A with a target file whose interval [A, A+4h] is fully covered by the cache (rows through A+4h) and not yet logged:
  cohort  = book LONG names with w_norm ≥ 0.5·capw, w_norm = w / Σ|w| (target weights sum to gross_norm), capw = cap_mult / n_names
            (fund_ema top-15% is NOT reconstructible per past anchor from the state files — aux.json holds only the latest EMA — so the cohort is the
            book-long component only; recorded as cohort_def = "book_long_only" in every record)
  layer   = P if the 3-day gain r3d = Π(1+ret5 rows E−863..E) − 1 ≥ +0.20 (≥ 80% finite bars, else U = unknown), Q otherwise (same definition as Phase 2b/2c)
  onset   = first row in E+1..E+48 with cumulative return from the anchor close ≤ −θ, θ ∈ {5, 8, 12}% (one per name per anchor), τ = that bar's close;
            mirror-up events (first ≥ +θ) recorded as type "mirror" for the placebo
  forward = r(τ→τ+1h/3h/next anchor/12h) including the first bar (incl) and from τ+5m (delay5m, primary); null where the cache does not yet reach —
            later runs append {"update": true, id, filled fields} records; a reader keeps the latest record per id
  value   = −r(τ+5m→next anchor)·1e4 − 8.9 bps (half round-trip 3.92 + adverse markout 5), weight = w_norm (book) and w_raw (target file)
RE-JUDGEMENT RULE (frozen, do not tune): after ≥ 14 calendar days of logged anchors AND ≥ 200 P-layer θ=8% events with a filled r(τ+5m→next),
apply PREREG_crash_continuation_parabolic_stratum §2 verbatim to the 2026-09+ sample: CONFIRM = P-layer r(τ+5m→next) CI95 upper < 0 (UTC-day-block
bootstrap 2000, seed 20260905) on the forward sample AND θ5/θ12 same sign AND mirror placebo not negative AND P − Q CI95 upper < 0 AND value bound
≥ +0.03 bps/anchor/gross (CI lower > 0); REJECT = P CI lower > −15 bps or mirror significantly negative; else UNDECIDED. The rule is applied by the
lead, not by this script; the script only logs and prints running counts/means.
usage: parabolic_onset_forward_log.py [--since 2026-09-01T00:00:00Z] [--dry-run]"""
import os, sys, json, time, hashlib, argparse, calendar
import numpy as np
HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; STATE = f"{WS}/state"; BUNDLE_CFG = f"{WS}/shadow_bundle/config.json"
REPO = os.path.dirname(os.path.abspath(__file__)).split("/multi_asset/")[0]; OUTD = f"{REPO}/multi_asset/exports/live/parabolic_onset_forward"
EVENTS = f"{OUTD}/events.jsonl"; RUNLOG = f"{OUTD}/run_log.jsonl"
THETAS = (0.05, 0.08, 0.12); COST = 8.9; CHN = ["ret5", "rng", "cpos", "lqv", "lcnt", "lasz", "tbf"]
SELF = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
ap = argparse.ArgumentParser(); ap.add_argument("--since", default="2026-09-01T00:00:00Z"); ap.add_argument("--dry-run", action="store_true"); args = ap.parse_args()
SINCE = calendar.timegm(time.strptime(args.since, "%Y-%m-%dT%H:%M:%SZ"))
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""): h.update(ch)
    return h.hexdigest()
cfg = json.load(open(BUNDLE_CFG)); SYMS = list(cfg["symbols_panel"]); CAPM = float(cfg["params"]["cap_mult"]); NW = len(SYMS); SI = {s: j for j, s in enumerate(SYMS)}
z = np.load(f"{STATE}/rolling.npz", allow_pickle=True); CTS = z["ts"].astype(np.int64); D = z["data"]
assert D.ndim == 3 and D.shape[1] == NW and D.shape[2] == 7 and D.dtype == np.float16, ("cache layout", D.shape, D.dtype)
assert np.all(np.diff(CTS) == 300) and int(CTS[0]) % 300 == 0, "cache ts must be a contiguous 5-min grid"
T = len(CTS); row = {int(t): i for i, t in enumerate(CTS)}
r5 = D[:, :, 0].astype(np.float32); fin = np.isfinite(r5); LC = np.cumsum(np.where(fin, np.log1p(np.clip(r5, -0.99, None)), 0.0), 0, dtype=np.float64); FN = np.cumsum(fin, 0)
def existing():
    done = set(); ids = {}
    if os.path.exists(EVENTS):
        for line in open(EVENTS):
            try: r = json.loads(line)
            except Exception: continue
            if r.get("type") == "anchor": done.add(int(r["anchor"]))
            elif r.get("type") in ("onset", "mirror"): ids[r["id"]] = {**ids.get(r["id"], {}), **r}
    return done, ids
def fwd(tau, j, e_next, delay):
    a = tau + delay; out = {}
    for name, b in (("1h", tau + 12), ("3h", tau + 36), ("next", e_next), ("12h", tau + 144)):
        out[name] = (float(np.expm1(LC[b, j] - LC[a, j])) if (b > a and b < T) else None)
    return out
done, ids = existing(); anchors = []
for fn in sorted(os.listdir(f"{STATE}/target_live_king")):
    if not fn.endswith(".json"): continue
    A = int(fn.split(".")[0])
    if A < SINCE or A in done or A % 14400 != 0: continue
    if A not in row or (A + 14400) not in row or row[A] < 864: continue   # need rows E−863..E and E+1..E+48 inside the cache
    anchors.append(A)
new_records = []; stats = {"anchors": 0, "events": {f"theta{int(t*100)}": {"P": 0, "Q": 0, "U": 0, "mirror": 0} for t in THETAS}}
for A in anchors:
    tj = json.load(open(f"{STATE}/target_live_king/{A}.json")); w = tj["weights"]; l1 = sum(abs(v) for v in w.values()); n_names = int(tj["n_names"]); capw = CAPM / max(n_names, 1)
    E = row[A]; E_next = E + 48
    coh = [(s, v, v / l1) for s, v in w.items() if v > 0 and l1 > 0 and (v / l1) >= 0.5 * capw and s in SI]
    js = np.array([SI[s] for s, _, _ in coh], int)
    n3 = FN[E, js] - FN[E - 864, js]; r3d = np.where(n3 >= 691, np.expm1(LC[E, js] - LC[E - 864, js]), np.nan)
    rec_anchor = {"type": "anchor", "anchor": A, "anchor_utc": time.strftime("%FT%TZ", time.gmtime(A)), "cohort_def": "book_long_only", "n_cohort": len(coh), "capw": capw, "n_names": n_names, "gross_norm": tj.get("gross_norm"),
                  "target_sha": sha(f"{STATE}/target_live_king/{A}.json"), "booster_sha": tj.get("booster_sha"), "n_P": int(np.sum(r3d >= 0.20)), "n_Q": int(np.sum(r3d < 0.20)), "n_U": int(np.sum(~np.isfinite(r3d))), "logged_utc": time.strftime("%FT%TZ", time.gmtime()), "script_sha": SELF}
    cum = np.expm1(LC[E + 1: E + 49][:, js] - LC[E, js])   # (48, n) cumulative return from the anchor close
    for th in THETAS:
        k_ = f"theta{int(th*100)}"
        for sign, typ in ((-1, "onset"), (+1, "mirror")):
            hit = (cum <= -th) if sign < 0 else (cum >= th)
            for c in np.where(hit.any(0))[0]:
                k = int(hit[:, c].argmax()) + 1; tau = E + k; s, wr, wn = coh[c]; j = js[c]
                layer = "P" if r3d[c] >= 0.20 else ("Q" if np.isfinite(r3d[c]) else "U")
                f0 = fwd(tau, j, E_next, 0); f1 = fwd(tau, j, E_next, 1)
                rec = {"type": typ, "id": f"{A}:{s}:{k_}:{typ}", "anchor": A, "anchor_utc": rec_anchor["anchor_utc"], "symbol": s, "theta": th, "layer": layer, "r3d": (float(r3d[c]) if np.isfinite(r3d[c]) else None),
                       "k_bars": k, "tau_minutes": 5 * k, "tau_utc": time.strftime("%FT%TZ", time.gmtime(int(CTS[tau]))), "w_raw": wr, "w_norm": wn, "capw": capw,
                       "fwd_incl": f0, "fwd_delay5m": f1, "value_bps": (float(-f1["next"] * 1e4 - COST) if f1["next"] is not None else None), "cohort_def": "book_long_only", "logged_utc": rec_anchor["logged_utc"]}
                new_records.append(rec)
                if typ == "onset": stats["events"][k_][layer] += 1
                else: stats["events"][k_]["mirror"] += 1
    new_records.append(rec_anchor); stats["anchors"] += 1
# update pass: fill forward fields of earlier events now covered by the cache
updates = 0
for id_, r in ids.items():
    if r.get("anchor", 0) < SINCE or r["anchor"] not in row: continue
    missing = [h for h in ("1h", "3h", "next", "12h") if (r.get("fwd_delay5m") or {}).get(h) is None or (r.get("fwd_incl") or {}).get(h) is None]
    if not missing: continue
    E = row[r["anchor"]]; tau = E + int(r["k_bars"]); j = SI.get(r["symbol"])
    if j is None: continue
    f0 = fwd(tau, j, E + 48, 0); f1 = fwd(tau, j, E + 48, 1)
    filled0 = {h: f0[h] for h in missing if f0[h] is not None}; filled1 = {h: f1[h] for h in missing if f1[h] is not None}
    if filled0 or filled1:
        up = {"type": r["type"], "update": True, "id": id_, "anchor": r["anchor"], "symbol": r["symbol"], "theta": r["theta"], "layer": r.get("layer"), "fwd_incl": {**(r.get("fwd_incl") or {}), **filled0}, "fwd_delay5m": {**(r.get("fwd_delay5m") or {}), **filled1}, "logged_utc": time.strftime("%FT%TZ", time.gmtime())}
        if up["fwd_delay5m"].get("next") is not None: up["value_bps"] = float(-up["fwd_delay5m"]["next"] * 1e4 - COST)
        new_records.append(up); updates += 1
if not args.dry_run:
    os.makedirs(OUTD, exist_ok=True)
    with open(EVENTS, "a") as f:
        for r in new_records: f.write(json.dumps(r, separators=(",", ":")) + "\n")
# running summary over the whole log (latest record per id), 2026-09+ anchors
done2, ids2 = existing()
if args.dry_run:
    for r in new_records:
        if r.get("type") in ("onset", "mirror") and not r.get("update"): ids2[r["id"]] = r
summ = {}
for th in THETAS:
    k_ = f"theta{int(th*100)}"; summ[k_] = {}
    for lab, cond in (("P", lambda r: r["type"] == "onset" and r.get("layer") == "P"), ("Q", lambda r: r["type"] == "onset" and r.get("layer") == "Q"), ("mirror_P", lambda r: r["type"] == "mirror" and r.get("layer") == "P")):
        rs = [r for r in ids2.values() if r["anchor"] >= SINCE and abs(r["theta"] - th) < 1e-9 and cond(r)]
        v = [r["fwd_delay5m"]["next"] for r in rs if (r.get("fwd_delay5m") or {}).get("next") is not None]
        summ[k_][lab] = {"n_events": len(rs), "n_filled_next": len(v), "mean_r_tau5m_to_next_bps": (round(float(np.mean(v)) * 1e4, 1) if v else None)}
line = {"run_utc": time.strftime("%FT%TZ", time.gmtime()), "script_sha": SELF, "cache_sha": sha(f"{STATE}/rolling.npz"), "cache_range": [time.strftime("%FT%TZ", time.gmtime(int(CTS[0]))), time.strftime("%FT%TZ", time.gmtime(int(CTS[-1])))], "since": args.since, "anchors_new": stats["anchors"], "anchors_total_logged": len(done2), "events_new": stats["events"], "updates": updates, "summary_2026_09plus": summ, "dry_run": args.dry_run}
if not args.dry_run:
    with open(RUNLOG, "a") as f: f.write(json.dumps(line) + "\n")
print(json.dumps(line, indent=1))

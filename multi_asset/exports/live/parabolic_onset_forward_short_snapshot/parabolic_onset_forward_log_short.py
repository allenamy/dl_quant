#!/usr/bin/env python3
"""parabolic_onset_forward_log_short.py -- DERIVED, do not hand-edit.

Derived from parabolic_onset_forward_log.py by derive_short_cohort_forward_log.py (see the .diff and
DERIVE_RECEIPT.json next to this file). Prereg: docs/PREREG_short_squeeze_onset_forward_2026-09-25.md
revision 1 (lead-frozen criteria, inherited verbatim from 26aeb23 with a sign mirror).

WHAT IT MEASURES: for names the book is SHORT, does an intra-anchor UP onset (cumulative >= +theta)
continue up to the next anchor -- i.e. does the loss on a held short keep running, and is exiting that
short worth more than the cost? P layer is unchanged (r3d >= +0.20): a shorted name that already ran up
20% and keeps going up IS the squeeze.

THE THREE MIRRORS vs the parent (everything else is byte-identical):
  cohort  v > 0            ->  v < 0            (threshold on |w|)
  onset   first <= -theta  ->  first >= +theta  (the placebo mirrors to the DOWN direction)
  value   -r - cost        ->  +r - cost        (exiting a short is worth the rise avoided)

WINDOW (prereg rev 1 §4, lead): anchors >= 2026-09-25T00:00Z are the forward sample and are the ONLY
ones that count toward the re-judge gate. 2026-09-01..09-24 is backfilled for a shared axis with the
long cohort but is DESCRIPTIVE ONLY -- it overlaps 09-16..24, the period that generated the hypothesis.
The run_log emits the two segments as separate objects plus an explicit gate_status, because adding
them together is the single most likely way to violate this prereg.

ZERO-TOUCH: reads ~/wide_shadow/state/rolling.npz, shadow_bundle/config.json and
state/target_live_king/<A>.json. Calls NO API. Writes ONLY under its own output directory
(~/parabolic_onset_forward_short by default, $SHORT_OUTD to override) -- never under ~/wide_shadow,
~/dl_quant_live, or the research repo. It lives outside ~/Desktop on purpose: launchd hits a TCC wall
on the iCloud repo where it can stat but NOT enumerate, so a job there runs "successfully" and does
nothing. Startup asserts it can ENUMERATE its inputs.

usage: parabolic_onset_forward_log_short.py [--since 2026-09-01T00:00:00Z] [--dry-run]
"""
import os, sys, json, time, hashlib, argparse, calendar
import numpy as np
HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; STATE = f"{WS}/state"; BUNDLE_CFG = f"{WS}/shadow_bundle/config.json"
OUTD = os.environ.get("SHORT_OUTD", f"{HOME}/parabolic_onset_forward_short")
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
for _d in (STATE, f"{STATE}/target_live_king"):
    # ENUMERATE, not stat: the TCC wall on ~/Desktop allows stat and blocks listing, so a stat-based
    # self-check passes while the job still runs silently empty (the notary chain did this for 16 days).
    _n = len(os.listdir(_d))
    assert _n > 0, f"cannot enumerate {_d} (got {_n} entries) -- refusing to run silently empty"
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
    coh = [(s, v, v / l1) for s, v in w.items() if v < 0 and l1 > 0 and (-v / l1) >= 0.5 * capw and s in SI]
    js = np.array([SI[s] for s, _, _ in coh], int)
    n3 = FN[E, js] - FN[E - 864, js]; r3d = np.where(n3 >= 691, np.expm1(LC[E, js] - LC[E - 864, js]), np.nan)
    rec_anchor = {"type": "anchor", "anchor": A, "anchor_utc": time.strftime("%FT%TZ", time.gmtime(A)), "cohort_def": "book_short_only", "n_cohort": len(coh), "capw": capw, "n_names": n_names, "gross_norm": tj.get("gross_norm"),
                  "target_sha": sha(f"{STATE}/target_live_king/{A}.json"), "booster_sha": tj.get("booster_sha"), "n_P": int(np.sum(r3d >= 0.20)), "n_Q": int(np.sum(r3d < 0.20)), "n_U": int(np.sum(~np.isfinite(r3d))), "logged_utc": time.strftime("%FT%TZ", time.gmtime()), "script_sha": SELF}
    cum = np.expm1(LC[E + 1: E + 49][:, js] - LC[E, js])   # (48, n) cumulative return from the anchor close
    for th in THETAS:
        k_ = f"theta{int(th*100)}"
        for sign, typ in ((+1, "onset"), (-1, "mirror")):
            hit = (cum <= -th) if sign < 0 else (cum >= th)
            for c in np.where(hit.any(0))[0]:
                k = int(hit[:, c].argmax()) + 1; tau = E + k; s, wr, wn = coh[c]; j = js[c]
                layer = "P" if r3d[c] >= 0.20 else ("Q" if np.isfinite(r3d[c]) else "U")
                f0 = fwd(tau, j, E_next, 0); f1 = fwd(tau, j, E_next, 1)
                rec = {"type": typ, "id": f"{A}:{s}:{k_}:{typ}", "anchor": A, "anchor_utc": rec_anchor["anchor_utc"], "symbol": s, "theta": th, "layer": layer, "r3d": (float(r3d[c]) if np.isfinite(r3d[c]) else None),
                       "k_bars": k, "tau_minutes": 5 * k, "tau_utc": time.strftime("%FT%TZ", time.gmtime(int(CTS[tau]))), "w_raw": wr, "w_norm": wn, "capw": capw,
                       "fwd_incl": f0, "fwd_delay5m": f1, "value_bps": (float(+f1["next"] * 1e4 - COST) if f1["next"] is not None else None), "cohort_def": "book_short_only", "logged_utc": rec_anchor["logged_utc"]}
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
        if up["fwd_delay5m"].get("next") is not None: up["value_bps"] = float(+up["fwd_delay5m"]["next"] * 1e4 - COST)
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
GATE_START = calendar.timegm(time.strptime("2026-09-25T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ"))
summ = {}
# Two segments, reported SEPARATELY and never added together (prereg rev 1 §5): only anchors
# >= GATE_START are forward evidence; 09-01..09-24 overlaps the period that generated the hypothesis
# and is descriptive only. Summing them is the single most likely way to violate this prereg, so the
# device emits them as separate objects rather than trusting anyone to keep them apart.
for seg, lo, hi in (("gate_forward_ge_" + "2026-09-25T00:00:00Z".replace("-", "").replace(":", "").replace("T", "_")[:11], GATE_START, 1 << 62),
                    ("in_sample_descriptive_NOT_forward", SINCE, GATE_START)):
    summ[seg] = {}
    for th in THETAS:
        k_ = f"theta{int(th*100)}"; summ[seg][k_] = {}
        for lab, cond in (("P", lambda r: r["type"] == "onset" and r.get("layer") == "P"), ("Q", lambda r: r["type"] == "onset" and r.get("layer") == "Q"), ("mirror_P", lambda r: r["type"] == "mirror" and r.get("layer") == "P")):
            rs = [r for r in ids2.values() if lo <= r["anchor"] < hi and abs(r["theta"] - th) < 1e-9 and cond(r)]
            v = [r["fwd_delay5m"]["next"] for r in rs if (r.get("fwd_delay5m") or {}).get("next") is not None]
            summ[seg][k_][lab] = {"n_events": len(rs), "n_filled_next": len(v), "mean_r_tau5m_to_next_bps": (round(float(np.mean(v)) * 1e4, 1) if v else None)}
_gseg = [k for k in summ if k.startswith("gate_forward_")][0]
_gate_days = sorted({(a // 86400) for a in done2 if a >= GATE_START})
GATE_STATUS = {"gate_start_utc": "2026-09-25T00:00:00Z", "segment_used": _gseg,
               "theta8_P_filled_next": summ[_gseg]["theta8"]["P"]["n_filled_next"],
               "n_calendar_days": len(_gate_days), "need_theta8_P_filled": 200, "need_calendar_days": 14,
               "TRIGGERED": bool(summ[_gseg]["theta8"]["P"]["n_filled_next"] >= 200 and len(_gate_days) >= 14),
               "NOTE": "the in-sample segment is NEVER added to these counts"}
line = {"run_utc": time.strftime("%FT%TZ", time.gmtime()), "script_sha": SELF, "cache_sha": sha(f"{STATE}/rolling.npz"), "cache_range": [time.strftime("%FT%TZ", time.gmtime(int(CTS[0]))), time.strftime("%FT%TZ", time.gmtime(int(CTS[-1])))], "since": args.since, "anchors_new": stats["anchors"], "anchors_total_logged": len(done2), "events_new": stats["events"], "updates": updates, "summary_by_segment": summ, "gate_status": GATE_STATUS, "cohort_def": "book_short_only", "prereg": "docs/PREREG_short_squeeze_onset_forward_2026-09-25.md rev1", "dry_run": args.dry_run}
if not args.dry_run:
    with open(RUNLOG, "a") as f: f.write(json.dumps(line) + "\n")
print(json.dumps(line, indent=1))

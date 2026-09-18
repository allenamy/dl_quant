#!/usr/bin/env python3
"""FP3 P-C3 v2 (2026-09-18, after independent review round 11 R11-PC3): DIAGNOSTIC — alternative stop TRIGGERS on the PRODUCTION positions plus a
static held-price footprint. NOT a stop-effect estimate and NOT a counterfactual with independent branch positions (see LIMITS).

Three trigger specifications evaluated on the live ledgers:
  V0 production   : depth = unrealised / |current notional| ≤ depth_pct, consecutive_anchors as configured (the executor's own per_name_stop.evaluate)
  V1 entry-basis  : depth = unrealised / |entry notional| (avg cost × |qty|) — the denominator ONLY; dust eligibility and the exit test keep the
                    CURRENT notional (per_name_stop.evaluate cannot take a separate denominator ⇒ an explicit REPLICA of its four steps is used for
                    V1; the replica is verified against the production function on V0 over the whole window before it is trusted: `replica_check`)
  V2 one-anchor   : production denominator, consecutive_anchors = 1 (production function)

v2 corrections (each was a reviewer counterexample on v1):
  · cost basis: fills are applied up to each readback row's OWN read_ts (same cross-section), not A+3600; a ZERO readback ends the lifecycle (pos/avg
    cleared; the next lifecycle's basis is known only from its own fills, otherwise UNKNOWN by the venue re-seat rule); a fill that crosses zero sets the
    residual position's basis to that fill's price and marks it KNOWN; fills deduped by (symbol, trade_id); protective-flatten readbacks are observation
    points of the basis walk (they are not stop-evaluation snapshots, as in production).
  · forward footprint: primary window (A, A+72h] = 18 four-hour windows from the EVENT ANCHOR A; a window is priced only if all 48 five-minute rows are
    finite; any incomplete window ⇒ the event is CENSORED (coverage fields kept, never compounded as 0); maturity gate: A + 72h ≤ last panel row at
    evaluation time, else CENSORED (immature). Secondary, exit-aligned window (A+4h, A+76h] (the production exit trades at the NEXT run, ≥ A+4h24m; v1's
    convention) reported beside it with its own censoring. `evaluated_at_utc` and the panel's last row are recorded.
  · production event matching: production triggers = names newly present in phase_C `per_name_stop.stopped` (anchor_runs.log), keyed by the 4h bucket of
    the phase_C log time; joined to V0 device events on (symbol, bucket) exactly (±1 bucket reported as near-miss, not matched); every production event is
    listed matched / missed with a reason; recall and precision reported; V1's events and V0's matched events are DIFFERENT populations.
LIMITS (unchanged from the reviewer's finding, stated rather than fixed): all three specs read the SAME production positions after a trigger — an
earlier or later stop does not get its own position/cash lifecycle, so no spec's "avoided P&L" is a stop effect; funding, fees, exit price/time,
reshape/neutrality effects are not modelled. Independent-position counterfactual: NOT DONE.
usage: pc3_stop_counterfactual.py <from_day YYYYMMDD> <to_day> <out.json>    env: PC3_PILOT_LOG (default ~/dl_quant_live/state/live/pilot_log),
      PC3_ANCHOR_RUNS (default ~/dl_quant_live/state/anchor_runs.log), PC3_PNS_DIR (default ~/dl_quant_live/live), PC3_ROLLING / PC3_SYMS (producer panel)."""
import sys, os, json, time, glob, collections, hashlib
import numpy as np

W4H = 14400; NWIN = 18; EPS = 1e-12
VERSION = "v2"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""):
            h.update(ch)
    return h.hexdigest()


U = lambda t: time.strftime("%m-%d %H:%MZ", time.gmtime(float(t)))


# ── 1. cost-basis walk (weighted average cost, cash-engine v5 semantics) ──────────────────────────────────────────────────────────────────────
class Basis:
    """Per-symbol position / average-cost / known flag, advanced by fills and reconciled at readbacks."""

    def __init__(self):
        self.pos = collections.defaultdict(float); self.avg = collections.defaultdict(float); self.known = collections.defaultdict(lambda: True)

    def apply_fill(self, r):
        s = r["symbol"]; px = float(r["fill_px"]); q = float(r["fill_notional"]) / px * (1.0 if str(r.get("side", "")).upper() == "BUY" else -1.0); p0 = self.pos[s]
        if abs(p0) < EPS:                                  # new lifecycle (or first fill after a flat) ⇒ basis is this fill: KNOWN
            self.avg[s] = px; self.known[s] = True
        elif (p0 > 0) == (q > 0):                          # adding to the position: weighted average (basis stays known iff it was)
            self.avg[s] = (abs(p0) * self.avg[s] + abs(q) * px) / max(abs(p0) + abs(q), EPS)
        elif abs(q) > abs(p0) + EPS:                       # crossing zero: the residual's basis is THIS fill's price ⇒ KNOWN (reviewer fixture 3)
            self.avg[s] = px; self.known[s] = True
        # reducing without crossing: avg unchanged, known unchanged
        self.pos[s] = p0 + q
        if abs(self.pos[s]) < EPS:
            self.pos[s] = 0.0; self.avg[s] = 0.0; self.known[s] = True

    def reconcile(self, s, q, mark):
        """Observation of the venue position q at a readback (mark = |notional|/|qty|). Zero ⇒ lifecycle ends. Non-zero mismatch beyond 1 USDT ⇒
        venue re-seat: quantity adopted, basis UNKNOWN until the lifecycle ends."""
        if abs(q) < EPS:
            self.pos[s] = 0.0; self.avg[s] = 0.0; self.known[s] = True; return "flat"
        if abs(self.pos[s] - q) * mark > 1.0:
            self.pos[s] = q; self.known[s] = False; return "reseat"
        return "ok"


def build_snapshots(fills, readbacks):
    """fills: rows with symbol/fill_ts/fill_px/fill_notional/side(/trade_id); readbacks: rows with symbol/anchor_ts/read_ts/venue_position_qty/
    venue_position_notional/source. Returns (snapshots, basis) where snapshots = [(A, {positions_notional, positions_unrealized, positions_entry_notional},
    unknown_names)] for every post_anchor readback bucket A = floor(anchor_ts / 4h). Fills are applied per symbol up to each readback row's own read_ts."""
    seen = {}
    for r in fills:
        k = (r["symbol"], r.get("trade_id")); kk = (str(r.get("backfilled_utc") or ""),)
        if k not in seen or kk >= seen[k][0]:
            seen[k] = (kk, r)
    by_sym = collections.defaultdict(list)
    for _, r in seen.values():
        by_sym[r["symbol"]].append(r)
    for s in by_sym:
        by_sym[s].sort(key=lambda r: float(r["fill_ts"]))
    ptr = collections.defaultdict(int); B = Basis()
    obs = sorted(readbacks, key=lambda r: (float(r.get("read_ts") or r["anchor_ts"]), r["symbol"]))
    snaps = collections.OrderedDict(); unk = collections.defaultdict(set); recon = collections.Counter()
    for r in obs:
        s = r["symbol"]; rt = float(r.get("read_ts") or r["anchor_ts"]); q = float(r["venue_position_qty"]); v = float(r["venue_position_notional"])
        L = by_sym.get(s, [])
        while ptr[s] < len(L) and float(L[ptr[s]]["fill_ts"]) <= rt:
            B.apply_fill(L[ptr[s]]); ptr[s] += 1
        mark = (abs(v) / abs(q)) if abs(q) > EPS else 0.0
        recon[B.reconcile(s, q, mark)] += 1
        if not str(r.get("source", "")).endswith("@post_anchor"):
            continue                                        # flatten readbacks: observation only (production evaluates at terminal readbacks)
        A = int(float(r["anchor_ts"]) // W4H * W4H)
        if A not in snaps:
            snaps[A] = {"positions_notional": {}, "positions_unrealized": {}, "positions_entry_notional": {}}
        if abs(q) < EPS:
            continue
        snaps[A]["positions_notional"][s] = v
        if B.known[s] and B.avg[s] > 0:
            snaps[A]["positions_unrealized"][s] = (mark - B.avg[s]) * q
            snaps[A]["positions_entry_notional"][s] = abs(B.avg[s] * q)
        else:
            unk[A].add(s)
    out = [(A, snap, sorted(unk[A])) for A, snap in snaps.items()]
    return out, {"reconcile_counts": dict(recon), "n_fills_deduped": sum(len(v) for v in by_sym.values())}


# ── 2. the trigger rule: production function + explicit replica (V1 needs a denominator the function cannot take) ─────────────────────────────
def evaluate_replica(snapshot, state, conf, now_ts, denominator="current"):
    """Replica of per_name_stop.evaluate (409ea16) steps 1–4 with ONE change: the depth denominator. Eligibility (dust) and the exit test keep the
    CURRENT notional in both modes. denominator='current' ⇒ must equal the production function bitwise (verified in main); 'entry' ⇒ V1."""
    st = {"counters": dict(state.get("counters", {})), "stopped": dict(state.get("stopped", {})), "cooldown": dict(state.get("cooldown", {}))}
    if not conf.get("enabled") or snapshot is None:
        return st, []
    depth_pct = float(conf.get("depth_pct", -0.25)); need = int(conf.get("consecutive_anchors", 2)); cool = float(conf.get("cooloff_days", 7)); minn = float(conf.get("min_notional_usdt", 20.0))
    pn = snapshot.get("positions_notional") or {}; pu = snapshot.get("positions_unrealized") or {}; pe = snapshot.get("positions_entry_notional") or {}
    for s in list(st["stopped"]):
        if abs(float(pn.get(s, 0.0))) < minn:
            st["cooldown"][s] = now_ts + cool * 86400.0; del st["stopped"][s]
    for s in list(st["cooldown"]):
        if float(st["cooldown"][s]) <= now_ts:
            del st["cooldown"][s]
    seen = set()
    for s, notional in pn.items():
        if s in st["stopped"] or s in st["cooldown"]:
            continue
        n = abs(float(notional))
        if n < minn:
            continue
        u = pu.get(s)
        if u is None:
            continue
        if denominator == "entry":
            d = pe.get(s)
            if d is None or abs(float(d)) < EPS:
                continue
            depth = float(u) / abs(float(d))
        else:
            depth = float(u) / n
        seen.add(s)
        if depth <= depth_pct:
            c = int(st["counters"].get(s, 0)) + 1
            if c >= need:
                st["stopped"][s] = now_ts; st["counters"].pop(s, None)
            else:
                st["counters"][s] = c
        else:
            st["counters"].pop(s, None)
    for s in list(st["counters"]):
        if s not in seen:
            del st["counters"][s]
    return st, []


# ── 3. forward footprint with coverage + maturity ────────────────────────────────────────────────────────────────────────────────────────────
def forward_footprint(A, s, rts, ret5, sidx, panel_last, start_offset=0):
    """Compounded price return over 18 four-hour windows (A+off, A+off+72h]; priced only if every window has exactly 48 finite rows. Returns a dict
    with status PRICED / CENSORED_IMMATURE / CENSORED_INCOMPLETE / NO_PANEL_SYMBOL and coverage fields."""
    start = A + start_offset; end = start + NWIN * W4H
    res = {"window_utc": [U(start), U(end)], "n_windows": NWIN, "n_windows_priced": 0, "first_missing_window": None, "status": None, "path_return": None}
    if s not in sidx:
        res["status"] = "NO_PANEL_SYMBOL"; return res
    if end > panel_last:
        res["status"] = "CENSORED_IMMATURE"; res["hours_available"] = round((panel_last - start) / 3600.0, 3)
    col = sidx[s]; path = 1.0; n_ok = 0
    for k in range(NWIN):
        a, b = start + k * W4H, start + (k + 1) * W4H
        m = (rts > a) & (rts <= b)
        seg = ret5[m, col]
        if int(m.sum()) != 48 or not np.all(np.isfinite(seg)):
            if res["first_missing_window"] is None:
                res["first_missing_window"] = k
            if res["status"] is None:
                res["status"] = "CENSORED_INCOMPLETE"
            continue
        n_ok += 1
        if res["first_missing_window"] is None:
            path *= float(np.prod(1.0 + seg))
    res["n_windows_priced"] = n_ok
    if res["status"] is None:
        res["status"] = "PRICED"; res["path_return"] = path - 1.0
    return res


# ── 4. specs ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def run_spec(spec, snapshots, conf0, PNS, price_fn):
    conf = dict(conf0); state = {"counters": {}, "stopped": {}, "cooldown": {}}; events = []
    if spec == "V2":
        conf["consecutive_anchors"] = 1
    for A, snap, unk in snapshots:
        now = A + 3600
        before = set(state["stopped"])
        if spec == "V1":
            state, _ = evaluate_replica(snap, state, conf, now, denominator="entry")
        else:
            state, _ = PNS.evaluate({"positions_notional": snap["positions_notional"], "positions_unrealized": snap["positions_unrealized"]}, state, conf, now)
        for s in sorted(set(state["stopped"]) - before):
            v = float(snap["positions_notional"].get(s, 0.0)); side = 1.0 if v > 0 else -1.0
            den = abs(snap["positions_entry_notional"][s]) if spec == "V1" else abs(v)
            e = {"symbol": s, "anchor": A, "utc": U(A), "side": "long" if side > 0 else "short", "depth": snap["positions_unrealized"][s] / den, "notional": abs(v),
                 "entry_notional": snap["positions_entry_notional"].get(s)}
            for tag, off in (("primary_0_72h", 0), ("exit_aligned_4_76h", W4H)):
                fp = price_fn(A, s, off); e[tag] = fp
                e[tag]["avoided_pnl_usdt"] = (None if fp["path_return"] is None else -side * abs(v) * fp["path_return"])
            events.append(e)
    return events


def summarise(events):
    pr = [e for e in events if e["primary_0_72h"]["status"] == "PRICED"]
    vals = [e["primary_0_72h"]["avoided_pnl_usdt"] for e in pr]
    cens = collections.Counter(e["primary_0_72h"]["status"] for e in events if e["primary_0_72h"]["status"] != "PRICED")
    ex = [e for e in events if e["exit_aligned_4_76h"]["status"] == "PRICED"]; exv = [e["exit_aligned_4_76h"]["avoided_pnl_usdt"] for e in ex]
    return {"n_stops": len(events), "primary_0_72h": {"n_priced": len(pr), "censored": dict(cens), "avoided_pnl_sum_usdt": float(sum(vals)) if vals else None,
                                                       "avoided_pnl_median_usdt": float(np.median(vals)) if vals else None, "n_helped": int(sum(x > 0 for x in vals)), "frac_helped": (float(np.mean([x > 0 for x in vals])) if vals else None)},
            "exit_aligned_4_76h": {"n_priced": len(ex), "avoided_pnl_sum_usdt": float(sum(exv)) if exv else None, "n_helped": int(sum(x > 0 for x in exv)), "frac_helped": (float(np.mean([x > 0 for x in exv])) if exv else None)},
            "by_side": dict(collections.Counter(e["side"] for e in events))}


# ── 5. production triggers and the join ──────────────────────────────────────────────────────────────────────────────────────────────────────
def production_triggers(anchor_runs_path, t_from, t_to):
    """Names NEWLY present in phase_C per_name_stop.stopped (first appearance after absence), keyed by the 4h bucket of the phase_C log time (UTC)."""
    prev = set(); out = []
    for l in open(anchor_runs_path):
        if " phase_C: " not in l:
            continue
        try:
            tk = time.mktime(time.strptime(l[:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone
            d = json.loads(l.split(" phase_C: ", 1)[1]); p = d.get("per_name_stop")
        except Exception:
            continue
        if not isinstance(p, dict):
            continue
        cur = set(p.get("stopped") or [])
        for s in sorted(cur - prev):
            if t_from <= tk <= t_to:
                out.append({"symbol": s, "phase_C_utc": l[:19] + "Z", "bucket": int(tk // W4H * W4H), "bucket_utc": U(tk // W4H * W4H)})
        prev = cur
    return out


def match_production(prod, dev_events, snapshots, conf0):
    """Join on (symbol, bucket) exactly. For each production event: matched / near-miss (±1 bucket) / missed with a reason derived from the device's
    snapshot at that bucket. Device events with no production event are listed too."""
    dev = {(e["symbol"], e["anchor"]): e for e in dev_events}; snap_by = {A: (snap, unk) for A, snap, unk in snapshots}
    rows = []; matched = set()
    for p in prod:
        k = (p["symbol"], p["bucket"]); row = dict(p)
        if k in dev:
            row["status"] = "MATCHED"; matched.add(k)
        else:
            near = [b for b in (p["bucket"] - W4H, p["bucket"] + W4H) if (p["symbol"], b) in dev]
            if near:
                row["status"] = "NEAR_MISS_±1_bucket"; row["device_bucket_utc"] = U(near[0])
            else:
                row["status"] = "MISSED"
            sn = snap_by.get(p["bucket"])
            if sn is None:
                row["reason"] = "no device snapshot at bucket (no post_anchor readback)"
            else:
                snap, unk = sn; s = p["symbol"]
                if s in unk:
                    row["reason"] = "unknown basis at bucket (venue re-seat / missing fills)"
                elif s not in snap["positions_notional"]:
                    row["reason"] = "name not in readback at bucket"
                elif s in snap["positions_unrealized"]:
                    d = snap["positions_unrealized"][s] / abs(snap["positions_notional"][s]); row["device_depth_at_bucket"] = d
                    pv = snap_by.get(p["bucket"] - W4H); dp = None
                    if pv is not None and s in pv[0]["positions_unrealized"]:
                        dp = pv[0]["positions_unrealized"][s] / abs(pv[0]["positions_notional"][s]); row["device_depth_prev_bucket"] = dp
                    if d > float(conf0["depth_pct"]):
                        row["reason"] = "device depth %.3f > threshold %.2f" % (d, conf0["depth_pct"])
                    elif dp is not None and dp > float(conf0["depth_pct"]):
                        row["reason"] = "depth crossed at bucket (%.3f) but not at the previous bucket (%.3f): reconstructed basis shallower than the venue's" % (d, dp)
                    else:
                        row["reason"] = "depth crossed at bucket but consecutive-count/state differs"
                else:
                    row["reason"] = "no unrealised value at bucket"
        rows.append(row)
    dev_only = [{"symbol": e["symbol"], "bucket_utc": e["utc"], "depth": e["depth"]} for k, e in dev.items() if k not in matched]
    n_p = len(prod); n_m = len(matched); n_d = len(dev_events)
    return {"join_key": "(symbol, floor(time/4h)) exact; ±1 bucket reported as near-miss, not matched", "n_production": n_p, "n_device_V0": n_d, "n_matched": n_m,
            "recall": (n_m / n_p if n_p else None), "precision": (n_m / n_d if n_d else None), "production_events": rows, "device_only_events": dev_only,
            "note": "V1's events and V0's matched events are different populations; nothing here calibrates V1/V2 against production"}


# ── main ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def main():
    F, T, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
    REPO = os.path.expanduser("~/dl_quant_live"); WS = os.path.expanduser("~/wide_shadow")
    P = os.environ.get("PC3_PILOT_LOG") or f"{REPO}/state/live/pilot_log"; AR = os.environ.get("PC3_ANCHOR_RUNS") or f"{REPO}/state/anchor_runs.log"
    PNS_DIR = os.environ.get("PC3_PNS_DIR") or f"{REPO}/live"; ROLL = os.environ.get("PC3_ROLLING") or f"{WS}/state/rolling.npz"; SYMS = os.environ.get("PC3_SYMS") or f"{WS}/fea171/xfer_syms.npz"
    sys.path.insert(0, PNS_DIR); import per_name_stop as PNS
    days = sorted(d.split("/")[-1] for d in glob.glob(f"{P}/2026*") if F <= d.split("/")[-1] <= T)
    rows = lambda d, n: [json.loads(l) for l in open(f"{P}/{d}/{n}.jsonl") if l.strip()] if os.path.exists(f"{P}/{d}/{n}.jsonl") else []
    conf0 = dict(PNS.cfg(), enabled=True)
    fills = [r for d in days for r in rows(d, "fills")]; rb = [r for d in days for r in rows(d, "position_readback")]
    snapshots, walk = build_snapshots(fills, rb)
    anchors = [A for A, _, _ in snapshots]
    R = np.load(ROLL, allow_pickle=True); rts = R["ts"].astype(np.int64); ret5 = np.asarray(R["data"][:, :, 0], np.float64); panel_last = int(rts[-1])
    syms = [str(x) for x in np.load(SYMS, allow_pickle=True)["symbols"]]; sidx = {s: i for i, s in enumerate(syms)}
    price_fn = lambda A, s, off: forward_footprint(A, s, rts, ret5, sidx, panel_last, start_offset=off)
    # replica check: the replica with the CURRENT denominator must reproduce the production function state-by-state on V0 over the whole window
    st_p = {"counters": {}, "stopped": {}, "cooldown": {}}; st_r = dict(st_p); agree = 0; first_dis = None
    for A, snap, unk in snapshots:
        sn = {"positions_notional": snap["positions_notional"], "positions_unrealized": snap["positions_unrealized"]}
        st_p, _ = PNS.evaluate(sn, st_p, conf0, A + 3600); st_r, _ = evaluate_replica(snap, st_r, conf0, A + 3600, "current")
        if st_p == st_r:
            agree += 1
        elif first_dis is None:
            first_dis = U(A)
    replica_check = {"n_anchors": len(snapshots), "n_agree_bitwise": agree, "first_disagreement": first_dis, "trusted_for_V1": agree == len(snapshots)}
    out = {"device": "pc3_stop_counterfactual.py", "version": VERSION, "self_sha256": sha(os.path.abspath(__file__)), "evaluated_at_utc": time.strftime("%FT%TZ", time.gmtime()),
           "label": "生产持仓上的替代触发 + 静态持有价格足迹(诊断); 不是止损效果; 独立持仓反事实未做",
           "window": [days[0], days[-1]], "n_anchors": len(anchors), "conf_production": {k: conf0.get(k) for k in ("depth_pct", "consecutive_anchors", "cooloff_days", "min_notional_usdt", "_profile")},
           "inputs": {"pilot_log": P, "anchor_runs": AR, "per_name_stop_dir": PNS_DIR, "per_name_stop_sha256": sha(os.path.join(PNS_DIR, "per_name_stop.py")), "rolling_sha256": sha(ROLL), "rolling_last_row_utc": U(panel_last), "syms": SYMS},
           "basis_walk": walk, "unknown_basis_names_per_anchor_mean": float(np.mean([len(u) for _, _, u in snapshots])) if snapshots else None,
           "replica_check": replica_check, "specs": {}}
    if not replica_check["trusted_for_V1"]:
        out["specs"]["V1"] = {"status": "NOT_RUN: replica disagrees with the production function on V0", "replica_check": replica_check}
    for spec in ("V0", "V1", "V2"):
        if spec == "V1" and not replica_check["trusted_for_V1"]:
            continue
        ev = run_spec(spec, snapshots, conf0, PNS, price_fn)
        out["specs"][spec] = dict(summarise(ev), events=ev)
    t_from = time.mktime(time.strptime(days[0], "%Y%m%d")) - time.timezone; t_to = time.mktime(time.strptime(days[-1], "%Y%m%d")) - time.timezone + 86400
    prod = production_triggers(AR, t_from, t_to)
    out["production_match"] = match_production(prod, out["specs"]["V0"]["events"], snapshots, conf0)
    json.dump(out, open(OUT, "w"), indent=1, default=str)
    print("window", out["window"], "anchors", len(anchors), "| unknown-basis names/anchor", round(out["unknown_basis_names_per_anchor_mean"], 1), "| replica", replica_check, "| panel last", U(panel_last))
    for spec, v in out["specs"].items():
        if "events" not in v:
            print(spec, v["status"]); continue
        p = v["primary_0_72h"]; x = v["exit_aligned_4_76h"]
        print(f"{spec}: stops {v['n_stops']} | primary (A,A+72h]: priced {p['n_priced']} censored {p['censored']} sum {p['avoided_pnl_sum_usdt']} helped {p['n_helped']}/{p['n_priced']} | exit-aligned (A+4h,A+76h]: priced {x['n_priced']} sum {x['avoided_pnl_sum_usdt']} helped {x['n_helped']}/{x['n_priced']} | sides {v['by_side']}")
    m = out["production_match"]; print(f"production match: {m['n_matched']}/{m['n_production']} recall {m['recall']} precision {m['precision']} (device V0 {m['n_device_V0']})")
    for r in m["production_events"]:
        if r["status"] != "MATCHED": print("   ", r["bucket_utc"], r["symbol"], r["status"], r.get("reason", ""), r.get("device_bucket_utc", ""))


if __name__ == "__main__":
    main()

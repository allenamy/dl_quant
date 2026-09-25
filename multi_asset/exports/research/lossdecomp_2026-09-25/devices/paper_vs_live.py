#!/usr/bin/env python3
"""Paper vs live over the loss window (lead 2026-09-25, priority 1: strategy problem or execution problem?). READ-ONLY, pooled, no venue.
Prices: ONE source for both sides — the live producer's rolling cache (latest complete snapshot, sha recorded), return channel = nc_contract.rr_from_ch0
(ch0 + the snapshot's sparse boundary table; the same rr every NC consumer reads). Per post-anchor readback batch k (anchor A_k, read time t_k):
  target_usdt_i = w_i(target_live/A_k.json, sha recorded) / sum|w| x gross_mult(2.0) x NAV_k (daily_nav row nearest t_k)   [what the executor sizes]
  actual_usdt_i = venue_position_notional at readback k
  r_i           = rr-compounded return from the last 5m close <= t_k to the last 5m close <= t_{k+1}
  paper_k = sum target x r ; live_k = sum actual x r ; dev_k = live_k - paper_k = sum (actual - target) x r
  dev split by name category at k: STOP (name hit a per-name stop at or before t_k), HALT (the 09-24 16Z anchor, opening halted),
  UNTARGETED_HELD (actual != 0, target == 0: exits not completed), OTHER (partial / rejects / min_notional / withheld / sizing).
Also paper0 = same targets held anchor-to-anchor from the anchor time A_k (no execution delay), for the timing component.
Outputs PAPER_VS_LIVE.json + stdout table. usage: ~/wide_shadow/venv/bin/python paper_vs_live.py <out dir>"""
import json, os, sys, glob, hashlib, collections, time, calendar
import numpy as np

HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; L = f"{HOME}/dl_quant_live/state/live/pilot_log"
T_START, T_END = 1789562700 - 1800, 1790297100 + 3600
sys.path.insert(0, f"{WS}/fea171"); import nc_contract as NC
fmt = lambda t: time.strftime("%m-%dT%H:%MZ", time.gmtime(t))
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
STOPS = [("2026-09-17T04:44", ["ONEUSDT"]), ("2026-09-18T08:44", ["NEARUSDT"]), ("2026-09-18T12:45", ["GUSDT"]), ("2026-09-18T20:45", ["ARBUSDT"]),
         ("2026-09-19T08:44", ["STARUSDT"]), ("2026-09-19T12:45", ["ARUSDT", "ZAMAUSDT"]), ("2026-09-19T20:45", ["ENAUSDT"]), ("2026-09-21T12:46", ["PHAUSDT"]),
         ("2026-09-22T20:44", ["MINAUSDT"]), ("2026-09-23T00:46", ["BCHUSDT"]), ("2026-09-23T04:45", ["METUSDT", "TIAUSDT"]), ("2026-09-23T08:45", ["HUSDT"])]
STOP_T = {}
for t, ns in STOPS:
    for n in ns: STOP_T.setdefault(n, calendar.timegm(time.strptime(t, "%Y-%m-%dT%H:%M")))
HALT_ANCHOR = 1790265600


def jl(name):
    out = []
    for d in sorted(glob.glob(f"{L}/2026*")):
        if os.path.basename(d) < "20260916": continue
        p = f"{d}/{name}.jsonl"
        if os.path.exists(p): out += [json.loads(l) for l in open(p) if l.strip()]
    return out


def main():
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    snap = sorted(glob.glob(f"{WS}/state/snap/17*"))[-1]
    Z = np.load(f"{snap}/rolling.npz"); B = np.load(f"{snap}/boundary_raw.npz"); ts = Z["ts"].astype(np.int64)
    RR = NC.rr_from_ch0(ts, Z["data"][:, :, 0], B["ts"], B["col"], B["raw"]).astype(np.float64)
    syms = json.load(open(f"{WS}/shadow_bundle/config.json"))["symbols_panel"]; col = {s: j for j, s in enumerate(syms)}
    LP = np.vstack([np.zeros((1, RR.shape[1])), np.cumsum(np.log1p(np.nan_to_num(RR)), axis=0)])   # LP[i+1] = log price at close ts[i]
    def ret(s, tA, tB):
        j = col.get(s)
        if j is None: return None
        i0 = int(np.searchsorted(ts, tA, side="right")) - 1; i1 = int(np.searchsorted(ts, tB, side="right")) - 1
        if i0 < 0 or i1 < i0: return None
        return float(np.expm1(LP[i1 + 1, j] - LP[i0 + 1, j]))
    rec = {"price_source": {"snapshot": snap, "rolling_sha256": sha(f"{snap}/rolling.npz"), "boundary_sha256": sha(f"{snap}/boundary_raw.npz"),
                            "rows": [fmt(ts[0]), fmt(ts[-1])]}}
    P = jl("position_readback"); navs = sorted((r["nav_ts"], r["nav"]) for r in jl("daily_nav"))
    batches = collections.defaultdict(dict); rt = {}
    for p in P:
        a = float(p["anchor_ts"]); batches[a][p["symbol"]] = float(p.get("venue_position_notional") or 0.0)
        rt[a] = max(rt.get(a, 0.0), float(p.get("read_ts") or a))
    keys = [k for k in sorted(batches) if T_START <= rt[k] <= T_END and rt[k] <= ts[-1] + 300]
    tot = collections.defaultdict(float); rows = []; tl_used = {}; per_name_dev = collections.defaultdict(float)
    for a, b in zip(keys[:-1], keys[1:]):
        ta, tb = rt[a], rt[b]; A = int(a // 14400 * 14400)
        p = f"{WS}/state/target_live/{A}.json"
        if not os.path.exists(p): rows.append({"anchor": fmt(A), "skip": "no target_live"}); continue
        T = json.load(open(p)); w = T["weights"]; sw = sum(abs(v) for v in w.values()); tl_used[str(A)] = sha(p)
        nav = min(navs, key=lambda x: abs(x[0] - ta))[1]; G = 2.0 * nav
        tgt = {s: v / sw * G for s, v in w.items()}; act = batches[a]
        names = set(tgt) | set(act); paper = live = 0.0; cat = collections.defaultdict(float); miss = 0
        for s in names:
            r = ret(s, ta, tb)
            if r is None: miss += 1; continue
            tu, au = tgt.get(s, 0.0), act.get(s, 0.0); paper += tu * r; live += au * r; d = (au - tu) * r
            if A == HALT_ANCHOR: c = "HALT"
            elif s in STOP_T and STOP_T[s] <= ta: c = "STOP"
            elif tu == 0.0 and au != 0.0: c = "UNTARGETED_HELD"
            else: c = "OTHER"
            cat[c] += d; per_name_dev[s] += d
        # paper0: same target from the anchor time to the next anchor time
        p0 = 0.0
        for s, tu in tgt.items():
            r0 = ret(s, A, A + 14400)
            if r0 is not None: p0 += tu * r0
        row = {"anchor": fmt(A), "t_from": fmt(ta), "t_to": fmt(tb), "nav": round(nav, 2), "paper": paper, "live": live, "dev": live - paper, "paper0_anchor_time": p0,
               "dev_by_cat": dict(cat), "names_without_price": miss}
        rows.append(row)
        for k in ("paper", "live", "dev", "paper0_anchor_time"): tot[k] += row[k]
        for k, v in cat.items(): tot["dev_" + k] += v
    rec.update({"intervals": rows, "totals": dict(tot), "target_live_sha256": tl_used, "stop_times": {k: fmt(v) for k, v in STOP_T.items()},
                "worst_dev_names": sorted(((s, round(v, 2)) for s, v in per_name_dev.items()), key=lambda x: x[1])[:15],
                "best_dev_names": sorted(((s, round(v, 2)) for s, v in per_name_dev.items()), key=lambda x: -x[1])[:10]})
    json.dump(rec, open(f"{out}/PAPER_VS_LIVE.json", "w"), indent=1)
    print(f"{'anchor':12s} {'paper@exec':>10s} {'live(rr)':>10s} {'dev':>9s} {'paper@A':>10s}   dev by category")
    day = collections.defaultdict(lambda: collections.defaultdict(float))
    for r in rows:
        if "skip" in r: print(r); continue
        print(f"{r['anchor']:12s} {r['paper']:10.1f} {r['live']:10.1f} {r['dev']:9.1f} {r['paper0_anchor_time']:10.1f}   " + " ".join(f"{k}:{v:.0f}" for k, v in r["dev_by_cat"].items() if abs(v) >= 1))
        for k in ("paper", "live", "dev", "paper0_anchor_time"): day[r["t_to"][:5]][k] += r[k]
    print("\nDAILY:"); [print(" ", d, {k: round(v, 1) for k, v in day[d].items()}) for d in sorted(day)]
    print("\nTOTALS:", {k: round(v, 2) for k, v in tot.items()})
    print("worst deviation names:", rec["worst_dev_names"][:10]); print("best deviation names:", rec["best_dev_names"][:10])


if __name__ == "__main__":
    main()

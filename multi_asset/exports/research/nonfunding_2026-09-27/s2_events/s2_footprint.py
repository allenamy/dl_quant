#!/usr/bin/env python3
"""s2_footprint.py — S2 step 1 (DECISION_RULE_nonfunding_sources_2026-09-27 §0-3 / §2): ZERO-RETURN footprint of the in-service book on
exchange events. Committed before it is run; reads no return of any kind.

Events: census_events_f991bc80.jsonl (L3 census, copied into the repo; sha asserted), types D_upbit_krw_listing and
B_binance_monitoring_tag_ADD. Book: the in-service NC combo targets, scaled_diagnostic (the engine's main reading), seeds 42 / 2027 / 7
(production-parity archives for 42 and 2027; dlarch's reference cell combo for 7). HELD book at anchor A = the last PUBLISHED target at
or before A (trade_mask False = hold contracts, so the held target is carried).

For every event with a USDT perp symbol: A* = the last anchor <= publish_s ("the last anchor before the event"). held weight w = held
target[A*, symbol]. Also recorded: publish - A* in minutes (an event published inside A*'s decision window, < 24 min after A*, meets the
book that A* was about to trade, named but kept).
Denominators, all reported (the rule's "events" = D3, written before any number):
  D0 all events of the type | D1 with a USDT perp symbol at publish | D2 D1 and A* inside the combo axis (2023-01-01 .. axis end) |
  D3 D2 and the symbol is a column of the combo (can be held at all).
Coverage = #(D3 events with |w| > 1e-9) / #D3, per seed, per type, per segment (pre-2026 = publish < 2026-01-01; 2026 after).
Rule §0-3: coverage < 20% (mean over seeds) => S2 is tested only as an event RETURN source; the verdict line says which.
usage: /workspace/venv/bin/python -B s2_footprint.py <census.jsonl> <out.json>
"""
import os, sys, json, hashlib, time, calendar
import numpy as np
CENSUS_SHA = "f991bc80966ad0b6"
NC = {42: "/dev/shm/news2_2026-09-23/work/combo_s42", 2027: "/dev/shm/news2_2026-09-23/work/combo_s2027", 7: "/workspace/dlarch_2026-09-24/chain/ref_nc_s7X/work/combo_s7"}
TYPES = ("D_upbit_krw_listing", "B_binance_monitoring_tag_ADD")
Y26 = calendar.timegm((2026, 1, 1, 0, 0, 0))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def main():
    cp, out = sys.argv[1], sys.argv[2]
    assert sha(cp).startswith(CENSUS_SHA), "census sha"
    ev = [json.loads(l) for l in open(cp)]
    rec = {"device": "s2_footprint.py", "self_sha256": sha(os.path.abspath(__file__)), "census_sha256": sha(cp),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "zero_returns": True, "combos": {}, "by_type": {}, "events": []}
    books = {}
    for s, d in NC.items():
        p = f"{d}/scaled_diagnostic.npz"; z = np.load(p); rec["combos"][str(s)] = {"path": p, "sha256": sha(p)}
        W = z["weights"]; tm = z["trade_mask"]; held = np.zeros_like(W); cur = np.zeros(W.shape[1])
        for i in range(len(tm)):
            if tm[i]: cur = W[i]
            held[i] = cur
        books[s] = {"A": z["E_ts"].astype(np.int64), "held": held, "col": {str(x): j for j, x in enumerate(z["symbols"])}}
    A = books[42]["A"]
    for s in books: assert np.array_equal(books[s]["A"], A)
    for t in TYPES:
        E = [e for e in ev if e["type"] == t]
        cnt = {"D0": len(E), "D1": 0, "D2": 0, "D3": 0}; held_by = {str(s): {"pre2026": [0, 0], "2026": [0, 0]} for s in NC}
        side = {str(s): {"long": 0, "short": 0} for s in NC}
        for e in E:
            if not e.get("symbol"): continue
            cnt["D1"] += 1
            ps = int(e["publish_s"]); i = int(np.searchsorted(A, ps, side="right")) - 1
            if i < 0 or ps - A[i] >= 14400: continue
            cnt["D2"] += 1
            if e["symbol"] not in books[42]["col"]: continue
            cnt["D3"] += 1; seg = "2026" if ps >= Y26 else "pre2026"
            row = {"type": t, "symbol": e["symbol"], "publish_utc": e["publish_utc"], "anchor_utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(A[i]))),
                   "min_after_anchor": round((ps - A[i]) / 60, 1), "segment": seg, "w": {}}
            for s in NC:
                w = float(books[s]["held"][i, books[s]["col"][e["symbol"]]]); row["w"][str(s)] = w
                held_by[str(s)][seg][1] += 1
                if abs(w) > 1e-9:
                    held_by[str(s)][seg][0] += 1; side[str(s)]["long" if w > 0 else "short"] += 1
            rec["events"].append(row)
        cov = {s: (sum(v[0] for v in held_by[s].values()) / max(cnt["D3"], 1)) for s in held_by}
        mean_cov = float(np.mean(list(cov.values())))
        rec["by_type"][t] = {"denominators": cnt, "held_counts_by_seed_segment_[held,of]": held_by, "held_side_by_seed": side,
                             "coverage_by_seed": cov, "coverage_mean_over_seeds": mean_cov,
                             "S2_use": ("EVENT_RETURN_SOURCE_ONLY (coverage < 20%)" if mean_cov < 0.20 else "GATE_AND_RETURN_SOURCE (coverage >= 20%)")}
        print(f"S2_FOOTPRINT {t}: D0 {cnt['D0']} D1 {cnt['D1']} D2 {cnt['D2']} D3 {cnt['D3']} coverage {json.dumps({k: round(v, 3) for k, v in cov.items()})} "
              f"-> {rec['by_type'][t]['S2_use']} sides {json.dumps(side)}", flush=True)
    json.dump(rec, open(out + ".tmp", "w"), indent=1); os.replace(out + ".tmp", out)
    assert json.load(open(out))["self_sha256"] == rec["self_sha256"]
    print("S2_FOOTPRINT DONE", sha(out)[:16], flush=True)


if __name__ == "__main__":
    main()

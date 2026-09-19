#!/usr/bin/env python3
"""replay_exec 2026-09-19 · diagnostic (not a gate): how far the simulator's price chain (producer rolling.npz ret5 chained from the first
executor-recorded mid, simlib.Panel) is from the executor's OWN recorded mids, and what that costs on the LIVE book.

  1 clipped bars   rows of rolling.npz channel 0 with |ret5| ≥ 0.2999 (the producer panel is hard-clipped at ±0.30, like the
                   research 5m cache — E-0908-B family); a clipped bar leaves the chain permanently off by the missing move.
  2 level error    |chain(near_b(anchor_ts)) / mid_at_anchor − 1| over every recorded mid of anchors 08-26 00Z .. 09-18 20Z.
  3 P&L cost       per consecutive anchor pair (A, A+4h) inside a period: Σ_live positions q·P_chain(A)·(r_chain − r_mid), the
                   price P&L the chain gets wrong on the executor's REAL book (positions = the readback at the window t0 of A).
                   Mid-to-mid returns include spread noise, so this is an upper-bound-flavoured description, not an exact error.
usage: diag_price_chain_v3.py <out.json> [mirror]
"""
import collections, json, os, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import simlib as L
import v1b_gate as G


def main():
    out_p = sys.argv[1]
    M = L.Mirror(sys.argv[2] if len(sys.argv) > 2 else L.MIRROR_DEFAULT)
    L.install_readonly_guard()
    assert not M.verify_manifest()
    P = L.Panel(M); L.build_references(M, P)
    R = np.load(os.path.join(M.root, "producer", "rolling.npz"), allow_pickle=True)
    ret = np.asarray(R["data"][:, :, 0], float)
    clipped = [{"symbol": P.syms[j], "bar_end_utc": L.U(P.ts[k]), "ret5": float(ret[k, j])} for k, j in zip(*np.where(np.abs(ret) >= 0.2999))]
    an = M.anchor_rows()
    mids = {}
    for A, r in sorted(an.items()):
        v = r.get("mid_at_anchor_vector"); v = json.loads(v) if isinstance(v, str) else (v or {})
        mids[A] = (float(r["anchor_ts"]), {s: float(m) for s, m in v.items() if m})
    dev = []
    for A, (t, v) in mids.items():
        if not (L.A_V1_FIRST <= A <= L.A_V1_LAST):
            continue
        b = L.near_b(t)
        if b > P.t_last:
            continue
        for s, m in v.items():
            if s in P.ref:
                dev.append(abs(P.px(s, b) / m - 1.0))
    dev = np.array(dev)
    W, _ = L.live_windows()
    rb = collections.defaultdict(dict)
    for r in M.range_rows("position_readback"):
        q = float(r["venue_position_qty"])
        if q:
            rb[round(float(r["read_ts"]))][r["symbol"]] = q
    pnl = {}
    for label in ("CAL", "HOLDOUT"):
        p = G.PERIODS[label]; rows = []
        for A1 in range(p["first_anchor"], p["last_anchor"] + 1, 14400):
            A2 = A1 + 14400
            if A1 not in mids or A2 not in mids:
                continue
            w = [w for w in W if L.nominal(w["t0"]) == A1]
            if not w:
                continue
            (t1, m1), (t2, m2) = mids[A1], mids[A2]
            b1, b2 = L.near_b(t1), L.near_b(t2)
            if b2 > P.t_last:
                continue
            e = 0.0
            for s, q in rb.get(round(w[0]["t0"]), {}).items():
                if s in P.ref and s in m1 and s in m2:
                    c1, c2 = P.px(s, b1), P.px(s, b2)
                    e += q * c1 * (c2 / c1 - m2[s] / m1[s])
            rows.append((L.UA(A1), e))
        x = np.abs([e for _, e in rows])
        pnl[label] = {"n_pairs": len(rows), "mean_abs_usdt": float(x.mean()), "p50_abs_usdt": float(np.median(x)),
                      "p90_abs_usdt": float(np.percentile(x, 90)), "max_abs_usdt": float(x.max()),
                      "worst": sorted(rows, key=lambda r: -abs(r[1]))[:5]}
    doc = {"device": "diag_price_chain_v3.py", "device_sha256": L.sha_file(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "rerun": f"cd {os.path.relpath(HERE, L.REPO)} && /usr/bin/python3 diag_price_chain_v3.py {os.path.basename(out_p)}",
           "inputs_sha256": L.input_shas(M), "clipped_bars": clipped, "n_clipped_bars": len(clipped),
           "chain_vs_executor_mid_level": {"n_mids": int(len(dev)), "p50": float(np.median(dev)), "p90": float(np.percentile(dev, 90)),
                                           "p99": float(np.percentile(dev, 99)), "max": float(dev.max()), "share_gt_1pct": float((dev > 0.01).mean())},
           "live_book_price_pnl_chain_minus_mid": pnl}
    with open(out_p + ".part", "w") as fh:
        json.dump(doc, fh, indent=1)
    os.replace(out_p + ".part", out_p)
    print(json.dumps({k: doc[k] for k in ("n_clipped_bars", "chain_vs_executor_mid_level", "live_book_price_pnl_chain_minus_mid")}, indent=1))


if __name__ == "__main__":
    main()

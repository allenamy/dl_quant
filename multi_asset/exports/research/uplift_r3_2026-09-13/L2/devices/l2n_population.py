#!/usr/bin/env python3
"""l2n_population.py — S1 step 1 (AMENDMENT_L2_NC_population_2026-09-27 §1, §4 rows 3/9/+1). ZERO RETURNS: reads combo targets, legs
(ZFD / WL / RN8 / KZ never used as targets), the TRD-01 W24H mask, the A0 population files and the archive listing; never y4 / META.

P_all^NC(i, k) = held NC target[i, n] < -1e-12 AND masked fund seat w2m(i) > 1e-12 AND legs.ZFD[i, n] < 0 AND tradable_W24H[i, n],
seeds k in {42, 2027}; held = last PUBLISHED scaled_diagnostic target at or before i (trade_mask False = hold). Axis = NC combo axis
(2023-01-01 ..) cut at L2's UB 2026-08-30T20Z.
Outputs:
  out/L2N_population_s{42,2027}.npz  {ts, symbols, P}
  receipts/RECEIPT_L2N_population.json  per-year counts, empty-population anchors (w2m == 0), and the A0 vs NC overlap per seed and year
  (pairs: |A0|, |NC|, |A0 & NC|, share of A0, share of NC, Jaccard, anchors where both are non-empty), plus the NC need-set of
  (symbol, UTC day) for the L2 label windows [E - 24h - 15 min, E - 10 min] (the l2_b_pull.py rule) intersected with the archive listing,
  and the subset NOT already attempted by the A0 pull (the re-pull list).
usage: /workspace/venv/bin/python -B l2n_population.py
"""
import os, sys, json, time, hashlib, calendar
import numpy as np
L2 = "/workspace/uplift_r3_2026-09-13/L2"; OUT = f"{L2}/out"; REC = f"{L2}/receipts"
COMBO = {"42": "/dev/shm/news2_2026-09-23/work/combo_s42/scaled_diagnostic.npz", "2027": "/dev/shm/news2_2026-09-23/work/combo_s2027/scaled_diagnostic.npz"}
LEGS = "/dev/shm/news2_2026-09-23/work/legs.npz"; LEGS_SHA16 = "9ee5886f37d1727c"
TRD = "/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz"
A0POP = {k: f"{OUT}/L2_A_population_s{k}.npz" for k in ("42", "2027")}
LISTING = f"{OUT}/L2_A_listing.json"; METRICS = f"{OUT}/metrics"
UB = calendar.timegm((2026, 8, 30, 20, 0, 0)); DAY = 86400; DUST = 1e-12


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def year(t): return time.gmtime(int(t)).tm_year


def main():
    L = np.load(LEGS); assert sha(LEGS).startswith(LEGS_SHA16)
    la = L["E_ts"].astype(np.int64); lsym = [str(x) for x in L["symbols"]]
    WL = L["WL"].astype(np.float64); den = WL[:, 0] + WL[:, 2]; w2m = np.where(den > 1e-12, WL[:, 2] / np.where(den > 1e-12, den, 1), 0.5)
    ZFD = L["ZFD"]
    T = np.load(TRD); assert np.array_equal(T["ts"].astype(np.int64), la) and [str(x) for x in T["symbols"]] == lsym
    rec = {"device": "l2n_population.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "zero_returns": True, "inputs": {"legs": sha(LEGS), "trd_w24h": sha(TRD), **{f"combo_s{k}": sha(p) for k, p in COMBO.items()},
                                            **{f"A0pop_s{k}": sha(p) for k, p in A0POP.items()}, "listing": sha(LISTING)},
           "definition": "held NC target < 0 & w2m > 0 & ZFD < 0 & TRD-01 W24H tradable", "per_seed": {}}
    listed = {s: set(calendar.timegm(time.strptime(d, "%Y-%m-%d")) // DAY for d in v["zip_dates"]) for s, v in json.load(open(LISTING)).items()}
    need = {}
    for k, p in COMBO.items():
        z = np.load(p); ca = z["E_ts"].astype(np.int64); assert [str(x) for x in z["symbols"]] == lsym
        W = z["weights"]; tm = z["trade_mask"]; held = np.zeros_like(W); cur = np.zeros(W.shape[1])
        for i in range(len(tm)):
            if tm[i]: cur = W[i]
            held[i] = cur
        keep = ca <= UB; ca = ca[keep]; held = held[keep]
        pos = np.searchsorted(la, ca); assert np.array_equal(la[pos], ca)
        P = (held < -DUST) & (w2m[pos] > 1e-12)[:, None] & (np.nan_to_num(ZFD[pos], nan=0.0) < 0) & T["mask"][pos]
        np.savez_compressed(f"{OUT}/L2N_population_s{k}.npz", ts=ca, symbols=np.array(lsym), P=P)
        A0 = np.load(A0POP[k]); at = A0["ts"].astype(np.int64); assert [str(x) for x in A0["symbols"]] == lsym
        common = np.intersect1d(ca, at); ic = np.searchsorted(ca, common); ia = np.searchsorted(at, common)
        Pn, Pa = P[ic], A0["P"][ia]
        yr = np.array([year(t) for t in common]); ov = {}
        for y in list(np.unique(yr)) + ["all"]:
            m = np.ones(len(common), bool) if y == "all" else (yr == y)
            a_, n_ = Pa[m], Pn[m]; inter = int((a_ & n_).sum()); na, nn = int(a_.sum()), int(n_.sum())
            ov[str(y)] = {"anchors": int(m.sum()), "pairs_A0": na, "pairs_NC": nn, "pairs_both": inter,
                          "share_of_A0": inter / na if na else None, "share_of_NC": inter / nn if nn else None,
                          "jaccard": inter / (na + nn - inter) if (na + nn - inter) else None,
                          "anchors_both_nonempty": int((a_.any(1) & n_.any(1)).sum()), "anchors_A0_nonempty": int(a_.any(1).sum()), "anchors_NC_nonempty": int(n_.any(1).sum())}
        cy = np.array([year(t) for t in ca])
        rec["per_seed"][k] = {"anchors": int(len(ca)), "first": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(ca[0]))), "last": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(ca[-1]))),
                              "names_per_anchor_median_nonempty": float(np.median(P.sum(1)[P.any(1)])) if P.any() else 0.0,
                              "empty_population_anchors": int((~P.any(1)).sum()), "empty_because_w2m_zero": int((w2m[pos] <= 1e-12).sum()),
                              "pairs_by_year": {str(y): int(P[cy == y].sum()) for y in np.unique(cy)}, "overlap_A0_vs_NC": ov,
                              "out": f"{OUT}/L2N_population_s{k}.npz", "out_sha256": sha(f"{OUT}/L2N_population_s{k}.npz")}
        lo = (ca - DAY - 900) // DAY; hi = (ca - 600) // DAY
        for n in np.flatnonzero(P.any(0)):
            S = need.setdefault(lsym[n], set())
            for i in np.flatnonzero(P[:, n]): S.update(range(int(lo[i]), int(hi[i]) + 1))
        print(f"L2N_POP s{k}: anchors {len(ca)} median names {rec['per_seed'][k]['names_per_anchor_median_nonempty']} overlap(all) {json.dumps(ov['all'])}", flush=True)
    attempted = {}
    for s in need:
        p = f"{METRICS}/{s}.npz"
        attempted[s] = set(int(d) for d in np.load(p)["file_day"]) if os.path.exists(p) else set()
    need_listed = {s: sorted(v & listed.get(s, set())) for s, v in need.items()}
    repull = {s: sorted(set(v) - attempted[s]) for s, v in need_listed.items() if set(v) - attempted[s]}
    rec["need_set"] = {"symbols": len(need), "symbol_days": int(sum(len(v) for v in need.values())),
                       "symbol_days_listed": int(sum(len(v) for v in need_listed.values())),
                       "not_in_listing": int(sum(len(v - listed.get(s, set())) for s, v in need.items())),
                       "already_attempted_by_A0_pull": int(sum(len(set(v) & attempted[s]) for s, v in need_listed.items())),
                       "repull_symbols": len(repull), "repull_symbol_days": int(sum(len(v) for v in repull.values())),
                       "symbols_with_no_A0_file": sorted(s for s in need if not attempted[s])}
    jp = f"{OUT}/L2N_repull_list.json"; json.dump({s: v for s, v in repull.items()}, open(jp, "w")); rec["need_set"]["repull_list"] = jp; rec["need_set"]["repull_list_sha256"] = sha(jp)
    json.dump(rec, open(f"{REC}/RECEIPT_L2N_population.json.tmp", "w"), indent=1); os.replace(f"{REC}/RECEIPT_L2N_population.json.tmp", f"{REC}/RECEIPT_L2N_population.json")
    assert json.load(open(f"{REC}/RECEIPT_L2N_population.json"))["self_sha256"] == rec["self_sha256"]
    print("L2N_POP DONE", json.dumps({k: v for k, v in rec["need_set"].items() if k != "symbols_with_no_A0_file"}), sha(f"{REC}/RECEIPT_L2N_population.json")[:16], flush=True)


if __name__ == "__main__":
    main()

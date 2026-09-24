#!/usr/bin/env python3
"""b7_descriptive_diag.py — POST-HOC, DESCRIPTIVE, NON-GATING companion to b7_compare.py (written AFTER the B7 verdict line was read).
It changes nothing about the frozen B7 rule or verdict (B7_PARITY.json is an input, read only). It answers three descriptive questions:
  D1  how large is the positive control's disagreement (certified β at 2026-09-18T20Z vs kline-rebuilt β), as a distribution, and which
      names carry the tail (public price data, not execution data);
  D2  at book level, how is the gap Σ t_i·(β_res_i − β_prod_i) distributed — POOLED shares only (blind rule): share from the layer-(i)
      >1% names, share from names whose production n_obs < 180, share from the rest; Σ|t_i·Δβ_i|; and a scale reference for the
      instrument: the control's per-name disagreement propagated with today's targets (Σ t_i·δctrl_i, Σ|t_i|·|δctrl_i|), both as a share
      of |β_exec record|. δctrl is measured at a DIFFERENT anchor (18T20Z); this is a scale reference, not an error bound;
  D3  STGUSDT (watchdog local stop 12:48:39Z): is it in the non-zero target set at each anchor, and its share of the gap (0 if not).
Blind state: orders copy is read only for (anchor_ts, symbol, target_w); nothing per name about execution is printed or written except
STGUSDT's membership (asked by the lead) — every other execution-derived number is a pooled sum.
usage: /usr/bin/python3 -B b7_descriptive_diag.py <inputs_dir> <b7_out_dir> <out_json>
"""
import csv, hashlib, json, os, sys, time
import numpy as np

H4 = 14400
A08, A12 = 1790236800, 1790251200


def sha_file(p):
    with open(p, "rb") as f: return hashlib.sha256(f.read()).hexdigest()


def qs(x):
    x = np.asarray(x, float)
    if x.size == 0: raise ValueError("empty sequence")
    return {"n": int(x.size), "p50": float(np.quantile(x, .5)), "p90": float(np.quantile(x, .9)), "p99": float(np.quantile(x, .99)), "max": float(x.max())}


def main():
    inp, bo, outp = [os.path.abspath(a) for a in sys.argv[1:4]]
    P = json.load(open(os.path.join(bo, "B7_PARITY.json")))
    out = {"device": "b7_descriptive_diag.py", "self_sha256": sha_file(os.path.abspath(__file__)), "status": "POST-HOC DESCRIPTIVE, NON-GATING",
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "inputs": {"B7_PARITY.json": sha_file(os.path.join(bo, "B7_PARITY.json")), "B7_PER_NAME.csv": sha_file(os.path.join(bo, "B7_PER_NAME.csv")),
                      "B7_CONTROL_per_name.csv": sha_file(os.path.join(bo, "B7_CONTROL_per_name.csv")),
                      "orders_copy": sha_file(os.path.join(inp, "orders_20260924.jsonl")), "anchors_copy": sha_file(os.path.join(inp, "anchors_20260924.jsonl"))}}
    # D1
    C = list(csv.DictReader(open(os.path.join(bo, "B7_CONTROL_per_name.csv"))))
    dctl = {r["symbol"]: float(r["beta_klines"]) - float(r["beta_certified"]) for r in C if r["ua_in_certified_window"] == "False"}
    ad = np.abs(np.array(list(dctl.values())))
    top = sorted(C, key=lambda r: -float(r["abs_diff"]))[:8]
    out["D1_control"] = {"abs_dbeta": qs(ad), "n_over_1e-6": int((ad > 1e-6).sum()), "n_over_1e-4": int((ad > 1e-4).sum()), "n_over_1e-3": int((ad > 1e-3).sum()),
                         "signed_mean_dbeta": float(np.mean(list(dctl.values()))),
                         "top8": [{"symbol": r["symbol"], "beta_certified": float(r["beta_certified"]), "beta_klines": float(r["beta_klines"]), "abs_diff": float(r["abs_diff"])} for r in top]}
    # layer-(i) per-name table
    N = list(csv.DictReader(open(os.path.join(bo, "B7_PER_NAME.csv"))))
    pn = {(r["anchor"], r["symbol"]): r for r in N}
    ords = []
    for l in open(os.path.join(inp, "orders_20260924.jsonl")):
        o = json.loads(l); ords.append((o.get("anchor_ts"), o.get("symbol"), o.get("target_w")))
    A_rows = [json.loads(l) for l in open(os.path.join(inp, "anchors_20260924.jsonl"))]
    out["D2_gap_pooled"] = {}; out["D3_STGUSDT"] = {}
    for A, lab in ((A08, "A08"), (A12, "A12")):
        li = P["per_anchor"][lab]["layer_ii"]; rec = li["record"]
        row = [r for r in A_rows if int(float(r["anchor_ts"]) // H4 * H4) == A]; assert len(row) == 1
        ats = row[0]["anchor_ts"]; G = float(rec["book_gross_usdt"]); be = float(rec["beta_exec_usdt"])
        tw = {}
        for a_ts, s, w in ords:
            if a_ts == ats and w is not None: tw[s] = float(w)
        nz = {s: w * G for s, w in tw.items() if w != 0.0}
        assert len(nz) == rec["n_targeted_names"], "closure c2 not reproduced"
        over = {o["symbol"] for o in P["per_anchor"][lab]["layer_i"]["rel_over_1pct"]}
        contrib = {}
        for s, t in nz.items():
            if s == "BTCUSDT": contrib[s] = 0.0; continue
            r = pn[(lab, s)]; contrib[s] = t * (float(r["beta_res"]) - float(r["beta_prod"]))
        gap = sum(contrib.values())
        assert abs(gap - (li["beta_exec_usdt_research"] - be)) <= 1e-6 * max(1.0, abs(gap)), "gap does not reproduce B7_PARITY"
        short = {s for s in nz if s != "BTCUSDT" and int(pn[(lab, s)]["n_obs_prod"]) < 180}
        g_over = sum(v for s, v in contrib.items() if s in over)
        g_short = sum(v for s, v in contrib.items() if s in short and s not in over)
        g_rest = gap - g_over - g_short
        ab = np.array([abs(v) for v in contrib.values()])
        srt = np.sort(ab)[::-1]
        ctl_names = [s for s in nz if s in dctl]
        prop_signed = sum(nz[s] * dctl[s] for s in ctl_names)
        prop_abs = sum(abs(nz[s]) * abs(dctl[s]) for s in ctl_names)
        out["D2_gap_pooled"][lab] = {
            "beta_exec_record_usdt": be, "beta_exec_research_usdt": li["beta_exec_usdt_research"], "gap_usdt": gap,
            "gap_over_book_gross": gap / G, "record_over_book_gross": be / G,
            "n_targeted": len(nz), "n_targeted_in_over1pct_list": len(over & set(nz)), "n_targeted_with_prod_nobs_lt_180": len(short),
            "share_of_gap_from_over1pct_names": g_over / gap, "share_of_gap_from_nobs_lt_180_names_not_in_list": g_short / gap,
            "share_of_gap_from_rest": g_rest / gap,
            "sum_abs_contrib_usdt": float(ab.sum()), "net_over_sum_abs": gap / float(ab.sum()),
            "top1_top5_top20_abs_contrib_share_of_sum_abs": [float(srt[:k].sum() / ab.sum()) for k in (1, 5, 20)],
            "ctrl_scale_ref": {"n_targeted_with_ctrl": len(ctl_names), "signed_usdt": prop_signed, "signed_over_abs_record": prop_signed / abs(be),
                               "abs_usdt": prop_abs, "abs_over_abs_record": prop_abs / abs(be),
                               "note": "δctrl measured at 2026-09-18T20Z (different window); scale reference only, not an error bound"}}
        stg_t = "STGUSDT" in nz
        out["D3_STGUSDT"][lab] = {"in_nonzero_target_set": stg_t, "share_of_gap": (contrib["STGUSDT"] / gap) if stg_t else 0.0,
                                  "layer_i_rel": float(pn[(lab, "STGUSDT")]["rel_diff"]) if (lab, "STGUSDT") in pn and pn[(lab, "STGUSDT")]["rel_diff"] else None,
                                  "n_obs_prod": int(pn[(lab, "STGUSDT")]["n_obs_prod"]) if (lab, "STGUSDT") in pn else None}
    json.dump(out, open(outp, "w"), indent=1)
    print("B7_DIAG DONE (descriptive, non-gating)", "out_sha256=" + sha_file(outp), flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""d10_lineD_read.py -- the reading of the line D funding-only control cell, by the FROZEN rule
(docs/PLAN_funding_only_control_cell_2026-09-26.md R1.3, frozen by lead c5cfeb5e5; closure definition per lead's ruling on
news2's 20:1xZ question: lead ruled 2026-09-27 02:2xZ, quoted in CLOSURE_DEFINITION below). Written and committed BEFORE the cell's engine output exists.

Judge: the frozen news_stats.py (sha 7141ba42) imported and initialised exactly as dlarch_cell_retain.load_frozen does (never forked).
All three cells are read from their RETAIN small series (dlarch_cell_retain schema): the D10 cell, DLARCH_REF_NC_s42X (in-service
NC s42 on the X axis) and DLARCH_T0_s42 (T0 reference column). Same anchor axis asserted.

Per segment (frozen SEG: pre2026 = 2023-06-30T04Z..2025-12-31T20Z; 2026 = 2026-01-01..2026-08-31T00Z, which is exactly the reading
window < 2026-09-01T02Z) and per base (NC = the column the implication reads; T0 = reference column):
  D           = 1e4 * mean over full days of the frozen dbar (daily compounded NAV return, path-mean of paired differences), bps/day
  SE_MBB30    = 1e4 * std of the block-bootstrap means of that daily series (BT.mbb_indices, 30-day blocks, B = 10,000, rng (20260923,1))
  ci95        = the frozen boot(x, 30)["ci95_bps"]
  resolvable  = |D| >= 3 * SE_MBB30  -> "本段可分辨" else "本段分辨不出"   (descriptive, not an admission gate)
  channels    = additive daily sums of gm * {pnl, car, cst, unk} (bps of NAV), paired differences, path mean, over the same full days
  closure     = |additive total (gm * g) - (pnl - car - cst - unk)| <= 1e-6 bps/day per segment per column, else CLOSURE_FAIL (no verdict)
  compounding = D - additive total, reported on its own line, never folded into a channel
Also: turnover (tau), hold / halt anchors, and the input-side / model-layer profile read from the stage receipts given on argv.
Pre-declared implication (R1.3): if the 2026 D vs NC < 0 AND its ci95 upper bound < 0 -> the October plan must ship "producer on the
D10 rule" and "retrain on the new features" in ONE release; otherwise no change to the October plan. The verdict line never uses
"adopt / deploy / PASS / harmful / beneficial".
usage: d10_lineD_read.py --engine DIR --cell-ser NPZ --nc-ser NPZ --t0-ser NPZ --profile JSON[,JSON...] --out OUT.json
"""
import argparse, hashlib, json, os, sys
import numpy as np

JUDGE_SHA = "7141ba42ab227b9f35b48acce62d5e2a2494f364fdf6a83189974cb2af67e03c"
CLOSURE_TOL = 1e-6
CLOSURE_DEFINITION = ("lead ruling 2026-09-27 02:2xZ: closure is checked on ADDITIVE daily sums, |gm*g additive total - (pnl - car - cst - unk)| <= 1e-6 bps/day per segment per column; the headline D stays the compounded frozen dbar; the compounding term is reported on its own line")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def load(engine):
    sys.path.insert(0, engine)
    assert sha(os.path.join(engine, "news_stats.py")) == JUDGE_SHA, "frozen judge moved"
    import news_stats as NS, bt_tables as BT, bt_driver_lib as DL
    NS.BT, NS.DL = BT, DL
    for f, want in NS.DEV.items(): assert sha(os.path.join(engine, f)) == want, f"frozen dependency {f} moved"
    return NS, BT


def ser(p):
    Z = np.load(p); A = Z["anchors"].astype(np.int64)
    return A, {k: Z[f"{k}_per_path"] for k in ("r", "pnl", "car", "cst", "unk", "g", "tau", "hold", "halt")}


def day_sum(A, X, m, days):
    """(npath, ndays) sums over the anchors of each full day inside the mask."""
    d = (A[m] // 86400) * 86400; pos = np.searchsorted(days, d); ok = (pos < len(days)) & (days[np.minimum(pos, len(days) - 1)] == d)
    out = np.zeros((X.shape[0], len(days)))
    np.add.at(out.T, pos[ok], X[:, m][:, ok].T)
    return out


def main():
    ap = argparse.ArgumentParser()
    for k in ("--engine", "--cell-ser", "--nc-ser", "--t0-ser", "--out"): ap.add_argument(k, required=True)
    ap.add_argument("--profile", default="")
    ap.add_argument("--role", required=True, choices=["LINE_D_CELL", "POSITIVE_CONTROL"],
                    help="POSITIVE_CONTROL runs the same arithmetic on existing cells and never writes a line-D verdict or implication")
    a = ap.parse_args()
    NS, BT = load(a.engine); gm = float(BT.GM)
    cells = {"cell": ser(a.cell_ser), "NC": ser(a.nc_ser), "T0": ser(a.t0_ser)}
    A = cells["cell"][0]
    for k, (Ak, _) in cells.items(): assert np.array_equal(Ak, A), f"{k}: different anchor axis -- refusing"
    rec = {"device_sha256": sha(os.path.abspath(__file__)), "judge_sha256": JUDGE_SHA, "closure_definition": CLOSURE_DEFINITION,
           "inputs": {k: [p, sha(p)] for k, p in (("cell", a.cell_ser), ("NC", a.nc_ser), ("T0", a.t0_ser))}, "segments": {}}
    paths = {k: [{"A": A, "r": v[1]["r"][i]} for i in range(v[1]["r"].shape[0])] for k, v in cells.items()}
    closure_fail = False
    for seg in ("pre2026", "2026"):
        m = NS.seg_mask(A, *NS.SEG[seg]); days = NS.full_days(A, m); S = {"n_days": int(len(days)), "bounds": list(NS.SEG[seg]), "vs": {}}
        for base in ("NC", "T0"):
            db, _ = NS.dbar(paths["cell"], paths[base], m, days)
            idx = BT.mbb_indices(len(db), NS.BLOCK_MAIN, NS.B, NS.RNG); se = float(1e4 * db[idx].mean(1).std())
            D = float(1e4 * db.mean()); bt = NS.boot(db, NS.BLOCK_MAIN)
            ch = {}
            for k in ("g", "pnl", "car", "cst", "unk"):
                x = day_sum(A, gm * cells["cell"][1][k], m, days) - day_sum(A, gm * cells[base][1][k], m, days)
                ch[k] = float(x.mean())                                  # already in bps of NAV per day (g, channels are bps of gross)
            add_total = ch["g"]; parts = ch["pnl"] - ch["car"] - ch["cst"] - ch["unk"]
            err = abs(add_total - parts); ok = err <= CLOSURE_TOL; closure_fail |= not ok
            tau = float((cells["cell"][1]["tau"][:, m] - cells[base][1]["tau"][:, m]).mean())
            S["vs"][base] = {"D_bps_per_day": D, "SE_MBB30_bps": se, "ci95_bps": bt["ci95_bps"], "ci97_5_bps": bt["ci97.5_two_sided_bps"],
                             "resolvable": "本段可分辨" if abs(D) >= 3 * se else "本段分辨不出",
                             "channels_additive_bps_per_day": {"total_g": add_total, "price_pnl": ch["pnl"], "funding_car": ch["car"],
                                                               "fee_cst": ch["cst"], "unknown_unk": ch["unk"]},
                             "closure_abs_err": err, "closure": "OK" if ok else "CLOSURE_FAIL",
                             "compounding_term_bps_per_day": D - add_total, "turnover_diff_per_anchor": tau,
                             "hold_anchors_diff_path_mean": float((cells["cell"][1]["hold"][:, m].sum(1) - cells[base][1]["hold"][:, m].sum(1)).mean()),
                             "halt_anchors_diff_path_mean": float((cells["cell"][1]["halt"][:, m].sum(1) - cells[base][1]["halt"][:, m].sum(1)).mean())}
            if base == "T0": S["vs"][base]["role"] = "REFERENCE COLUMN (R1.3 draft 2)"
        rec["segments"][seg] = S
    rec["profile"] = {p: json.load(open(p)) for p in a.profile.split(",") if p}
    rec["role"] = a.role
    if a.role == "POSITIVE_CONTROL":
        rec["VERDICT_LINE"] = "POSITIVE CONTROL on existing cells -- NOT a line-D reading; no verdict, no implication"
    elif closure_fail:
        rec["VERDICT_LINE"] = "CLOSURE_FAIL: no verdict line (R1.3 frozen)"
    else:
        v26 = rec["segments"]["2026"]["vs"]["NC"]
        impl = v26["D_bps_per_day"] < 0 and v26["ci95_bps"][1] < 0
        rec["october_implication"] = ("PRE-DECLARED CASE MET: 2026 D < 0 and MBB95 upper < 0 -> producer D10 rule and retrain on the new "
                                      "features must ship in ONE release; switching features first is not allowed" if impl else
                                      "pre-declared case not met: no change to the October plan; description only")
        rec["VERDICT_LINE"] = (f"描述: 只换资金费特征(模型不变)对在役 NC s42, 2026 段 D = {v26['D_bps_per_day']:+.3f} bps/日 "
                               f"(MBB30 SE {v26['SE_MBB30_bps']:.3f}, 95% [{v26['ci95_bps'][0]:+.2f}, {v26['ci95_bps'][1]:+.2f}], {v26['resolvable']}); "
                               f"pre-2026 D = {rec['segments']['pre2026']['vs']['NC']['D_bps_per_day']:+.3f} "
                               f"({rec['segments']['pre2026']['vs']['NC']['resolvable']}). 不回答「修数据好不好」(PLAN §4)。")
    with open(a.out, "w") as fh:
        fh.write(json.dumps(rec, indent=1, ensure_ascii=False)); fh.flush(); os.fsync(fh.fileno())
    print(rec["VERDICT_LINE"]); print(rec.get("october_implication", ""))


if __name__ == "__main__":
    main()

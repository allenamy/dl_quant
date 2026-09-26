#!/usr/bin/env python3
"""alloc_footprint.py — DECISION_RULE_combination_layer §2-2 behavioural footprint. ZERO RETURNS: reads only combo-layer targets
(scaled_diagnostic.npz: kc, fc, raw, trade_mask, reason) and seats. Committed before any footprint is computed.

Per arm x seed, against the same-seed NC combo (s42 / s2027: the production-parity archive /dev/shm/news2_2026-09-23/work/combo_s<k>;
s7: dlarch's reference cell combo /workspace/dlarch_2026-09-24/chain/ref_nc_s7X/work/combo_s7), on three windows
(pre2026 2023-06-30T04Z..2025-12-31T20Z, 2026 2026-01-01..2026-09-18T20Z, FULL = both):
  seats        masked fund seat of the arm: mean / p10 / p50 / p90; mean |delta| vs the in-service seat; anchors where the seat differs
  weights      per-anchor Pearson corr of arm raw vs NC raw over names nonzero in either (>= 20 names): median / mean
  turnover     mean over consecutive anchors of sum|w_t - w_{t-1}| with w = raw / sum|raw| (the executor divides by gross): arm and NC
  publication  reason counts; GROSS-GATE rule (§2-2): frac of anchors whose arm reason contains 'gross' while NC's does not
  mechanism    2026 median per-anchor corr of the King book kc vs the F10 book fc over names nonzero in either (>= 20 names;
               dlarch_floor_ablate.py med() definition): arm and NC  [A3 non-inferiority mechanism control, threshold 0.80]
Gross-gate verdict per arm (written before any number): the rule fraction is computed on FULL for each seed;
  NOT_DEPLOYABLE if it exceeds 5% at all three seeds; DEPLOYABLE if it is <= 5% at all three; otherwise SEEDS_DISAGREE_ESCALATE (lead decides).
usage: /workspace/venv/bin/python -B alloc_footprint.py <out.json> <arm> [<arm> ...]     (arm = <rule>_<mix>, e.g. cap050_shared)
"""
import os, sys, json, hashlib, time, calendar
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import alloc_rules as R

CELLS = "/workspace/alloc_2026-09-26/cells"
NC = {42: "/dev/shm/news2_2026-09-23/work/combo_s42", 2027: "/dev/shm/news2_2026-09-23/work/combo_s2027",
      7: "/workspace/dlarch_2026-09-24/chain/ref_nc_s7X/work/combo_s7"}
LEGS = "/dev/shm/news2_2026-09-23/work/legs.npz"
SEEDS = (42, 2027, 7); MIN_NAMES = 20; GATE_FRAC = 0.05
def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
WIN = {"pre2026": (ts("2023-06-30T04:00:00Z"), ts("2025-12-31T20:00:00Z")), "2026": (ts("2026-01-01T00:00:00Z"), ts("2026-09-18T20:00:00Z"))}
WIN["FULL"] = (WIN["pre2026"][0], WIN["2026"][1])


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def rowcorr(X, Y, rows):
    out = []
    for i in rows:
        x, y = X[i], Y[i]; nz = (np.abs(x) > 1e-12) | (np.abs(y) > 1e-12)
        if nz.sum() >= MIN_NAMES and x[nz].std() > 0 and y[nz].std() > 0: out.append(float(np.corrcoef(x[nz], y[nz])[0, 1]))
    return (float(np.median(out)), float(np.mean(out)), len(out)) if out else (None, None, 0)


def turnover(Wt, rows):
    g = np.abs(Wt).sum(1, keepdims=True); w = np.where(g > 1e-12, Wt / np.where(g > 1e-12, g, 1), 0.0)
    r = np.asarray(rows); r = r[r >= 1]
    return float(np.abs(w[r] - w[r - 1]).sum(1).mean())


def main():
    out_path, arms = sys.argv[1], sys.argv[2:]
    L = np.load(LEGS); LR, WL = L["LR"], L["WL"]; la = L["E_ts"].astype(np.int64)
    s_in = R.masked_fund(WL.astype(np.float64))
    rec = {"device": "alloc_footprint.py", "self_sha256": sha(os.path.abspath(__file__)), "alloc_rules_sha256": sha(os.path.join(HERE, "alloc_rules.py")),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "zero_returns": True, "windows": WIN, "nc_combos": {}, "arms": {}}
    ncz = {}
    for s in SEEDS:
        p = f"{NC[s]}/scaled_diagnostic.npz"; rec["nc_combos"][str(s)] = {"path": p, "sha256": sha(p)}
        z = np.load(p); ncz[s] = {k: z[k] for k in ("E_ts", "kc", "fc", "raw", "trade_mask", "reason")}
    for arm in arms:
        rule, mix = arm.rsplit("_", 1)
        seats, srec = R.seats_for(rule, LR, WL); s_arm = R.masked_fund(seats)
        A = {"rule": rule, "mix": mix, "seat_receipt": srec, "seeds": {}}
        for s in SEEDS:
            p = f"{CELLS}/{arm}_s{s}/work/combo_s{s}/scaled_diagnostic.npz"
            z = np.load(p); a = z["E_ts"].astype(np.int64); n = ncz[s]; assert np.array_equal(a, n["E_ts"].astype(np.int64))
            pos = np.searchsorted(la, a); assert np.array_equal(la[pos], a)
            reason_a = z["reason"].astype(str); reason_n = n["reason"].astype(str)
            S = {"combo_path": p, "combo_sha256": sha(p), "windows": {}}
            for w, (lo, hi) in WIN.items():
                m = (a >= lo) & (a <= hi); rows = np.flatnonzero(m); sa = s_arm[pos][m]; si = s_in[pos][m]
                ga = np.array(["gross" in r for r in reason_a[m]]); gn = np.array(["gross" in r for r in reason_n[m]])
                mc_a = rowcorr(z["kc"], z["fc"], rows) if w == "2026" else None
                mc_n = rowcorr(n["kc"], n["fc"], rows) if w == "2026" else None
                wc = rowcorr(z["raw"], n["raw"], rows)
                S["windows"][w] = {
                    "n_anchors": int(m.sum()),
                    "seat_fund_masked": {"mean": float(sa.mean()), "p10": float(np.percentile(sa, 10)), "p50": float(np.median(sa)), "p90": float(np.percentile(sa, 90))},
                    "seat_fund_masked_inservice_mean": float(si.mean()), "seat_abs_delta_mean": float(np.abs(sa - si).mean()),
                    "anchors_seat_differs": int((np.abs(sa - si) > 1e-12).sum()),
                    "weight_corr_vs_NC": {"median": wc[0], "mean": wc[1], "n": wc[2]},
                    "turnover_proxy": {"arm": turnover(z["raw"], rows), "NC": turnover(n["raw"], rows)},
                    "publish": {"arm": int(z["trade_mask"][m].sum()), "NC": int(n["trade_mask"][m].sum())},
                    "reasons_arm": {k: int(v) for k, v in zip(*np.unique(reason_a[m], return_counts=True))},
                    "reasons_NC": {k: int(v) for k, v in zip(*np.unique(reason_n[m], return_counts=True))},
                    "gross_gate_rule_frac": float((ga & ~gn).mean()), "gross_gate_arm_frac": float(ga.mean()), "gross_gate_NC_frac": float(gn.mean()),
                    "mechanism_kc_fc_corr_2026": (None if mc_a is None else {"arm_median": mc_a[0], "arm_mean": mc_a[1], "NC_median": mc_n[0], "NC_mean": mc_n[1], "n": mc_a[2]})}
            A["seeds"][str(s)] = S
            print(f"FOOTPRINT {arm} s{s} FULL wcorr_med={S['windows']['FULL']['weight_corr_vs_NC']['median']} gross_rule_frac={S['windows']['FULL']['gross_gate_rule_frac']:.4f}", flush=True)
        fr = [A["seeds"][str(s)]["windows"]["FULL"]["gross_gate_rule_frac"] for s in SEEDS]
        A["gross_gate_verdict"] = ("NOT_DEPLOYABLE" if all(f > GATE_FRAC for f in fr) else "DEPLOYABLE" if all(f <= GATE_FRAC for f in fr) else "SEEDS_DISAGREE_ESCALATE")
        A["gross_gate_rule_frac_by_seed"] = dict(zip(map(str, SEEDS), fr))
        mc = [A["seeds"][str(s)]["windows"]["2026"]["mechanism_kc_fc_corr_2026"]["arm_median"] for s in SEEDS]
        A["mechanism_corr_2026_median_mean_over_seeds"] = float(np.mean(mc))
        rec["arms"][arm] = A
        print(f"FOOTPRINT_VERDICT {arm} gross_gate={A['gross_gate_verdict']} fracs={fr} mech2026={mc}", flush=True)
    json.dump(rec, open(out_path + ".tmp", "w"), indent=1); os.replace(out_path + ".tmp", out_path)
    assert json.load(open(out_path))["self_sha256"] == rec["self_sha256"]
    print("ALLOC_FOOTPRINT DONE", out_path, sha(out_path)[:16], flush=True)


if __name__ == "__main__":
    main()

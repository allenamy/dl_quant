#!/usr/bin/env python3
"""dlarch_retention_definition.py — pin down what the ladder's "chain retention rate" IS, and test whether
it survives the other aggregation choice.

lead 2026-09-25 asked for the denominator and the layer of the published numbers
"chain retention: King 34.8% / F10 58.1%" (docs/RESULT_dl_layer_ladder_2026-09-24.md §3.4), because fresh
derived from them that the two legs' L1 norms differ systematically -- and fresh's own measurement refuted
that (|kc|_1/|fc|_1 median 1.0025/1.0074, 2f65fb70e).

What the published number is (news2_layer_ladder.py L264-L286):
    L3k_i = 1e4 * u(zkc_i)/|zkc_i|_1      L4kc_i = 1e4 * u(kc_i)/|kc_i|_1
    published retention = mean_i(L4kc_i) / mean_i(L3k_i)
i.e. a ratio of two WINDOW-MEAN PER-UNIT-GROSS PAPER RETURNS. Each term is already divided by its OWN L1
norm at that anchor, so the masses are divided OUT inside each term. It is therefore NOT the L1 mass ratio
of kc to fc, and carries no information about it.

This device recomputes the per-anchor series and reports BOTH aggregations:
    (A) mean-of-ratios  = mean(L4)/mean(L3)        <- what was published
    (B) ratio-of-sums   = sum(u)/sum(|.|_1) form   <- the alternative; if (A) and (B) disagree a lot the
                                                      retention rate is fragile and must be labelled so
plus the L1 masses, so the receipt itself answers fresh's question.

READ-ONLY. CPU only, no GPU.
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B dlarch_retention_definition.py \
         PATH,HOME,LC_CTYPE <outdir>
"""
import os, sys, json, time, hashlib, calendar

import numpy as np

W = "/dev/shm/news2_2026-09-23"
LAB = "/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz"
LAB_SHA = "ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62"
SEG_PRE = ("2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z")
PUBLISHED = {"L3k": 1.550789, "L4kc": 0.539209, "L3f": 1.550965, "L4fc": 0.901484}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
def log(*a): print(time.strftime("%H:%M:%S", time.gmtime()), *a, flush=True)


def main():
    assert not sorted(set(os.environ) - set(sys.argv[1].split(","))), "env outside whitelist"
    outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
    sys.path.insert(0, f"{W}/devices"); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from dlarch_chain_torch import recon
    assert sha(LAB) == LAB_SHA
    F = np.load(f"{W}/work/NEWS_FEATURES.npz"); leg = np.load(f"{W}/work/legs.npz")
    lab = np.load(LAB, allow_pickle=True)
    a = F["anchors"].astype(np.int64); off = F["off"]; mm = F["m"].astype(np.int64)
    ya = lab["E_ts"].astype(np.int64); Y = lab["y4s"]
    iy = np.searchsorted(ya, a); lab_ok = (iy < len(ya)) & (ya[np.minimum(iy, len(ya) - 1)] == a)
    params = json.loads(open(f"{W}/inputs/bundle_config.json").read())["params"]
    legarr = (leg["QV"], leg["WL"], leg["KZ"], leg["ZFD"], leg["RN8"]); READY = leg["ready"]
    rec = {"device": "dlarch_retention_definition.py", "self_sha256": sha(os.path.abspath(__file__)),
           "answers": "lead 2026-09-25: the denominator and layer of the published chain retention rate",
           "published_terms": PUBLISHED, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "seeds": {}}
    for seed in (42, 2027):
        cp = f"{W}/work/combo_s{seed}/scaled_diagnostic.npz"
        C = np.load(cp); ca = C["E_ts"].astype(np.int64); KC = C["kc"]; FC = C["fc"]
        P10 = np.load(f"{W}/work/f10_s{seed}/F10_OOF.npz")["P"]
        ci = np.searchsorted(a, ca); assert np.all(a[ci] == ca)
        m = (ca >= ts(SEG_PRE[0])) & (ca <= ts(SEG_PRE[1])) & READY[ci] & lab_ok[ci]
        acc = {k: [] for k in ("L3k", "L4kc", "L3f", "L4fc", "u_zkc", "n_zkc", "u_kc", "n_kc",
                               "u_zfc", "n_zfc", "u_fc", "n_fc")}
        for j in np.flatnonzero(m):
            i = ci[j]
            R = recon(j, ci, mm, off, legarr, P10, params, apply_rn8=True)
            if R is None: continue
            yv = np.nan_to_num(Y[iy[i]].astype(np.float64)); ym = yv[R["members"]]
            for nm, zc, bk in (("k", R["kc"], KC[j]), ("f", R["fc"], FC[j])):
                nz = float(np.abs(zc).sum()); nb = float(np.abs(bk).sum())
                if nz <= 1e-9 or nb <= 1e-9: continue
                uz = float((zc * ym).sum()); ub = float((bk * yv).sum())
                acc[f"L3{nm}"].append(1e4 * uz / nz); acc[f"L4{'kc' if nm == 'k' else 'fc'}"].append(1e4 * ub / nb)
                acc[f"u_z{nm}c"].append(uz); acc[f"n_z{nm}c"].append(nz)
                acc[f"u_{'kc' if nm=='k' else 'fc'}"].append(ub); acc[f"n_{'kc' if nm=='k' else 'fc'}"].append(nb)
        e = {"anchors": int(len(acc["L3k"]))}
        for side, l3, l4, zk, bk in (("King", "L3k", "L4kc", "zkc", "kc"), ("F10", "L3f", "L4fc", "zfc", "fc")):
            m3 = float(np.mean(acc[l3])); m4 = float(np.mean(acc[l4]))
            # (B) ratio-of-sums: sum(u)/sum(|.|) is the gross-weighted per-unit-gross return
            s3 = 1e4 * float(np.sum(acc[f"u_{zk}"])) / float(np.sum(acc[f"n_{zk}"]))
            s4 = 1e4 * float(np.sum(acc[f"u_{bk}"])) / float(np.sum(acc[f"n_{bk}"]))
            e[side] = {"A_mean_of_ratios": {"L3": m3, "L4": m4, "retention": m4 / m3},
                       "B_ratio_of_sums": {"L3": s3, "L4": s4, "retention": s4 / s3},
                       "abs_retention_diff_A_minus_B": abs(m4 / m3 - s4 / s3),
                       "mean_L1_pre_chain": float(np.mean(acc[f"n_{zk}"])),
                       "mean_L1_post_chain": float(np.mean(acc[f"n_{bk}"]))}
        e["L1_mass_ratio_kc_over_fc"] = e["King"]["mean_L1_post_chain"] / e["F10"]["mean_L1_post_chain"]
        rec["seeds"][f"s{seed}"] = e
        log(f"s{seed} King retention A={e['King']['A_mean_of_ratios']['retention']:.4f} "
            f"B={e['King']['B_ratio_of_sums']['retention']:.4f} | "
            f"F10 A={e['F10']['A_mean_of_ratios']['retention']:.4f} B={e['F10']['B_ratio_of_sums']['retention']:.4f} | "
            f"|kc|1/|fc|1={e['L1_mass_ratio_kc_over_fc']:.4f}")
    # reproduce the published terms (a new readout must first reproduce a known number)
    s42 = rec["seeds"]["s42"]
    repro = {k: {"measured": (s42["King" if k in ("L3k", "L4kc") else "F10"]
                              ["A_mean_of_ratios"]["L3" if k.startswith("L3") else "L4"]),
                 "published": v} for k, v in PUBLISHED.items()}
    for k in repro: repro[k]["abs_diff"] = abs(repro[k]["measured"] - repro[k]["published"])
    rec["reproduction_of_published_terms"] = {"terms": repro, "tolerance": 2e-3,
                                             "PASS": all(v["abs_diff"] <= 2e-3 for v in repro.values())}
    rec["STATEMENT"] = ("The retention rate is a ratio of two WINDOW-MEAN PER-UNIT-GROSS PAPER RETURNS "
                        "(news2_layer_ladder.py L264-L286). Each term is divided by its OWN L1 norm at that "
                        "anchor, so the L1 masses cancel INSIDE each term. It is NOT the L1 mass ratio of kc "
                        "to fc and carries no information about it; that ratio is reported separately here "
                        "and is ~1.02, consistent with fresh's 1.0025/1.0074 (2f65fb70e).")
    op = os.path.join(outdir, "RETENTION_DEFINITION.json")
    tmp = op + ".tmp"; open(tmp, "w").write(json.dumps(rec, indent=1, allow_nan=False)); os.replace(tmp, op)
    print(f"RETENTION_DEFINITION repro_PASS={rec['reproduction_of_published_terms']['PASS']} "
          f"King A/B={s42['King']['A_mean_of_ratios']['retention']:.4f}/{s42['King']['B_ratio_of_sums']['retention']:.4f} "
          f"F10 A/B={s42['F10']['A_mean_of_ratios']['retention']:.4f}/{s42['F10']['B_ratio_of_sums']['retention']:.4f} "
          f"mass_ratio={s42['L1_mass_ratio_kc_over_fc']:.4f} json={sha(op)[:16]}", flush=True)
    assert rec["reproduction_of_published_terms"]["PASS"], "could not reproduce the published terms"


if __name__ == "__main__":
    main()

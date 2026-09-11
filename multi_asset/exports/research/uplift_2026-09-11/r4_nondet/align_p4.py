"""P4: align each DL draw's walk-forward OOS preds (dlw_ext axis, 10206) onto the v4 DL axis (10212).
align() copied VERBATIM from r3_xib/align_preds.py, itself verbatim from review_scratch/build_dev_v4.py
(the script that produced the archived f10_A0_s{42,2027}.npy the A0 baseline rides on).

Also measures the DL-LAYER dispersion directly: per-anchor cross-sectional Spearman between every pair of
draws, split into (a) SAME-SEED pairs (seed 42, different training runs) and (b) DIFFERENT-SEED pairs.
"""
import numpy as np, os, sys, json
from scipy.stats import rankdata

R = "/workspace/uplift_2026-09-11/r4_nondet"
DST = R + "/f8x/preds"
HCP = "/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds"
R3X = "/workspace/uplift_2026-09-11/r3_xib/f8x/preds"
EX = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True)["E_ts"].astype(np.int64)
tt = np.load("/workspace/dlw_v4raw/data/dlw_targets.npz", allow_pickle=True)["E_ts"].astype(np.int64)


def align(P, src_E, dst_E):          # VERBATIM build_dev_v4.py
    o = np.full((len(dst_E), P.shape[1]), np.nan, np.float32)
    r = {int(t): i for i, t in enumerate(src_E)}
    for k, t in enumerate(dst_E):
        i = r.get(int(t))
        if i is not None:
            o[k] = P[i]
    return o


import hashlib
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""):
            h.update(ch)
    return h.hexdigest()


MINE = sys.argv[1].split(",") if len(sys.argv) > 1 else []
OUT = {}
for L in MINE:
    p = "%s/f8_%s/preds/f10_V2MAIN_s42.npy" % (R, L)
    if not os.path.exists(p):
        OUT[L] = "MISSING " + p; print(L, OUT[L], flush=True); continue
    Y = np.load(p)
    assert Y.shape[0] == len(EX), (Y.shape, len(EX))
    q = "%s/f10_A0_s%s.npy" % (DST, L)
    np.save(q, align(Y, EX, tt))
    OUT[L] = {"src": p, "src_sha256": sha(p), "dst": q, "dst_sha256": sha(q)}
    print(L, OUT[L]["src_sha256"][:16], "->", os.path.basename(q), flush=True)
# round-3 draws (already aligned by the same align()): symlink, do not recompute
for L in ("7", "101", "1234", "31337", "REP42"):
    s = "%s/f10_A0_s%s.npy" % (R3X, L); d = "%s/f10_A0_s%s.npy" % (DST, L)
    if os.path.exists(s) and not os.path.exists(d):
        os.symlink(s, d)
    if os.path.exists(d): OUT["r3_" + L] = {"src": s, "src_sha256": sha(s)}
for L in ("42", "2027"):
    OUT["arch_" + L] = {"src": "%s/f10_A0_s%s.npy" % (HCP, L), "src_sha256": sha("%s/f10_A0_s%s.npy" % (HCP, L))}

# ---- DL-layer dispersion ----
def xrank_corr(A, B):
    cs = []
    for i in range(A.shape[0]):
        ok = np.isfinite(A[i]) & np.isfinite(B[i])
        if ok.sum() < 50: continue
        a = rankdata(A[i][ok]); b = rankdata(B[i][ok])
        sa, sb = a.std(), b.std()
        if sa > 0 and sb > 0:
            cs.append(float(((a - a.mean()) * (b - b.mean())).mean() / (sa * sb)))
    return float(np.mean(cs)), len(cs)


LAB = {}
for L in MINE + ["REP42", "7", "101", "1234", "31337"]:
    p = "%s/f10_A0_s%s.npy" % (DST, L)
    if os.path.exists(p): LAB[L] = np.load(p)
for L in ("42", "2027"):
    LAB["ARCH" + L] = np.load("%s/f10_A0_s%s.npy" % (HCP, L))

SEED42_NEW = [L for L in MINE if L in LAB] + (["REP42"] if "REP42" in LAB else [])
OTHER_SEED_NEW = [L for L in ("7", "101", "1234", "31337") if L in LAB]
ks = sorted(LAB)
M = {}
for i, a in enumerate(ks):
    for b in ks[i + 1:]:
        M["%s|%s" % (a, b)] = xrank_corr(LAB[a], LAB[b])[0]


def grp(pairs):
    v = [M[k] for k in M if tuple(sorted(k.split("|"))) in pairs]
    return {"n_pairs": len(v), "mean": float(np.mean(v)) if v else None,
            "min": float(np.min(v)) if v else None, "max": float(np.max(v)) if v else None}


P_same = set(tuple(sorted((a, b))) for i, a in enumerate(SEED42_NEW) for b in SEED42_NEW[i + 1:])
P_diff = set(tuple(sorted((a, b))) for i, a in enumerate(OTHER_SEED_NEW) for b in OTHER_SEED_NEW[i + 1:])
P_cross = set(tuple(sorted((a, b))) for a in SEED42_NEW for b in OTHER_SEED_NEW)
P_arch = set([tuple(sorted(("ARCH42", "ARCH2027")))])
P_a42 = set(tuple(sorted(("ARCH42", b))) for b in SEED42_NEW)
RES = {"align": OUT,
       "SAME_SEED42_newenv_pairs": grp(P_same),
       "DIFF_SEED_newenv_pairs": grp(P_diff),
       "SEED42_vs_OTHERSEED_newenv": grp(P_cross),
       "ARCHIVED_s42_vs_ARCHIVED_s2027": grp(P_arch),
       "ARCHIVED_s42_vs_SAME_SEED42_newenv": grp(P_a42),
       "all_pairs": M, "labels_same_seed": SEED42_NEW, "labels_other_seed": OTHER_SEED_NEW}
json.dump(RES, open(R + "/receipts/ALIGN_P4.json", "w"), indent=1, default=str)
for k in ("SAME_SEED42_newenv_pairs", "DIFF_SEED_newenv_pairs", "SEED42_vs_OTHERSEED_newenv",
          "ARCHIVED_s42_vs_ARCHIVED_s2027", "ARCHIVED_s42_vs_SAME_SEED42_newenv"):
    print("%-38s %s" % (k, RES[k]), flush=True)
print("ALIGN_P4_DONE")

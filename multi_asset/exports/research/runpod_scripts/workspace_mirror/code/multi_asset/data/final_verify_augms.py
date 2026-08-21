"""Final full-range verification of npz_v2arch_augms after the build completes:
 1. build-log error scan (no 'error'/'no-series'/'len-mismatch'/'base-not-88').
 2. day count + span; every fold day (train+val+test for 2025-10-10 & 2026-01-10) present.
 3. sampled base-88 byte-identity + X_basis non-degeneracy across the whole span.
"""
from __future__ import annotations
import os, os.path as p, sys
import numpy as np
_REPO = p.dirname(p.dirname(p.dirname(p.abspath(__file__))))
sys.path.insert(0, _REPO)
import multi_asset.data.add_basis_dynamics as ab  # noqa

BASE = p.join(_REPO, "data", "npz_v2arch")
AUG = p.join(_REPO, "data", "npz_v2arch_augms")
TRAIN, VAL, TEST, EMB = 450, 45, 28, 1


def fold_days(days, ts):
    ti = days.index(ts)
    test = days[ti:ti + TEST]
    ve = ti - EMB; vs = ve - VAL; val = days[vs:ve]
    te = vs - EMB; trs = max(0, te - TRAIN); train = days[trs:te]
    return train + val + test


def check_day(day):
    b = np.load(p.join(BASE, f"{day}.npz"), allow_pickle=True)
    a = np.load(p.join(AUG, f"{day}.npz"), allow_pickle=True)
    Xa, Xb = a["X"], b["X"]
    c_id = (Xa.dtype == Xb.dtype and Xa.shape[-1] == 98 and Xa[:, :, :88].tobytes() == Xb.tobytes())
    xba = Xa[:, :, 88:98].astype(np.float64)
    c_nd = (np.isfinite(xba).mean() > 0.999 and np.all(np.nanstd(xba.reshape(-1, 10), 0) > 1e-9))
    return c_id, c_nd


def main():
    # 1. build-log error scan
    log = "/tmp/build_augms_full.log"
    errs = []
    if p.exists(log):
        for ln in open(log):
            low = ln.lower()
            if any(t in low for t in ("error", "no-series", "len-mismatch", "base-not-88", "missing-base", "traceback")):
                errs.append(ln.strip())
    print(f"[1] build-log error lines: {len(errs)}")
    for e in errs[:10]:
        print("    " + e)

    # 2. count + span + fold-day presence
    aug_days = sorted(f[:-4] for f in os.listdir(AUG) if f.endswith(".npz") and f[0].isdigit())
    base_days = sorted(f[:-4] for f in os.listdir(BASE) if f.endswith(".npz") and f[0].isdigit())
    print(f"[2] augms n={len(aug_days)} span {aug_days[0]}..{aug_days[-1]}")
    augset = set(aug_days)
    all_present = True
    for ts in ["2025-10-10", "2026-01-10"]:
        fd = fold_days(base_days, ts)  # fold computed on FULL base day list (ground truth)
        missing = [d for d in fd if d not in augset]
        print(f"    fold {ts}: {len(fd)} days, missing in augms = {len(missing)} {missing[:5]}")
        all_present &= (len(missing) == 0)

    # 3. sampled byte-identity + non-degeneracy across span
    idx = np.linspace(0, len(aug_days) - 1, 20).astype(int)
    sample = [aug_days[i] for i in sorted(set(idx))]
    nid = nnd = 0
    for d in sample:
        cid, cnd = check_day(d)
        nid += cid; nnd += cnd
        if not (cid and cnd):
            print(f"    SAMPLE FAIL {d}: byteid={cid} nondegen={cnd}")
    print(f"[3] sampled {len(sample)} days: base88_byteid {nid}/{len(sample)}, X_basis nondegen {nnd}/{len(sample)}")

    ok = (len(errs) == 0 and all_present and nid == len(sample) and nnd == len(sample))
    print(f"FINAL: {'ALL PASS — cache ready' if ok else 'REVIEW NEEDED'}")


if __name__ == "__main__":
    main()

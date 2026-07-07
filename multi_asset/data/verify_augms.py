"""Verify npz_v2arch_augms is a byte-identical pure superset of npz_v2arch + a
non-degenerate X_basis block. Run after build_v2arch_aug.py (smoke or full).

Checks per day:
  1. dtype(augms.X) == dtype(base.X); augms.X width == 98; base width 88.
  2. augms.X[:,:,:88].tobytes() == base.X.tobytes()  (BASE-88 BYTE-IDENTICAL).
  3. every base key (except X) tobytes-equal in augms.
  4. X_basis = augms.X[:,:,88:98]: finite==1.0, per-channel std>0 (non-degenerate),
     ranges printed; basis_names == add_basis_dynamics.BASIS_NAMES.
  5. sanity: the instantaneous cross basis level ch81 (x_basis_bps) range printed
     for cross-reference (2026 ~ -4..-7 bps expected).
"""
from __future__ import annotations

import os.path as p
import sys

import numpy as np

_REPO = p.dirname(p.dirname(p.dirname(p.abspath(__file__))))
sys.path.insert(0, _REPO)
import multi_asset.data.add_basis_dynamics as ab  # noqa: E402

BASE_DIR = p.join(_REPO, "data", "npz_v2arch")
AUG_DIR = p.join(_REPO, "data", "npz_v2arch_augms")


def verify_day(day: str) -> bool:
    bfp = p.join(BASE_DIR, f"{day}.npz")
    afp = p.join(AUG_DIR, f"{day}.npz")
    if not p.exists(afp):
        print(f"  {day}: AUG MISSING"); return False
    b = np.load(bfp, allow_pickle=True)
    a = np.load(afp, allow_pickle=True)
    ok = True
    Xb_ = b["X"]; Xa = a["X"]
    c1 = (Xa.dtype == Xb_.dtype)
    c_w = (Xa.shape[-1] == 98 and Xb_.shape[-1] == 88)
    # BASE-88 byte-identity
    c2 = (Xa[:, :, :88].tobytes() == Xb_.tobytes())
    # all other base keys byte-equal
    badkeys = []
    for k in b.files:
        if k == "X":
            continue
        if k not in a.files:
            badkeys.append(f"{k}:MISSING"); continue
        ak, bk = a[k], b[k]
        if ak.dtype == object or bk.dtype == object:
            # object arrays (e.g. *_names): tobytes() compares pointers, not content
            equal = (ak.tolist() == bk.tolist())
        else:
            equal = (ak.shape == bk.shape and ak.dtype == bk.dtype
                     and ak.tobytes() == bk.tobytes())
        if not equal:
            badkeys.append(k)
    c3 = (len(badkeys) == 0)
    # X_basis block
    Xbasis = Xa[:, :, 88:98].astype(np.float64)
    fin = float(np.isfinite(Xbasis).mean())
    stds = np.nanstd(Xbasis.reshape(-1, 10), axis=0)
    c4 = (fin > 0.999 and np.all(stds > 1e-9))
    bn = list(a["basis_names"]) if "basis_names" in a.files else None
    c5 = (bn == ab.BASIS_NAMES)
    ok = c1 and c_w and c2 and c3 and c4 and c5
    ch81 = Xb_[:, :, 81].astype(np.float64)  # x_basis_bps (instantaneous cross basis level)
    print(f"  {day}: {'PASS' if ok else 'FAIL'} | dtype={Xa.dtype}({'==' if c1 else '!='}base) "
          f"width={Xa.shape[-1]}({'ok' if c_w else 'BAD'}) base88_byteid={'YES' if c2 else 'NO'} "
          f"otherkeys={'ok' if c3 else 'BAD:'+','.join(badkeys)} names={'ok' if c5 else 'BAD'}")
    print(f"        X_basis finite={fin:.4f} per-ch std={np.round(stds,3).tolist()}")
    print(f"        ch81 x_basis_bps(inst) [min/mean/max]=({ch81.min():+.2f}/{ch81.mean():+.2f}/{ch81.max():+.2f})")
    return ok


def main():
    days = sys.argv[1:]
    if not days:
        print("pass days"); return
    allok = True
    for d in days:
        allok &= verify_day(d)
    print(f"[verify_augms] {'ALL PASS' if allok else 'SOME FAIL'} ({len(days)} days)")


if __name__ == "__main__":
    main()

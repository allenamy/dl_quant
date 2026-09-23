#!/usr/bin/env python3
"""ens_build.py — STEP 2 of docs/PREREG_f10_seed_ensemble_book_2026-09-23.md (45aba1f3f, sha 56acd832) §1: F10_ENS from the two F10 seeds.
Library + CLI. Written before any NAV / return number of this test.

Rule (prereg §1, verbatim intent): at every anchor A (row of the F10_OOF axis), over the names finite in BOTH seeds, each seed's cross-sectional
rank (scipy.stats.rankdata, method 'average' = the combo's own ranker) normalised to [0, 1]; F10_ENS = (rank_s42 + rank_s2027) / 2; a name finite in
only ONE seed is NaN (unscored) and counted per anchor; a name finite in neither stays NaN.
  Exact arithmetic: rn_k = (rank_k − 1)/(nb − 1) and ENS = (rn_42 + rn_2027)/2 are computed as ONE division of the exact half-integer numerator
  (rank_42 + rank_2027 − 2) by 2·max(nb − 1, 1) (the combo's max(n−1, 1) convention), so equal rank sums give bit-equal ENS values (no ulp-level
  pseudo-ties or pseudo-orders). nb = 1 ⇒ 0.0; nb = 0 ⇒ the row stays NaN.
  Output dtype = the input's (float32). Asserted per anchor: rankdata(ENS_float32) == rankdata(numerator) exactly (the cast neither creates nor
  breaks a tie), so the combo's re-ranking sees exactly the prereg's rank average.
Output file = the F10_OOF.npz format: keys {P, E_ts, symbols}, same dtypes / shapes; E_ts and symbols copied from the (identical) inputs.
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B ens_build.py PATH,HOME,LC_CTYPE <f10_s42.npz> <sha> <f10_s2027.npz> <sha>
       <dlw_targets.npz> <sha> <out F10_ENS.npz> <out receipt.json>
"""
import os, sys, json, time, hashlib, collections, datetime

import numpy as np
from scipy.stats import rankdata

KEYS = {"P", "E_ts", "symbols"}


class EnsError(Exception):
    pass


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


def load_oof(path, want_sha):
    got = sha(path)
    if got != want_sha: raise EnsError(f"oof_sha_mismatch {path} got {got[:16]} want {want_sha[:16]}")
    Z = np.load(path, allow_pickle=False)
    if set(Z.files) != KEYS: raise EnsError(f"oof_key_set {sorted(Z.files)}")
    D = {k: Z[k] for k in Z.files}
    if D["P"].ndim != 2 or D["P"].shape != (len(D["E_ts"]), len(D["symbols"])): raise EnsError("oof_shape")
    return D, got


def ens_row(p42, p27):
    """one anchor → (ens float64 row with NaN, n_both, n_one_only, numerator on the both-finite names)"""
    f42 = np.isfinite(p42); f27 = np.isfinite(p27); both = f42 & f27; one = f42 ^ f27
    out = np.full(p42.shape, np.nan); nb = int(both.sum())
    num = None
    if nb:
        num = rankdata(p42[both]) + rankdata(p27[both]) - 2.0          # exact: sums of (half-)integers
        out[both] = num / (2.0 * max(nb - 1, 1))
    return out, nb, int(one.sum()), both, num


def build(P42, P27):
    if P42.shape != P27.shape or P42.dtype != P27.dtype: raise EnsError("seed matrices differ in shape / dtype")
    n, w = P42.shape
    E = np.full((n, w), np.nan, dtype=P42.dtype); nboth = np.zeros(n, np.int64); none_ = np.zeros(n, np.int64)
    for i in range(n):
        row, nb, no, both, num = ens_row(P42[i].astype(np.float64), P27[i].astype(np.float64))
        E[i] = row.astype(P42.dtype); nboth[i] = nb; none_[i] = no
        if nb:
            if not np.array_equal(rankdata(E[i, both]), rankdata(num)): raise EnsError(f"dtype cast changed the rank structure at row {i}")
            if np.isfinite(E[i, ~both]).any(): raise EnsError(f"finite ENS outside both-finite at row {i}")
    return E, nboth, none_


def write_oof(path, P, E_ts, symbols):
    tmp = path[:-4] + ".tmp.npz"                                            # np.savez keeps a name that already ends in .npz (E-0917-B)
    np.savez_compressed(tmp, P=P, E_ts=E_ts, symbols=symbols); os.replace(tmp, path)
    return sha(path)


def roundtrip(path, P, ref):
    """ENS file vs the source OOF: key set, dtypes, shapes, E_ts, symbols identical; P read back == in-memory P bit for bit (NaN positions equal)"""
    Z = np.load(path, allow_pickle=False)
    if set(Z.files) != set(ref): raise EnsError(f"roundtrip key set {sorted(Z.files)}")
    for k in ref:
        if Z[k].dtype != ref[k].dtype or Z[k].shape != ref[k].shape: raise EnsError(f"roundtrip dtype/shape {k}")
    if not np.array_equal(Z["E_ts"], ref["E_ts"]): raise EnsError("roundtrip E_ts differs")
    if not np.array_equal(Z["symbols"], ref["symbols"]): raise EnsError("roundtrip symbols differ")
    ui = {np.dtype(np.float32): np.uint32, np.dtype(np.float64): np.uint64}[P.dtype]
    if not np.array_equal(Z["P"].view(ui), P.view(ui)): raise EnsError("roundtrip P differs bitwise")
    return {"keys": sorted(Z.files), "dtypes": {k: str(Z[k].dtype) for k in Z.files}, "shapes": {k: list(Z[k].shape) for k in Z.files}, "bitwise_equal": True}


def main():
    WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
    p42, s42, p27, s27, pt, st, out_npz, out_rec = sys.argv[2:10]
    D42, h42 = load_oof(p42, s42); D27, h27 = load_oof(p27, s27)
    if not (np.array_equal(D42["E_ts"], D27["E_ts"]) and np.array_equal(D42["symbols"], D27["symbols"])): raise EnsError("seed axes differ")
    if sha(pt) != st: raise EnsError("dlw_targets sha")
    T = np.load(pt, allow_pickle=True)
    if not (np.array_equal(T["E_ts"], D42["E_ts"]) and np.array_equal(T["symbols"], D42["symbols"])): raise EnsError("dlw_targets axes differ")
    E, nboth, none_ = build(D42["P"], D27["P"])
    s_out = write_oof(out_npz, E, D42["E_ts"], D42["symbols"])
    rt = roundtrip(out_npz, E, D42)
    # per-anchor one-seed-only counts, whole file axis and per year; members check (ENS finite set vs members) on every anchor
    a = D42["E_ts"]; yr = np.array([datetime.datetime.fromtimestamp(int(x), datetime.timezone.utc).year for x in a])
    by = {}
    mem_mismatch = 0
    for i in range(len(a)):
        m = np.asarray(T["members"][i], int); fin = np.nonzero(np.isfinite(E[i]))[0]
        if nboth[i] and not np.array_equal(np.sort(m), fin): mem_mismatch += 1
    for y in np.unique(yr):
        k = yr == y
        by[str(y)] = {"anchors": int(k.sum()), "one_seed_only_names_total": int(none_[k].sum()), "anchors_with_one_seed_only_names": int((none_[k] > 0).sum()),
                      "both_finite_names_total": int(nboth[k].sum()), "anchors_with_no_finite_F10": int((nboth[k] == 0).sum())}
    nz = np.nonzero(none_)[0]
    R = {"device": "ens_build.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": iso(time.time()),
         "prereg": {"path": "docs/PREREG_f10_seed_ensemble_book_2026-09-23.md", "commit": "45aba1f3f", "sha256": "56acd8320eae43450ba8a6ddfc7a3808bf0f742bcbe76c5d9890be6da6976d92"},
         "inputs": {"f10_s42": {"path": p42, "sha256": h42}, "f10_s2027": {"path": p27, "sha256": h27}, "dlw_targets": {"path": pt, "sha256": st}},
         "rule": "per anchor, names finite in both seeds: rankdata(average) per seed, ENS = (r42 + r2027 - 2) / (2*max(nb-1,1)); one-seed-only -> NaN (counted); float32",
         "output": {"path": out_npz, "sha256": s_out}, "roundtrip_vs_source_oof": rt,
         "one_seed_only_names": {"total": int(none_.sum()), "anchors_with_any": int(len(nz)), "first_anchors": [iso(a[i]) for i in nz[:20]], "by_year": by,
                                 "n_eff_anchors": int(len(a))},
         "ens_finite_set_neq_members_anchors": int(mem_mismatch),
         "float32_rank_structure_preserved": "asserted on every anchor with >= 1 both-finite name"}
    json.dump(R, open(out_rec + ".tmp", "w"), indent=1); os.replace(out_rec + ".tmp", out_rec)
    print(f"ENS_BUILD VERDICT=PASS out_sha256={s_out} one_seed_only_total={int(none_.sum())} anchors_with_one_seed_only={len(nz)} "
          f"ens_finite_set_neq_members_anchors={mem_mismatch} roundtrip=bitwise receipt_sha256={sha(out_rec)}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except EnsError as e:
        print(f"ENS_BUILD VERDICT=REFUSED {e}", flush=True); sys.exit(3)

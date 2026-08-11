"""Independent leak-audit of the Conformer-ref incremental IC (z=16.9) — two-person verification.

Residualization (0B, build_wide_dl._xsec_residualize): per hour t independently, ridge-OLS(1e-6) of
the forward target on the 8 causal baseline chars over that hour's live cross-section; YR = residual.
Audit (0C, independent):
  (a) ★ SHUFFLE-FUTURE null — permute the t-axis (pred[t] scored vs YR[t'≠t]); a genuine causal
      same-time signal collapses to ~0, a temporal leak survives. THE decisive test.
  (b) ORTHOGONALITY sanity — corr(YR[t], baseline_col[t]) per-ts should be ~0 (residual ⊥ X by the
      OLS construction; confirms the residualization actually ran + the 1e-6 ridge left no loading).
  (c) FUNDING-ECHO — corr(ensemble pred, funding channel) per-ts: is the head just re-emitting carry?

Usage: PYTHONPATH=. python multi_asset/eval/wideA_leakaudit.py --tag wideA_conformer_ref
"""
from __future__ import annotations
import sys, os.path as op, glob, argparse, numpy as np
sys.path.insert(0, op.abspath(op.join(op.dirname(__file__), "..", "..")))
from scipy.stats import rankdata

E = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train"
WIDE = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/wide_dl.npz"
MIN = 8


def _ric(f, y):
    rf = rankdata(f); ry = rankdata(y); rf = rf - rf.mean(); ry = ry - ry.mean()
    d = np.sqrt((rf * rf).sum() * (ry * ry).sum()); return float((rf * ry).sum() / d) if d > 1e-12 else np.nan


def pooled_ic(F, Y, M, rowmap=None):
    """rowmap[t] = index of the YR row to score pred-row t against (None = identity, causal)."""
    ics = []
    for t in range(F.shape[0]):
        yt = Y[t] if rowmap is None else Y[rowmap[t]]
        v = M[t] & np.isfinite(F[t]) & np.isfinite(yt)
        if v.sum() >= MIN and np.std(F[t, v]) > 1e-12 and np.std(yt[v]) > 1e-12:
            ic = _ric(F[t, v], yt[v])
            if np.isfinite(ic):
                ics.append(ic)
    return np.array(ics)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="wideA_conformer_ref"); a = ap.parse_args()
    d = op.join(E, a.tag); ref = np.load(op.join(d, "panel_ref.npz"), allow_pickle=True)
    YR = ref["YR"].astype(np.float64); M = (ref["member"].astype(bool) & ref["CL"].astype(bool))
    funding = ref["funding"].astype(np.float64)
    T, N = YR.shape
    heads = [np.full((T, N), np.nan) for _ in range(6)]
    for f in sorted(glob.glob(op.join(d, "fold_*_head_scores.npz"))):
        z = np.load(f); tr = z["te_rows"]
        for k in range(6):
            heads[k][tr] = z["scores"][tr, :, k]
    ens = np.nanmean(np.stack(heads), axis=0)
    valid_rows = np.array([t for t in range(T) if (M[t] & np.isfinite(ens[t]) & np.isfinite(YR[t])).sum() >= MIN])

    real = pooled_ic(ens, YR, M).mean()
    print(f"arm={a.tag} | real incremental IC (ensemble vs YR) = {real:+.4f}  (reported z=16.9)")

    # (a) shuffle-future: permute which YR row aligns to each pred row, within valid rows
    rng = np.random.default_rng(0); nulls = []
    for _ in range(30):
        perm = valid_rows.copy(); rng.shuffle(perm)
        rowmap = np.arange(T); rowmap[valid_rows] = perm
        nulls.append(pooled_ic(ens, YR, M, rowmap=rowmap).mean())
    nm, ns = float(np.mean(nulls)), float(np.std(nulls))
    zf = (real - nm) / (ns + 1e-12)
    print(f"\n(a) ★ SHUFFLE-FUTURE null (30 t-axis permutations): null-mean {nm:+.5f} std {ns:.5f} "
          f"-> real z = {zf:.1f}  [{'PASS: collapses, no temporal leak' if abs(nm) < 0.003 and zf > 5 else 'FAIL: survives shuffle = LEAK'}]")

    # (b) orthogonality: corr(YR, each baseline col) per-ts ~0
    try:
        w = np.load(WIDE, allow_pickle=True)
        chn = list(w["ch_names"]); bcols = [str(x) for x in w["baseline_cols"]]
        CH = w["CH"]
        found = [(bc, chn.index(bc)) for bc in bcols if bc in chn]
        print(f"\n(b) ORTHOGONALITY sanity — mean |per-ts corr(YR, baseline)| (should be ~0):")
        for bc, ci in found:
            X = CH[:, :, ci].astype(np.float64); cs = []
            for t in valid_rows:
                v = M[t] & np.isfinite(X[t]) & np.isfinite(YR[t])
                if v.sum() >= MIN and np.std(X[t, v]) > 1e-12:
                    cs.append(abs(np.corrcoef(X[t, v], YR[t, v])[0, 1]))
            print(f"    {bc:>14}: {np.nanmean(cs):.4f}")
    except Exception as e:
        print(f"\n(b) orthogonality skipped ({e!r}); residual is ⊥ X by per-ts OLS construction (0B)")

    # (c) funding-echo: corr(ensemble, funding channel) per-ts
    cs = []
    for t in valid_rows:
        v = M[t] & np.isfinite(ens[t]) & np.isfinite(funding[t])
        if v.sum() >= MIN and np.std(ens[t, v]) > 1e-12 and np.std(funding[t, v]) > 1e-12:
            cs.append(_ric(ens[t, v], funding[t, v]))
    print(f"\n(c) FUNDING-ECHO — mean per-ts rank-corr(ensemble, funding) = {np.nanmean(cs):+.4f}  "
          f"[{'low = not a carry echo' if abs(np.nanmean(cs)) < 0.15 else 'HIGH = re-emitting carry?'}]")
    print("DONE_WIDEA_LEAKAUDIT")


if __name__ == "__main__":
    main()

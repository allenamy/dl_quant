"""State-permute NULL leak check (audit item 3) for a Run2 (state+gain) run.

Loads a trained Run2 checkpoint and runs test inference (a) UNCHANGED and (b) with
the 18-d state_prior block (regime_prior cols 6:) DAY-PERMUTED — each test day
receives a DIFFERENT (permuted) day's state vectors, everything else identical.

Interpretation:
  * real causal conditioning  -> permuted cd drops materially toward Run1 levels.
  * cd UNCHANGED              -> the state isn't driving the win (attribution suspect).
  * cd up / σ,β shift wildly  -> leak suspect (escalate).

The model's frozen train-window stats (rs_* buffers) ride in the ckpt state_dict,
so the permuted state is normalised with the identical operator. 3 permutation seeds.

Run (GPU, in a CLEAN window — never concurrent with a primary arm):
  PYTHONPATH=. python multi_asset/model/state_permute_null.py \
      --config configs/d1gate/d1_2026_04_run2.json \
      --ckpt experiments/d1gate/d1_2026_04_run2/fold_0/ema_best.pt \
      --norm experiments/d1gate/d1_2026_04_run2/fold_0/norm_params.npz
"""
from __future__ import annotations

import argparse
import json
import os.path as osp
import sys

import numpy as np
import torch
from torch.utils.data import DataLoader

_REPO = osp.dirname(osp.dirname(osp.dirname(osp.abspath(__file__))))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from multi_asset.train.train_dual_lob import (  # noqa: E402
    _build_folds, _common_ds_kwargs, build_dual_lob_model, _forward_dual,
)
from multi_asset.data.dual_lob_dataset import DualLOBDataset  # noqa: E402

HZ = 600_000_000
DAY = 86_400_000_000
BASE_PRIOR = 6   # cols [0:6] = base regime_prior; [6:] = state overlay


def _pear(a, b):
    a = a - a.mean(); b = b - b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d > 0 else 0.0


def _nonoverlap(ts):
    idx = np.argsort(ts, kind="stable"); keep = []; last = None
    for i in idx:
        if last is None or ts[i] - last >= HZ:
            keep.append(i); last = ts[i]
    return np.array(keep, dtype=int)


def score(q, y, ts):
    q = q.astype(np.float64); y = y.astype(np.float64)
    dP = _pear(q, y)
    qc = q - q.mean(); yc = y - y.mean(); v = (qc * qc).sum()
    b = float((qc * yc).sum() / v) if v > 0 else float("nan")
    sg = q.std() / (y.std() + 1e-12)
    day = ts // DAY; rs = []
    for d in np.unique(day):
        m = np.where(day == d)[0]; sub = m[_nonoverlap(ts[m])]
        if len(sub) > 20 and q[sub].std() > 1e-12:
            rs.append(_pear(q[sub], y[sub]))
    return dP, (float(np.mean(rs)) if rs else float("nan")), b, sg


def permute_state_by_day(rp, ts, seed):
    """Return a copy of rp (N, d_prior) with cols [6:] replaced by a DIFFERENT
    day's state (day-level permutation; derangement so no day keeps its own)."""
    rp2 = rp.copy()
    day = ts // DAY
    udays = np.unique(day)
    rng = np.random.default_rng(seed)
    # derangement of day indices (retry until no fixed point)
    n = len(udays)
    for _ in range(1000):
        perm = rng.permutation(n)
        if not np.any(perm == np.arange(n)):
            break
    idx_by_day = {d: np.where(day == d)[0] for d in udays}
    for j, d in enumerate(udays):
        src_rows = idx_by_day[udays[perm[j]]]     # donor day's rows
        dst_rows = idx_by_day[d]
        # match by intraday position (wrap if donor shorter)
        donor = src_rows[np.arange(len(dst_rows)) % len(src_rows)]
        rp2[dst_rows, BASE_PRIOR:] = rp[donor, BASE_PRIOR:]
    return rp2


@torch.no_grad()
def infer(model, device, xf, xr, xp, rp):
    """Batched inference -> q50 (N,)."""
    N = xf.shape[0]; out = []
    for s in range(0, N, 512):
        e = min(s + 512, N)
        b_xf = torch.from_numpy(xf[s:e]).to(device)
        b_xr = torch.from_numpy(xr[s:e]).to(device)
        b_xp = torch.from_numpy(xp[s:e]).to(device)
        b_rp = torch.from_numpy(rp[s:e]).to(device)
        o = _forward_dual(model, b_xf, b_xr, b_rp, b_xp)
        out.append(o["quantiles"][:, 1].cpu().numpy())
    return np.concatenate(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--norm", required=True)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    a = ap.parse_args()
    device = "cuda" if torch.cuda.is_available() else "cpu"

    cfg = json.load(open(a.config)); data_cfg = cfg["data"]; train_cfg = cfg["training"]
    model_cfg = cfg.get("model", {})
    npz_dir = data_cfg["npz_dir"]
    embargo = int(train_cfg.get("embargo_days", 0))
    _hsec = data_cfg.get("horizons_sec"); horizons = [f"y_{int(h)}" for h in _hsec] if _hsec else ["y_600"]

    days = [p.stem for p in sorted(__import__("pathlib").Path(npz_dir).glob("*.npz")) if p.stem[0].isdigit()]
    fold = _build_folds(days, train_cfg, embargo)[0]

    nz = np.load(a.norm); x_mean, x_std = nz["x_mean"], nz["x_std"]
    y_norm = (float(nz["y_median"]), float(nz["y_sigma"]), 5.0)
    # _common_ds_kwargs already carries state_prior_dir / align_target_dir (0A wired).
    common = dict(normalize=True, x_mean=x_mean, x_std=x_std, y_norm=y_norm, preload=True,
                  **_common_ds_kwargs(data_cfg, horizons))
    test_ds = DualLOBDataset(npz_dir, fold["test"], **common)

    s0 = test_ds._load_day(0)
    model = build_dual_lob_model(model_cfg, int(s0["X"].shape[-1]), int(s0["X_raw"].shape[-2]))
    ck = torch.load(a.ckpt, map_location=device, weights_only=False)
    model.load_state_dict(ck["state"] if isinstance(ck, dict) and "state" in ck else ck)
    model.to(device).eval()
    print(f"[permute-null] rs_fitted={float(getattr(model,'rs_fitted',torch.tensor([0.]))[0]):.0f} "
          f"d_prior={model.d_prior} test_days={len(fold['test'])}")

    # collect test tensors in dataset order
    loader = DataLoader(test_ds, batch_size=1024, shuffle=False)
    XF, XR, XP, RP, Y, M = [], [], [], [], [], []
    for batch in loader:
        xf, xr, rp, y, m, xp = batch  # DualLOBDataset 6-tuple (regime_prior present)
        XF.append(xf.numpy()); XR.append(xr.numpy()); XP.append(xp.numpy())
        RP.append(rp.numpy()); Y.append(y.numpy()); M.append(m.numpy())
    xf = np.concatenate(XF); xr = np.concatenate(XR); xp = np.concatenate(XP)
    rp = np.concatenate(RP); y = np.concatenate(Y); m = np.concatenate(M)
    ts = test_ds.get_all_timestamps()
    keep = m.astype(bool)

    # REAL
    q_real = infer(model, device, xf, xr, xp, rp)
    dP, cd, b, sg = score(q_real[keep], y[keep], ts[keep])
    print(f"\n  REAL            cd-CLEAN={cd:+.4f} DENSE={dP:+.4f} beta={b:+.3f} sigma={sg:.3f}")
    # PERMUTED
    cds = []
    for seed in a.seeds:
        rp_p = permute_state_by_day(rp, ts, seed)
        q_p = infer(model, device, xf, xr, xp, rp_p)
        dP2, cd2, b2, sg2 = score(q_p[keep], y[keep], ts[keep])
        cds.append(cd2)
        print(f"  PERMUTED seed={seed}  cd-CLEAN={cd2:+.4f} DENSE={dP2:+.4f} beta={b2:+.3f} sigma={sg2:.3f}")
    print(f"\n  real cd={cd:+.4f}  permuted mean cd={np.mean(cds):+.4f}  drop={cd-np.mean(cds):+.4f} "
          f"({100*(cd-np.mean(cds))/max(abs(cd),1e-9):.0f}% of real)")
    print("DONE_PERMUTE_NULL.")


if __name__ == "__main__":
    main()

"""ARM P tests: (1) projection unit test (conflict -> aux orthogonalised to primary;
no-conflict -> unchanged); (2) end-to-end pcgrad backward sets finite .grad on the
shared trunk and returns a finite proxy loss."""
import json, glob, os
import numpy as np
import torch
torch.backends.mkldnn.enabled = False
from torch.utils.data import DataLoader
from multi_asset.data.dual_lob_dataset import DualLOBDataset
from multi_asset.train.train_dual_lob import (
    _common_ds_kwargs, build_dual_lob_model, _forward_dual, _build_loss_fn_for_dul)
from multi_asset.train.pcgrad import pcgrad_multi_horizon_backward


def _proj(gi, gp):
    dot = gi.dot(gp)
    if dot < 0:
        gi = gi - (dot / (gp.dot(gp) + 1e-12)) * gp
    return gi


def unit_test():
    gp = torch.tensor([1.0, 0.0, 0.0])
    conflict = torch.tensor([-0.5, 1.0, 0.0])       # dot = -0.5 < 0
    p = _proj(conflict, gp)
    d_after = float(p.dot(gp))
    align = torch.tensor([0.5, 1.0, 0.0])           # dot = +0.5 > 0
    p2 = _proj(align, gp)
    ok = abs(d_after) < 1e-6 and torch.allclose(p2, align)
    print(f"PROJECTION unit: conflict dot-after={d_after:.2e} (expect 0), align-unchanged={torch.allclose(p2, align)} -> {'PASS' if ok else 'FAIL'}")
    return ok


def e2e_test():
    c = json.load(open("configs/d1gate/aux_2026_01.json")); d = c["data"]; mc = c["model"]
    days = [os.path.basename(f)[:-4] for f in sorted(glob.glob("data/npz_v2arch_align/2026-01-1*.npz"))][:2]
    nz = np.load("experiments/d1gate/d1_2026_01_run2/fold_0/norm_params.npz")
    yn = (float(nz["y_median"]), float(nz["y_sigma"]), 5.0)
    common = dict(normalize=True, x_mean=nz["x_mean"], x_std=nz["x_std"], y_norm=yn,
                  **_common_ds_kwargs(d, ["y_600"]))
    ds = DualLOBDataset("data/npz_v2arch", days, **common)
    s0 = ds._load_day(0)
    model = build_dual_lob_model(mc, int(s0["X"].shape[-1]), int(s0["X_raw"].shape[-2]))
    model.train()
    opt = torch.optim.Adam(model.parameters(), lr=1e-4)
    loss_fn = _build_loss_fn_for_dul(c["training"]["dul_config"])
    xf, xr, rp, y, m, xp = next(iter(DataLoader(ds, batch_size=16, shuffle=False)))
    out = _forward_dual(model, xf, xr, rp, xp, all_horizons=True)
    proxy = pcgrad_multi_horizon_backward(model, opt, out, y, m, loss_fn,
                                          horizon_weights=[0.3, 1.0], primary_idx=1)
    # shared trunk params should have finite, non-None grads
    shared = [p for n, p in model.named_parameters() if "backbone" in n and p.requires_grad]
    have = [p.grad is not None and torch.isfinite(p.grad).all() for p in shared]
    frac = sum(have) / max(len(have), 1)
    gnorm = torch.sqrt(sum((p.grad**2).sum() for p in shared if p.grad is not None)).item()
    ok = (proxy is not None) and np.isfinite(proxy) and frac > 0.8 and np.isfinite(gnorm) and gnorm > 0
    print(f"E2E pcgrad: proxy={proxy:.4f} trunk-grad-finite-frac={frac:.2f} trunk-gnorm={gnorm:.3e} -> {'PASS' if ok else 'FAIL'}")
    return ok


def main():
    a = unit_test()
    b = e2e_test()
    print("ALL_PCGRAD_TESTS_PASS" if (a and b) else "PCGRAD_TESTS_FAIL")


if __name__ == "__main__":
    main()

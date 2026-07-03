"""CPU forward smoke for ALIGN-as-AUX: build model (state+gain+n_horizons=2),
forward all_horizons + primary-only, compute the multi-horizon loss. De-risks the
untested state(d24)+gain+2-horizon combination before a GPU slot is spent."""
import json, os, glob
import numpy as np
import torch
torch.backends.mkldnn.enabled = False   # CPU conformer conv: avoid mkldnn primitive failure
from torch.utils.data import DataLoader
from multi_asset.data.dual_lob_dataset import DualLOBDataset
from multi_asset.train.train_dual_lob import (
    _common_ds_kwargs, build_dual_lob_model, _forward_dual, _multi_horizon_loss,
    _build_loss_fn_for_dul)

c = json.load(open("configs/d1gate/aux_2026_01.json")); d = c["data"]; mc = c["model"]
days = [os.path.basename(f)[:-4] for f in sorted(glob.glob("data/npz_v2arch_align/2026-01-1*.npz"))][:2]
nz = np.load("experiments/d1gate/d1_2026_01_run2/fold_0/norm_params.npz")
yn = (float(nz["y_median"]), float(nz["y_sigma"]), 5.0)
common = dict(normalize=True, x_mean=nz["x_mean"], x_std=nz["x_std"], y_norm=yn,
              **_common_ds_kwargs(d, ["y_600"]))
ds = DualLOBDataset("data/npz_v2arch", days, **common)
s0 = ds._load_day(0)
model = build_dual_lob_model(mc, int(s0["X"].shape[-1]), int(s0["X_raw"].shape[-2]))
print("model n_horizons:", getattr(model, "n_horizons", 1),
      "| output_gain:", getattr(model, "use_output_gain", None),
      "| state_prior:", getattr(model, "use_state_prior", None))
if hasattr(model, "fit_regime_state_stats"):
    model.fit_regime_state_stats(ds)
    print("regime-state fit rs_fitted =", float(model.rs_fitted[0]))

loader = DataLoader(ds, batch_size=8, shuffle=False)
xf, xr, rp, y, m, xp = next(iter(loader))
model.eval()
with torch.no_grad():
    out_all = _forward_dual(model, xf, xr, rp, xp, all_horizons=True)
    out_pri = _forward_dual(model, xf, xr, rp, xp)

qh = out_all.get("quantiles_by_horizon")
n_emit = (len(qh) if hasattr(qh, "__len__") else getattr(qh, "shape", None)) if qh is not None else None
print("all_horizons: quantiles_by_horizon present =", qh is not None, "| n_emit =", n_emit)
pri_shape = tuple(out_pri["quantiles"].shape)
print("primary-only quantiles shape =", pri_shape, "(expect [8,3])")

ok_loss = False
try:
    loss_fn = _build_loss_fn_for_dul(c["training"]["dul_config"])
    loss = _multi_horizon_loss(out_all, y, m, loss_fn, [0.3, 1.0])
    lv = float(loss[0] if isinstance(loss, (tuple, list)) else loss)
    ok_loss = np.isfinite(lv)
    print("multi-horizon loss (hw=[0.3,1.0]) =", round(lv, 4), "finite =", ok_loss)
except Exception as e:
    print("LOSS_ERR:", repr(e))

print("FORWARD_SMOKE_OK" if (ok_loss and pri_shape[-1] == 3) else "FORWARD_SMOKE_FAIL")

import json, torch, numpy as np
torch.backends.mkldnn.enabled = False
from torch.utils.data import DataLoader
from multi_asset.data.dual_lob_dataset import DualLOBDataset
from multi_asset.train.train_dual_lob import build_dual_lob_model, _forward_dual
from src.training.trainer_v2 import _build_loss_fn_for_dul, _multi_horizon_loss
cfg = json.load(open("configs/arms/mh180_2026_01.json"))
mc, tc = cfg["model"], cfg["training"]
dev = torch.device("cpu")
ds = DualLOBDataset("data/npz_v2arch", ["2026-01-10","2026-01-11"], normalize=True,
        x_mean=np.zeros(88,np.float32), x_std=np.ones(88,np.float32),
        y_norm=(0.0, 1.35e-3, 5.0), horizons=["y_180","y_600"],
        y180_sidecar_dir="data/npz_v2arch_y180", preload=False)
s0 = ds._load_day(0); nf=int(s0["X"].shape[-1]); nl=int(s0["X_raw"].shape[-2])
model = build_dual_lob_model(mc, nf, nl).to(dev)
print("n_horizons:", model.n_horizons, "primary_idx:", model.primary_horizon_idx)
loss_fn = _build_loss_fn_for_dul(tc["dul_config"]); hw = tc["dul_config"]["horizon_weights"]
batch = next(iter(DataLoader(ds, batch_size=32, shuffle=False)))
x_feat, x_raw, rp, y, mask, x_perp = batch
print("batch y shape:", tuple(y.shape), "(expect (32,2))")
out = _forward_dual(model, x_feat, x_raw, rp, x_perp, all_horizons=True)
print("quantiles_by_horizon:", tuple(out["quantiles_by_horizon"].shape),
      "point_pred (primary):", tuple(out["point_pred"].shape))
loss = _multi_horizon_loss(out, y, mask, loss_fn, hw)
print("MH loss=%.5f finite=%s" % (float(loss.item()), bool(torch.isfinite(loss))))
loss.backward()
gn = sum((p.grad.norm().item()**2) for p in model.parameters() if p.grad is not None)**0.5
print("backward OK grad_norm=%.4f | MH180 FORWARD+LOSS: OK" % gn)

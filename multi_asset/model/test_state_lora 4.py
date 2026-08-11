"""ARM L mandatory tests: bit-identity (flag-on init == unwrapped base output) +
batch-invariance (per-sample gate => no cross-sample leakage, eval mode) + a
liveness check (nonzero B actually changes the output => the LoRA is wired)."""
import json, glob, os
import numpy as np
import torch
torch.backends.mkldnn.enabled = False
from torch.utils.data import DataLoader
from multi_asset.data.dual_lob_dataset import DualLOBDataset
from multi_asset.train.train_dual_lob import _common_ds_kwargs, build_dual_lob_model, _forward_dual
from multi_asset.model.state_lora import StateLoRALinear


def _batch():
    c = json.load(open("configs/d1gate/d1_2026_01_run2.json"))  # Run2 (state+gain, d_prior=24)
    d = c["data"]
    days = [os.path.basename(f)[:-4] for f in sorted(glob.glob("data/npz_v2arch_state/2026-01-1*.npz"))][:1]
    nz = np.load("experiments/d1gate/d1_2026_01_run2/fold_0/norm_params.npz")
    yn = (float(nz["y_median"]), float(nz["y_sigma"]), 5.0)
    common = dict(normalize=True, x_mean=nz["x_mean"], x_std=nz["x_std"], y_norm=yn,
                  **_common_ds_kwargs(d, ["y_600"]))
    ds = DualLOBDataset("data/npz_v2arch", days, **common)
    s0 = ds._load_day(0)
    mc = dict(c["model"]); mc["use_state_lora"] = True; mc["lora_rank"] = 4; mc["lora_which"] = "ffn2"
    model = build_dual_lob_model(mc, int(s0["X"].shape[-1]), int(s0["X_raw"].shape[-2]))
    model.eval()
    loader = DataLoader(ds, batch_size=12, shuffle=False)
    xf, xr, rp, y, m, xp = next(iter(loader))
    return model, xf, xr, rp, xp


def main():
    model, xf, xr, rp, xp = _batch()
    n_lora = sum(p.numel() for n, p in model.named_parameters()
                 if "_lora_adapters" in n or "lora_hypernet" in n or (".A" in n) or (".B" in n))
    # count adapters
    adapters = model._lora_adapters
    lora_params = sum(a.A.numel() + a.B.numel() for a in adapters) + \
        sum(p.numel() for p in model.lora_hypernet.parameters())
    print(f"use_state_lora={model.use_state_lora} n_adapters={len(adapters)} lora_params={lora_params}")

    with torch.no_grad():
        out_on = _forward_dual(model, xf, xr, rp, xp)["quantiles"].clone()

    # (1) BIT-IDENTITY: unwrap adapters (restore .base linears) -> output must match
    #     exactly (B is zero-init so the delta is 0 at init).
    for a in adapters:
        # find the parent ffn holding this adapter and restore the base linear
        pass
    # unwrap by walking backbone blocks
    for blk in model.backbone.blocks:
        for fn in ("ffn1", "ffn2"):
            ffn = getattr(blk, fn, None)
            if ffn is None:
                continue
            for ln in ("fc1", "fc2"):
                mod = getattr(ffn, ln, None)
                if isinstance(mod, StateLoRALinear):
                    setattr(ffn, ln, mod.base)
    model.use_state_lora = False
    with torch.no_grad():
        out_off = _forward_dual(model, xf, xr, rp, xp)["quantiles"].clone()
    d_bit = (out_on - out_off).abs().max().item()
    print(f"BIT-IDENTITY max|on-off| = {d_bit:.3e}  -> {'PASS' if d_bit < 1e-6 else 'FAIL'}")

    # rebuild for the remaining tests
    model, xf, xr, rp, xp = _batch()
    # (2) LIVENESS: set B to nonzero -> output MUST change (proves the LoRA is wired)
    with torch.no_grad():
        base_out = _forward_dual(model, xf, xr, rp, xp)["quantiles"].clone()
        for a in model._lora_adapters:
            a.B.data.normal_(0, 0.1)
        live_out = _forward_dual(model, xf, xr, rp, xp)["quantiles"].clone()
    d_live = (base_out - live_out).abs().max().item()
    print(f"LIVENESS max|Δ| with nonzero B = {d_live:.3e}  -> {'PASS' if d_live > 1e-5 else 'FAIL'}")

    # (3) BATCH-INVARIANCE (eval mode, nonzero B so the gate matters): sample i run
    #     alone == sample i in the batch (gate depends only on state_i).
    with torch.no_grad():
        full = _forward_dual(model, xf, xr, rp, xp)["quantiles"]
        worst = 0.0
        for i in [0, 5, 11]:
            one = _forward_dual(model, xf[i:i+1], xr[i:i+1], rp[i:i+1], xp[i:i+1])["quantiles"]
            worst = max(worst, (full[i] - one[0]).abs().max().item())
    print(f"BATCH-INVARIANCE worst|batch-single| = {worst:.3e}  -> {'PASS' if worst < 1e-5 else 'FAIL'}")

    ok = d_bit < 1e-6 and d_live > 1e-5 and worst < 1e-5
    print("ALL_LORA_TESTS_PASS" if ok else "LORA_TESTS_FAIL")


if __name__ == "__main__":
    main()

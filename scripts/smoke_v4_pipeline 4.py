"""1-fold, 1-epoch smoke test for V4 pipeline on tiny synthetic NPZs."""
import os, sys, tempfile, subprocess, json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    with tempfile.TemporaryDirectory() as tmp:
        npz_dir = os.path.join(tmp, "npz")
        os.makedirs(npz_dir)
        rng = np.random.default_rng(0)
        n_levels = 20
        # 4 days x 200 windows each for 1 train / 1 val / 1 test fold + buffer
        for d in range(4):
            date = f"2024-01-{d+1:02d}"
            n = 200
            np.savez_compressed(
                os.path.join(npz_dir, f"{date}.npz"),
                X=rng.normal(size=(n, 60, 64)).astype(np.float32),
                X_raw=rng.normal(size=(n, 60, n_levels, 4)).astype(np.float32),
                y_60=rng.normal(0, 0.001, n).astype(np.float32),
                y_180=rng.normal(0, 0.001, n).astype(np.float32),
                y_mask_60=np.ones(n, dtype=np.uint8),
                y_mask_180=np.ones(n, dtype=np.uint8),
                y=rng.normal(0, 0.001, n).astype(np.float32),
                y_mask=np.ones(n, dtype=np.uint8),
                regime_prior=rng.normal(size=(n, 6)).astype(np.float32),
                timestamps=(np.arange(n, dtype=np.int64) + d * n) * 1_000_000,
                features=np.array([f"f{i}" for i in range(64)], dtype=object),
            )

        config = {
            "data": {
                "csv_path": "",
                "npz_dir": npz_dir,
                "n_levels": n_levels,
                "horizon_sec": 180,
                "input_len": 60,
                "stride": 10,
                "horizons_sec": [60, 180],
            },
            "model": {
                "d_model": 16,
                "d_raw": 8,
                "n_mask_blocks": 1,
                "n_cross_layers": 1,
                "patch_size": 5,
                "attn_nhead": 2,
                "attn_d_ff": 32,
                "d_prior": 6,
                "dropout": 0.0,
                "n_horizons": 2,
                "n_symbols": 1,
                "use_monotonic_quantile": True,
                "use_revin": True,
                "use_masknet": False,
                "use_gdcn": True,
                "use_raw_path": True,
                "use_attention": True,
                "use_conv": True,
                "use_channel_mix_conv": True,
                "use_level_attention_pool": True,
                "use_patch_attention_pool": True,
                "use_ppnet_gate": True,
            },
            "training": {
                "epochs": 1,
                "batch_size": 8,
                "lr": 1e-3,
                "weight_decay": 0.0,
                "patience": 2,
                "grad_clip": 1.0,
                "train_days": 2,
                "val_days": 1,
                "test_days": 1,
                "fold_stride": 1,
                "dul_config": {
                    "lambda_quantile": 1.0,
                    "lambda_utility_rank": 0.3,
                    "lambda_calib": 0.0,
                    "utility_alpha": 1.0,
                },
            },
            "output_dir": os.path.join(tmp, "out"),
        }
        cfg_path = os.path.join(tmp, "cfg.json")
        with open(cfg_path, "w") as f:
            json.dump(config, f)

        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        res = subprocess.run(
            ["python3", "run_pipeline_v3.py", "--config", cfg_path,
             "--skip-features", "--model", "V3"],
            capture_output=True, text=True, cwd=repo_root, timeout=300,
        )
        print("STDOUT tail:")
        print(res.stdout[-3000:])
        print("STDERR tail:")
        print(res.stderr[-2000:])
        if res.returncode != 0:
            raise AssertionError(f"Smoke test failed with returncode {res.returncode}")

        import torch
        ckpt = torch.load(os.path.join(config["output_dir"], "fold_0", "best_model.pt"),
                          map_location="cpu", weights_only=False)
        saved_cfg = ckpt.get("config", {})
        for k in ("use_patch_attention_pool", "use_ppnet_gate",
                  "use_channel_mix_conv", "use_level_attention_pool"):
            assert saved_cfg.get(k) is True, \
                f"V4 flag {k} not persisted in checkpoint (got {saved_cfg.get(k)})"
        print(f"V4 flags in checkpoint: OK")
        print("PASS: smoke_v4_pipeline")


if __name__ == "__main__":
    main()

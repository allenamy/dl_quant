"""Generate V4 ablation configs by overriding single flags in v4_full.json."""
from __future__ import annotations
import json, os
from pathlib import Path


def _set_nested(cfg: dict, path: str, value) -> None:
    """Set cfg[a][b][c] given path='a.b.c'."""
    keys = path.split(".")
    node = cfg
    for k in keys[:-1]:
        node = node[k]
    node[keys[-1]] = value


def generate(base_path: str = "configs/v4_full.json",
             out_dir: str = "configs/v4_ablations") -> None:
    base = json.loads(Path(base_path).read_text())
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    ablations = [
        # (name, override_path, override_value, extra_notes)
        ("no_ppnet", "model.use_ppnet_gate", False, None),
        ("no_multi_horizon", "model.n_horizons", 1, "horizons_sec"),
        ("no_ridge_features", "data.include_ridge_features", False, None),
        ("no_patch_attention_pool", "model.use_patch_attention_pool", False, None),
        ("no_channel_mix", "model.use_channel_mix_conv", False, None),
        ("no_level_attention", "model.use_level_attention_pool", False, None),
        ("no_utility_rank", "training.dul_config.lambda_utility_rank", 0.0, None),
        ("plus_masknet", "model.use_masknet", True, None),
    ]

    for name, path, value, extra in ablations:
        cfg = json.loads(json.dumps(base))  # deep copy
        _set_nested(cfg, path, value)
        if extra == "horizons_sec":
            cfg["data"]["horizons_sec"] = [180]
        cfg["output_dir"] = f"experiments/v4_ablations/{name}"
        cfg["_ablation"] = name
        out_path = Path(out_dir) / f"{name}.json"
        out_path.write_text(json.dumps(cfg, indent=2))
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    generate()

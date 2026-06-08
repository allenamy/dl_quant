# Naming Convention & Single-Asset Lineage Map

> **创建:** 2026-05-20 UTC+8 | **状态:** reference
> Purpose: kill the single-asset naming ambiguity (`dual_path_v3` file vs `REG_arch`/`V5` model) before it propagates into multi-asset.

## The single-asset ambiguity (for reference)

Single-asset has TWO version axes that both used "v":

1. **Code-class lineage** (`nn.Module` rewrites):
   `DualPathLOBModel` (v1/v2, `src/model/dual_path_model.py`) → **`DualPathLOBModelV3`** (v3, `src/model/dual_path_model_v3.py`). The v3 class is the workhorse skeleton.
2. **Research generation** (flag preset + training recipe on the v3 skeleton, NOT a new class):
   V4 → V5 → **REG_arch**. All are `DualPathLOBModelV3(**flags)`.

**REG_arch (the single-asset winner) ≡** `DualPathLOBModelV3` with `backbone_kind="conformer"`, `use_film_multistage=True`, `use_direction_aware_head=True`, `use_monotonic_quantile=True`, 2 conformer blocks (kernel 15), d_model 32. Config: `configs/v5push/singh_alpha0_huber_track_reg_arch.json`. Checkpoints: `experiments/v5push/singh_daqh_lambda0/fold_*/best_model.pt`.

## Multi-asset naming rules (this project)

1. **No version letters in new code.** Name by FUNCTION, not generation. (No `_v2`/`_v3`; use dates in docs per Documentation Discipline.)
2. **"REG_arch" is retained as the architecture-preset name** (it's the recognized single-asset winner across all docs/memory) — but always means the flag-preset above, never a class.
3. **Multi-asset module names** (function-descriptive):
   - `multi_asset/model/panel_backbone.py` — the per-asset temporal encoder = the proven single-asset REG_arch backbone (imported `DualPathLOBModelV3`), applied per-symbol with shared weights. (plan called this `universal_reg_arch.py`; renamed to `panel_backbone.py` for clarity.)
   - `multi_asset/model/cross_asset_mixer.py` — cross-asset attention + market-factor token (the multi-asset-specific structure).
   - `multi_asset/data/panel_*.py` — the synchronized cross-section ("panel") pipeline.
4. **"panel"** = our term for the timestamp-synchronized (symbols × time) cross-section. Used consistently for the multi-asset data structure.
5. Single-asset symbols imported from `src.*` are referred to by their real class names (`DualPathLOBModelV3`, `CrossAssetAttention`) — never aliased to hide the lineage.

## Plan-doc → code-file name updates (supersedes plan filenames where they differ)

| Plan name | Actual file | Reason |
|:--|:--|:--|
| `model/universal_reg_arch.py` | `model/panel_backbone.py` | "universal_reg_arch" still carries version ambiguity; "panel_backbone" is function-clear |
| `model/market_factor_token.py` | `model/cross_asset_mixer.py` | consolidate cross-asset attention + market token in one clearly-named module |

(All other plan filenames stand.)

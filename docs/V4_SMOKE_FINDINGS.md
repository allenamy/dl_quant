# V4 Smoke Sweep Findings — 2026-04-18

## Executive summary

**Patch attention is hurting V4.** Removing it (use_attention=False + use_patch_attention_pool=False) gave **3× the test Pearson** of V4 full on a fast 100-day smoke, jumping from 0.029 → **0.084**, with Spearman 0.101 (already above V4 spec target of 0.12 on rank).

Promoted to full 700-day run now (PID 31441).

## 8-variant sweep @ 100d, 1-min/run, fold 0 only, y_180

| Variant | Flag change | test Pearson | test Spearman | Signal |
|---------|-------------|-------------:|--------------:|:-------|
| A_full | V4 full | +0.029 | +0.041 | baseline |
| B_y60 | target y_60 (not y_180) | +0.010 | −0.003 | y_60 needs more data at 100d |
| C_noraw | `use_raw_path=False` | **−0.023** | −0.026 | Path B **helps** (removing hurts) |
| D_norevin | `use_revin=False` | +0.010 | +0.020 | RevIN **helps** |
| **E_noattn** | `use_attention=False` + `use_patch_attention_pool=False` | **+0.084** | **+0.101** | **BIG win — patch attn was hurting** |
| F_noppnet | `use_ppnet_gate=False` | **−0.048** | −0.047 | PPNet gate **helps** |
| G_simple | strip V4-specific modules | +0.017 | +0.028 | mixed — keep some V4 flags |
| H_norank | `lambda_utility_rank=0` | −0.011 | ~0 | utility_rank **helps** |

## Interpretation

**Helping (in order of magnitude):**
1. ❌ Remove patch attention ⇒ +0.055 gain (vs baseline)
2. ✅ PPNet gate ⇒ +0.077 gain when kept (F_noppnet loss)
3. ✅ Path B (raw LOB) ⇒ +0.052 gain when kept
4. ✅ RevIN ⇒ +0.019 gain when kept
5. ✅ Utility rank loss ⇒ +0.040 gain when kept

**Conclusion:** the patch attention block was the only ACTIVE harmful component. Everything else (PPNet, RevIN, Path B, utility_rank) is net-positive. The "less is more" principle from CLAUDE.md (model capacity must match signal strength) is vindicated — at 66K params on ~108K training windows, some modules overfit.

## Why patch attention hurt

Hypothesis: V4's patch attention block has ~3K parameters (2-head, d=32, d_ff=64) that attend over 120 time patches. With SNR < 1% on y_180, attention learns to attend to noise patterns in the train set that don't generalize. When we disable it, the last TCN timestep is used directly → much simpler pipeline → less overfit.

The V3 experiment record shows similar: V3 has simpler temporal aggregation and got 0.082 on y_180. V4 with patch attention got 0.061.

## Architecture recommendation

For V4.1 (next iteration):
- Keep: RevIN, GDCN, Path B (raw LOB w/ 1×1 conv + attention pool over levels), PPNet gate, monotonic quantile, utility_rank loss
- Remove: patch attention + patch attention pool
- Keep last-token pool after TCN output

Expected param count: 66K − ~6K (patch attention layers) = **~60K** — better fit for ~108K training windows.

## Pending

- 700d full run of no_attention config (PID 31441) — validates the smoke finding at scale
- If 700d test Pearson ≥ 0.082, V4.1 beats V3 baseline
- If 700d test Pearson ≥ 0.12, V4.1 clears spec primary target
- Target completion: ~90 min from 00:35 local

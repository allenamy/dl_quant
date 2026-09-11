# VOID — v3 lineage, do not cite

These files were produced earlier in this same session against
`w10_ablation_series_pod_live_w3fix_callog_s42.npz`, arm `d30_n2_c42`, whose `config_json` reads
`SLOW_NPY = /workspace/shadow_bundle_v3/slow_pred_pinned.npy` and `W3FIX = "0.21,0,0.79"` (FIXED seat).

Two defects against the pinned 2026-09-09 caliber:
1. v3 king predictions (`shadow_bundle_v3`) — superseded by the v4 chain.
2. FIXED seat 0.21, while the live book uses a DYNAMIC seat (msharpe). The task's own A0 baseline table
   is the dynamic-seat row.

Every number in `leadlag.json` and `g1_incremental.json` is therefore VOID. The v4 replacements are in
`../devices_v4/` and the conclusions they support differ in kind: at v4 the σ_fund family FAILS the
frozen G1 lead test that it passed at v3.

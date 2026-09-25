Independent beta parity gate (lead ruling 2026-09-25), device nc_v2_beta_parity.py 70faeebe (committed 24175c371 before the run).
Command (verbatim, cwd = quant_research):
  ~/wide_shadow/venv/bin/python -B multi_asset/exports/research/nc_2026-09-23/devices/nc_v2_beta_parity.py ~/cc_tmp/nc_20260923/treeNC6 ~/cc_tmp/nc_20260923/v2gate_20260925T0503Z multi_asset/exports/research/nc_2026-09-23/receipts/m3v2_beta_parity_2026-09-25/NC_V2_BETA_PARITY.json > …/stdout.log 2>&1; echo "beta parity rc=$?"
  → 05:15:51–05:15:56Z · beta parity rc=0 · NC_V2_BETA_PARITY PASS anchors=6
  per anchor: BASELINE served==direct GREEN (0 betas / 0 n_obs differing, counters equal, served version m3_beta_v2, n 450);
  RED control (clipped input) DETECTED: 7 names differ (boundary table cells 15).
  SERVED = the v2 sandbox fields of gate 3' run 2 (v2gate_20260925T0503Z).

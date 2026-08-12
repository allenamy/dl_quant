#!/bin/bash
# OI-as-REGIME DL test (FiLM consumes regime_prior[14] = 6 vol + 8 designed OI/funding).
# DISK-SAFE SEQUENTIAL: build a SEPARATE partial OI cache for one fold's exact date
# range, train+eval that fold, DELETE the cache, then the next fold. Never holds both
# ~70G OI caches at once (105G free; strong ~64G, choppy ~74G — sequential fits).
# The SHARED caches (data/npzv4_dual, data/npz_v2arch) are NEVER touched.
#
# STRONG : npzv4_dual -> npzv4_dual_oi (2023-02-15..2025-05-12, covers train700+val+test
#          for test 2025-04-10), trainer=train_v2arch (matches richreg_strong/adaptive).
# CHOPPY : npz_v2arch -> npz_v2arch_oi (2025-05-15..2026-05-31, covers train300+val+test
#          for test 2026-05-01), trainer=train_dual_lob (matches richreg_choppy/adaptive).
#
# Chains AFTER 'RICH-REGIME COMPLETE'. Each train via nw0/preload. Dual-caliber EMA eval
# vs adaptive baselines: STRONG 0.0747/0.1054 (P/S), CHOPPY 0.0402.
# Launch (setsid-friendly): setsid bash multi_asset/scripts/run_oi_filmdl.sh &
cd /mnt/storage/private/work_hsy/quant_research_multi_asset || exit 1
PY=/root/miniconda3/envs/hsy_v5push/bin/python
export PYTHONPATH=.
exec > /tmp/oi_filmdl.log 2>&1
echo "=== OI-FILMDL runner $(date) ==="

# block while ANY trainer or GPU app is running (shared single 3090).
wait_clear () {
  while pgrep -f "train_v2arch.py|train_dual_lob.py" >/dev/null 2>&1 \
     || [ "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | grep -c .)" != "0" ]; do
    sleep 20
  done
}

# build a SEPARATE partial OI cache (CPU only; never edits src). Aborts on failure.
build_oi () {
  local src=$1 dst=$2 start=$3 end=$4 label=$5
  echo "=== BUILD ${label}: data/${src} -> data/${dst} [${start}..${end}] $(date) ==="
  CUDA_VISIBLE_DEVICES="" $PY -u multi_asset/data/add_oi_regime_prior.py \
      --src "${src}" --dst "${dst}" --start "${start}" --end "${end}" --apply \
      || { echo "BUILD FAILED ${label}"; return 1; }
  echo "=== BUILD ${label} done: $(ls data/${dst}/*.npz 2>/dev/null | wc -l) day(s), $(du -sh data/${dst} 2>/dev/null | cut -f1) $(date) ==="
  df -h . | tail -1
}

# train one fold + dual-caliber EMA eval.
train_eval () {
  local trainer=$1 cfg=$2 out=$3 label=$4
  wait_clear
  echo "=== LAUNCH ${label} (${trainer}) $(date) ==="
  $PY -u multi_asset/train/${trainer}.py --config "${cfg}" \
      --start-fold 0 --max-folds 1 --seed 42 > /tmp/oi_${label}.log 2>&1 < /dev/null
  local pf="${out}/fold_0/test_preds.npz"
  echo "=== EVAL ${label} (dual-caliber EMA; baselines STRONG 0.0747/0.1054, CHOPPY 0.0402) $(date) ==="
  if [ -f "$pf" ]; then $PY multi_asset/eval/eval_caliber.py --preds "$pf" --ema 2>&1
  else echo "MISSING ${label} preds"; tail -8 /tmp/oi_${label}.log; fi
  echo "=== DONE ${label} $(date) ==="
}

echo "=== wait for REGIME-MoE COMPLETE (reordered: OI-FiLM-DL is secondary, after the MoE main direction) ==="
while ! grep -q "REGIME-MoE COMPLETE" /tmp/moe_dl.log 2>/dev/null; do sleep 60; done
echo "=== rich-regime done, starting OI-FILMDL $(date) ==="

# ---------- STRONG (npzv4_dual_oi) ----------
if build_oi npzv4_dual npzv4_dual_oi 2023-02-15 2025-05-12 strong; then
  train_eval train_v2arch configs/npzv4_dual/perp_dp32_a02_oiregime_2025_04.json \
             experiments/npzv4_dual/perp_dp32_a02_oiregime_2025_04 oiregime_strong
fi
echo "=== DELETE data/npzv4_dual_oi (free disk before choppy) $(date) ==="
rm -rf data/npzv4_dual_oi
df -h . | tail -1

# ---------- CHOPPY (npz_v2arch_oi) ----------
if build_oi npz_v2arch npz_v2arch_oi 2025-05-15 2026-05-31 choppy; then
  train_eval train_dual_lob configs/v2arch/dp32_oiregime_2026_05.json \
             experiments/v2arch_dp32/dp32_oiregime_2026_05 oiregime_choppy
fi
echo "=== DELETE data/npz_v2arch_oi (free disk) $(date) ==="
rm -rf data/npz_v2arch_oi
df -h . | tail -1

echo "=== OI-FILMDL COMPLETE $(date) ==="

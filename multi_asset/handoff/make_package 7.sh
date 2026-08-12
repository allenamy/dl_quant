#!/bin/bash
# make_package.sh — assemble the self-contained multi-asset-v2 handoff package.
#
# The source repo carries ~5 months of research history; the partner only needs the transfer set.
# This copies exactly that set (curated from MANIFEST + the runtime import closure) into a clean
# tree -> handoff_package_v1.tar.gz. Regenerable: re-run any time the handoff files change.
#
# 0B, 2026-07-19. Usage: bash multi_asset/handoff/make_package.sh
set -euo pipefail

M=/mnt/storage/private/work_hsy/quant_research_multi_asset
H=$M/multi_asset/handoff
E=$M/multi_asset/engine
D=$M/multi_asset/data
PKG=$M/handoff_package_v1
TAR=$M/handoff_package_v1.tar.gz

echo "[pkg] clean $PKG"
rm -rf "$PKG"
mkdir -p "$PKG"/{battery,docs,engine/live,checkpoints}
mkdir -p "$PKG"/pipeline/multi_asset/{data,train,model,losses}
mkdir -p "$PKG"/pipeline/src/model/backbones

blurb() { printf '%s\n' "$2" > "$PKG/$1/_ABOUT.txt"; }

# ---------------------------------------------------------------- battery (self-contained)
cp "$H/acceptance_battery.py" "$H/acceptance_battery_SPEC.md" "$H/acceptance_thresholds_0C_frozen.json" "$PKG/battery/"
blurb battery "Automated model-acceptance battery. Run: python acceptance_battery.py --self-test --champion <king_dir> (expect SELF-TEST OK), then --candidate <dir> --champion <king_dir> to gate a retrain. Self-contained (numpy/pandas/scipy). SPEC + frozen thresholds are the pre-registration contract (0C)."

# ---------------------------------------------------------------- docs
cp "$H/REPRODUCTION.md" "$H/RUNBOOK.md" "$H/MANIFEST.md" "$H/PRIMER.md" "$PKG/docs/"
blurb docs "PRIMER.md = start here (what the system is + mechanism). REPRODUCTION.md = data->panel->train->eval->engine with checkpoints. RUNBOOK.md = weights/execution/pilot. MANIFEST.md = asset inventory + data licensing."

# ---------------------------------------------------------------- engine (six-piece + live)
for f in signal_chain vol_gate isotonic_calib ic_monitor funding_risk netting panel_source replay_fullhist exp_funding_weighting __init__; do
  cp "$E/$f.py" "$PKG/engine/" 2>/dev/null || echo "  [warn] missing engine/$f.py"
done
cp "$E/README.md" "$PKG/engine/"
for f in datasource funding_derive build_tail __init__; do
  cp "$E/live/$f.py" "$PKG/engine/live/" 2>/dev/null || echo "  [warn] missing engine/live/$f.py (live shadow WIP)"
done
blurb engine "The six-piece signal->execution engine (C1 signal_chain / C2 vol_gate / C3 isotonic_calib / C4 ic_monitor / C5 funding_risk / C6 netting) + panel_source (data layer) + replay_fullhist (driver) + README.md (READ its caliber verdict first). live/ = the CDN-T+1 live-shadow ingest (pluggable DataSource; swap RESTDataSource on unfirewalled infra). NOTE: panel_source.py has hardcoded server paths — edit them for your infra."

# ---------------------------------------------------------------- pipeline (build + train chain)
for f in build_wide_dl wide_factory wide_panel_dataset build_wide_panel dump_wide_universe \
         dump_funding_metrics_panel download_wide_metrics build_wide_metrics_channels \
         repair_cdn_enum densify_s2_cl4 __init__; do
  cp "$D/$f.py" "$PKG/pipeline/multi_asset/data/" 2>/dev/null || echo "  [warn] missing data/$f.py"
done
cp "$M/multi_asset/exports/eda/king_pred_panel.py" "$PKG/pipeline/multi_asset/data/" 2>/dev/null || echo "  [warn] missing king_pred_panel.py"
cp "$M/multi_asset/train/train_wide_harness.py" "$M/multi_asset/train/__init__.py" "$PKG/pipeline/multi_asset/train/" 2>/dev/null || true
for f in wide_harness temporal_spatial_panel cross_asset_panel __init__; do
  cp "$M/multi_asset/model/$f.py" "$PKG/pipeline/multi_asset/model/" 2>/dev/null || echo "  [warn] missing model/$f.py"
done
cp "$M/multi_asset/losses/xsec_residual_loss.py" "$M/multi_asset/losses/__init__.py" "$PKG/pipeline/multi_asset/losses/" 2>/dev/null || true
cp "$M/multi_asset/__init__.py" "$PKG/pipeline/multi_asset/" 2>/dev/null || true
# src/model closure (imported by the model)
cp "$M/src/__init__.py" "$PKG/pipeline/src/" 2>/dev/null || touch "$PKG/pipeline/src/__init__.py"
cp "$M/src/model/__init__.py" "$PKG/pipeline/src/model/" 2>/dev/null || touch "$PKG/pipeline/src/model/__init__.py"
for f in attention_pool direction_aware_quantile_head raw_lob_encoder; do
  cp "$M/src/model/$f.py" "$PKG/pipeline/src/model/" 2>/dev/null || echo "  [warn] missing src/model/$f.py"
done
cp "$M/src/model/backbones/__init__.py" "$PKG/pipeline/src/model/backbones/" 2>/dev/null || touch "$PKG/pipeline/src/model/backbones/__init__.py"
cp "$M/src/model/backbones/conformer_backbone.py" "$PKG/pipeline/src/model/backbones/" 2>/dev/null || echo "  [warn] missing conformer_backbone.py"
blurb pipeline "The code that turns raw Binance data into the panel, trains king/S2, and stitches the prediction panels. Preserves the multi_asset/ + src/ import layout — run with PYTHONPATH=pipeline:pipeline/multi_asset. Exact CLI in docs/REPRODUCTION.md. Paths inside are hardcoded to the source server; edit for your infra."

# ---------------------------------------------------------------- README + repo index
cp "$H/PACKAGE_README.md" "$PKG/README.md"

# ---------------------------------------------------------------- checkpoints manifest (md5, files NOT bundled)
CK="$PKG/checkpoints/CHECKPOINTS.md"
{
  echo "# Checkpoints & large artifacts (NOT bundled — pull by path, verify by md5)"
  echo
  echo "> These binaries are too large for the package. Retrain to reproduce them (docs/REPRODUCTION.md),"
  echo "> or copy them from the source server at the paths below and verify the md5."
  echo
  echo "| artifact | server path | bytes | md5 |"
  echo "|---|---|---|---|"
} > "$CK"
manifest_row() {  # $1 = path
  if [ -f "$1" ]; then
    sz=$(stat -c%s "$1"); m=$(md5sum "$1" | cut -c1-32)
    echo "| $(basename "$1") | \`$1\` | $sz | $m |" >> "$CK"
  fi
}
KING=$M/multi_asset/exports/train/wideA_lamorth0_xattn_5yr
S2=$M/multi_asset/exports/train/wideA_s2_y24_5yr
for i in 0 1 2 3 4; do manifest_row "$KING/fold_${i}_model.pt"; done
manifest_row "$KING/panel_ref.npz"
for i in 0 1 2 3 4; do manifest_row "$S2/fold_${i}_model.pt"; done
manifest_row "$S2/panel_ref.npz"
manifest_row "$M/multi_asset/exports/wide_dl_full.npz"
manifest_row "$M/multi_asset/exports/wide_panel_full.npz"
manifest_row "$M/multi_asset/exports/eda/king_pred_panel.npz"
manifest_row "$M/multi_asset/exports/eda/s2_pred_panel_cl4.npz"
{
  echo
  echo "**Champion = king** \`wideA_lamorth0_xattn_5yr\` (H=4) + **S2** \`wideA_s2_y24_5yr\` (H=24)."
  echo "The .pt are ~1MB weights; the head_scores.npz (160MB each, OOS scores) are regenerable from the .pt +"
  echo "wide_dl_full.npz via the eval path (docs/REPRODUCTION.md §4) — not listed here. The battery consumes"
  echo "either the fold-product dirs or the stitched king_pred_panel.npz."
} >> "$CK"
blurb checkpoints "CHECKPOINTS.md = server paths + md5 for the large binaries (weights/panels/pred-panels), which are NOT in this package. Retrain to reproduce, or copy by path and verify md5."

# ---------------------------------------------------------------- tar
echo "[pkg] tar -> $TAR"
cd "$M" && tar czf "$TAR" handoff_package_v1
echo "[pkg] DONE  size=$(du -h "$TAR" | cut -f1)  files=$(find "$PKG" -type f | wc -l)"
echo "[pkg] tree:"
( cd "$PKG" && find . -type f | sort | sed 's#^\./#  #' )

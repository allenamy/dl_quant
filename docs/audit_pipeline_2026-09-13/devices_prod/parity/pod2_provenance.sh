#!/bin/bash
# pod2_provenance.sh -- AUDIT_PROD: read-only provenance of the training-side builders and build reports on pod2 (sha256 + mtime), and read-only copies of the
# small build-report JSONs into receipts_prod/pod2_reports/ (no statistic). Usage: bash docs/audit_pipeline_2026-09-13/devices_prod/parity/pod2_provenance.sh
set -u
R=/Users/haosiyu/Desktop/quant_research/docs/audit_pipeline_2026-09-13/receipts_prod
mkdir -p $R/pod2_reports
OUT=$R/pod2_provenance.txt
{
echo "# pod2_provenance $(date -u +%Y-%m-%dT%H:%M:%SZ) device_sha256 $(shasum -a 256 "$0" | cut -c1-64)"
ssh -o ConnectTimeout=20 pod2 'cd /workspace && for f in pod_fea_ext.py pod_dlw_features_ext.py pod_dlw_targets_ext.py pod_f8_build_ext.py pod_f10_refit_ext.py pod_f10_np_export.py pod_f10_train_ext.py pod_export_bundle_v3.py pod_panel_ext.py f10/f8_higher_order_features.py review_scratch/pod_fea_ext_clamp.py review_scratch/pod_dlw_targets_raw.py w3_monthly_chain_2026-09-12/device/pod_fea_ext_clamp.py f8_ext/models/f10_live_s42_np.npz data/wide_panel_4h_v2ext.npz data/wide_panel_4h_v3splice.npz data/wide_fea_v2ext_meta.npz dlw_ext/data/dlw_fea82.npz f8_ext/data/f8_fea89.npz dlw_ext/data/dlw_targets.npz dlw_ext/results/dlw_features_report.json dlw_ext/results/dlw_targets_report.json f8_ext/results/f8_build_report.json uplift_2026-09-11/r6/out/dlw_hf3_x0910/results/dlw_features_report.json uplift_2026-09-11/r6/out/dlw_v4raw_x0910/results/dlw_targets_report.json uplift_2026-09-11/r6/out/f8_v4_x0910/results/f8_build_report.json; do if [ -f "$f" ]; then echo "$(sha256sum "$f" | cut -c1-64)  $(stat -c %y "$f" | cut -c1-19)  $f"; else echo "MISSING  $f"; fi; done'
} > $OUT 2>&1
for f in dlw_ext/results/dlw_features_report.json dlw_ext/results/dlw_targets_report.json f8_ext/results/f8_build_report.json uplift_2026-09-11/r6/out/dlw_hf3_x0910/results/dlw_features_report.json uplift_2026-09-11/r6/out/dlw_v4raw_x0910/results/dlw_targets_report.json uplift_2026-09-11/r6/out/f8_v4_x0910/results/f8_build_report.json; do
  n=$(echo "$f" | tr / _); scp -q "pod2:/workspace/$f" "$R/pod2_reports/$n"; echo "copy $(shasum -a 256 "$R/pod2_reports/$n" | cut -c1-64)  pod2_reports/$n" >> $OUT
done
echo "DONE rc=0" >> $OUT

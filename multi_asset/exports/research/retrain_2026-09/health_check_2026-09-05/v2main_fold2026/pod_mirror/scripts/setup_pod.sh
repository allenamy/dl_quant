#!/bin/bash
# setup_pod.sh — build the v2main_fold2026 working tree on pod2 (writes ONLY under /workspace/review_scratch/v2main_fold2026/).
set -e
ROOT=/workspace/review_scratch/v2main_fold2026; HC=/workspace/review_scratch/health_check
mkdir -p $ROOT/{scripts,preds,results,models,logs,replay}; cd $ROOT
R=$ROOT/replay; mkdir -p $R/{masks,calib,results,logs}
cp $HC/w10_health.py $R/w10_health.py; cp $HC/check_equiv.py $R/check_equiv.py; cp $HC/health_metrics.py $R/health_metrics_orig.py
cp $HC/masks/umask_UPIT.npz $HC/masks/umask_UFROZEN.npz $HC/masks/btc_rv30.npz $HC/masks/regime_series.npz $R/masks/ 2>/dev/null || true
cp $HC/calib/costb_fee_steady.json $HC/calib/costb_feeslip_steady.json $HC/calib/cost_calib.json $R/calib/
echo "--- copied device sha256 (must equal health_check's)"; sha256sum $HC/w10_health.py $R/w10_health.py $HC/health_metrics.py $R/health_metrics_orig.py $HC/masks/umask_UPIT.npz $R/masks/umask_UPIT.npz $HC/calib/costb_fee_steady.json $R/calib/costb_fee_steady.json
# dev / dev_alt: verbatim health_check layouts (same link targets); dev_alt_ext: prod meta + ext targets + own preds dir
for v in dev dev_alt dev_alt_ext; do
  d=$R/$v; mkdir -p $d/pod_backup_2026-08-21 $d/probe_artifacts $d/logs
  for f in nets_histv2_0_0_0.npy nets_histv2_-30_2_42.npy slow_pred_hist_oos.npy wide_panel_4h_hist_v2.npz; do ln -sfn /workspace/port_w10/pod_backup_2026-08-21/$f $d/pod_backup_2026-08-21/$f; done
  if [ $v = dev ]; then ln -sfn /workspace/port_w10/pod_backup_2026-08-21/wide_fea_hist_meta.npz $d/pod_backup_2026-08-21/wide_fea_hist_meta.npz
  else ln -sfn /workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz $d/pod_backup_2026-08-21/wide_fea_hist_meta.npz; fi
  if [ $v = dev_alt_ext ]; then
    mkdir -p $d/f8_2026-08-22/preds $d/dlw_2026-08-22/data
    ln -sfn /workspace/dlw_ext/data/dlw_targets.npz $d/dlw_2026-08-22/data/dlw_targets.npz
    for s in 42 2027; do ln -sfn $ROOT/preds/f10_V2MAIN_ext2026_s$s.npy $d/f8_2026-08-22/preds/f10_V2MAIN_ext2026_s$s.npy; ln -sfn $ROOT/preds/f10_V2MAIN_s${s}_padext.npy $d/f8_2026-08-22/preds/f10_V2MAIN_s${s}_padext.npy; ln -sfn /workspace/f8_ext/preds/f10_V2MAIN_s$s.npy $d/f8_2026-08-22/preds/f10_V2MAIN_ext0901_s$s.npy; done
  else ln -sfn /workspace/port_w10/f8_2026-08-22 $d/f8_2026-08-22; ln -sfn /workspace/port_w10/dlw_2026-08-22 $d/dlw_2026-08-22; fi
done
echo "--- resolved link targets vs health_check (dev, dev_alt must be SAME)"
for v in dev dev_alt; do for f in nets_histv2_0_0_0.npy nets_histv2_-30_2_42.npy slow_pred_hist_oos.npy wide_fea_hist_meta.npz wide_panel_4h_hist_v2.npz; do a=$(readlink -f $R/$v/pod_backup_2026-08-21/$f); b=$(readlink -f $HC/$v/pod_backup_2026-08-21/$f); [ "$a" = "$b" ] && echo "SAME $v/$f -> $a" || echo "DIFF $v/$f mine=$a hc=$b"; done
  for f in f8_2026-08-22 dlw_2026-08-22; do a=$(readlink -f $R/$v/$f); b=$(readlink -f $HC/$v/$f); [ "$a" = "$b" ] && echo "SAME $v/$f -> $a" || echo "DIFF $v/$f mine=$a hc=$b"; done; done
echo "--- dev_alt_ext"; find $R/dev_alt_ext -maxdepth 3 -type l -exec ls -l {} \; | awk '{print $9, $10, $11}'
# padded old preds (10086 -> 10206 rows, NaN tail) — old file untouched, read-only
/workspace/venv/bin/python - <<'PY'
import numpy as np, hashlib
TO = np.load("/workspace/data/dlw_targets.npz", allow_pickle=True); TE = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True)
Eo = TO["E_ts"].astype(np.int64); Ee = TE["E_ts"].astype(np.int64); assert np.array_equal(Ee[:len(Eo)], Eo) and [str(x) for x in TO["symbols"]] == [str(x) for x in TE["symbols"]]
for s in (42, 2027):
    src = f"/workspace/port_w10/f8_2026-08-22/preds/f10_V2MAIN_s{s}.npy"; A = np.load(src); assert A.shape == (len(Eo), 829)
    P = np.full((len(Ee), 829), np.nan, np.float32); P[:len(Eo)] = A
    dst = f"/workspace/review_scratch/v2main_fold2026/preds/f10_V2MAIN_s{s}_padext.npy"; np.save(dst, P)
    B = np.load(dst); assert np.array_equal(np.nan_to_num(B[:len(Eo)], nan=-9), np.nan_to_num(A, nan=-9)) and np.isnan(B[len(Eo):]).all()
    print("padded", dst, B.shape, "src sha", hashlib.sha256(open(src,'rb').read()).hexdigest()[:16], "dst sha", hashlib.sha256(open(dst,'rb').read()).hexdigest()[:16])
PY
/workspace/venv/bin/python -c "import torch, numpy, scipy; print('torch', torch.__version__, 'cuda', torch.version.cuda, 'avail', torch.cuda.is_available(), torch.cuda.get_device_name(0), '| numpy', numpy.__version__, 'scipy', scipy.__version__)"
echo "SETUP_DONE $(date -u +%FT%TZ)"

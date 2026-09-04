set -e
R=/workspace/review_scratch/combo_recheck; cd $R/dev
PY=/workspace/venv/bin/python; export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
TAG=equiv_canon_callog_s42
CMD="env LEGS=101 LOOK=900 WRULE=msharpe SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy FSEED=42 CAL=log OUT_TAG=$TAG $PY ../w10_universe_recheck.py"
echo "CMD[$TAG] (cwd=$R/dev): $CMD" | tee -a logs/commands.txt
env LEGS=101 LOOK=900 WRULE=msharpe SLOW_NPY=/workspace/shadow_bundle_v3/slow_pred_pinned.npy FSEED=42 CAL=log OUT_TAG=$TAG $PY ../w10_universe_recheck.py > logs/$TAG.log 2>&1 && echo "${TAG}_OK" || echo "${TAG}_FAIL"
grep -E "^CONFIG|^NOTE|RECEIPT_EX d30|^DONE" logs/$TAG.log
$PY - <<'EOP'
import numpy as np, json
a=np.load("/workspace/review_scratch/combo_recheck/dev/probe_artifacts/w10_ablation_series_equiv_canon_callog_s42.npz",allow_pickle=True)
b=np.load("/workspace/port_w10/probe_artifacts/w10_ablation_series_pod_canon_callog_s42.npz",allow_pickle=True)
for k in ("d30_n2_c42_rec","S0_rec","d30_n2_c42_W","S0_W"):
    print(k,"array_equal:",np.array_equal(a[k],b[k]),"shapes",a[k].shape,b[k].shape)
ca=json.loads(str(a["config_json"])); cb=json.loads(str(b["config_json"])); ca.pop("REF_SKIP",None)
print("config_json equal (minus REF_SKIP):",ca==cb)
EOP

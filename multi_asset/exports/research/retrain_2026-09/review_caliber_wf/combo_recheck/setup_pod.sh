set -e
R=/workspace/review_scratch/combo_recheck
mkdir -p $R/dev/pod_backup_2026-08-21 $R/dev/probe_artifacts $R/dev/logs $R/dev_alt/pod_backup_2026-08-21 $R/dev_alt/probe_artifacts $R/dev_alt/logs
for D in dev dev_alt; do
  ln -sfn /workspace/port_w10/dlw_2026-08-22 $R/$D/dlw_2026-08-22
  ln -sfn /workspace/port_w10/f8_2026-08-22 $R/$D/f8_2026-08-22
  for f in nets_histv2_-30_2_42.npy nets_histv2_0_0_0.npy slow_pred_hist_oos.npy wide_panel_4h_hist_v2.npz; do
    ln -sfn /workspace/port_w10/pod_backup_2026-08-21/$f $R/$D/pod_backup_2026-08-21/$f
  done
done
ln -sfn /workspace/port_w10/pod_backup_2026-08-21/wide_fea_hist_meta.npz $R/dev/pod_backup_2026-08-21/wide_fea_hist_meta.npz
ln -sfn /workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz $R/dev_alt/pod_backup_2026-08-21/wide_fea_hist_meta.npz
cp /workspace/port_w10/w10_universe.py $R/w10_universe_recheck.py
cat > $R/patch_refskip.py <<'EOP'
p="/workspace/review_scratch/combo_recheck/w10_universe_recheck.py"; s=open(p).read()
old1='assert TRADE_TOPN in (0, 400), f"TRADE_TOPN 白名单外: {TRADE_TOPN}"\n'
new1=old1+'REF_SKIP = int(os.environ.get("REF_SKIP", "0")); assert REF_SKIP in (0, 1)   # combo_recheck 2026-09-04: 1 = skip pod_backup reference parity (port stubs are 144-byte placeholders); self-reported in _CFG\n'
assert s.count(old1)==1; s=s.replace(old1,new1)
old2='_CFG = {"KMOD_F10": KMOD_F10,'
new2='_CFG = {"REF_SKIP": REF_SKIP, "KMOD_F10": KMOD_F10,'
assert s.count(old2)==1; s=s.replace(old2,new2)
old3='    ref = np.load(f"{B}/{reff}")\n    if WRULE == "msharpe" and LOOK == 900 and LEGS == "111":\n'
new3='    ref = np.load(f"{B}/{reff}")\n    if REF_SKIP:   # combo_recheck: reference parity skipped on request (REF_SKIP=1)\n        print(f"NOTE {nm}: REF_SKIP=1, reference parity vs pod_backup skipped", flush=True); ref = None\n    elif WRULE == "msharpe" and LOOK == 900 and LEGS == "111":\n'
assert s.count(old3)==1; s=s.replace(old3,new3)
open(p,"w").write(s); print("patched")
EOP
/workspace/venv/bin/python $R/patch_refskip.py
echo "=====DIFF port vs recheck====="
diff /workspace/port_w10/w10_universe.py $R/w10_universe_recheck.py || true
sha256sum /workspace/port_w10/w10_universe.py $R/w10_universe_recheck.py
ls -la $R/dev $R/dev/pod_backup_2026-08-21 $R/dev_alt/pod_backup_2026-08-21

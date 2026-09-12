#!/usr/bin/env bash
# MINIMAL REPRODUCTION RECIPE FOR THE PROGRAMME'S PLANNING NUMBER
# Audit 2026-09-12.  NOT EXECUTED AS A WHOLE BY THE AUDITOR: steps 0-2 and 4 were run
# read-only this session; step 3 (the replay that regenerates the arm npz) was NOT run,
# because it writes into the programme tree on pod2.  Every path and every env value in
# step 3 was read out of the producing source, not inferred.
#
# There are TWO planning numbers.  Read finding F2 in REPRO_AUDIT_2026-09-12.md first.
#   PATH A  (what CLOSEOUT s7 quotes): arm A0, mean g 0.6342, Sharpe 1.2912, n 9138.
#           Its F10 leg and its king leg are BOTH off the v4 lineage.  See F2.
#   PATH B  (caliber-correct):         arm A1x_ext_s42, mean g 0.6602, Sharpe 1.2857, n 9199.
# Do PATH B.  Do PATH A only to audit what was published.
#
# MACHINE: everything below is pod2.  Nothing is on jpline (unreachable).  No GPU needed.
# ---------------------------------------------------------------------------------------

set -euo pipefail
PY=/workspace/venv/bin/python
U=/workspace/uplift_2026-09-11

# ---- STEP 0: verify the device and the cost book (RUN THIS FIRST, it is the whole pin) ----
sha256sum $U/w10_sleeve.py            # MUST be b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650
sha256sum $U/r3k/costb_PWR_G230k.json # MUST be 295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53
# VERIFIED by the auditor 2026-09-12: both match.

# ---- STEP 1: verify the pinned v4 inputs exist and hash as recorded ----
sha256sum /workspace/data/dlnative_5m_wide829_f16_holefix2.npz   # 1d7f459dee434ec4... (pin records sha16 only)
sha256sum /workspace/dlw_v4raw/data/dlw_targets.npz              # d1976cf6246cdc25...
sha256sum /workspace/dlw_v4raw/data/dlw_fea82.npz                # 40608701cad1aea1...
sha256sum /workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz  # 0e3c09ac86c727ac...
ls -l /workspace/review_scratch/health_check/dev_v4/BUILD.json
# VERIFIED by the auditor 2026-09-12: all present, hashes as above (first three cross-check
# against r9_coverage/receipts/lineage_A0.json).

# ---- STEP 2: PATH B - confirm the v4-native arm is on disk and unmodified ----
ARM=$U/r9/dev_ext/probe_artifacts/w10_ablation_series_R9_A1x_ext_s42.npz
sha256sum $ARM   # MUST be 57d18ca50e3a30bb798ec3626e0b3c71e6f6bf72a6e376cfbfb5365a45d6d3b8
                 # (this value is recorded in r9_coverage/receipts/RECEIPT_r9_judge.json)
# VERIFIED by the auditor 2026-09-12: matches.

# ---- STEP 3: (ONLY IF YOU WANT TO REGENERATE THE ARM RATHER THAN TRUST IT) ----
# Source of truth for this command: r9_coverage/receipts/RECEIPT_r9_replay_runs.json
#   .device / .device_sha256 / .cost_json / .env_whitelist / .common_env / .trees.ext.links / .jobs
# ENV WHITELIST (exactly 14 keys, closed set; the device asserts a whitelist on each):
#   LEGS CAL WRULE LOOK MEMBERS_TOPN FTRIM PHI UMASK_SCOPE UMASK_NPZ SLOW_NPY FSEED FPRED COSTB_JSON OUT_TAG
# Thread pins used by the sibling rounds: OMP_NUM_THREADS=3 OPENBLAS_NUM_THREADS=3 MKL_NUM_THREADS=3
#
# The device reads FIVE inputs by RELATIVE path from its cwd.  You must build that tree first
# (r9 built it as symlinks; do the same INSIDE YOUR OWN directory, never inside $U):
#   <cwd>/pod_backup_2026-08-21/wide_fea_hist_meta.npz   -> $U/r6/out/meta_newprod_v4_x0910.npz
#   <cwd>/pod_backup_2026-08-21/slow_pred_hist_oos.npy   -> $U/r6/out/SLOW_v4_x0910.npy
#   <cwd>/pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz-> $U/r6/out/wide_panel_4h_v2ext_x0910.npz
#   <cwd>/pod_backup_2026-08-21/nets_histv2_-30_2_42.npy -> /workspace/review_scratch/health_check/dev_alt/pod_backup_2026-08-21/nets_histv2_-30_2_42.npy
#   <cwd>/pod_backup_2026-08-21/nets_histv2_0_0_0.npy    -> /workspace/review_scratch/health_check/dev_alt/pod_backup_2026-08-21/nets_histv2_0_0_0.npy
#   <cwd>/dlw_2026-08-22                                 -> $U/r6/out/dlw_v4raw_x0910
#   <cwd>/f8_2026-08-22/preds/f10_v4RAWx_s42.npy         -> $U/r9/out/f10_v4RAWx_s42.npy
#
#   cd <YOUR OWN DIR>
#   env LEGS=101 CAL=log WRULE=msharpe LOOK=900 MEMBERS_TOPN=829 FTRIM=zero PHI=0.45 \
#       UMASK_SCOPE=m1 \
#       UMASK_NPZ=/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz \
#       COSTB_JSON=$U/r3k/costb_PWR_G230k.json \
#       SLOW_NPY=$U/r6/out/SLOW_v4_x0910.npy \
#       FSEED=42 FPRED=f10_v4RAWx_s42.npy OUT_TAG=R9_A1x_ext_s42 \
#       OMP_NUM_THREADS=3 OPENBLAS_NUM_THREADS=3 MKL_NUM_THREADS=3 \
#       $PY $U/w10_sleeve.py
#   # writes <cwd>/probe_artifacts/w10_ablation_series_R9_A1x_ext_s42.npz  (~29 s, CPU only)
#   # the device prints a CONFIG json line and self-reports its own sha256 - check it.

# ---- STEP 4: read the number out of the arm.  Pure read; prints, writes nothing. ----
OMP_NUM_THREADS=2 $PY - <<'PY'
import numpy as np, calendar, hashlib, time
def T(*a): return calendar.timegm(a+(0,)*(6-len(a)))
p="/workspace/uplift_2026-09-11/r9/dev_ext/probe_artifacts/w10_ablation_series_R9_A1x_ext_s42.npz"
print("arm sha256", hashlib.sha256(open(p,"rb").read()).hexdigest())
Z=np.load(p,allow_pickle=True); cc=[str(c) for c in Z["cols"]]; ix={c:i for i,c in enumerate(cc)}
k="d30_n2_c42_rec" if "d30_n2_c42_rec" in Z.files else "rec"
R=np.asarray(Z[k],float)[900:]                       # E-0911-A warm drop
ts=np.round(R[:,ix["ts"]]).astype(np.int64)
m=ts<=T(2026,9,10,0)                                  # coverage ceiling AFTER the r9 fix
g=(R[:,ix["net_ex"]]/R[:,ix["gross_total"]])[m]; tsx=ts[m]   # the frozen statistic
print("n",len(g),"mean_g %.4f"%g.mean(),"Sharpe %.4f"%(g.mean()/g.std(ddof=1)*np.sqrt(2190)))
d=tsx//86400; ud,inv=np.unique(d,return_inverse=True); nd=len(ud)
o=np.argsort(inv); st=np.searchsorted(inv[o],np.arange(nd)); en=np.append(st[1:],len(o))
for lab,sv,B in (("PINNED [20260905,1] B2000",[20260905,1],2000),("AS PUBLISHED [20260912,31] B4000",[20260912,31],4000)):
    rng=np.random.default_rng(sv); pick=rng.integers(0,nd,size=(B,nd))
    out=np.array([g[np.concatenate([o[st[j]:en[j]] for j in pick[b]])].mean() for b in range(B)])
    print(lab,"CI95 [%.4f, %.4f]"%(np.percentile(out,2.5),np.percentile(out,97.5)))
PY
# AUDITOR RAN THIS (with the two seed variants) 2026-09-12 and got:
#   n 9199   mean_g 0.6602   Sharpe 1.2857   CI95(published estimator) [0.1772, 1.1540]
#   -> reproduces r9_coverage/SUMMARY_r9.json A1x_ext_s42_NEW_WINDOW exactly.
#
# PATH A (published): same step 4 but arm = $U/r3k/arms/A0_PWR230k_s42.npz, cut 2026-08-30 20Z,
# and the extra filter that r8_repro.py applies (finite LIVE sigma from $U/r7f1/out/sigma_variants.npz).
# Auditor ran it: n 9138, mean_g 0.634196, Sharpe 1.291223, CI95 [0.16529, 1.10710]. EXACT.

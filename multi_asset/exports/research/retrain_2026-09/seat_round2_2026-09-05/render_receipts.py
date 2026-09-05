"""render_receipts.py — assemble REPORT_receipts.md for seat_round2: device identity (sha256 of the patched device, the original, the diff), the B0 bitwise-equivalence
receipt (logs/check_equiv.log + chain_b0.log), every device command verbatim (logs/commands.txt, final attempt only), artifact sha256 list, and the judge's own sha.
Read-only except REPORT_receipts.md. Then REPORT.md = REPORT_head.md + REPORT_tables.md + REPORT_receipts.md (concatenated by chain_report.sh)."""
import hashlib, os, re, json
ROOT = "/workspace/review_scratch/seat_round2"
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
L = []
def w(s=""): L.append(s)
w("## R. Receipts (device / equivalence / commands / artifacts)")
w("\n### R.1 Device identity")
w("| file | sha256 |"); w("|---|---|")
for f in ("w10_seat2.py", "w10_health_orig.py", "device.diff", "check_equiv.py", "judge_seat2.py", "run_arm.sh", "chain_b0.sh", "chain_arms.sh"):
    p = f"{ROOT}/{f}"
    if os.path.exists(p): w(f"| {f} | `{sha(p)}` |")
for f in ("/workspace/review_scratch/health_check/w10_health.py", "/workspace/review_scratch/health_check/masks/umask_UPIT.npz", "/workspace/review_scratch/health_check/calib/costb_fee_steady.json", "/workspace/shadow_bundle_v3/slow_pred_pinned.npy",
          "/workspace/port_w10/f8_2026-08-22/preds/f10_V2MAIN_s42.npy", "/workspace/port_w10/f8_2026-08-22/preds/f10_V2MAIN_s2027.npy", "/workspace/data/wide_fea_v2ext_meta.npz", "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz", "/workspace/data/wide_panel_4h_v2ext.npz"):
    if os.path.exists(f): w(f"| {f} | `{sha(f)}` |")
w("\n### R.2 Device diff (w10_health.py → w10_seat2.py)")
w("```diff"); w(open(f"{ROOT}/device.diff").read().rstrip()); w("```")
w("\n### R.3 B0 bitwise-equivalence receipt (patched device, default path, vs health_check M1_UPIT_{cal}_s{seed}_ccal; all four arrays d30_n2_c42_rec / S0_rec / d30_n2_c42_W / S0_W + config minus self-report keys)")
w("```"); w(open(f"{ROOT}/logs/check_equiv.log").read().rstrip()); w("```")
w("```"); w(open(f"{ROOT}/logs/chain_b0.log").read().rstrip()); w("```")
w("\n### R.4 Commands (verbatim from logs/commands.txt; cwd shown; OMP/OPENBLAS/MKL threads = 4 via run_arm.sh)")
w("```"); w(open(f"{ROOT}/logs/commands.txt").read().rstrip()); w("```")
w("\n### R.5 Artifact sha256 (probe_artifacts, arms B0..B6)")
w("```"); w(open(f"{ROOT}/logs/chain_arms.log").read().rstrip()); w("```")
w("\n### R.6 Judge run log (judge_seat2.py stdout)")
if os.path.exists(f"{ROOT}/logs/judge.log"):
    w("```"); w(open(f"{ROOT}/logs/judge.log").read().rstrip()); w("```")
open(f"{ROOT}/REPORT_receipts.md", "w").write("\n".join(L) + "\n")
print(f"wrote {ROOT}/REPORT_receipts.md ({len(L)} lines)")

"""rider_setup.py — Track A rider arm (PREREG_allweather_programme §5 amendment, team-lead 2026-09-05): device copy of the health-check
w10_health.py with ONE knob, fund z ×= (1 + SPOTSUP_B · spot_support), spot_support = anchor-wise rank in [-0.5, +0.5] (xz over the anchor's
members) of the spot-support score matrix (SPOTSUP_NPZ: ts × symbols aligned to the panel, like FEMAT_NPZ). Applied wherever the fund z is formed:
legs() (leg-return series that drive the msharpe seats) and run() (both books). SPOTSUP_B=0 (default) leaves every code path untouched = bitwise
baseline (identity receipt = the b=0 artifact vs the archived health-check main arm UPIT_prod_s42_ccal).
Also reproduces the health-check dev_alt/ input layout (setup_dev.sh recipe: symlinks to the same targets) under allweather_trackA/rider/.
Writes only under /workspace/review_scratch/allweather_trackA/rider/. Prints the patch diff and sha256 of both files.
"""
import os, re, subprocess, hashlib, difflib
ROOT = "/workspace/review_scratch/allweather_trackA/rider"
SRC = "/workspace/review_scratch/health_check/w10_health.py"
DST = f"{ROOT}/w10_health_spotsup.py"
os.makedirs(ROOT, exist_ok=True)
src = open(SRC).read()
def rep(text, old, new):
    assert text.count(old) == 1, (text.count(old), old[:80])
    return text.replace(old, new)
p = src
# 1. knob definitions + self-report
p = rep(p, '_CFG = {"COSTB_JSON": COSTB_JSON,',
        'SPOTSUP_B = float(os.environ.get("SPOTSUP_B", "0")); assert SPOTSUP_B in (0.0, 0.5, 1.0), SPOTSUP_B   # rider (PREREG_allweather §5, 2026-09-05): fund z ×= (1 + b·spot_support); 0 = bitwise baseline\n'
           'SPOTSUP_NPZ = os.environ.get("SPOTSUP_NPZ")   # ts × symbols spot-support score matrix (rank-transformed within members at use)\n'
           '_CFG = {"SPOTSUP_B": SPOTSUP_B, "SPOTSUP_NPZ": SPOTSUP_NPZ, "COSTB_JSON": COSTB_JSON,')
# 2. matrix loading after the FEMAT block
p = rep(p, '    FE = np.asarray(_fz["mat"], dtype=float); print(f"FEMAT injected: {FEMAT_NPZ} finite {np.isfinite(FE).mean():.3f}", flush=True)\n',
        '    FE = np.asarray(_fz["mat"], dtype=float); print(f"FEMAT injected: {FEMAT_NPZ} finite {np.isfinite(FE).mean():.3f}", flush=True)\n'
        'SS = None\n'
        'if SPOTSUP_B > 0:   # rider: spot-support matrix aligned to the panel (same assertions as FEMAT)\n'
        '    _sz = np.load(SPOTSUP_NPZ, allow_pickle=True)\n'
        '    assert [str(x) for x in _sz["symbols"]] == [str(x) for x in PW["symbols"]], "SPOTSUP symbols mismatch"\n'
        '    assert np.array_equal(_sz["ts"].astype(np.int64), PW["ts"].astype(np.int64)), "SPOTSUP ts mismatch"\n'
        '    SS = np.asarray(_sz["mat"], dtype=float); print(f"SPOTSUP injected: {SPOTSUP_NPZ} b={SPOTSUP_B} finite {np.isfinite(SS).mean():.3f}", flush=True)\n'
        'def SSF(j, m):   # rider multiplier on the fund z: 1 + b·xz(spot_support[j, m]); members without a score -> factor 1\n'
        '    return (1.0 + SPOTSUP_B * np.nan_to_num(xz(SS[j, m]))) if SS is not None else 1.0\n')
# 3. legs(): tilt the fund leg-return z (seat driver)
p = rep(p, '            z = np.nan_to_num(FZB(j, m) if (leg == "fund" and UMASK_SCOPE == "m1") else xz(sc[leg])); z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0\n',
        '            z = np.nan_to_num(FZB(j, m) if (leg == "fund" and UMASK_SCOPE == "m1") else xz(sc[leg]))\n'
        '            if leg == "fund" and SS is not None: z = z * SSF(j, m)   # rider tilt (seat driver)\n'
        '            z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0\n')
# 4. run(): tilt the fund z used by both books
p = rep(p, '        FZ = FZB(j, m) if UMASK_SCOPE == "m1" else xz(sc["fund"])   # fund z used by both books and the leg-contribution diagnostic\n',
        '        FZ = FZB(j, m) if UMASK_SCOPE == "m1" else xz(sc["fund"])   # fund z used by both books and the leg-contribution diagnostic\n'
        '        if SS is not None: FZ = FZ * SSF(j, m)   # rider tilt (both books)\n')
open(DST, "w").write(p)
diff = "".join(difflib.unified_diff(src.splitlines(True), p.splitlines(True), fromfile="w10_health.py", tofile="w10_health_spotsup.py"))
open(f"{ROOT}/w10_health_spotsup.diff", "w").write(diff)
print(diff)
for f in (SRC, DST): print("SHA256", hashlib.sha256(open(f, "rb").read()).hexdigest(), f)
# dev_alt layout (setup_dev.sh recipe, prod caliber = meta_newprod)
d = f"{ROOT}/dev_alt"
for sub in ("pod_backup_2026-08-21", "probe_artifacts", "logs"): os.makedirs(f"{d}/{sub}", exist_ok=True)
for f in ("nets_histv2_0_0_0.npy", "nets_histv2_-30_2_42.npy", "slow_pred_hist_oos.npy", "wide_panel_4h_hist_v2.npz"):
    t = f"/workspace/port_w10/pod_backup_2026-08-21/{f}"; l = f"{d}/pod_backup_2026-08-21/{f}"
    if not os.path.islink(l): os.symlink(t, l)
l = f"{d}/pod_backup_2026-08-21/wide_fea_hist_meta.npz"
if not os.path.islink(l): os.symlink("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod.npz", l)
for f in ("f8_2026-08-22", "dlw_2026-08-22"):
    l = f"{d}/{f}"
    if not os.path.islink(l): os.symlink(f"/workspace/port_w10/{f}", l)
ref = "/workspace/review_scratch/health_check/dev_alt"
for f in ("pod_backup_2026-08-21/nets_histv2_0_0_0.npy", "pod_backup_2026-08-21/slow_pred_hist_oos.npy", "pod_backup_2026-08-21/wide_fea_hist_meta.npz", "pod_backup_2026-08-21/wide_panel_4h_hist_v2.npz", "f8_2026-08-22", "dlw_2026-08-22"):
    a = os.path.realpath(f"{d}/{f}"); b = os.path.realpath(f"{ref}/{f}")
    print("SAME" if a == b else "DIFF", f, a, b)
print("RIDER_SETUP_DONE")

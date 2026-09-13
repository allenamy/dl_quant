#!/usr/bin/env python3
"""t2_drive.py — pod2 driver for PREREG_T2 §4: wave 1 = GATE P + PC-0 + PC-1 + WIRE (positive controls FIRST; STOP rules),
wave 2 = the three arms on the A0 and NW baselines, wave 3 = C2 shuffle-future (garbled tree, re-estimated path, bitwise prefix).
Every device run gets an EXACT env dict (no inheritance) = BASE ∪ baseline knobs ∪ arm knobs ∪ OUT_TAG, written to the receipt.
CPU only; live trees never touched; writes only under /workspace/uplift_r2_2026-09-13/T2/.
Launch: env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root /workspace/venv/bin/python devices/t2_drive.py PATH,HOME,LC_CTYPE
"""
import os, sys, json, time, hashlib, subprocess, shutil, calendar
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "launch with a non-empty env whitelist as argv[1]"
BANNED = ('CAL', 'JUDGE', 'UPLIFT', 'PANEL', 'LOOK', 'WRULE', 'LEGS', 'PHI', 'FSEED', 'W3FIX', 'FTRIM', 'UMASK', 'SLOW', 'FPRED', 'MEMBERS_TOPN', 'COSTB', 'SLEEVE', 'KMOD', 'SEAT', 'RNSM', 'LTRIM', 'CDAMP', 'FUNDSCALE', 'FEMAT', 'TRADE_TOPN', 'REF_SKIP', 'PYTHON', 'OMP', 'MKL', 'R15', 'R18', 'SMA', 'SBAND', 'FTPOS', 'OUT_TAG', 'T2')
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
BAN = sorted(k for k in os.environ if k.startswith(BANNED)); assert BAN == [], ("CALIBER FLAG PRESENT", BAN)
ENV = dict(env_whitelist=sorted(WHITE), env_actual={k: os.environ[k] for k in sorted(os.environ)}, launch_cmdline=" ".join(sys.argv))
import numpy as np
from scipy.stats import rankdata
ENV.update(python=sys.version.split()[0], numpy=np.__version__)
T0 = time.time()
T2 = "/workspace/uplift_r2_2026-09-13/T2"; D = T2 + "/dev"; DG = T2 + "/dev_garbled"; HC = "/workspace/review_scratch/health_check"; UP = "/workspace/uplift_2026-09-11"
PY = "/workspace/venv/bin/python"; DER = T2 + "/devices/w10_sleeve_t2.py"; KAPPA = T2 + "/devices/t2_kappa.py"
PREREG = T2 + "/PREREG_T2_carry_net_sizing_2026-09-13.md"; PREREG_SHA = "981293b02b2ddae6574fa6dcf8db9b09a65cfa9f122a8b72d7e604ad5ec87eca"
PIN = UP + "/w10_sleeve.py"; PIN_SHA = "b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650"
PAR = UP + "/r18_foundation/devices/w10_sleeve_r18.py"; PAR_SHA = "9b8a6323e8f0ac31ecb4046f6759dce09ba89645cbfc356db71f51c662b2c5c4"
DER_SHA = "380d6265082c67742a8cf47f844d76cf0e3cc3ca25557b29bdaf6c747907d341"
COSTB = UP + "/r3k/costb_PWR_G230k.json"; COSTB_SHA = "295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53"
ARCH_A0 = {"42": (UP + "/r3k/arms/A0_PWR230k_s42.npz", "352ac36fb319532756da71e7cc405fb0dcde6f36f6e28a57f1f681177bcfd339"), "2027": (UP + "/r3k/arms/A0_PWR230k_s2027.npz", "aa44e18fb6bcfa7ef54f1708d070b0a2a7d5333f6cea63dfca94fecf59be1c7b")}
ARCH_NW = {"42": (UP + "/r18_foundation/arms/NW_s42.npz", "afbcd92ea41d7e4cd75159e64e8640dedf7727219dd852df3a1f0ef3e7f4692d"), "2027": (UP + "/r18_foundation/arms/NW_s2027.npz", "89d28a319f2bd61f755cf973d1697f30b6fe0f3dfeb9aad20d2bb553575c11a5")}
ARCH_S = {"42": (UP + "/r15_structural/arms/S_s42.npz", "6d59d57fc4f139a5d7f7b75417b4f804a5a3397950ae2f8df64bdf1662ad8376"), "2027": (UP + "/r15_structural/arms/S_s2027.npz", "2e38ecf2930db850b2133b2879e74e67297fb5be81b198c1e9c50ad5b002beda")}
PC1_TARGET = {"42": "-0.0928", "2027": "-0.0894"}
UB = calendar.timegm((2026, 8, 30, 20, 0, 0)); TSTAR = calendar.timegm((2024, 7, 16, 0, 0, 0))
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def sh(cmd):
    try: return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as e: return "ERR %s" % e
assert sha(PREREG) == PREREG_SHA, ("PREREG SHA", sha(PREREG))
assert sha(PIN) == PIN_SHA and sha(PAR) == PAR_SHA and sha(DER) == DER_SHA, "device sha"
assert sha(COSTB) == COSTB_SHA
for grp in (ARCH_A0, ARCH_NW, ARCH_S):
    for s_, (p_, h_) in grp.items(): assert sha(p_) == h_, ("ARCHIVE SHA", p_)
KRC = json.load(open(T2 + "/receipts/RECEIPT_T2_kappa_main.json"))
assert KRC["prereg_sha256"] == PREREG_SHA and KRC["C1"]["PASS"] is True, ("C1 must PASS before any device run (PREREG §4)", KRC.get("C1", {}).get("PASS"))
KP_MAIN = KRC["path_outputs"]["main"]["path"]; assert sha(KP_MAIN) == KRC["path_outputs"]["main"]["sha256"]
SELF_SHA = sha(os.path.abspath(__file__))
for p in (D + "/logs", D + "/probe_artifacts", T2 + "/arms", T2 + "/receipts", T2 + "/logs"): os.makedirs(p, exist_ok=True)
K3 = "/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"; UM = HC + "/masks/umask_UPIT_CRYPTO.npz"
META_REAL = "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"; PANEL_REAL = "/workspace/data/wide_panel_4h_v2ext.npz"
def mklinks(root, meta_target, panel_target):
    bk = root + "/pod_backup_2026-08-21"; os.makedirs(bk, exist_ok=True); os.makedirs(root + "/logs", exist_ok=True); os.makedirs(root + "/probe_artifacts", exist_ok=True)
    L = {bk + "/nets_histv2_-30_2_42.npy": "/workspace/port_w10/pod_backup_2026-08-21/nets_histv2_-30_2_42.npy", bk + "/nets_histv2_0_0_0.npy": "/workspace/port_w10/pod_backup_2026-08-21/nets_histv2_0_0_0.npy",
         bk + "/slow_pred_hist_oos.npy": "/workspace/review_scratch/king_v4/SLOW_v4.npy", root + "/dlw_2026-08-22": "/workspace/dlw_v4raw", root + "/f8_2026-08-22": HC + "/dev_v4/f8_2026-08-22"}
    if meta_target: L[bk + "/wide_fea_hist_meta.npz"] = meta_target
    if panel_target: L[bk + "/wide_panel_4h_hist_v2.npz"] = panel_target
    for t, v in L.items():
        assert os.path.exists(v), v
        if not os.path.islink(t): os.symlink(v, t)
        assert os.path.realpath(t) == os.path.realpath(v), (t, os.path.realpath(t), v)
    return L
LINKS = mklinks(D, META_REAL, PANEL_REAL)
INPUTS = {k: dict(realpath=os.path.realpath(v), sha256=sha(v)) for k, v in LINKS.items() if os.path.isfile(v)}
for k in (K3, UM, COSTB, "/workspace/dlw_v4raw/data/dlw_targets.npz", HC + "/dev_v4/f8_2026-08-22/preds/f10_A0_s42.npy", HC + "/dev_v4/f8_2026-08-22/preds/f10_A0_s2027.npy", KP_MAIN):
    INPUTS[k] = dict(realpath=os.path.realpath(k), sha256=sha(k))
BASE = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "HOME": "/root", "OMP_NUM_THREADS": "3", "OPENBLAS_NUM_THREADS": "3", "MKL_NUM_THREADS": "3"}
def A0(seed): return {"LEGS": "101", "PHI": "0.45", "WRULE": "msharpe", "LOOK": "900", "MEMBERS_TOPN": "829", "FTRIM": "zero", "FTRIM_TH": "-0.0010", "UMASK_SCOPE": "m1", "CAL": "log", "FTPOS": "0", "SEATNET": "0",
                      "UMASK_NPZ": UM, "SLOW_NPY": K3, "FSEED": seed, "FPRED": "f10_A0_s%s.npy" % seed, "COSTB_JSON": COSTB}
def NWE(seed): e = A0(seed); e.update({"R18_ELIG": "1", "R18_WARM": "1", "R18_INSTR": "1"}); return e
while float(open("/proc/loadavg").read().split()[0]) > 6.0:
    print("load > 6, waiting", open("/proc/loadavg").read().strip(), flush=True); time.sleep(30)
GPU0 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID0 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); LOAD0 = open("/proc/loadavg").read().split()[:3]
RUNS = {}
def run(job):
    tag, base, seed, extra, cwd = job
    dst = T2 + "/arms/%s.npz" % tag
    env = dict(BASE); env.update(A0(seed) if base == "A0" else NWE(seed)); env.update(extra); env["OUT_TAG"] = tag
    t0 = time.time()
    if not os.path.exists(dst):
        with open(T2 + "/logs/%s.log" % tag, "w") as lf:
            rc = subprocess.call([PY, DER], cwd=cwd, stdout=lf, stderr=subprocess.STDOUT, env=env)
        src = cwd + "/probe_artifacts/w10_ablation_series_%s.npz" % tag
        if rc != 0 or not os.path.exists(src): return tag, dict(rc=rc, FAIL=True, env=env)
        shutil.move(src, dst)
        try: os.remove(cwd + "/probe_artifacts/w10_ablation_summary_%s.json" % tag)
        except FileNotFoundError: pass
    else: rc = "cached"
    Z = np.load(dst, allow_pickle=True); cfg = json.loads(str(Z["config_json"]))
    return tag, dict(rc=rc, secs=round(time.time() - t0, 1), base=base, seed=seed, cwd=cwd, device=DER, device_sha256=DER_SHA, self_sha256_reported=cfg["UPLIFT"]["self_sha256"], env=env, env_whitelist=sorted(env),
                     out=dst, out_sha256=sha(dst), n_rec=int(Z["d30_n2_c42_rec"].shape[0]), cfg_T2=cfg.get("T2"), cfg_R18=cfg.get("R18"),
                     cfg_knobs={k: cfg.get(k) for k in ("FTPOS", "SEATNET", "FTRIM", "FTRIM_TH", "PHI", "LEGS", "CAL", "UMASK_SCOPE", "FSEED", "FPRED", "COSTB_JSON", "LOOK", "WRULE", "MEMBERS_TOPN", "SLOW_NPY", "UMASK_NPZ")})
from concurrent.futures import ThreadPoolExecutor
def wave(jobs, name):
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=6) as ex:
        for tag, r in ex.map(run, jobs):
            RUNS[tag] = r; print("RUN", name, tag, r.get("rc"), r.get("secs"), "s", flush=True)
    bad = [t for t, _, _, _, _ in jobs if RUNS[t].get("FAIL")]
    assert not bad, ("device run failed", bad)
    for t, _, _, _, _ in jobs: assert RUNS[t]["self_sha256_reported"] == DER_SHA, (t, RUNS[t]["self_sha256_reported"])
    return round(time.time() - t0, 1)
def bitwise(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    if a.shape != b.shape: return dict(bitwise=False, shape_a=list(a.shape), shape_b=list(b.shape))
    na, nb = np.isnan(a), np.isnan(b); ok = bool(np.array_equal(na, nb) and np.array_equal(a[~na], b[~nb]))
    return dict(bitwise=ok, shape=list(a.shape), maxabs=0.0 if ok else float(np.nanmax(np.abs(a - b))), n_diff=0 if ok else int((a != b).sum()))
def arr(tag):
    Z = np.load(T2 + "/arms/%s.npz" % tag, allow_pickle=True); return Z
def gW(rec, cols):
    ts = rec[:, cols.index("ts")].astype(np.int64); g = rec[:, cols.index("net_ex")] / rec[:, cols.index("gross_total")]
    wa = ts <= UB; wa[:900] = False; return ts, g, wa
KT = lambda **k: {**{"T2_KPATH": KP_MAIN, "T2_KCOL": "scalar"}, **k}
SEEDS = ("42", "2027")
# ================================================================== WAVE 1: GATE P + PC-0 + PC-1 + WIRE
J1 = []
for s in SEEDS:
    J1 += [("GP_A0_s" + s, "A0", s, {}, D), ("GP_NW_s" + s, "NW", s, {}, D),
           ("PC0N_A0_s" + s, "A0", s, KT(T2_MODE="name", T2_KFORCE="0", T2_INSTR="1"), D), ("PC0S_A0_s" + s, "A0", s, KT(T2_MODE="seat", T2_KFORCE="0", T2_INSTR="1"), D),
           ("PC0N_NW_s" + s, "NW", s, KT(T2_MODE="name", T2_KFORCE="0", T2_INSTR="1"), D), ("PC0S_NW_s" + s, "NW", s, KT(T2_MODE="seat", T2_KFORCE="0", T2_INSTR="1"), D),
           ("PC1S_A0_s" + s, "A0", s, KT(T2_MODE="seat", T2_KFORCE="1", T2_INSTR="1"), D), ("WIRE_A0_s" + s, "A0", s, KT(T2_MODE="name", T2_KFORCE="1", T2_INSTR="1"), D)]
W1S = wave(J1, "W1")
GATE = {"P": {}, "PC0": {}, "PC1": {}, "WIRE": {}}
for s in SEEDS:
    A = np.load(ARCH_A0[s][0], allow_pickle=True); N = np.load(ARCH_NW[s][0], allow_pickle=True); S = np.load(ARCH_S[s][0], allow_pickle=True)
    a0rec, a0W = A["rec"], A["W"]; nwrec, nwW = N["d30_n2_c42_rec"], N["d30_n2_c42_W"]; srec, sW = S["d30_n2_c42_rec"], S["d30_n2_c42_W"]
    colsA = [str(c) for c in A["cols"]]
    for tag, ref_rec, ref_W, ref_name in (("GP_A0_s" + s, a0rec, a0W, "archived A0"), ("GP_NW_s" + s, nwrec, nwW, "archived NW")):
        Z = arr(tag); GATE["P"][tag] = dict(ref=ref_name, rec=bitwise(Z["d30_n2_c42_rec"], ref_rec), W=bitwise(Z["d30_n2_c42_W"], ref_W), cols_equal=bool([str(c) for c in Z["cols"]] == colsA), cfg_T2_mode=RUNS[tag]["cfg_T2"]["T2_MODE"])
    for tag, ref_rec, ref_W, ref_name in (("PC0N_A0_s" + s, a0rec, a0W, "archived A0"), ("PC0S_A0_s" + s, a0rec, a0W, "archived A0"), ("PC0N_NW_s" + s, nwrec, nwW, "archived NW"), ("PC0S_NW_s" + s, nwrec, nwW, "archived NW")):
        Z = arr(tag); aux = Z["d30_n2_c42_T2A"]; ac = [str(c) for c in Z["d30_n2_c42_T2A_cols"]]
        used = int(aux[:, ac.index("name_path_used")].sum()) if "PC0N" in tag else None
        seatk = aux[:, ac.index("kappa_seat")] if "PC0S" in tag else None
        GATE["PC0"][tag] = dict(ref=ref_name, rec=bitwise(Z["d30_n2_c42_rec"], ref_rec), W=bitwise(Z["d30_n2_c42_W"], ref_W), anchors_through_rank_path=used,
                               seat_kappa_unique=(sorted(set(np.round(seatk, 12).tolist())) if seatk is not None else None), cfg_T2=RUNS[tag]["cfg_T2"])
    Z = arr("PC1S_A0_s" + s); rec1 = Z["d30_n2_c42_rec"]
    ts, g1, wa = gW(rec1, colsA); ts0, g0, wa0 = gW(a0rec, colsA); assert np.array_equal(ts, ts0) and wa.sum() == 9138
    dg = float((g1 - g0)[wa].mean())
    GATE["PC1"]["PC1S_A0_s" + s] = dict(ref="archived r15 S_s" + s, rec=bitwise(rec1, srec), W=bitwise(Z["d30_n2_c42_W"], sW), dg_vs_A0_W_ALPHA=dg, dg_4dp="%.4f" % dg, target=PC1_TARGET[s], dg_matches_target=bool("%.4f" % dg == PC1_TARGET[s]))
    # WIRE (a) + (b)
    Z = arr("WIRE_A0_s" + s); recw = Z["d30_n2_c42_rec"]; tsw, gw, waw = gW(recw, colsA)
    frac = float((np.abs(gw - g0)[waw] > 1e-12).mean())
    GATE["WIRE"]["WIRE_A0_s" + s] = dict(frac_W_ALPHA_anchors_g_differs=frac, a_pass=bool(frac >= 0.5), rows=Z["d30_n2_c42_T2W_rows"].tolist())
# WIRE (b): independent re-implementation of FZ_book at the 12 rows (kappa forced 1 where active, lam from the path)
def xzI(v):
    ok = np.isfinite(v); o = np.full(v.shape[0], np.nan)
    if int(ok.sum()) >= 10: o[ok] = rankdata(v[ok]) / max(int(ok.sum()) - 1, 1) - 0.5
    return o
PWr = np.load(PANEL_REAL, allow_pickle=True); FNr = PWr["f_fund_now"]; IVr = PWr["f_fund_iv"]; FEr = PWr["f_fund_ema_v1"]; ptsr = PWr["ts"].astype(np.int64); prowr = {int(t): j for j, t in enumerate(ptsr)}
IVfr = np.where(np.isfinite(IVr) & (IVr > 0), IVr, 8.0)
MTr = np.load(META_REAL, allow_pickle=True); Er = MTr["E_ts"].astype(np.int64); Qr = MTr["qvk"]; imap = {int(t): i for i, t in enumerate(Er)}
UZ = np.load(UM, allow_pickle=True); umapr = {int(t): k for k, t in enumerate(UZ["ts"].astype(np.int64))}; UMr = np.asarray(UZ["mask"])
KPm = np.load(KP_MAIN, allow_pickle=True); assert np.array_equal(KPm["E_ts"].astype(np.int64), Er)
for s in SEEDS:
    Z = arr("WIRE_A0_s" + s); rows = Z["d30_n2_c42_T2W_rows"]; tsr = Z["d30_n2_c42_T2W_ts"]; fzr = Z["d30_n2_c42_T2W_fz"]; recw = Z["d30_n2_c42_rec"]
    chk = []
    for q, r in enumerate(rows):
        t = int(tsr[q]); assert int(recw[r, 0]) == t, ("wire row ts", r, t)
        i = imap[t]; j = prowr[t]
        qq = np.nan_to_num(Qr[i], nan=-1.0); o = np.argsort(-qq); o = o[qq[o] > -0.5]; m = np.sort(o[:829]).astype(np.int64)
        k = umapr.get(t)
        if k is not None: m = m[UMr[k][m]]
        act = bool(KPm["active_scalar"][i]); lam = np.float64(KPm["lam_scalar"][i])
        if act and not (lam == 0.0 and np.float64(1.0) == 0.0):
            c = np.nan_to_num(FNr[j, :], nan=0.0) * (4.0 / IVfr[j, :]); exp = xzI(lam * xzI(FEr[j, :]) - np.float64(1.0) * c)[m]
        else:
            exp = xzI(FEr[j, :])[m]
        er = np.full(829, np.nan); er[m] = exp
        chk.append(dict(row=int(r), ts=time.strftime("%Y-%m-%d %HZ", time.gmtime(t)), active=act, bitwise=bool(np.array_equal(er, fzr[q], equal_nan=True)), n_names=int(len(m))))
    GATE["WIRE"]["WIRE_A0_s" + s]["b_rows"] = chk; GATE["WIRE"]["WIRE_A0_s" + s]["b_pass"] = bool(len(chk) == 12 and all(c_["bitwise"] for c_ in chk))
GATE["P"]["PASS"] = all(v["rec"]["bitwise"] and v["W"]["bitwise"] and v["cols_equal"] and v["cfg_T2_mode"] == "off" for k, v in GATE["P"].items() if k != "PASS")
GATE["PC0"]["PASS"] = all(v["rec"]["bitwise"] and v["W"]["bitwise"] for k, v in GATE["PC0"].items() if k != "PASS")
GATE["PC1"]["PASS"] = all(v["rec"]["bitwise"] and v["W"]["bitwise"] and v["dg_matches_target"] for k, v in GATE["PC1"].items() if k != "PASS")
GATE["WIRE"]["PASS"] = all(v["a_pass"] and v["b_pass"] for k, v in GATE["WIRE"].items() if k != "PASS")
STOP = not (GATE["P"]["PASS"] and GATE["PC0"]["PASS"] and GATE["PC1"]["PASS"])
print("GATES", json.dumps({k: v["PASS"] for k, v in GATE.items()}), "STOP" if STOP else "", flush=True)
def write_receipt(extra):
    GPU1 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID1 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); LOAD1 = open("/proc/loadavg").read().split()[:3]
    RC = dict(self_sha256=SELF_SHA, prereg_sha256=PREREG_SHA, pinned_device_sha256=PIN_SHA, parent_r18_sha256=PAR_SHA, derived_device_sha256=DER_SHA, derived_device=DER, kappa_receipt_self_sha256=KRC["self_sha256"], kpath_main=dict(path=KP_MAIN, sha256=sha(KP_MAIN)),
              env=ENV, inputs=INPUTS, base_env=BASE, a0_knobs_s42=A0("42"), nw_knobs_s42=NWE("42"), gate=GATE, runs=RUNS, gpu_before=GPU0, gpu_after=GPU1, protected_pids_before=PID0, protected_pids_after=PID1, loadavg_before=LOAD0, loadavg_after=LOAD1,
              wall_s=round(time.time() - T0, 1), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **extra)
    json.dump(RC, open(T2 + "/receipts/RECEIPT_T2_drive.json", "w"), indent=1, default=str)
    print("GPU", GPU0, "->", GPU1, "| PIDs", PID0.replace("\n", ";"), "->", PID1.replace("\n", ";"), "| load", LOAD0, "->", LOAD1, flush=True)
if STOP:
    write_receipt(dict(STOP=True, wave1_s=W1S, note="GATE P / PC-0 / PC-1 failed: no arm run (PREREG §4)")); print("STOP_T2_drive"); sys.exit(3)
# ================================================================== WAVE 2: arms (A0 and NW baselines)
NAME_OK = GATE["WIRE"]["PASS"]
J2 = []
for base in ("A0", "NW"):
    for s in SEEDS:
        if NAME_OK:
            J2 += [("N_%s_s%s" % (base, s), base, s, KT(T2_MODE="name", T2_INSTR="1"), D), ("Ns_%s_s%s" % (base, s), base, s, KT(T2_MODE="name", T2_KCOL="sigma", T2_INSTR="1"), D)]
        J2 += [("SK_%s_s%s" % (base, s), base, s, KT(T2_MODE="seat", T2_INSTR="1"), D)]
W2S = wave(J2, "W2")
# ================================================================== WAVE 3: C2 shuffle-future (A0 env)
bk = DG + "/pod_backup_2026-08-21"; os.makedirs(bk, exist_ok=True)
GM = bk + "/wide_fea_hist_meta.npz"; GPn = bk + "/wide_panel_4h_hist_v2.npz"
Y4R = np.asarray(MTr["y4"]); PANR = {k: np.asarray(PWr[k]) for k in ("ts", "symbols", "f_rev_24h", "f_fund_now", "f_fund_ema_v1", "f_fund_iv")}   # read each npz member ONCE (an NpzFile re-decompresses on every access)
if not (os.path.exists(GM) and os.path.exists(GPn)):
    y4g = Y4R.copy(); fut_rows = np.nonzero(Er >= TSTAR)[0]
    for r in fut_rows:
        idx = np.nonzero(np.isfinite(Y4R[r]))[0]; perm = np.random.default_rng([20260913, int(r)]).permutation(len(idx)); y4g[r, idx] = Y4R[r, idx[perm]]
    np.savez(GM + ".tmp.npz", E_ts=MTr["E_ts"], members=MTr["members"], y4=y4g, qvk=Qr, names=MTr["names"]); os.replace(GM + ".tmp.npz", GM)
    keep = {k: PANR[k] for k in ("ts", "symbols", "f_rev_24h")}; prow_f = np.nonzero(ptsr > TSTAR)[0]
    for k in ("f_fund_now", "f_fund_ema_v1", "f_fund_iv"):
        a_ = PANR[k].copy()
        for j in prow_f: a_[j] = PANR[k][j][np.random.default_rng([20260914, int(j)]).permutation(a_.shape[1])]
        keep[k] = a_
    np.savez(GPn + ".tmp.npz", **keep); os.replace(GPn + ".tmp.npz", GPn)
GLINKS = mklinks(DG, None, None)
GARB = dict(meta=dict(path=GM, sha256=sha(GM)), panel=dict(path=GPn, sha256=sha(GPn)), TSTAR="2024-07-16 00:00Z", y4_rows_permuted=int((Er >= TSTAR).sum()), panel_rows_permuted=int((ptsr > TSTAR).sum()))
# prove the garbling actually changed the future and left the past intact
Mg = np.load(GM, allow_pickle=True); Pg = np.load(GPn, allow_pickle=True)
Y4G = np.asarray(Mg["y4"]); PG = {k: np.asarray(Pg[k]) for k in ("f_fund_now", "f_fund_ema_v1", "f_fund_iv")}
GARB["past_y4_bitwise"] = bool(np.array_equal(Y4G[Er < TSTAR], Y4R[Er < TSTAR], equal_nan=True)); GARB["future_y4_changed_cells"] = int((Y4G[Er >= TSTAR] != Y4R[Er >= TSTAR]).sum())
GARB["future_y4_nan_pattern_kept"] = bool(np.array_equal(np.isnan(Y4G), np.isnan(Y4R)))
GARB["past_panel_bitwise"] = bool(all(np.array_equal(PG[k][ptsr <= TSTAR], PANR[k][ptsr <= TSTAR], equal_nan=True) for k in PG))
GARB["future_panel_changed_cells"] = int(sum(int((PG[k][ptsr > TSTAR] != PANR[k][ptsr > TSTAR]).sum()) for k in PG))
GARB["meta_keys_other_than_y4_bitwise"] = bool(np.array_equal(np.asarray(Mg["qvk"]), Qr, equal_nan=True) and np.array_equal(np.asarray(Mg["E_ts"]), np.asarray(MTr["E_ts"])))
envk = {"PATH": BASE["PATH"], "HOME": "/root"}
with open(T2 + "/logs/t2_kappa_garbled.log", "w") as lf:
    rck = subprocess.call(["env", "-i", "PATH=" + BASE["PATH"], "HOME=/root", PY, KAPPA, "PATH,HOME,LC_CTYPE", "garbled"], cwd=T2, stdout=lf, stderr=subprocess.STDOUT)
assert rck == 0, ("garbled estimator failed", rck)
KG = json.load(open(T2 + "/receipts/RECEIPT_T2_kappa_garbled.json")); KP_G = KG["path_outputs"]["garbled"]["path"]
assert KG["inputs"]["meta"]["sha256"] == GARB["meta"]["sha256"] and KG["inputs"]["panel"]["sha256"] == GARB["panel"]["sha256"]
KPg = np.load(KP_G, allow_pickle=True); pre = Er <= TSTAR
C2P = {}
for k in ("active_scalar", "kappa_scalar", "lam_scalar", "active_sigma", "kappa_sigma", "lam_sigma", "bin_sigma", "refit_ts"):
    C2P[k] = bool(np.array_equal(np.asarray(KPg[k][pre], float), np.asarray(KPm[k][pre], float), equal_nan=True))
C2P["future_path_differs_cells"] = int(sum(int((~((KPg[k][~pre] == KPm[k][~pre]) | (np.isnan(KPg[k][~pre].astype(float)) & np.isnan(KPm[k][~pre].astype(float))))).sum()) for k in ("kappa_scalar", "lam_scalar")))
C2P["PASS"] = bool(all(v for k, v in C2P.items() if k not in ("future_path_differs_cells",)))
J3 = []
for s in SEEDS:
    J3 += [("C2_A0_s" + s, "A0", s, {}, DG)]
    if NAME_OK:
        J3 += [("C2_N_s" + s, "A0", s, {"T2_MODE": "name", "T2_KPATH": KP_G, "T2_KCOL": "scalar", "T2_INSTR": "1"}, DG), ("C2_Ns_s" + s, "A0", s, {"T2_MODE": "name", "T2_KPATH": KP_G, "T2_KCOL": "sigma", "T2_INSTR": "1"}, DG)]
    J3 += [("C2_SK_s" + s, "A0", s, {"T2_MODE": "seat", "T2_KPATH": KP_G, "T2_KCOL": "scalar", "T2_INSTR": "1"}, DG)]
W3S = wave(J3, "W3")
PAIRS = {"C2_A0_s%s": "GP_A0_s%s", "C2_N_s%s": "N_A0_s%s", "C2_Ns_s%s": "Ns_A0_s%s", "C2_SK_s%s": "SK_A0_s%s"}
Y4COLS = ("net", "pnl", "net_ex", "pnl_ex", "leg_king", "leg_rev24", "leg_fund")
C2 = {"path": C2P, "garbled_tree": GARB, "runs": {}}
for s in SEEDS:
    for gp, rp in PAIRS.items():
        g_, r_ = gp % s, rp % s
        if g_ not in RUNS: continue
        Zg, Zr = arr(g_), arr(r_); cols = [str(c) for c in Zr["cols"]]
        rg, rr = Zg["d30_n2_c42_rec"], Zr["d30_n2_c42_rec"]; tg, tr_ = rg[:, 0].astype(np.int64), rr[:, 0].astype(np.int64)
        mg, mr = tg <= TSTAR, tr_ <= TSTAR; lg, lr = tg < TSTAR, tr_ < TSTAR
        o = dict(real=r_, garbled=g_, ts_prefix_equal=bool(np.array_equal(tg[mg], tr_[mr])), n_rows_le_TSTAR=int(mr.sum()))
        if o["ts_prefix_equal"]:
            o["W_le_TSTAR"] = bitwise(Zg["d30_n2_c42_W"][mg], Zr["d30_n2_c42_W"][mr])
            keep_cols = [k for k, c in enumerate(cols) if c not in Y4COLS]
            o["rec_non_y4_cols_le_TSTAR"] = bitwise(rg[mg][:, keep_cols], rr[mr][:, keep_cols]); o["rec_all_cols_lt_TSTAR"] = bitwise(rg[lg], rr[lr])
            o["rec_rows_after_TSTAR_differ"] = int((np.abs(rg[~mg][:, cols.index("net_ex")][: int((~mr).sum())] - rr[~mr][:, cols.index("net_ex")][: int((~mg).sum())]) > 0).sum()) if (~mg).sum() and (~mr).sum() else 0
            o["PASS"] = bool(o["W_le_TSTAR"]["bitwise"] and o["rec_non_y4_cols_le_TSTAR"]["bitwise"] and o["rec_all_cols_lt_TSTAR"]["bitwise"] and C2P["PASS"])
        else: o["PASS"] = False
        C2["runs"][g_] = o
C2["arm_PASS"] = {a: bool(all(C2["runs"].get(("C2_%s_s%s" % (a, s)), {}).get("PASS", False) for s in SEEDS)) for a in (("N", "Ns", "SK") if NAME_OK else ("SK",))}
C2["baseline_PASS"] = bool(all(C2["runs"]["C2_A0_s%s" % s]["PASS"] for s in SEEDS))
print("C2", json.dumps({"path": C2P["PASS"], "arms": C2["arm_PASS"], "baseline": C2["baseline_PASS"]}), flush=True)
write_receipt(dict(STOP=False, name_arms_run=NAME_OK, wave1_s=W1S, wave2_s=W2S, wave3_s=W3S, kpath_garbled=dict(path=KP_G, sha256=sha(KP_G)), kappa_garbled_receipt_self_sha256=KG["self_sha256"], C2=C2))
print("DONE_t2_drive", round(time.time() - T0, 1), "s")

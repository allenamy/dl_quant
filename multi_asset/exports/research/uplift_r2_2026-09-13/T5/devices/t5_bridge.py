#!/usr/bin/env python3
"""t5_bridge.py — pod2 (PREREG_T5 §3-§8; gates G-T1, G-PANEL, G-SIM-R, G-ARCH-D, G-LEG, G-CLOSE).
Window simulator that mirrors the A0 device chain statement by statement (w10_sleeve_t5.py L243-L386) and swaps ingredient groups
{T FTRIM, W seat, B fund rank base, V fund values/freshness, M members, X exit rule, S eligibility, P stop layer, H state path, Z exec reshape}
(+ K king score only if a T4 array path is given) from the replay (R) to the deployed (D) version on the 30-anchor calendar.
All 2^|G| nodes x 2 seeds; Shapley (primary), fixed-order bridge, one-at-a-time, leave-one-out; lenses L-N, L-S, L-C; TC1, TC2; day-block bootstrap.
Launch: env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root /workspace/venv/bin/python devices/t5_bridge.py PATH,HOME,LC_CTYPE [K_NPZ]
"""
import os, sys, json, time, hashlib, subprocess, math, itertools
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "whitelist argv[1]"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
K_NPZ = sys.argv[2] if len(sys.argv) > 2 else None
import numpy as np
from scipy.stats import rankdata
R = "/workspace/uplift_r2_2026-09-13/T5"; T1R = "/workspace/uplift_r2_2026-09-13/T1"
PREREG_SHA = "33b20fa10109b95d9b4f0ff480619d82cd9bd1b7d2def7cf0a38c7938e83660f"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def sh(cmd):
    try: return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as e: return "ERR %s" % e
assert sha(R + "/PREREG_T5_deployed_carry_gap_2026-09-13.md") == PREREG_SHA, "prereg sha"
GPU0 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID0 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); LOAD0 = open("/proc/loadavg").read().split()[:3]
assert GPU0.replace(" ", "") == "0%,2MiB", ("GPU NOT IDLE, QUEUE", GPU0)
t0 = time.time(); B = 2000
utc = lambda t: time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
DRIVE = json.load(open(R + "/receipts/RECEIPT_T5_drive_gateP.json")); assert DRIVE["gate"]["P"]["PASS"], "G-P not passed"
ARMS = {"42": R + "/arms/C0_s42_t5.npz", "2027": R + "/arms/C0_s2027_t5.npz"}
for s_, p_ in ARMS.items(): assert sha(p_) == DRIVE["runs"]["C0_s" + s_]["out_sha256"], ("arm sha", s_)
INGP = R + "/receipts/T5_live_ingredients.npz"; ING_RC = json.load(open(R + "/receipts/RECEIPT_T5_live_ingredients.json")); assert sha(INGP) == ING_RC["out_sha256"]
MX = "/workspace/uplift_2026-09-11/r6/out/meta_newprod_v4_x0910.npz"; PX = "/workspace/uplift_2026-09-11/r6/out/wide_panel_4h_v2ext_x0910.npz"; PMAIN = "/workspace/data/wide_panel_4h_v2ext.npz"
T1D2 = T1R + "/receipts/T1_d2.npz"; T1ADD = T1R + "/receipts/RECEIPT_T1_addendum1.json"
INPUTS = {p: sha(p) for p in (ARMS["42"], ARMS["2027"], INGP, MX, PX, T1D2, T1ADD)}
# ---------------------------------------------------------------- deployed ingredients
ING = np.load(INGP, allow_pickle=True)
SYM = [str(s) for s in ING["symbols"]]; NW = len(SYM); CAL = [int(x) for x in ING["cal"]]; AT5 = [int(x) for x in ING["at5"]]; nC = len(CAL)
PM = ING["PM"]; LIVE = ING["LIVE"]; W3M = ING["W3M"]; SEL = ING["SEL"]; FED = ING["FED"]; KC = ING["KC"]; FC = ING["FC"]; WTL = ING["WTL"]
WARM = {1787702400: (ING["WARM_0826_kc"], ING["WARM_0826_fc"]), 1788062400: (ING["WARM_0830_kc"], ING["WARM_0830_fc"])}
NONCOMBO = (1788033600, 1788048000); A0826_00 = 1787702400; A0830_04 = 1788062400
kAT5 = [k for k, A in enumerate(CAL) if A in AT5]; assert len(kAT5) == 27
PXz = np.load(PX, allow_pickle=True); assert [str(s) for s in PXz["symbols"]] == SYM
tsP = PXz["ts"].astype(np.int64); prow = {int(t): j for j, t in enumerate(tsP)}
FNx = PXz["f_fund_now"].astype(np.float64); IVx = PXz["f_fund_iv"].astype(np.float64); IVfx = np.where(np.isfinite(IVx) & (IVx > 0), IVx, 8.0)
C4x = np.nan_to_num(FNx, nan=0.0) * (4.0 / IVfx); RN8x = FNx * (8.0 / IVfx)
assert [str(s) for s in np.load(PMAIN, allow_pickle=True)["symbols"]] == SYM
C4 = np.stack([C4x[prow[A]] for A in CAL]); RN8 = np.stack([RN8x[prow[A]] for A in CAL])
MXz = np.load(MX, allow_pickle=True); EM = MXz["E_ts"].astype(np.int64); emap = {int(t): i for i, t in enumerate(EM)}; Y4X = MXz["y4"]
# ---------------------------------------------------------------- replay dumps
def load_arm(p):
    Z = np.load(p, allow_pickle=True); pre = "d30_n2_c42_T5_"
    d = {k[len(pre):]: Z[k] for k in Z.files if k.startswith(pre)}
    d["rec_full"] = Z["d30_n2_c42_rec"]; d["cols"] = [str(c) for c in Z["cols"]]
    assert [int(x) for x in d["ts"]] == [1787688000] + CAL, "dump calendar"
    return d
DUMP = {s: load_arm(p) for s, p in ARMS.items()}
GROUPS = ["T", "W", "B", "V", "M", "X", "S", "P", "H", "Z"]
KD = None
if K_NPZ:
    KZ = np.load(K_NPZ, allow_pickle=True); KD = dict(v1=KZ["pred_v1"], v0=KZ["pred_v0"]); GROUPS.append("K")
    INPUTS[K_NPZ] = sha(K_NPZ)
NG = len(GROUPS); GI = {g: q for q, g in enumerate(GROUPS)}; FULL = (1 << NG) - 1
SMA = 0.1; SBAND = 2.5e-4; PHI = 0.45; FTRIM_TH = float("-0.0010")
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out
# ---------------------------------------------------------------- G-PANEL (device panel rows == x0910 rows used for carry)
GP = {}
for s, d in DUMP.items():
    fn = d["FN"][1:].astype(np.float64); iv = d["IV"][1:].astype(np.float64)
    fx = np.stack([FNx[prow[A]] for A in CAL]); ivx = np.stack([IVx[prow[A]] for A in CAL])
    eq = lambda a, b: bool(np.array_equal(np.isnan(a), np.isnan(b)) and np.array_equal(a[~np.isnan(a)], b[~np.isnan(b)]))
    GP[s] = dict(FN_equal=eq(fn, fx), IV_equal=eq(iv, ivx), dtype_FN=str(d["FN"].dtype), dtype_IV=str(d["IV"].dtype))
G_PANEL = dict(per_seed=GP, PASS=all(v["FN_equal"] and v["IV_equal"] for v in GP.values()))
print("G-PANEL", json.dumps(G_PANEL), flush=True); assert G_PANEL["PASS"]
# ---------------------------------------------------------------- simulator
def simulate(seed, bits, legs=False, inject=False, king_variant="v1", want_books=False):
    d = DUMP[seed]; S = set(g for g in GROUPS if bits >> GI[g] & 1)
    if inject: assert bits == FULL
    NL = 5
    if "H" in S or inject:
        H, HF = WARM[A0826_00][0].copy(), WARM[A0826_00][1].copy()
        HL = np.zeros((NL, NW)); HL[4] = H; HFL = np.zeros((NL, NW)); HFL[4] = HF
    else:
        H = d["smk"][0].copy(); HF = d["smf"][0].copy()
        HL = np.vstack([d["SMC_out"][0], np.zeros((1, NW))]); HFL = np.vstack([d["SMFC_out"][0], np.zeros((1, NW))])
    v = np.full(nC, np.nan); Nsum = np.zeros(NW); diag = dict(skipped=[], ftrim_k=[], ftrim_f=[], nsel=[], nmem=[])
    books = {}
    for k, A in enumerate(CAL):
        r = k + 1; Dav = A not in NONCOMBO
        if "H" in S or inject:
            if A in NONCOMBO: continue
            if A == A0830_04:
                H, HF = WARM[A0830_04][0].copy(), WARM[A0830_04][1].copy(); HL = np.zeros((NL, NW)); HL[4] = H; HFL = np.zeros((NL, NW)); HFL[4] = HF
        if inject:
            if A not in AT5: continue
            if A != A0830_04:
                H, HF = KC[k - 1].copy(), FC[k - 1].copy(); HL = np.zeros((NL, NW)); HL[4] = H; HFL = np.zeros((NL, NW)); HFL[4] = HF
        use = lambda g: (g in S) and Dav
        M = PM[k] if use("M") else d["mem"][r]
        m = np.where(M)[0]
        w3 = W3M[k] if use("W") else d["w3"][r]
        FEv = FED[k] if use("V") else d["FE"][r]
        FZ = xz(FEv[m]) if use("B") else xz(FEv)[m]
        if use("K"): kz = xz(KD[king_variant][k][m])
        else: kz = xz(d["SLOW"][r][m])
        rz = xz(-d["R24"][r][m]); fz10 = xz(d["F10P"][r][m])
        _fs = 1.0
        z = w3[0]*np.nan_to_num(kz) + w3[1]*np.nan_to_num(rz) + w3[2]*_fs*np.nan_to_num(FZ)
        if legs: ZC = np.stack([w3[0]*np.nan_to_num(kz), w3[1]*np.nan_to_num(rz), w3[2]*_fs*np.nan_to_num(FZ), np.zeros(len(m)), np.zeros(len(m))])
        FNm = d["FN"][r][m]; IVm = d["IV"][r][m]
        _fnp = FNm * (8.0 / np.where(IVm > 0, IVm, 8.0)); _fnp = np.where(np.isfinite(_fnp), _fnp, 0.0)
        trim = not use("T")
        if trim:
            kill_k = (z < 0) & (_fnp <= FTRIM_TH)
            if legs: ZC = np.where(kill_k[None, :], 0.0, ZC)
            z = np.where(kill_k, 0.0, z)
        if use("S"): sel = SEL[k][m]
        else:
            ok = np.isfinite(d["Y4"][r][m]); qv4h = np.expm1(np.clip(d["QVK"][r][m], 0, 30)) * 48
            sel = ok & (qv4h >= 2.5e5)
        if sel.sum() < 80: diag["skipped"].append((utc(A), "sel<80")); continue
        w = np.where(sel, z, 0.0)
        w[sel] -= w[sel].mean()
        g = np.abs(w).sum()
        if g < 1e-9: diag["skipped"].append((utc(A), "g<1e-9")); continue
        w /= g; capw = 2.5 / max(int(sel.sum()), 1)
        if legs:
            WC = np.where(sel[None, :], ZC, 0.0); WC[:, sel] -= WC[:, sel].mean(axis=1, keepdims=True); WC /= g
            _wpre = w.copy()
        w = np.clip(w, -capw, capw)
        if legs:
            _rat = np.where(_wpre != 0.0, w / np.where(_wpre != 0.0, _wpre, 1.0), 1.0); WC = WC * _rat[None, :]
        g2 = np.abs(w).sum()
        if g2 > 1e-9: w /= g2
        if legs and g2 > 1e-9: WC /= g2
        tgt = np.zeros(NW); tgt[m] = w
        if legs: TGC = np.zeros((NL, NW)); TGC[:, m] = WC
        stop = not use("P")
        if stop:
            bl = d["bl"][r]
            if bl.any():
                tgt[bl] = 0.0
                if legs: TGC[:, bl] = 0.0
        sm = H + SMA * (tgt - H); trade = sm - H
        if legs:
            SMC = HL + SMA * (TGC - HL); SMC = np.where((np.abs(trade) < SBAND)[None, :], HL, SMC)
        sm = np.where(np.abs(trade) < SBAND, H, sm); trade = sm - H
        Mmask = np.zeros(NW, bool); Mmask[m] = True; selmask = np.zeros(NW, bool); selmask[m[sel]] = True
        if use("X"):
            keep = LIVE & Mmask & selmask; leave = (~keep) & (np.abs(sm) > 1e-12)
            sm = np.where(leave, 0.0, sm)
            if legs: SMC[:, leave] = 0.0
        else:
            _nonsel = np.zeros(NW, bool); _nonsel[m[~sel]] = True
            sm = np.where(_nonsel, 0.0, sm); trade = sm - H
            if legs: SMC[:, _nonsel] = 0.0
        # F10 chain (same chain, king score replaced by F10 score, own state HF)
        _w3f = w3
        _zf = (_w3f[0] * np.nan_to_num(fz10) + _w3f[1] * np.nan_to_num(rz) + _w3f[2] * np.nan_to_num(FZ))
        if legs: ZFC = np.stack([np.zeros(len(m)), _w3f[1] * np.nan_to_num(rz), _w3f[2] * np.nan_to_num(FZ), _w3f[0] * np.nan_to_num(fz10), np.zeros(len(m))])
        if trim:
            kill_f = (_zf < 0) & (_fnp <= FTRIM_TH)
            if legs: ZFC = np.where(kill_f[None, :], 0.0, ZFC)
            _zf = np.where(kill_f, 0.0, _zf)
        _wf = np.where(sel, _zf, 0.0)
        if sel.any():
            _wf[sel] -= _wf[sel].mean()
        if legs:
            WFC = np.where(sel[None, :], ZFC, 0.0)
            if sel.any(): WFC[:, sel] -= WFC[:, sel].mean(axis=1, keepdims=True)
        _gf = np.abs(_wf).sum()
        if _gf > 1e-9:
            _wf = _wf / _gf
            if legs: WFC = WFC / _gf; _wfpre = _wf.copy()
            _wf = np.clip(_wf, -capw, capw)
            if legs:
                _ratf = np.where(_wfpre != 0.0, _wf / np.where(_wfpre != 0.0, _wfpre, 1.0), 1.0); WFC = WFC * _ratf[None, :]
            _g2f = np.abs(_wf).sum()
            if _g2f > 1e-9:
                _wf = _wf / _g2f
                if legs: WFC = WFC / _g2f
            _tgtf = np.zeros(NW); _tgtf[m] = _wf
            _smf = HF + SMA * (_tgtf - HF)
            _trf = _smf - HF
            if legs:
                TGFC = np.zeros((NL, NW)); TGFC[:, m] = WFC
                SMFC = HFL + SMA * (TGFC - HFL); SMFC = np.where((np.abs(_trf) < SBAND)[None, :], HFL, SMFC)
            _smf = np.where(np.abs(_trf) < SBAND, HF, _smf)
            if use("X"):
                leavef = (~keep) & (np.abs(_smf) > 1e-12); _smf = np.where(leavef, 0.0, _smf)
                if legs: SMFC[:, leavef] = 0.0
            else:
                _smf = np.where(_nonsel, 0.0, _smf)
                if legs: SMFC[:, _nonsel] = 0.0
            if stop:
                _blf = bl
                if _blf.any():
                    _smf[_blf] = 0.0
                    if legs: SMFC[:, _blf] = 0.0
        else:
            _smf = HF.copy()
            if legs: SMFC = HFL.copy()
        if use("Z"):
            smb = 0.55 * sm + 0.45 * _smf; book = smb
            if legs: LK = 0.55 * SMC; LF = 0.45 * SMFC
        else:
            smb = (1.0 - PHI) * sm + PHI * _smf
            if legs: LK = (1.0 - PHI) * SMC; LF = PHI * SMFC
            nz = np.abs(smb) > 1e-12
            smr = smb.copy()
            if nz.any():
                smr[nz] -= smr[nz].mean()
                if legs: LK[:, nz] -= LK[:, nz].mean(axis=1, keepdims=True); LF[:, nz] -= LF[:, nz].mean(axis=1, keepdims=True)
                _g0 = np.abs(smb).sum(); _g1 = np.abs(smr).sum()
                if _g1 > 1e-9:
                    smr *= _g0 / _g1
                    if legs: LK *= _g0 / _g1; LF *= _g0 / _g1
            book = smr
        gw = np.abs(book).sum(); v[k] = float((book * C4[k]).sum() / gw * 1e4)
        if A in AT5: Nsum += book / gw * C4[k] * 1e4
        diag["nsel"].append(int(sel.sum())); diag["nmem"].append(int(len(m)))
        if trim: diag["ftrim_k"].append(int(kill_k.sum())); diag["ftrim_f"].append(int(kill_f.sum()))
        if want_books:
            bk = dict(sm=sm.copy(), smf=_smf.copy(), smb=smb.copy(), book=book.copy(), gw=gw)
            if legs: bk.update(LK=LK.copy(), LF=LF.copy(), SMC=SMC.copy(), SMFC=SMFC.copy())
            if not use("Z"):
                fnow = np.nan_to_num(d["FN"][r][m], nan=0.0); ivv = d["IV"][r][m]; ivv = np.where(np.isfinite(ivv) & (ivv > 0), ivv, 8.0)
                bk["carry_T1cal"] = float((smr[m] * fnow * (4.0 / ivv)).sum() * 1e4) / float(np.abs(smb).sum())
            books[A] = bk
        H = sm; HF = _smf
        if legs: HL = SMC; HFL = SMFC
    return v, Nsum, diag, books
# ---------------------------------------------------------------- G-SIM-R and G-LEG at R
GSIM = {}; RBOOKS = {}
for s, d in DUMP.items():
    assert np.array_equal(d["H_in"][1:], d["smk"][:-1]) and np.array_equal(d["HF_in"][1:], d["smf"][:-1]), "dump state continuity"
    v0, _, dg0, bk = simulate(s, 0, legs=True, want_books=True); RBOOKS[s] = bk
    mx = dict(sm=0.0, smf=0.0, smb=0.0, smr=0.0, legs_T1rows=0.0, SMC=0.0, SMFC=0.0, carry_T1cal=0.0, leg_identity=0.0)
    for k, A in enumerate(CAL):
        r = k + 1; b = bk[A]
        mx["sm"] = max(mx["sm"], float(np.abs(b["sm"] - d["smk"][r]).max())); mx["smf"] = max(mx["smf"], float(np.abs(b["smf"] - d["smf"][r]).max()))
        mx["smb"] = max(mx["smb"], float(np.abs(b["smb"] - d["smb"][r]).max())); mx["smr"] = max(mx["smr"], float(np.abs(b["book"] - d["smr"][r]).max()))
        mx["legs_T1rows"] = max(mx["legs_T1rows"], float(np.abs((b["LK"] + b["LF"])[:4] - d["SMRC"][r]).max()))
        mx["SMC"] = max(mx["SMC"], float(np.abs(b["SMC"][:4] - d["SMC_out"][r]).max())); mx["SMFC"] = max(mx["SMFC"], float(np.abs(b["SMFC"][:4] - d["SMFC_out"][r]).max()))
        rc = d["rec"][r]; mx["carry_T1cal"] = max(mx["carry_T1cal"], abs(b["carry_T1cal"] - rc[20] / rc[5]))
        mx["leg_identity"] = max(mx["leg_identity"], float(np.abs(b["LK"].sum(0) + b["LF"].sum(0) - b["book"]).max()))
    GSIM[s] = dict(maxabs=mx, skipped=dg0["skipped"], PASS=bool(max(mx[x] for x in ("sm", "smf", "smb", "smr", "legs_T1rows", "SMC", "SMFC")) <= 1e-12 and mx["carry_T1cal"] <= 1e-9 and not dg0["skipped"]))
G_SIM_R = dict(per_seed=GSIM, PASS=all(v["PASS"] for v in GSIM.values()))
print("G-SIM-R", json.dumps(G_SIM_R), flush=True); assert G_SIM_R["PASS"], "G-SIM-R failed: no L-B / L-C numbers"
# ---------------------------------------------------------------- G-T1
ADD = json.load(open(T1ADD))["result"]; DZ = np.load(T1D2, allow_pickle=True); DC = [str(c) for c in DZ["cols"]]; DD = DZ["D"]
d2rows = {int(rw[DC.index("A")]): float(rw[DC.index("carry")]) for rw in DD}
d2rows[A0826_00] = float(ADD["X3"]["A30_anchor_rows"]["2026-08-26 00:00Z"]["D2"]["carry"])
A29 = [A for A in CAL if A != 1788033600]
CD_all = {A: float((WTL[k] * C4[k]).sum() / np.abs(WTL[k]).sum() * 1e4) for k, A in enumerate(CAL) if np.isfinite(WTL[k]).all()}
gt1 = dict(D2_per_anchor_maxabs=max(abs(CD_all[A] - d2rows[A]) for A in A29), D2_mean_A29=float(np.mean([CD_all[A] for A in A29])), T1_D2_mean_A29=float(ADD["X3"]["A30_means"]["D2_carry"]))
for s, d in DUMP.items():
    rc = d["rec"][1:]; gt1["R_carry_A30_s" + s] = float((rc[:, 20] / rc[:, 5]).mean()); gt1["T1_R_carry_A30_s" + s] = float(ADD["X3_per_arm"]["C0_s" + s]["carry_A30"])
    assert np.array_equal(d["rec"], d["rec_full"][np.searchsorted(d["rec_full"][:, 0], d["ts"])]), "dump rec rows"
gt1["PASS"] = bool(gt1["D2_per_anchor_maxabs"] <= 1e-9 and abs(gt1["D2_mean_A29"] - gt1["T1_D2_mean_A29"]) <= 1e-9 and all(abs(gt1["R_carry_A30_s" + s] - gt1["T1_R_carry_A30_s" + s]) <= 1e-9 for s in DUMP))
G_T1 = gt1; print("G-T1", json.dumps(G_T1), flush=True); assert G_T1["PASS"], "G-T1 failed: reconcile first"
# ---------------------------------------------------------------- all nodes (parallel)
from multiprocessing import Pool
def node_task(args):
    s, bits = args
    v, Ns, dg, _ = simulate(s, bits)
    return s, bits, v, Ns, len(dg["skipped"])
V = {s: np.full((1 << NG, nC), np.nan) for s in DUMP}; NS = {s: np.zeros((1 << NG, NW)) for s in DUMP}; SKIP = {s: np.zeros(1 << NG, int) for s in DUMP}
tasks = [(s, b) for s in DUMP for b in range(1 << NG)]
with Pool(40) as pool:
    for s, bits, v, Ns, nsk in pool.imap_unordered(node_task, tasks, chunksize=8):
        V[s][bits] = v; NS[s][bits] = Ns; SKIP[s][bits] = nsk
print("nodes done", len(tasks), round(time.time() - t0, 1), flush=True)
# ---------------------------------------------------------------- decomposition per seed
days = np.array([A // 86400 for A in AT5]); ki = np.array(kAT5)
def boot_ratio(num, den, k):
    u, inv = np.unique(days, return_inverse=True); nd = len(u)
    sn = np.bincount(inv, weights=num, minlength=nd); sdn = np.bincount(inv, weights=den, minlength=nd)
    rng = np.random.default_rng([20260905, k]); dr = rng.integers(0, nd, size=(B, nd))
    rep = sn[dr].sum(1) / sdn[dr].sum(1)
    return [float(sn.sum() / sdn.sum()), float(np.percentile(rep, 2.5)), float(np.percentile(rep, 97.5))]
coef = [math.factorial(q) * math.factorial(NG - q - 1) / math.factorial(NG) for q in range(NG)]
popc = np.array([bin(b).count("1") for b in range(1 << NG)])
ORDER = ["T", "B", "W", "V", "M", "S", "X", "P", "H", "Z"] + (["K"] if "K" in GROUPS else [])
C_D = np.array([CD_all[A] for A in AT5])
OUT = dict(groups=GROUPS, order=ORDER, AT5=[utc(A) for A in AT5], seeds={})
NPZ = dict(AT5=np.array(AT5), C_D=C_D)
for s, d in DUMP.items():
    Vs = V[s][:, ki]; C_R_T1 = np.array([d["rec"][k + 1][20] / d["rec"][k + 1][5] for k in kAT5]); C_R_full = Vs[0]
    G0 = C_R_T1 - C_R_full; REM = C_D - Vs[FULL]; DEL = C_D - C_R_T1
    phi = {}
    for g in GROUPS:
        q = GI[g]; acc = np.zeros(len(ki))
        for b in range(1 << NG):
            if b >> q & 1: continue
            acc += coef[popc[b]] * (Vs[b | (1 << q)] - Vs[b])
        phi[g] = acc
    close_shap = float(np.abs(DEL - (G0 + sum(phi.values()) + REM)).max()); eff = float(np.abs(sum(phi.values()) - (Vs[FULL] - Vs[0])).max())
    seq = {}; pref = 0
    for g in ORDER:
        nb = pref | (1 << GI[g]); seq[g] = Vs[nb] - Vs[pref]; pref = nb
    close_seq = float(np.abs(DEL - (G0 + sum(seq.values()) + REM)).max())
    oat = {g: Vs[1 << GI[g]] - Vs[0] for g in GROUPS}; loo = {g: Vs[FULL] - Vs[FULL ^ (1 << GI[g])] for g in GROUPS}
    comp = dict(G0=G0, **{"phi_" + g: phi[g] for g in GROUPS}, REM=REM)
    shares = {c: boot_ratio(x, DEL, 51) for c, x in comp.items()}; means = {c: boot_ratio(x, np.ones(len(ki)), 51) for c, x in comp.items()}
    seq_sh = {g: boot_ratio(seq[g], DEL, 52) for g in ORDER}; seq_mean = {g: float(seq[g].mean()) for g in ORDER}
    head = dict(C_D=boot_ratio(C_D, np.ones(len(ki)), 57), C_R_T1=boot_ratio(C_R_T1, np.ones(len(ki)), 57), C_R_full=float(C_R_full.mean()), Delta=boot_ratio(DEL, np.ones(len(ki)), 57), ratio=boot_ratio(C_D, C_R_T1, 57),
                v_full=float(Vs[FULL].mean()), n=len(ki))
    per_day = {time.strftime("%m-%d", time.gmtime(int(dd) * 86400)): dict(n=int((days == dd).sum()), Delta=float(DEL[days == dd].mean()), C_D=float(C_D[days == dd].mean()), C_R_T1=float(C_R_T1[days == dd].mean()),
               **{"phi_" + g: float(phi[g][days == dd].mean()) for g in GROUPS}, REM=float(REM[days == dd].mean())) for dd in np.unique(days)}
    # per-name Shapley
    NSs = NS[s]; phin = {}
    for g in GROUPS:
        q = GI[g]; acc = np.zeros(NW)
        for b in range(1 << NG):
            if b >> q & 1: continue
            acc += coef[popc[b]] * (NSs[b | (1 << q)] - NSs[b])
        phin[g] = acc / len(ki)
    wD = WTL[ki] / np.abs(WTL[ki]).sum(1, keepdims=True); wR = np.stack([RBOOKS[s][A]["book"] / np.abs(RBOOKS[s][A]["book"]).sum() for A in AT5])
    rn8m = np.nanmean(np.where(np.isfinite(RN8[ki]), RN8[ki], np.nan), 0)
    def namerow(n, g): return dict(symbol=SYM[n], phi=float(phin[g][n]), wD_mean=float(wD[:, n].mean()), wR_mean=float(wR[:, n].mean()), rn8_mean_bp=(float(rn8m[n] * 1e4) if np.isfinite(rn8m[n]) else None), live=bool(LIVE[n]))
    names = {g: dict(top_pos=[namerow(n, g) for n in np.argsort(-phin[g])[:15]], top_neg=[namerow(n, g) for n in np.argsort(phin[g])[:10]], sum_check=float(phin[g].sum() - phi[g].mean())) for g in GROUPS}
    # N' diagnostic (archived-state injection)
    vN1, _, dgN1, _ = simulate(s, FULL, inject=True)
    diagNp = dict(flow_at_A=boot_ratio(C_D - vN1[ki], np.ones(len(ki)), 51), carried_state=boot_ratio(vN1[ki] - Vs[FULL], np.ones(len(ki)), 51), skipped=dgN1["skipped"])
    # B_N books and weight distance
    _, _, dgN, bkN = simulate(s, FULL, legs=True, want_books=True)
    dist = []
    for k, A in zip(kAT5, AT5):
        bN = bkN[A]["book"] / np.abs(bkN[A]["book"]).sum(); dist.append((float(np.abs(wD[kAT5.index(k)] - bN).sum()), float(np.corrcoef(wD[kAT5.index(k)], bN)[0, 1])))
    legs_idN = max(float(np.abs(bkN[A]["LK"].sum(0) + bkN[A]["LF"].sum(0) - bkN[A]["book"]).max()) for A in AT5)
    # ---------------- L-C chain / leg lens
    LEGN = ["king", "rev24", "fund", "f10", "inherited"]
    def leg_carry(bk):
        out = {}
        for A in AT5:
            b = bk[A]; gw = np.abs(b["book"]).sum()
            for ch, Lm in (("K", b["LK"]), ("F", b["LF"])):
                for li, ln in enumerate(LEGN):
                    out.setdefault(ch + "-" + ln, []).append(float((Lm[li] * C4[CAL.index(A)]).sum() / gw * 1e4))
        return {c: np.array(x) for c, x in out.items()}
    LR_ = leg_carry(RBOOKS[s]); LN_ = leg_carry(bkN)
    LD_K = np.array([float((0.55 * KC[k] * C4[k]).sum() / np.abs(WTL[k]).sum() * 1e4) for k in kAT5]); LD_F = np.array([float((0.45 * FC[k] * C4[k]).sum() / np.abs(WTL[k]).sum() * 1e4) for k in kAT5])
    close_LC_R = float(np.abs(sum(LR_.values()) - C_R_full).max()); close_LC_N = float(np.abs(sum(LN_.values()) - Vs[FULL]).max()); close_LC_D = float(np.abs(LD_K + LD_F - C_D).max())
    LC = dict(R={c: boot_ratio(x, np.ones(len(ki)), 55) for c, x in LR_.items()}, BN={c: boot_ratio(x, np.ones(len(ki)), 55) for c, x in LN_.items()},
              D=dict(K_chain=boot_ratio(LD_K, np.ones(len(ki)), 55), F_chain=boot_ratio(LD_F, np.ones(len(ki)), 55)),
              R_chain=dict(K=float(sum(v_ for c, v_ in LR_.items() if c.startswith("K-")).mean()), F=float(sum(v_ for c, v_ in LR_.items() if c.startswith("F-")).mean())),
              BN_chain=dict(K=float(sum(v_ for c, v_ in LN_.items() if c.startswith("K-")).mean()), F=float(sum(v_ for c, v_ in LN_.items() if c.startswith("F-")).mean())),
              fund_leg_share_of_carry=dict(R=float((LR_["K-fund"] + LR_["F-fund"]).sum() / C_R_full.sum()), BN=float((LN_["K-fund"] + LN_["F-fund"]).sum() / Vs[FULL].sum())),
              seats=dict(w3_R_mean=[float(x) for x in d["w3"][[k + 1 for k in kAT5]].mean(0)], w3m_D_mean=[float(x) for x in W3M[ki].mean(0)], w3_R_first_last=[[float(x) for x in d["w3"][kAT5[0] + 1]], [float(x) for x in d["w3"][kAT5[-1] + 1]]]),
              closure=dict(R=close_LC_R, BN=close_LC_N, D=close_LC_D), leg_identity_BN=legs_idN)
    # ---------------- L-N and L-S lenses (R = simulated all-R book == device smr)
    cellsN = ["onlyD_long", "onlyD_short", "onlyR_long", "onlyR_short", "common_same_long", "common_same_short", "common_opposite"]
    BUCK = ["<=-30bp", "-30..-10bp", "-10..0bp", "0..10bp", "10..30bp", ">=30bp", "no_quote"]
    def bucket(rn):
        b = np.full(NW, 6, int); fin = np.isfinite(rn)
        b[fin & (rn <= -0.0030)] = 0; b[fin & (rn > -0.0030) & (rn <= -0.0010)] = 1; b[fin & (rn > -0.0010) & (rn < 0.0)] = 2
        b[fin & (rn >= 0.0) & (rn < 0.0010)] = 3; b[fin & (rn >= 0.0010) & (rn < 0.0030)] = 4; b[fin & (rn >= 0.0030)] = 5
        return b
    LNv = {c: np.zeros(len(ki)) for c in cellsN}; LSv = {}; LS_D = {}; LS_R = {}; common_names = np.zeros(NW)
    for q_, (k, A) in enumerate(zip(kAT5, AT5)):
        wd = wD[q_]; wr = wR[q_]; c = C4[k] * 1e4
        oD = (wr == 0) & (wd != 0); oR = (wd == 0) & (wr != 0); both = (wd != 0) & (wr != 0)
        LNv["onlyD_long"][q_] = float((wd * c)[oD & (wd > 0)].sum()); LNv["onlyD_short"][q_] = float((wd * c)[oD & (wd < 0)].sum())
        LNv["onlyR_long"][q_] = -float((wr * c)[oR & (wr > 0)].sum()); LNv["onlyR_short"][q_] = -float((wr * c)[oR & (wr < 0)].sum())
        dd_ = (wd - wr) * c
        LNv["common_same_long"][q_] = float(dd_[both & (wd > 0) & (wr > 0)].sum()); LNv["common_same_short"][q_] = float(dd_[both & (wd < 0) & (wr < 0)].sum())
        LNv["common_opposite"][q_] = float(dd_[both & (np.sign(wd) != np.sign(wr))].sum())
        common_names += np.where(both, dd_, 0.0)
        bk_ = bucket(RN8[k])
        for side, sgn in (("long", 1), ("short", -1)):
            for bi, bn in enumerate(BUCK):
                cellD = (np.sign(wd) == sgn) & (bk_ == bi); cellR = (np.sign(wr) == sgn) & (bk_ == bi)
                key = side + "|" + bn
                LS_D.setdefault(key, np.zeros(len(ki)))[q_] = float((wd * c)[cellD].sum()); LS_R.setdefault(key, np.zeros(len(ki)))[q_] = float((wr * c)[cellR].sum())
    for key in LS_D: LSv[key] = LS_D[key] - LS_R[key]
    close_LN = float(np.abs(DEL - (G0 + sum(LNv.values()))).max()); close_LS = float(np.abs(DEL - (G0 + sum(LSv.values()))).max())
    LN = dict(cells={c: dict(mean_share=boot_ratio(x, DEL, 53), mean=boot_ratio(x, np.ones(len(ki)), 53)) for c, x in LNv.items()},
              top_common=[dict(symbol=SYM[n], contrib=float(common_names[n] / len(ki)), wD_mean=float(wD[:, n].mean()), wR_mean=float(wR[:, n].mean()), rn8_mean_bp=(float(rn8m[n] * 1e4) if np.isfinite(rn8m[n]) else None)) for n in np.argsort(-np.abs(common_names))[:20]],
              n_names_mean=dict(onlyD=float(np.mean([((wR[q] == 0) & (wD[q] != 0)).sum() for q in range(len(ki))])), onlyR=float(np.mean([((wD[q] == 0) & (wR[q] != 0)).sum() for q in range(len(ki))])), common=float(np.mean([((wD[q] != 0) & (wR[q] != 0)).sum() for q in range(len(ki))]))))
    LS = dict(cells={key: dict(D=float(LS_D[key].mean()), R=float(LS_R[key].mean()), delta_mean=boot_ratio(LSv[key], np.ones(len(ki)), 54), delta_share=boot_ratio(LSv[key], DEL, 54)) for key in LSv},
              gross_share=dict(D_short_le_m10=float(np.mean([np.abs(wD[q][(wD[q] < 0) & np.isfinite(RN8[k]) & (RN8[k] <= -0.0010)]).sum() for q, k in enumerate(kAT5)])),
                               R_short_le_m10=float(np.mean([np.abs(wR[q][(wR[q] < 0) & np.isfinite(RN8[k]) & (RN8[k] <= -0.0010)]).sum() for q, k in enumerate(kAT5)]))))
    tc1_num = LSv["short|<=-30bp"] + LSv["short|-30..-10bp"]
    TC1 = dict(delta_share=boot_ratio(tc1_num, DEL, 56), delta_mean=boot_ratio(tc1_num, np.ones(len(ki)), 56),
               D_cohort_share_of_CD=float((LS_D["short|<=-30bp"] + LS_D["short|-30..-10bp"]).sum() / C_D.sum()), R_cohort_share_of_CR=float((LS_R["short|<=-30bp"] + LS_R["short|-30..-10bp"]).sum() / C_R_full.sum()))
    TC1["reading_point"] = ("YES" if TC1["delta_share"][0] >= 0.5 else ("NO" if TC1["delta_share"][0] <= 0.2 else "PARTIAL"))
    # FTRIM activity on R
    _, _, dgR, _ = simulate(s, 0)
    OUT["seeds"][s] = dict(headline=head, per_day=per_day, shapley=dict(share=shares, mean=means, efficiency_maxabs=eff, closure_maxabs=close_shap),
                           sequential=dict(share=seq_sh, mean=seq_mean, closure_maxabs=close_seq), one_at_a_time={g: float(oat[g].mean()) for g in GROUPS}, leave_one_out={g: float(loo[g].mean()) for g in GROUPS},
                           names_per_group=names, Nprime=diagNp, BN_vs_D=dict(L1_mean=float(np.mean([x[0] for x in dist])), corr_mean=float(np.mean([x[1] for x in dist]))),
                           LC=LC, LN=dict(LN, closure_maxabs=close_LN), LS=dict(LS, closure_maxabs=close_LS), TC1=TC1,
                           R_ftrim=dict(mean_killed_king_chain=float(np.mean(dgR["ftrim_k"])), mean_killed_f10_chain=float(np.mean(dgR["ftrim_f"])), mean_nsel=float(np.mean(dgR["nsel"])), mean_nmem=float(np.mean(dgR["nmem"]))),
                           node_skips=int(SKIP[s].sum()))
    NPZ.update({f"s{s}_V": V[s], f"s{s}_NS": NS[s], f"s{s}_C_R_T1": C_R_T1, f"s{s}_G0": G0, f"s{s}_REM": REM, f"s{s}_DEL": DEL, **{f"s{s}_phi_{g}": phi[g] for g in GROUPS}, **{f"s{s}_seq_{g}": seq[g] for g in ORDER}})
    print("seed", s, "done", round(time.time() - t0, 1), flush=True)
# ---------------------------------------------------------------- G-CLOSE, G-LEG, G-ARCH-D (re-assert)
cl = {s: dict(shapley=o["shapley"]["closure_maxabs"], sequential=o["sequential"]["closure_maxabs"], LN=o["LN"]["closure_maxabs"], LS=o["LS"]["closure_maxabs"], LC_R=o["LC"]["closure"]["R"], LC_BN=o["LC"]["closure"]["BN"], LC_D=o["LC"]["closure"]["D"]) for s, o in OUT["seeds"].items()}
G_CLOSE = dict(per_seed=cl, PASS=all(max(v.values()) <= 1e-6 for v in cl.values()))
G_LEG = dict(R=max(GSIM[s]["maxabs"]["leg_identity"] for s in GSIM), BN=max(o["LC"]["leg_identity_BN"] for o in OUT["seeds"].values())); G_LEG["PASS"] = bool(G_LEG["R"] <= 1e-12 and G_LEG["BN"] <= 1e-12)
G_ARCH_D = dict(max_abs=max(float(np.abs(WTL[k] - (0.55 * KC[k] + 0.45 * FC[k])).max()) for k in kAT5)); G_ARCH_D["PASS"] = bool(G_ARCH_D["max_abs"] <= 1e-9)
print("G-CLOSE", json.dumps(G_CLOSE), "G-LEG", json.dumps(G_LEG), "G-ARCH-D", json.dumps(G_ARCH_D), flush=True)
# ---------------------------------------------------------------- king-form anchors (descriptive)
KF = {}
for s, d in DUMP.items():
    KF[s] = {utc(A): dict(C_D=CD_all[A], C_R_T1=float(d["rec"][CAL.index(A) + 1][20] / d["rec"][CAL.index(A) + 1][5])) for A in (A0826_00, 1788048000)}
# ---------------------------------------------------------------- TC2 (deployed only)
E2 = [int(x) for x in ING["E2A"]]; WE2 = ING["WE2"]; wE = WE2 / np.abs(WE2).sum(1, keepdims=True)
Y = np.stack([np.nan_to_num(Y4X[emap[A]].astype(np.float64), nan=0.0) for A in E2]); RNE = np.stack([RN8x[prow[A]] for A in E2])
wA = WTL[ki] / np.abs(WTL[ki]).sum(1, keepdims=True)
cohortA = (wA < 0) & np.isfinite(RN8[ki]) & (RN8[ki] <= -0.0010)
CAug = cohortA.any(0); AugCarry = np.where(cohortA, wA * C4[ki] * 1e4, 0.0).sum(0)
Ls = np.where(wE < 0, wE * Y * 1e4, 0.0); Ln = Ls.sum(0)
d0906 = np.array([time.strftime("%m-%d", time.gmtime(A)) == "09-06" for A in E2]); Ln06 = Ls[d0906].sum(0)
neg = Ln < 0; neg06 = Ln06 < 0
M1 = float(Ln[CAug & neg].sum() / Ln[neg].sum()); M2 = float(Ln06[CAug & neg06].sum() / Ln06[neg06].sum()) if neg06.any() else None
M3 = float(AugCarry[CAug & neg].sum() / AugCarry[CAug].sum())
stillE = ((wE < 0) & np.isfinite(RNE) & (RNE <= -0.0010)).sum(0); shortE = (wE < 0).sum(0)
top = [dict(symbol=SYM[n], L_short_E2a_bps_sum=float(Ln[n]), L_short_0906=float(Ln06[n]), in_C_Aug=bool(CAug[n]), aug_carry_bps_sum=float(AugCarry[n]), E2a_anchors_short=int(shortE[n]), E2a_anchors_short_rn8_le_m10=int(stillE[n])) for n in np.argsort(Ln)[:15]]
TC2 = dict(n_E2a=len(E2), n_0906=int(d0906.sum()), n_C_Aug=int(CAug.sum()), M1=M1, M2=M2, M3=M3, reading=("SAME NAMES" if M1 >= 0.5 else ("DIFFERENT NAMES" if M1 <= 0.2 else "PARTIAL")),
           total_short_price_E2a_per_anchor=float(Ln.sum() / len(E2)), C_Aug_short_price_E2a_per_anchor=float(Ln[CAug].sum() / len(E2)), total_short_loss_names_E2a=float(Ln[neg].sum()), top15_short_losers=top,
           C_Aug_names_by_aug_carry=[dict(symbol=SYM[n], aug_carry_bps_sum=float(AugCarry[n]), L_short_E2a=float(Ln[n])) for n in np.argsort(AugCarry)[::-1][:20] if CAug[n]])
print("TC2", json.dumps({k: v for k, v in TC2.items() if k not in ("top15_short_losers", "C_Aug_names_by_aug_carry")}), flush=True)
# ---------------------------------------------------------------- write
GPU1 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID1 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); LOAD1 = open("/proc/loadavg").read().split()[:3]
np.savez_compressed(R + "/receipts/T5_bridge_components.npz", **NPZ)
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, K_included=bool("K" in GROUPS), K_npz=K_NPZ, gates=dict(G_PANEL=G_PANEL, G_SIM_R=G_SIM_R, G_T1=G_T1, G_CLOSE=G_CLOSE, G_LEG=G_LEG, G_ARCH_D=G_ARCH_D, G_P=DRIVE["gate"]["P"]["PASS"],
          G_ING=dict(S=ING_RC["G_ING_S"]["PASS"], V=ING_RC["G_ING_V"]["PASS"], ARCH_D_mac=ING_RC["G_ARCH_D"]["PASS"])), result=OUT, kingform_anchors=KF, TC2=TC2,
          inputs=INPUTS, components_npz_sha256=sha(R + "/receipts/T5_bridge_components.npz"), env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), python=sys.version.split()[0], numpy=np.__version__,
          gpu_before=GPU0, gpu_after=GPU1, pids_before=PID0, pids_after=PID1, load_before=LOAD0, load_after=LOAD1, built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=round(time.time() - t0, 1))
json.dump(RC, open(R + "/receipts/RECEIPT_T5_bridge.json", "w"), indent=1, default=lambda o: (o.tolist() if isinstance(o, np.ndarray) else float(o) if isinstance(o, np.floating) else int(o) if isinstance(o, np.integer) else bool(o) if isinstance(o, np.bool_) else str(o)))
print("GPU", GPU0, "->", GPU1, "| PIDs", PID0.replace("\n", ";"), "->", PID1.replace("\n", ";")); print("DONE_t5_bridge", RC["wall_s"])

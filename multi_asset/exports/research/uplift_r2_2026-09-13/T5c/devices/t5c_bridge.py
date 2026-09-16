#!/usr/bin/env python3
"""t5c_bridge.py — pod2 (nice, Pool <= 16). PREREG_T5c §4-§8; gates G-RAW, G-SIM-R, G-T1c, G-CLOSE (G-X / G-UM from the driver receipt).
King-chain-only bridge from the A0 replay king chain (R_K, KA lineage) to the deployed king chain (D_K = state_H_kc) over 9 construction groups
{T FTRIM, W seat, B fund rank base, V fund values, M members, X exit, S eligibility, P stop layer, H state path} with time-varying D versions
(FTRIM from 09-02 12Z, M1 base from 09-04 04Z, archived w3m incl. 09-05 16Z seeding, 08-30 04Z warm start). Outcomes per anchor: price, carry,
cost, net (bps / 4h / unit gross). Shapley (primary), fixed order, one-at-a-time, leave-one-out; readings SAME-LOSS / DEPLOYMENT-GAP; 09-06
exclusion and KB-lineage sensitivities; side lens and name lists; descriptive deployed book / V2MAIN chain.
Launch: bash devices/launch_pod2.sh t5c_bridge.py
"""
import os, sys, json, time, hashlib, subprocess, math
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE and sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
from scipy.stats import rankdata
R = "/workspace/uplift_r2_2026-09-13/T5c"; T1R = "/workspace/uplift_r2_2026-09-13/T1"; R6 = "/workspace/uplift_2026-09-11/r6/out"
PREREG_SHA = "a669c62782c58d424eed17cf3c7b2a8ad78050c059f43cb2e6496737eaf56a48"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def sh(cmd):
    try: return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as e: return "ERR %s" % e
assert sha(R + "/PREREG_T5c_september_replay_vs_deployed_2026-09-13.md") == PREREG_SHA
GPU0 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID0 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); assert GPU0.replace(" ", "") == "0%,2MiB", GPU0
t0 = time.time(); B = 2000
utc = lambda t: time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
DRV = json.load(open(R + "/receipts/RECEIPT_T5c_drive.json")); assert DRV["gate_G_UM"]["PASS"] and DRV["gate_G_X"]["PASS"], "G-UM / G-X not passed"
ARMS = {tag: DRV["runs"][tag]["out"] for tag in ("KA_s42", "KA_s2027", "KB_s42", "KB_s2027")}
for tag, p in ARMS.items(): assert sha(p) == DRV["runs"][tag]["out_sha256"], tag
INGP = R + "/receipts/T5c_live_ingredients.npz"; INGRC = json.load(open(R + "/receipts/RECEIPT_T5c_live_ingredients.json")); assert sha(INGP) == INGRC["out_sha256"]
MX = R6 + "/meta_newprod_v4_x0910.npz"; PX = R6 + "/wide_panel_4h_v2ext_x0910.npz"; DLW = R6 + "/dlw_v4raw_x0910/data/dlw_targets.npz"; COSTB = "/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
T1D2 = T1R + "/receipts/T1_d2.npz"
INPUTS = {p: sha(p) for p in list(ARMS.values()) + [INGP, MX, PX, DLW, COSTB, T1D2]}
ING = np.load(INGP, allow_pickle=True)
SYM = [str(s) for s in ING["symbols"]]; NW = len(SYM); CAL = [int(x) for x in ING["cal"]]; WIN = [int(x) for x in ING["win"]]; nC = len(CAL)
PM = ING["PM"]; LIVE = ING["LIVE"]; W3M = ING["W3M"]; SEL = ING["SEL"]; FED = ING["FED"]; RN8L = ING["RN8L"]; BIDX = ING["BASE_IDX"]; BASEV = ING["BASEV"]
KC = ING["KC"]; FC = ING["FC"]; WTL = ING["WTL"]; WARM_kc = ING["WARM_kc"]
FTRIM_ON = int(ING["FTRIM_ON"]); M1_ON = int(ING["M1_ON"]); SEED_ON = int(ING["SEED_ON"]); BOOST_SWITCH = 1788249600
kW = [k for k, A in enumerate(CAL) if A in WIN]; assert len(kW) == 61
PXz = np.load(PX, allow_pickle=True); assert [str(s) for s in PXz["symbols"]] == SYM; prow = {int(t): j for j, t in enumerate(PXz["ts"].astype(np.int64))}
FNx = PXz["f_fund_now"].astype(np.float64); IVx = PXz["f_fund_iv"].astype(np.float64); IVfx = np.where(np.isfinite(IVx) & (IVx > 0), IVx, 8.0)
C4 = np.stack([np.nan_to_num(FNx[prow[A]], nan=0.0) * (4.0 / IVfx[prow[A]]) for A in CAL]); RN8 = np.stack([FNx[prow[A]] * (8.0 / IVfx[prow[A]]) for A in CAL])
MXz = np.load(MX, allow_pickle=True); emap = {int(t): i for i, t in enumerate(MXz["E_ts"].astype(np.int64))}
Y4 = np.stack([MXz["y4"][emap[A]].astype(np.float64) for A in CAL]); Y4c = np.nan_to_num(Y4, nan=0.0); QVKx = np.stack([MXz["qvk"][emap[A]].astype(np.float64) for A in CAL])
CB = json.load(open(COSTB)); tiers = CB["tiers"] if isinstance(CB, dict) else CB
COST_B = [(float(t["maker_bps"]), float(t["taker_bps"]), float(t["maker_share"])) if isinstance(t, dict) else (float(t[0]), float(t[1]), float(t[2])) for t in tiers]
QV4H = np.expm1(np.clip(QVKx, 0, 30)) * 48; TIER = np.where(QV4H >= 5e6, 0, np.where(QV4H >= 1e6, 1, 2)); RATES = np.array([fr * mk + (1 - fr) * tk for (mk, tk, fr) in COST_B]); RATE = RATES[TIER]
# ---------------------------------------------------------------- replay dumps
def load_arm(p):
    Z = np.load(p, allow_pickle=True); pre = "d30_n2_c42_T5_"
    d = {k[len(pre):]: Z[k] for k in Z.files if k.startswith(pre)}
    assert [int(x) for x in d["ts"]] == [int(ING["pre"])] + CAL, "dump calendar"
    return d
DUMP = {tag: load_arm(p) for tag, p in ARMS.items()}
# G-RAW: device y4 rows == x0910 meta rows == dlw y4s rows
DL = np.load(DLW, allow_pickle=True); dmap = {int(t): i for i, t in enumerate(DL["E_ts"].astype(np.int64))}; assert [str(s) for s in DL["symbols"]] == SYM
graw = dict(device_eq_meta=True, meta_eq_dlw=True)
for tag, d in DUMP.items():
    for k, A in enumerate(CAL):
        a = d["Y4"][k + 1].astype(np.float64); b = MXz["y4"][emap[A]].astype(np.float64)
        if not (np.array_equal(np.isnan(a), np.isnan(b)) and np.array_equal(a[~np.isnan(a)], b[~np.isnan(b)])): graw["device_eq_meta"] = False
for A in CAL:
    a = MXz["y4"][emap[A]].astype(np.float64); b = DL["y4s"][dmap[A]].astype(np.float64)
    if not (np.array_equal(np.isnan(a), np.isnan(b)) and np.array_equal(a[~np.isnan(a)], b[~np.isnan(b)])): graw["meta_eq_dlw"] = False
G_RAW = dict(graw, PASS=bool(graw["device_eq_meta"] and graw["meta_eq_dlw"])); print("G-RAW", G_RAW, flush=True); assert G_RAW["PASS"]
GROUPS = ["T", "W", "B", "V", "M", "X", "S", "P", "H"]; NG = len(GROUPS); GI = {g: q for q, g in enumerate(GROUPS)}; FULL = (1 << NG) - 1
SMA = 0.1; SBAND = 2.5e-4; FTRIM_TH = float("-0.0010")
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out
def fund_z(k, m, FEv, useB, useV):
    if not useB: return xz(FEv)[m]
    if CAL[k] < M1_ON: return xz(FEv[m])
    bv = BASEV[k]
    if useV:
        okb = np.isfinite(bv); vals = bv[okb]; nidx = BIDX[okb]
    else:
        okb = np.isfinite(bv) & (BIDX >= 0); cand = BIDX[okb]; pv = FEv[cand]; fin = np.isfinite(pv); vals = pv[fin]; nidx = cand[fin]
    out = np.full(len(m), np.nan)
    if len(vals) >= 10:
        rr = rankdata(vals) / max(len(vals) - 1, 1) - 0.5
        posarr = np.full(NW, -1, np.int64); on = nidx >= 0; posarr[nidx[on]] = np.nonzero(on)[0]
        q = posarr[m]; valid = (q >= 0) & np.isfinite(FEv[m]); out[valid] = rr[q[valid]]
    return out
def simulate(tag, bits, legs=False, want=False):
    d = DUMP[tag]; S = set(g for g in GROUPS if bits >> GI[g] & 1); use = lambda g: g in S
    NL = 5
    if use("H"):
        H = WARM_kc.copy(); HL = np.zeros((NL, NW)); HL[4] = H
    else:
        H = d["smk"][0].copy(); HL = np.vstack([d["SMC_out"][0], np.zeros((1, NW))])
    prev = H.copy()
    out = dict(P=np.full(nC, np.nan), C=np.full(nC, np.nan), K=np.full(nC, np.nan)); NP = np.zeros(NW); NCy = np.zeros(NW); skipped = []; books = {}
    for k, A in enumerate(CAL):
        r = k + 1
        M = PM[k] if use("M") else d["mem"][r]; m = np.where(M)[0]
        w3 = W3M[k] if use("W") else d["w3"][r]
        FEv = FED[k] if use("V") else d["FE"][r]
        FZ = fund_z(k, m, FEv, use("B"), use("V"))
        kz = xz(d["SLOW"][r][m]); rz = xz(-d["R24"][r][m]); _fs = 1.0
        z = w3[0]*np.nan_to_num(kz) + w3[1]*np.nan_to_num(rz) + w3[2]*_fs*np.nan_to_num(FZ)
        if legs: ZC = np.stack([w3[0]*np.nan_to_num(kz), w3[1]*np.nan_to_num(rz), w3[2]*_fs*np.nan_to_num(FZ), np.zeros(len(m)), np.zeros(len(m))])
        if use("T"):
            kill = ((z < 0) & np.isfinite(RN8L[k][m]) & (RN8L[k][m] <= FTRIM_TH)) if A >= FTRIM_ON else np.zeros(len(m), bool)
        else:
            FNm = d["FN"][r][m]; IVm = d["IV"][r][m]
            _fnp = FNm * (8.0 / np.where(IVm > 0, IVm, 8.0)); _fnp = np.where(np.isfinite(_fnp), _fnp, 0.0)
            kill = (z < 0) & (_fnp <= FTRIM_TH)
        if legs: ZC = np.where(kill[None, :], 0.0, ZC)
        z = np.where(kill, 0.0, z)
        if use("S"): sel = SEL[k][m]
        else:
            ok = np.isfinite(d["Y4"][r][m]); qv4h = np.expm1(np.clip(d["QVK"][r][m], 0, 30)) * 48; sel = ok & (qv4h >= 2.5e5)
        if sel.sum() < 80: skipped.append((utc(A), "sel<80")); continue
        w = np.where(sel, z, 0.0)
        w[sel] -= w[sel].mean()
        g = np.abs(w).sum()
        if g < 1e-9: skipped.append((utc(A), "g<1e-9")); continue
        w /= g; capw = 2.5 / max(int(sel.sum()), 1)
        if legs:
            WC = np.where(sel[None, :], ZC, 0.0); WC[:, sel] -= WC[:, sel].mean(axis=1, keepdims=True); WC /= g; _wpre = w.copy()
        w = np.clip(w, -capw, capw)
        if legs:
            _rat = np.where(_wpre != 0.0, w / np.where(_wpre != 0.0, _wpre, 1.0), 1.0); WC = WC * _rat[None, :]
        g2 = np.abs(w).sum()
        if g2 > 1e-9: w /= g2
        if legs and g2 > 1e-9: WC /= g2
        tgt = np.zeros(NW); tgt[m] = w
        if legs: TGC = np.zeros((NL, NW)); TGC[:, m] = WC
        if not use("P"):
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
            keep = LIVE & Mmask & selmask; leave = (~keep) & (np.abs(sm) > 1e-12); sm = np.where(leave, 0.0, sm)
            if legs: SMC[:, leave] = 0.0
        else:
            _nonsel = np.zeros(NW, bool); _nonsel[m[~sel]] = True; sm = np.where(_nonsel, 0.0, sm); trade = sm - H
            if legs: SMC[:, _nonsel] = 0.0
        gw = np.abs(sm).sum()
        out["P"][k] = float((sm * Y4c[k]).sum() / gw * 1e4); out["C"][k] = float((sm * C4[k]).sum() / gw * 1e4); out["K"][k] = float((np.abs(sm - prev) * RATE[k]).sum() / gw)
        if A in WIN: NP += sm / gw * Y4c[k] * 1e4; NCy += sm / gw * C4[k] * 1e4
        if want: books[A] = dict(sm=sm.copy(), SMC=(SMC.copy() if legs else None), kill=int(kill.sum()), nsel=int(sel.sum()), nmem=int(len(m)))
        prev = sm; H = sm
        if legs: HL = SMC
    out["N"] = out["P"] - out["C"] - out["K"]
    return out, NP, NCy, skipped, books
def outcomes_of(book_seq, prev0):
    o = dict(P=np.full(nC, np.nan), C=np.full(nC, np.nan), K=np.full(nC, np.nan)); prev = prev0
    for k in range(nC):
        w = book_seq[k]; gw = np.abs(w).sum()
        o["P"][k] = float((w * Y4c[k]).sum() / gw * 1e4); o["C"][k] = float((w * C4[k]).sum() / gw * 1e4); o["K"][k] = float((np.abs(w - prev) * RATE[k]).sum() / gw); prev = w
    o["N"] = o["P"] - o["C"] - o["K"]; return o
# ---------------------------------------------------------------- G-SIM-R (all four runs)
GSIM = {}; RB = {}
for tag, d in DUMP.items():
    o, _, _, skp, bk = simulate(tag, 0, legs=True, want=True); RB[tag] = (o, bk)
    mx_sm = max(float(np.abs(bk[A]["sm"] - d["smk"][k + 1]).max()) for k, A in enumerate(CAL)); mx_leg = max(float(np.abs(bk[A]["SMC"][:4] - d["SMC_out"][k + 1]).max()) for k, A in enumerate(CAL))
    GSIM[tag] = dict(max_abs_sm=mx_sm, max_abs_legs=mx_leg, skipped=skp, PASS=bool(mx_sm <= 1e-12 and mx_leg <= 1e-12 and not skp))
G_SIM_R = dict(per_run=GSIM, PASS=all(v["PASS"] for v in GSIM.values())); print("G-SIM-R", json.dumps(G_SIM_R), flush=True); assert G_SIM_R["PASS"]
# ---------------------------------------------------------------- deployed books (archived) and G-T1c
kc_prev0 = KC[0] * 0 + WARM_kc   # entering state of the kc chain at 08-30 04Z
DK = outcomes_of([KC[k] for k in range(nC)], WARM_kc)
DB = outcomes_of([WTL[k] for k in range(nC)], 0.55 * WARM_kc + 0.45 * ING["WARM_fc"])
DF = outcomes_of([FC[k] for k in range(nC)], ING["WARM_fc"])
DZ = np.load(T1D2, allow_pickle=True); DCc = [str(c) for c in DZ["cols"]]; t1rows = {int(rw[DCc.index("A")]): (float(rw[DCc.index("price")]), float(rw[DCc.index("carry")])) for rw in DZ["D"]}
gt = dict(n=0, max_abs_price=0.0, max_abs_carry=0.0)
for k, A in enumerate(CAL):
    if A in WIN and A in t1rows:
        gt["n"] += 1; gt["max_abs_price"] = max(gt["max_abs_price"], abs(DB["P"][k] - t1rows[A][0])); gt["max_abs_carry"] = max(gt["max_abs_carry"], abs(DB["C"][k] - t1rows[A][1]))
wWin = WTL[kW] / np.abs(WTL[kW]).sum(1, keepdims=True); Lshort = np.where(wWin < 0, wWin * Y4c[kW] * 1e4, 0.0)
gt["T5_short_price_per_anchor"] = float(Lshort.sum() / len(kW)); gt["T5_value"] = -4.5274112840994265
G_T1c = dict(gt, PASS=bool(gt["n"] == 61 and gt["max_abs_price"] <= 1e-9 and gt["max_abs_carry"] <= 1e-9 and abs(gt["T5_short_price_per_anchor"] - gt["T5_value"]) <= 1e-9))
print("G-T1c", json.dumps(G_T1c), flush=True); assert G_T1c["PASS"], "G-T1c failed: reconcile first"
# ---------------------------------------------------------------- nodes
from multiprocessing import Pool
def task(args):
    tag, bits = args; o, NP, NCy, skp, _ = simulate(tag, bits); return tag, bits, o, NP, NCy, len(skp)
OUTC = ("P", "C", "K", "N")
V = {tag: {q: np.full((1 << NG, nC), np.nan) for q in OUTC} for tag in ("KA_s42", "KA_s2027")}; NSP = {tag: np.zeros((1 << NG, NW)) for tag in V}; NSC = {tag: np.zeros((1 << NG, NW)) for tag in V}; SK = {tag: 0 for tag in V}
with Pool(16) as pool:
    for tag, bits, o, NP, NCy, nsk in pool.imap_unordered(task, [(t, b) for t in V for b in range(1 << NG)], chunksize=4):
        for q in OUTC: V[tag][q][bits] = o[q]
        NSP[tag][bits] = NP; NSC[tag][bits] = NCy; SK[tag] += nsk
print("nodes done", round(time.time() - t0, 1), flush=True)
days = np.array([CAL[k] // 86400 for k in kW]); popc = np.array([bin(b).count("1") for b in range(1 << NG)])
coef = [math.factorial(q) * math.factorial(NG - q - 1) / math.factorial(NG) for q in range(NG)]
def boot(num, den, k, sel=None):
    dd = days if sel is None else days[sel]; nu = num if sel is None else num[sel]; de = den if sel is None else den[sel]
    u, inv = np.unique(dd, return_inverse=True); nd = len(u)
    sn = np.bincount(inv, weights=nu, minlength=nd); sdn = np.bincount(inv, weights=de, minlength=nd)
    rng = np.random.default_rng([20260905, k]); dr = rng.integers(0, nd, size=(B, nd)); rep = sn[dr].sum(1) / sdn[dr].sum(1)
    return [float(sn.sum() / sdn.sum()), float(np.percentile(rep, 2.5)), float(np.percentile(rep, 97.5))]
one = np.ones(len(kW)); no0906 = np.array([time.strftime("%m-%d", time.gmtime(CAL[k])) != "09-06" for k in kW])
def readings(dk, rk, sel=None):
    mean_dk = boot(dk, one, 81, sel); mean_rk = boot(rk, one, 81, sel); diff = boot(dk - rk, one, 87, sel)
    same = bool(mean_dk[1] <= mean_rk[0] <= mean_dk[2]); gap = bool(diff[1] > 0 or diff[2] < 0)
    label = {(True, False): "STRATEGY'S OWN LOSS (king chain)", (False, True): "DEPLOYMENT DIFFERENCE", (True, True): "SAME DIRECTION WITH A GAP", (False, False): "UNDECIDABLE"}[(same, gap)]

    # ⚠ 更正 DEV-05 · P2 · AUD-KB K4 2026-09-16(原句字节保留, 不改写): T5c 装置保留原样(存档); 引用其标签时改引 FX-EVAL K2 重标(R-LOSS, δ D1 = 0.05): 价格与净额 = **SHARED LOSS, DIFFERENCE INCONCLUSIVE**, carry = INCONCLUSIVE(RELABEL_TABLE_K2 T5c 行); 新装置复用 R-LOSS, 不复用本谓词

    return dict(D_K=mean_dk, R_K=mean_rk, diff_D_minus_R=diff, SAME_LOSS=same, DEPLOYMENT_GAP=gap, label=label, replay_lost_point=bool(mean_rk[0] < 0))
RES = dict(groups=GROUPS, order=["T", "B", "W", "V", "M", "S", "X", "P", "H"], window=[utc(CAL[kW[0]]), utc(CAL[kW[-1]])], n_window=len(kW), n_days=int(len(np.unique(days))), seeds={})
NPZ = {}
for tag in ("KA_s42", "KA_s2027"):
    oR = RB[tag][0]; rs = {}
    rs["readings"] = {q: readings(DK[q][kW], oR[q][kW]) for q in OUTC}
    rs["readings_excl_0906"] = {q: readings(DK[q][kW], oR[q][kW], no0906) for q in OUTC}
    rs["levels"] = {name: {q: boot(src[q][kW], one, 81) for q in OUTC} for name, src in (("D_K", DK), ("R_K", oR), ("D_B", DB), ("D_F", DF))}
    rs["D_B_vs_D_K_price"] = dict(corr=float(np.corrcoef(DB["P"][kW], DK["P"][kW])[0, 1]), mean_diff=boot(DB["P"][kW] - DK["P"][kW], one, 81))
    sh_all = {}
    for q, kboot in (("P", 82), ("C", 83), ("N", 84), ("K", 85)):
        Vq = V[tag][q][:, kW]; DEL = DK[q][kW] - Vq[0]; REM = DK[q][kW] - Vq[FULL]
        phi = {}
        for g in GROUPS:
            gi = GI[g]; acc = np.zeros(len(kW))
            for b in range(1 << NG):
                if b >> gi & 1: continue
                acc += coef[popc[b]] * (Vq[b | (1 << gi)] - Vq[b])
            phi[g] = acc
        close = float(np.abs(DEL - (sum(phi.values()) + REM)).max())
        seq = {}; pref = 0
        for g in RES["order"]:
            nb = pref | (1 << GI[g]); seq[g] = Vq[nb] - Vq[pref]; pref = nb
        close_seq = float(np.abs(DEL - (sum(seq.values()) + REM)).max())
        periods = dict(T=FTRIM_ON, B=M1_ON, W=SEED_ON)
        per = {}
        for g in GROUPS:
            if g in periods:
                pre_ = np.array([CAL[k] < periods[g] for k in kW]); per[g] = dict(before=float(phi[g][pre_].mean()) if pre_.any() else None, after=float(phi[g][~pre_].mean()) if (~pre_).any() else None)
        preB = np.array([CAL[k] < BOOST_SWITCH for k in kW]); per["REM"] = dict(before=float(REM[preB].mean()), after=float(REM[~preB].mean()))
        sh_all[q] = dict(delta=boot(DEL, one, kboot), share={("phi_" + g): boot(phi[g], DEL, kboot) for g in GROUPS} | {"REM": boot(REM, DEL, kboot)},
                         mean={("phi_" + g): boot(phi[g], one, kboot) for g in GROUPS} | {"REM": boot(REM, one, kboot)},
                         sequential={g: float(seq[g].mean()) for g in RES["order"]}, sequential_share={g: boot(seq[g], DEL, 86) for g in RES["order"]},
                         one_at_a_time={g: float((Vq[1 << GI[g]] - Vq[0]).mean()) for g in GROUPS}, leave_one_out={g: float((Vq[FULL] - Vq[FULL ^ (1 << GI[g])]).mean()) for g in GROUPS},
                         closure_maxabs=close, closure_seq_maxabs=close_seq, periods=per,
                         excl_0906=dict(delta=boot(DEL, one, kboot, no0906), share={("phi_" + g): boot(phi[g], DEL, kboot, no0906) for g in GROUPS} | {"REM": boot(REM, DEL, kboot, no0906)}))
        NPZ.update({f"{tag}_{q}_V": V[tag][q], f"{tag}_{q}_DEL": DEL, f"{tag}_{q}_REM": REM, **{f"{tag}_{q}_phi_{g}": phi[g] for g in GROUPS}})
        if q == "P":
            phin = {}
            for g in GROUPS:
                gi = GI[g]; acc = np.zeros(NW)
                for b in range(1 << NG):
                    if b >> gi & 1: continue
                    acc += coef[popc[b]] * (NSP[tag][b | (1 << gi)] - NSP[tag][b])
                phin[g] = acc / len(kW)
            wD = KC[kW] / np.abs(KC[kW]).sum(1, keepdims=True); wR = np.stack([RB[tag][1][CAL[k]]["sm"] / np.abs(RB[tag][1][CAL[k]]["sm"]).sum() for k in kW])
            rn8m = np.array([np.nanmean(RN8[kW][:, n]) if np.isfinite(RN8[kW][:, n]).any() else np.nan for n in range(NW)])
            row = lambda n, g: dict(symbol=SYM[n], phi=float(phin[g][n]), wD=float(wD[:, n].mean()), wR=float(wR[:, n].mean()), rn8_bp=(float(rn8m[n] * 1e4) if np.isfinite(rn8m[n]) else None))
            sh_all[q]["names"] = {g: dict(top_pos=[row(n, g) for n in np.argsort(-phin[g])[:12]], top_neg=[row(n, g) for n in np.argsort(phin[g])[:12]], check=float(phin[g].sum() - phi[g].mean())) for g in GROUPS}
            gap_name = (NSP[tag][0] * 0 + (wD * Y4c[kW] * 1e4).sum(0) / len(kW)) - NSP[tag][0] / len(kW)
            sh_all[q]["names_total_gap"] = [dict(symbol=SYM[n], gap=float(gap_name[n]), wD=float(wD[:, n].mean()), wR=float(wR[:, n].mean())) for n in np.argsort(gap_name)[:15]]
            LsD = np.where(wD < 0, wD * Y4c[kW] * 1e4, 0.0).sum(0); LsR = np.where(wR < 0, wR * Y4c[kW] * 1e4, 0.0).sum(0)
            sh_all[q]["short_losers_D_K"] = [dict(symbol=SYM[n], D_short_sum=float(LsD[n]), R_short_sum=float(LsR[n]), wD=float(wD[:, n].mean()), wR=float(wR[:, n].mean()), rn8_bp=(float(rn8m[n] * 1e4) if np.isfinite(rn8m[n]) else None)) for n in np.argsort(LsD)[:15]]
            side = {}
            for nm_, ww in (("D_K", wD), ("R_K", wR)):
                pl = (np.where(ww > 0, ww, 0) * Y4c[kW]).sum(1) * 1e4; ps = (np.where(ww < 0, ww, 0) * Y4c[kW]).sum(1) * 1e4
                side[nm_] = dict(long=boot(pl, one, 88), short=boot(ps, one, 88), gross_short=float(np.abs(np.where(ww < 0, ww, 0)).sum(1).mean()))
            side["diff_short"] = boot((np.where(wD < 0, wD, 0) * Y4c[kW]).sum(1) * 1e4 - (np.where(wR < 0, wR, 0) * Y4c[kW]).sum(1) * 1e4, one, 88)
            side["diff_long"] = boot((np.where(wD > 0, wD, 0) * Y4c[kW]).sum(1) * 1e4 - (np.where(wR > 0, wR, 0) * Y4c[kW]).sum(1) * 1e4, one, 88)
            sh_all[q]["side_lens"] = side
            sh_all[q]["R_ftrim_kills_mean"] = float(np.mean([RB[tag][1][CAL[k]]["kill"] for k in kW])); sh_all[q]["R_nsel_mean"] = float(np.mean([RB[tag][1][CAL[k]]["nsel"] for k in kW]))
            sh_all[q]["R_stop_blocks"] = dict(names_blocked_mean=float(np.mean([DUMP[tag]["bl"][k + 1].sum() for k in kW])), new_fires_in_window=int(sum(((DUMP[tag]["bl"][k + 1]) & ~(DUMP[tag]["bl"][k])).sum() for k in kW)))
    rs["bridge"] = sh_all; rs["node_skips"] = SK[tag]
    RES["seeds"][tag] = rs
    print(tag, "done", round(time.time() - t0, 1), flush=True)
# KB lineage sensitivity (readings only)
RES["KB"] = {tag: dict(readings={q: readings(DK[q][kW], RB[tag][0][q][kW]) for q in OUTC}, readings_excl_0906={q: readings(DK[q][kW], RB[tag][0][q][kW], no0906) for q in OUTC},
                       R_K_levels={q: boot(RB[tag][0][q][kW], one, 81) for q in OUTC}) for tag in ("KB_s42", "KB_s2027")}
cl = {tag: {q: dict(shapley=RES["seeds"][tag]["bridge"][q]["closure_maxabs"], sequential=RES["seeds"][tag]["bridge"][q]["closure_seq_maxabs"]) for q in OUTC} for tag in ("KA_s42", "KA_s2027")}
G_CLOSE = dict(per_seed=cl, PASS=all(max(v2["shapley"], v2["sequential"]) <= 1e-6 for v in cl.values() for v2 in v.values()))
print("G-CLOSE", json.dumps(G_CLOSE), flush=True)
np.savez_compressed(R + "/receipts/T5c_bridge_components.npz", CAL=np.array(CAL), WIN=np.array(WIN), **{f"DK_{q}": DK[q] for q in OUTC}, **{f"DB_{q}": DB[q] for q in OUTC}, **{f"DF_{q}": DF[q] for q in OUTC}, **NPZ)
GPU1 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID1 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2")
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, gates=dict(G_UM=DRV["gate_G_UM"]["PASS"], G_X=DRV["gate_G_X"]["PASS"], G_RAW=G_RAW, G_SIM_R=G_SIM_R, G_T1c=G_T1c, G_CLOSE=G_CLOSE,
          G_ING=dict(S=INGRC["G_ING_S"]["PASS"], V=INGRC["G_ING_V"]["PASS"], B=INGRC["G_ING_B"]["PASS"], B_mismatch=INGRC["G_ING_B"]["ii_mismatch"], T=INGRC["G_ING_T"]["PASS"], ARCH_D=INGRC["G_ARCH_D"]["PASS"])),
          result=RES, inputs=INPUTS, components_npz_sha256=sha(R + "/receipts/T5c_bridge_components.npz"), env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}),
          python=sys.version.split()[0], numpy=np.__version__, gpu_before=GPU0, gpu_after=GPU1, pids_before=PID0, pids_after=PID1, built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=round(time.time() - t0, 1))
json.dump(RC, open(R + "/receipts/RECEIPT_T5c_bridge.json", "w"), indent=1, default=lambda o: (o.tolist() if isinstance(o, np.ndarray) else float(o) if isinstance(o, np.floating) else int(o) if isinstance(o, np.integer) else bool(o) if isinstance(o, np.bool_) else str(o)))
print("DONE_t5c_bridge", RC["wall_s"])

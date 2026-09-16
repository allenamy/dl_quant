#!/usr/bin/env python3
"""t5d_bridge.py — pod2 (nice, Pool <= 16). PREREG_T5d §4-§8; gates G-PRED, G-RAW, G-SIM-R, G-ARCH-D, G-T1c, G-FIXW, G-T5C, G-CLOSE.
King-chain simulator and bridge of T5c (t5c_bridge.py logic, carry matrix made an explicit argument). Three calibers:
  T5c  = T5c arms (x0910 intervals) priced with the x0910 carry vector (must reproduce the T5c receipt),
  FIX  = the same T5c weights priced with the corrected carry vector (price and cost must be identical to T5c),
  REG  = T5d arms (corrected panel, FTRIM / fund EMA / state / W regenerated) priced with the corrected carry vector.
Reports Δ_fixed = FIX − T5c, Δ_regen = REG − T5c and the weight-regeneration effect REG − FIX (k=89); readings with the corrected label predicate
(both books must actually lose), economic equivalence band 0.25 bps/anchor and exclusion statements; the full T5c bridge on REG.
Run 2 (13:0xZ): run 1 omitted part of the T5c bridge's pre-registered descriptive outputs (per-name Shapley, names_total_gap, rn8 in the short-loser list,
gross short share, replay diagnostics, levels incl. D_F, sequential shares, closure per outcome, 09-06 shares). Run 2 adds them as NEW fields only;
every run-1 field must be unchanged (checked on the Mac against receipts/pod2/run1_bridge_incomplete/RECEIPT_T5d_bridge.json).
Launch: bash devices/launch_pod2.sh t5d_bridge.py
"""
import os, sys, json, time, hashlib, subprocess, math
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE and sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
from scipy.stats import rankdata
R = "/workspace/uplift_r2_2026-09-13/T5d"; T5C = "/workspace/uplift_r2_2026-09-13/T5c"; T1R = "/workspace/uplift_r2_2026-09-13/T1"; R6 = "/workspace/uplift_2026-09-11/r6/out"
PREREG_SHA = "a1ef16cdba5e95def27f77b180cba3f1ac954ad04c7b0a17f59c24e1a0c85a4f"; DELTA_EQ = 0.25
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def sh(cmd):
    try: return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as e: return "ERR %s" % e
assert sha(R + "/PREREG_T5d_iv_corrected_replay_2026-09-13.md") == PREREG_SHA
GPU0 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID0 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); assert GPU0.replace(" ", "") == "0%,2MiB", GPU0
t0 = time.time(); B = 2000
utc = lambda t: time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
DRV = json.load(open(R + "/receipts/RECEIPT_T5d_drive.json")); assert DRV["gate_G_Xprime"]["PASS"]
PRC = json.load(open(R + "/receipts/RECEIPT_T5d_ivfix_panel.json")); PXC = PRC["out"]; assert sha(PXC) == PRC["out_sha256"]
T5CD = json.load(open(T5C + "/receipts/RECEIPT_T5c_drive.json")); T5CB = json.load(open(T5C + "/receipts/RECEIPT_T5c_bridge.json"))
TAGS = ("KA_s42", "KA_s2027", "KB_s42", "KB_s2027")
ARM_D = {t: DRV["runs"][t]["out"] for t in TAGS}; ARM_C = {t: T5CD["runs"][t]["out"] for t in TAGS}
for t in TAGS: assert sha(ARM_D[t]) == DRV["runs"][t]["out_sha256"] and sha(ARM_C[t]) == T5CD["runs"][t]["out_sha256"], t
INGP = T5C + "/receipts/T5c_live_ingredients.npz"; assert sha(INGP) == json.load(open(T5C + "/receipts/RECEIPT_T5c_live_ingredients.json"))["out_sha256"]
MX = R6 + "/meta_newprod_v4_x0910.npz"; PXX = R6 + "/wide_panel_4h_v2ext_x0910.npz"; DLW = R6 + "/dlw_v4raw_x0910/data/dlw_targets.npz"; COSTB = "/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"; T1D2 = T1R + "/receipts/T1_d2.npz"
INPUTS = {p: sha(p) for p in list(ARM_D.values()) + list(ARM_C.values()) + [INGP, MX, PXX, PXC, DLW, COSTB, T1D2]}
ING = np.load(INGP, allow_pickle=True)
SYM = [str(s) for s in ING["symbols"]]; NW = len(SYM); CAL = [int(x) for x in ING["cal"]]; WIN = [int(x) for x in ING["win"]]; nC = len(CAL)
PM = ING["PM"]; LIVE = ING["LIVE"]; W3M = ING["W3M"]; SEL = ING["SEL"]; FED = ING["FED"]; RN8L = ING["RN8L"]; BIDX = ING["BASE_IDX"]; BASEV = ING["BASEV"]
KC = ING["KC"]; FC = ING["FC"]; WTL = ING["WTL"]; WARM_kc = ING["WARM_kc"]
FTRIM_ON = int(ING["FTRIM_ON"]); M1_ON = int(ING["M1_ON"]); SEED_ON = int(ING["SEED_ON"]); BOOST_SWITCH = 1788249600
kW = [k for k, A in enumerate(CAL) if A in WIN]; assert len(kW) == 61
def carry_rows(path):
    P = np.load(path, allow_pickle=True); assert [str(s) for s in P["symbols"]] == SYM; prow = {int(t): j for j, t in enumerate(P["ts"].astype(np.int64))}
    FN = P["f_fund_now"].astype(np.float64); IV = P["f_fund_iv"].astype(np.float64); IVf = np.where(np.isfinite(IV) & (IV > 0), IV, 8.0)
    return np.stack([np.nan_to_num(FN[prow[A]], nan=0.0) * (4.0 / IVf[prow[A]]) for A in CAL]), np.stack([FN[prow[A]] * (8.0 / IVf[prow[A]]) for A in CAL])
C4X, RN8X = carry_rows(PXX); C4C, RN8C = carry_rows(PXC)
MXz = np.load(MX, allow_pickle=True); emap = {int(t): i for i, t in enumerate(MXz["E_ts"].astype(np.int64))}
Y4c = np.nan_to_num(np.stack([MXz["y4"][emap[A]].astype(np.float64) for A in CAL]), nan=0.0); QVKx = np.stack([MXz["qvk"][emap[A]].astype(np.float64) for A in CAL])
CB = json.load(open(COSTB)); tiers = CB["tiers"] if isinstance(CB, dict) else CB
COST_B = [(float(t["maker_bps"]), float(t["taker_bps"]), float(t["maker_share"])) if isinstance(t, dict) else (float(t[0]), float(t[1]), float(t[2])) for t in tiers]
QV4H = np.expm1(np.clip(QVKx, 0, 30)) * 48; TIER = np.where(QV4H >= 5e6, 0, np.where(QV4H >= 1e6, 1, 2)); RATES = np.array([fr * mk + (1 - fr) * tk for (mk, tk, fr) in COST_B]); RATE = RATES[TIER]
days = np.array([CAL[k] // 86400 for k in kW]); one = np.ones(len(kW)); no0906 = np.array([time.strftime("%m-%d", time.gmtime(CAL[k])) != "09-06" for k in kW])
def boot(num, den, k, sel=None, dd=None):
    dd = days if dd is None else dd
    if sel is not None: dd, num, den = dd[sel], num[sel], den[sel]
    u, inv = np.unique(dd, return_inverse=True); nd = len(u)
    sn = np.bincount(inv, weights=num, minlength=nd); sdn = np.bincount(inv, weights=den, minlength=nd)
    rng = np.random.default_rng([20260905, k]); dr = rng.integers(0, nd, size=(B, nd)); rep = sn[dr].sum(1) / sdn[dr].sum(1)
    return [float(sn.sum() / sdn.sum()), float(np.percentile(rep, 2.5)), float(np.percentile(rep, 97.5))]
# ---------------------------------------------------------------- corrected label predicate (PREREG_T5d §6.1) and G-PRED
def readings(dk, rk, kind, sel=None, dd=None):
    mean_dk = boot(dk, np.ones(len(dk)), 81, sel, dd); mean_rk = boot(rk, np.ones(len(rk)), 81, sel, dd); diff = boot(dk - rk, np.ones(len(dk)), 87, sel, dd)
    same = bool(mean_dk[1] <= mean_rk[0] <= mean_dk[2]); gap = bool(diff[1] > 0 or diff[2] < 0); equiv = bool(-DELTA_EQ <= diff[1] and diff[2] <= DELTA_EQ)
    if kind == "return":
        loss_d = bool(mean_dk[0] < 0); loss_r = bool(mean_rk[0] < 0)
        if loss_d and loss_r:
            label = "BOTH LOST, DEPLOYMENT GAP" if gap else ("STRATEGY'S OWN LOSS (king chain, target layer)" if same else "BOTH LOST, UNDECIDABLE")

            # ⚠ 更正 DEV-06 · P2 · AUD-KB K4 2026-09-16(原句字节保留, 不改写): 引用 T5d 标签时改引 FX-EVAL K2 重标(R-LOSS, δ D1 = 0.05; RELABEL_TABLE_K2 T5d 行: 价格/净额 SHARED LOSS, DIFFERENCE INCONCLUSIVE); PREREG §6.2 的 δ = 0.25 只能写作「A0 全周期净额约 40% 的量级线(≈10.95% NAV/年 @2×)」, 不得称「经济上可忽略」

        else:
            label = "NOT A SHARED LOSS (%s lost; %s)" % ({(True, False): "deployed only", (False, True): "replay only", (False, False): "neither"}[(loss_d, loss_r)], "gap" if gap else "no gap")
    else:
        loss_d = loss_r = None; label = "DEPLOYMENT GAP" if gap else ("SAME LEVEL" if same else "UNDECIDABLE")
    excl = ("detected" if gap else ("economically negligible: excluded beyond ±%.2f" % DELTA_EQ if equiv else "not detected, not excluded: differences below %+.2f or above %+.2f are excluded (95%%, descriptive)" % (diff[1], diff[2])))
    return dict(D_K=mean_dk, R_K=mean_rk, diff_D_minus_R=diff, LOSS_D=loss_d, LOSS_R=loss_r, SAME=same, GAP=gap, EQUIV=equiv, label=label, difference_reading=excl)
rs_ = np.random.default_rng(7); base = rs_.uniform(0, 1, len(kW))
syn = dict(a=readings(10 + 10 * base, 10 + 10 * base, "return"), b=readings(-10 - 10 * base, -10 - 10 * base, "return"), c=readings(-10 - 10 * base, 10 + 10 * base, "return"),
           d=readings(-15 - 10 * base, -10 - 10 * base, "return"))
G_PRED = dict(a=syn["a"]["label"], b=syn["b"]["label"], c=syn["c"]["label"] + " GAP=%s" % syn["c"]["GAP"], d=syn["d"]["label"])
G_PRED["PASS"] = bool(syn["a"]["label"].startswith("NOT A SHARED LOSS") and syn["b"]["label"].startswith("STRATEGY'S OWN LOSS") and syn["c"]["label"].startswith("NOT A SHARED LOSS") and syn["c"]["GAP"] and syn["d"]["label"] == "BOTH LOST, DEPLOYMENT GAP")
print("G-PRED", json.dumps(G_PRED), flush=True); assert G_PRED["PASS"], "G-PRED failed: stop"
# ---------------------------------------------------------------- replay dumps
def load_arm(p):
    Z = np.load(p, allow_pickle=True); pre = "d30_n2_c42_T5_"
    d = {k[len(pre):]: Z[k] for k in Z.files if k.startswith(pre)}
    assert [int(x) for x in d["ts"]] == [int(ING["pre"])] + CAL, "dump calendar"
    return d
DUMP = {("REG", t): load_arm(ARM_D[t]) for t in TAGS}; DUMP.update({("T5C", t): load_arm(ARM_C[t]) for t in TAGS})
DL = np.load(DLW, allow_pickle=True); dmap = {int(t): i for i, t in enumerate(DL["E_ts"].astype(np.int64))}
graw = True
for key, d in DUMP.items():
    for k, A in enumerate(CAL):
        a = d["Y4"][k + 1].astype(np.float64); b = MXz["y4"][emap[A]].astype(np.float64); c = DL["y4s"][dmap[A]].astype(np.float64)
        if not (np.array_equal(np.isnan(a), np.isnan(b)) and np.array_equal(a[~np.isnan(a)], b[~np.isnan(b)]) and np.array_equal(np.isnan(b), np.isnan(c)) and np.array_equal(b[~np.isnan(b)], c[~np.isnan(c)])): graw = False
G_RAW = dict(PASS=graw); assert graw
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
def simulate(key, bits, C4v, legs=False, want=False):
    d = DUMP[key]; S = set(g for g in GROUPS if bits >> GI[g] & 1); use = lambda g: g in S
    NL = 5
    if use("H"):
        H = WARM_kc.copy(); HL = np.zeros((NL, NW)); HL[4] = H
    else:
        H = d["smk"][0].copy(); HL = np.vstack([d["SMC_out"][0], np.zeros((1, NW))])
    prev = H.copy()
    out = dict(P=np.full(nC, np.nan), C=np.full(nC, np.nan), K=np.full(nC, np.nan)); NP = np.zeros(NW); skipped = []; books = {}
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
        out["P"][k] = float((sm * Y4c[k]).sum() / gw * 1e4); out["C"][k] = float((sm * C4v[k]).sum() / gw * 1e4); out["K"][k] = float((np.abs(sm - prev) * RATE[k]).sum() / gw)
        if A in WIN: NP += sm / gw * Y4c[k] * 1e4
        if want: books[A] = dict(sm=sm.copy(), SMC=(SMC.copy() if legs else None), kill_idx=m[kill].copy(), nsel=int(sel.sum()))
        prev = sm; H = sm
        if legs: HL = SMC
    out["N"] = out["P"] - out["C"] - out["K"]
    return out, NP, skipped, books
def outcomes_of(seq, prev0, C4v):
    o = dict(P=np.full(nC, np.nan), C=np.full(nC, np.nan), K=np.full(nC, np.nan)); prev = prev0
    for k in range(nC):
        w = seq[k]; gw = np.abs(w).sum()
        o["P"][k] = float((w * Y4c[k]).sum() / gw * 1e4); o["C"][k] = float((w * C4v[k]).sum() / gw * 1e4); o["K"][k] = float((np.abs(w - prev) * RATE[k]).sum() / gw); prev = w
    o["N"] = o["P"] - o["C"] - o["K"]; return o
OUTC = ("P", "C", "K", "N"); KIND = dict(P="return", N="return", C="cost", K="cost")
# ---------------------------------------------------------------- G-SIM-R on the regenerated arms; all-R books of both calibers
GSIM = {}; RB = {}
for key, d in DUMP.items():
    C4v = C4C if key[0] == "REG" else C4X
    o, _, skp, bk = simulate(key, 0, C4v, legs=True, want=True); RB[key] = (o, bk)
    if key[0] == "REG":
        mx_sm = max(float(np.abs(bk[A]["sm"] - d["smk"][k + 1]).max()) for k, A in enumerate(CAL)); mx_leg = max(float(np.abs(bk[A]["SMC"][:4] - d["SMC_out"][k + 1]).max()) for k, A in enumerate(CAL))
        GSIM[key[1]] = dict(max_abs_sm=mx_sm, max_abs_legs=mx_leg, skipped=skp, PASS=bool(mx_sm <= 1e-12 and mx_leg <= 1e-12 and not skp))
G_SIM_R = dict(per_run=GSIM, PASS=all(v["PASS"] for v in GSIM.values())); print("G-SIM-R", json.dumps(G_SIM_R), flush=True); assert G_SIM_R["PASS"]
DK = {cal: outcomes_of([KC[k] for k in range(nC)], WARM_kc, c4) for cal, c4 in (("T5C", C4X), ("FIX", C4C))}
DB = {cal: outcomes_of([WTL[k] for k in range(nC)], 0.55 * WARM_kc + 0.45 * ING["WARM_fc"], c4) for cal, c4 in (("T5C", C4X), ("FIX", C4C))}
DF = {cal: outcomes_of([FC[k] for k in range(nC)], ING["WARM_fc"], c4) for cal, c4 in (("T5C", C4X), ("FIX", C4C))}
DZ = np.load(T1D2, allow_pickle=True); DCc = [str(c) for c in DZ["cols"]]; t1rows = {int(rw[DCc.index("A")]): (float(rw[DCc.index("price")]), float(rw[DCc.index("carry")])) for rw in DZ["D"]}
gt = dict(n=0, max_abs_price=0.0, max_abs_carry=0.0)
for k, A in enumerate(CAL):
    if A in WIN and A in t1rows:
        gt["n"] += 1; gt["max_abs_price"] = max(gt["max_abs_price"], abs(DB["T5C"]["P"][k] - t1rows[A][0])); gt["max_abs_carry"] = max(gt["max_abs_carry"], abs(DB["T5C"]["C"][k] - t1rows[A][1]))
wWin = WTL[kW] / np.abs(WTL[kW]).sum(1, keepdims=True); gt["T5_short_price_per_anchor"] = float(np.where(wWin < 0, wWin * Y4c[kW] * 1e4, 0.0).sum() / len(kW))
G_T1c = dict(gt, PASS=bool(gt["n"] == 61 and gt["max_abs_price"] <= 1e-9 and gt["max_abs_carry"] <= 1e-9 and abs(gt["T5_short_price_per_anchor"] + 4.5274112840994265) <= 1e-9))
G_ARCH_D = dict(max_abs=max(float(np.abs(WTL[k] - (0.55 * KC[k] + 0.45 * FC[k])).max()) for k in range(nC))); G_ARCH_D["PASS"] = bool(G_ARCH_D["max_abs"] <= 1e-9)
print("G-T1c", json.dumps(G_T1c), "G-ARCH-D", G_ARCH_D, flush=True); assert G_T1c["PASS"] and G_ARCH_D["PASS"]
# G-FIXW and G-T5C
FIXR = {}; gfix = True; gt5c = {}
for t in TAGS:
    oC = RB[("T5C", t)][0]; bk = RB[("T5C", t)][1]
    oF = outcomes_of([bk[A]["sm"] for A in CAL], DUMP[("T5C", t)]["smk"][0], C4C); FIXR[t] = oF
    if not (np.array_equal(oF["P"], oC["P"]) and np.array_equal(oF["K"], oC["K"])): gfix = False
    oC2 = outcomes_of([bk[A]["sm"] for A in CAL], DUMP[("T5C", t)]["smk"][0], C4X)
    if not all(np.array_equal(oC2[q], oC[q]) for q in OUTC): gfix = False
if not (np.array_equal(DK["FIX"]["P"], DK["T5C"]["P"]) and np.array_equal(DK["FIX"]["K"], DK["T5C"]["K"])): gfix = False
G_FIXW = dict(PASS=gfix); assert gfix, "G-FIXW failed"
def old_readings(dk, rk, sel=None):
    mean_dk = boot(dk, one, 81, sel); mean_rk = boot(rk, one, 81, sel); diff = boot(dk - rk, one, 87, sel); return mean_dk, mean_rk, diff
for t in ("KA_s42", "KA_s2027"):
    for q in OUTC:
        mdk, mrk, dif = old_readings(DK["T5C"][q][kW], RB[("T5C", t)][0][q][kW]); ref = T5CB["result"]["seeds"][t]["readings"][q]
        gt5c[t + "_" + q] = max(max(abs(a - b) for a, b in zip(mdk, ref["D_K"])), max(abs(a - b) for a, b in zip(mrk, ref["R_K"])), max(abs(a - b) for a, b in zip(dif, ref["diff_D_minus_R"])))
for t in ("KB_s42", "KB_s2027"):
    for q in ("P", "C", "N"):
        _, mrk, dif = old_readings(DK["T5C"][q][kW], RB[("T5C", t)][0][q][kW]); ref = T5CB["result"]["KB"][t]["readings"][q]
        gt5c[t + "_" + q] = max(max(abs(a - b) for a, b in zip(mrk, ref["R_K"])), max(abs(a - b) for a, b in zip(dif, ref["diff_D_minus_R"])))
G_T5C = dict(max_abs=max(gt5c.values()), per_cell=gt5c); G_T5C["PASS"] = bool(G_T5C["max_abs"] <= 1e-9)
print("G-FIXW", G_FIXW, "G-T5C", G_T5C["max_abs"], G_T5C["PASS"], flush=True); assert G_T5C["PASS"], "G-T5C failed: reconcile first"
# ---------------------------------------------------------------- the two deltas and readings under the three calibers
DELTAS = {}; READ = {}
for t in TAGS:
    oC = RB[("T5C", t)][0]; oF = FIXR[t]; oR = RB[("REG", t)][0]; dt = {}
    for q in OUTC:
        dt[q] = dict(T5c=boot(oC[q][kW], one, 89), FIX=boot(oF[q][kW], one, 89), REG=boot(oR[q][kW], one, 89),
                     delta_fixed=boot(oF[q][kW] - oC[q][kW], one, 89), delta_regen=boot(oR[q][kW] - oC[q][kW], one, 89), weight_effect=boot(oR[q][kW] - oF[q][kW], one, 89),
                     delta_regen_excl_0906=boot(oR[q][kW] - oC[q][kW], one, 89, no0906))
    DELTAS[t] = dt
    READ[t] = {cal: {q: readings((DK["T5C"] if cal == "T5C" else DK["FIX"])[q][kW], src[q][kW], KIND[q]) for q in OUTC} for cal, src in (("T5C", oC), ("FIX", oF), ("REG", oR))}
    READ[t]["REG_excl_0906"] = {q: readings(DK["FIX"][q][kW], oR[q][kW], KIND[q], no0906) for q in OUTC}
DELTAS["D_K"] = {q: dict(T5c=boot(DK["T5C"][q][kW], one, 89), FIX=boot(DK["FIX"][q][kW], one, 89), delta_fixed=boot(DK["FIX"][q][kW] - DK["T5C"][q][kW], one, 89)) for q in OUTC}
DELTAS["D_B"] = {q: dict(T5c=boot(DB["T5C"][q][kW], one, 89), FIX=boot(DB["FIX"][q][kW], one, 89), delta_fixed=boot(DB["FIX"][q][kW] - DB["T5C"][q][kW], one, 89)) for q in OUTC}
# FTRIM trigger changes and weight distance, REG vs T5c all-R replay (KA)
FTR = {}
for t in ("KA_s42", "KA_s2027"):
    bc = RB[("T5C", t)][1]; br = RB[("REG", t)][1]; dC = DUMP[("T5C", t)]; dR = DUMP[("REG", t)]; switches = []; l1 = []
    for k, A in enumerate(CAL):
        a = set(bc[A]["kill_idx"].tolist()); b = set(br[A]["kill_idx"].tolist())
        for n in sorted(a ^ b):
            ivc = float(dC["IV"][k + 1][n]); ivr = float(dR["IV"][k + 1][n]); fnn = float(dR["FN"][k + 1][n])
            switches.append(dict(anchor=utc(A), symbol=SYM[n], killed_T5c=n in a, killed_REG=n in b, fn=fnn, iv_x0910=ivc, iv_true=ivr, rn8_x0910_bp=fnn * 8.0 / (ivc if ivc > 0 else 8.0) * 1e4, rn8_true_bp=fnn * 8.0 / (ivr if ivr > 0 else 8.0) * 1e4, in_window=A in WIN))
        wc = bc[A]["sm"] / np.abs(bc[A]["sm"]).sum(); wr = br[A]["sm"] / np.abs(br[A]["sm"]).sum(); l1.append((utc(A), float(np.abs(wc - wr).sum())))
    top = sorted(l1, key=lambda x: -x[1])[:5]; win_l1 = [x[1] for x in l1 if x[0] >= utc(WIN[0])]
    names_w = {}
    for k in kW:
        A = CAL[k]; wc = bc[A]["sm"] / np.abs(bc[A]["sm"]).sum(); wr = br[A]["sm"] / np.abs(br[A]["sm"]).sum()
        for n in np.nonzero(np.abs(wc - wr) > 1e-9)[0]: names_w[SYM[n]] = names_w.get(SYM[n], 0.0) + float(abs(wr[n] - wc[n])) / len(kW)
    FTR[t] = dict(n_switch=len(switches), n_switch_in_window=sum(1 for s in switches if s["in_window"]), switches=switches, weight_L1_mean_window=float(np.mean(win_l1)), weight_L1_max=top,
                  names_weight_change=sorted(names_w.items(), key=lambda x: -x[1])[:15])
print("deltas done", round(time.time() - t0, 1), flush=True)
# ---------------------------------------------------------------- full T5c bridge on REG (corrected carry)
from multiprocessing import Pool
def task(args):
    t, bits = args; o, NP, skp, _ = simulate(("REG", t), bits, C4C); return t, bits, o, NP, len(skp)
V = {t: {q: np.full((1 << NG, nC), np.nan) for q in OUTC} for t in ("KA_s42", "KA_s2027")}; NSP = {t: np.zeros((1 << NG, NW)) for t in V}; SK = {t: 0 for t in V}
with Pool(16) as pool:
    for t, bits, o, NP, nsk in pool.imap_unordered(task, [(t, b) for t in V for b in range(1 << NG)], chunksize=4):
        for q in OUTC: V[t][q][bits] = o[q]
        NSP[t][bits] = NP; SK[t] += nsk
popc = np.array([bin(b).count("1") for b in range(1 << NG)]); coef = [math.factorial(q) * math.factorial(NG - q - 1) / math.factorial(NG) for q in range(NG)]
BR = {}; NPZ = {}; CLOSE = {}
for t in ("KA_s42", "KA_s2027"):
    sh_all = {}; oR = RB[("REG", t)][0]
    for q, kb in (("P", 82), ("C", 83), ("N", 84), ("K", 85)):
        Vq = V[t][q][:, kW]; DEL = DK["FIX"][q][kW] - Vq[0]; REM = DK["FIX"][q][kW] - Vq[FULL]
        assert np.array_equal(Vq[0], oR[q][kW])
        phi = {}
        for g in GROUPS:
            gi = GI[g]; acc = np.zeros(len(kW))
            for b in range(1 << NG):
                if b >> gi & 1: continue
                acc += coef[popc[b]] * (Vq[b | (1 << gi)] - Vq[b])
            phi[g] = acc
        close = float(np.abs(DEL - (sum(phi.values()) + REM)).max()); seq = {}; pref = 0
        for g in ["T", "B", "W", "V", "M", "S", "X", "P", "H"]:
            nb = pref | (1 << GI[g]); seq[g] = Vq[nb] - Vq[pref]; pref = nb
        close_seq = float(np.abs(DEL - (sum(seq.values()) + REM)).max()); CLOSE[t + "_" + q] = max(close, close_seq)
        per = {}
        for g, cut in (("T", FTRIM_ON), ("B", M1_ON), ("W", SEED_ON)):
            pre_ = np.array([CAL[k] < cut for k in kW]); per[g] = dict(before=float(phi[g][pre_].mean()), after=float(phi[g][~pre_].mean()))
        preB = np.array([CAL[k] < BOOST_SWITCH for k in kW]); per["REM"] = dict(before=float(REM[preB].mean()), after=float(REM[~preB].mean()))
        remci = boot(REM, one, kb)
        sh_all[q] = dict(delta=boot(DEL, one, kb), mean={("phi_" + g): boot(phi[g], one, kb) for g in GROUPS} | {"REM": remci}, share={("phi_" + g): boot(phi[g], DEL, kb) for g in GROUPS} | {"REM": boot(REM, DEL, kb)},
                         sequential={g: float(v.mean()) for g, v in seq.items()}, one_at_a_time={g: float((Vq[1 << GI[g]] - Vq[0]).mean()) for g in GROUPS}, leave_one_out={g: float((Vq[FULL] - Vq[FULL ^ (1 << GI[g])]).mean()) for g in GROUPS},
                         periods=per, REM_model_difference_reading=("economically negligible: excluded beyond ±%.2f" % DELTA_EQ if (-DELTA_EQ <= remci[1] and remci[2] <= DELTA_EQ) else ("detected" if (remci[1] > 0 or remci[2] < 0) else "not detected, not excluded: %+.2f .. %+.2f" % (remci[1], remci[2]))),
                         excl_0906_delta=boot(DEL, one, kb, no0906))
        sh_all[q].update(sequential_share={g: boot(seq[g], DEL, 86) for g in ["T", "B", "W", "V", "M", "S", "X", "P", "H"]}, closure_maxabs=close, closure_seq_maxabs=close_seq,
                         excl_0906_share={("phi_" + g): boot(phi[g], DEL, kb, no0906) for g in GROUPS} | {"REM": boot(REM, DEL, kb, no0906)})
        NPZ.update({f"{t}_{q}_V": V[t][q], f"{t}_{q}_DEL": DEL, f"{t}_{q}_REM": REM, **{f"{t}_{q}_phi_{g}": phi[g] for g in GROUPS}})
        if q == "P":
            wD = KC[kW] / np.abs(KC[kW]).sum(1, keepdims=True); wR = np.stack([RB[("REG", t)][1][CAL[k]]["sm"] / np.abs(RB[("REG", t)][1][CAL[k]]["sm"]).sum() for k in kW])
            side = {}
            for nm_, ww in (("D_K", wD), ("R_K", wR)):
                side[nm_] = dict(long=boot((np.where(ww > 0, ww, 0) * Y4c[kW]).sum(1) * 1e4, one, 88), short=boot((np.where(ww < 0, ww, 0) * Y4c[kW]).sum(1) * 1e4, one, 88))
            side["diff_short"] = boot((np.where(wD < 0, wD, 0) * Y4c[kW]).sum(1) * 1e4 - (np.where(wR < 0, wR, 0) * Y4c[kW]).sum(1) * 1e4, one, 88)
            side["diff_long"] = boot((np.where(wD > 0, wD, 0) * Y4c[kW]).sum(1) * 1e4 - (np.where(wR > 0, wR, 0) * Y4c[kW]).sum(1) * 1e4, one, 88)
            LsD = np.where(wD < 0, wD * Y4c[kW] * 1e4, 0.0).sum(0); LsR = np.where(wR < 0, wR * Y4c[kW] * 1e4, 0.0).sum(0)
            sh_all[q]["side_lens"] = side
            sh_all[q]["short_losers_D_K"] = [dict(symbol=SYM[n], D_short_sum=float(LsD[n]), R_short_sum=float(LsR[n]), wD=float(wD[:, n].mean()), wR=float(wR[:, n].mean())) for n in np.argsort(LsD)[:12]]
            # run 2: the remaining T5c-bridge name lists and diagnostics (rn8 from the CORRECTED panel)
            phin = {}
            for g in GROUPS:
                gi = GI[g]; acc = np.zeros(NW)
                for b in range(1 << NG):
                    if b >> gi & 1: continue
                    acc += coef[popc[b]] * (NSP[t][b | (1 << gi)] - NSP[t][b])
                phin[g] = acc / len(kW)
            rn8m = np.array([np.nanmean(RN8C[kW][:, n]) if np.isfinite(RN8C[kW][:, n]).any() else np.nan for n in range(NW)])
            row = lambda n, g: dict(symbol=SYM[n], phi=float(phin[g][n]), wD=float(wD[:, n].mean()), wR=float(wR[:, n].mean()), rn8_bp=(float(rn8m[n] * 1e4) if np.isfinite(rn8m[n]) else None))
            sh_all[q]["names"] = {g: dict(top_pos=[row(n, g) for n in np.argsort(-phin[g])[:12]], top_neg=[row(n, g) for n in np.argsort(phin[g])[:12]], check=float(phin[g].sum() - phi[g].mean())) for g in GROUPS}
            gap_name = (wD * Y4c[kW] * 1e4).sum(0) / len(kW) - NSP[t][0] / len(kW)
            sh_all[q]["names_total_gap"] = [dict(symbol=SYM[n], gap=float(gap_name[n]), wD=float(wD[:, n].mean()), wR=float(wR[:, n].mean())) for n in np.argsort(gap_name)[:15]]
            sh_all[q]["short_losers_D_K_15"] = [dict(symbol=SYM[n], D_short_sum=float(LsD[n]), R_short_sum=float(LsR[n]), wD=float(wD[:, n].mean()), wR=float(wR[:, n].mean()), rn8_bp=(float(rn8m[n] * 1e4) if np.isfinite(rn8m[n]) else None)) for n in np.argsort(LsD)[:15]]
            sh_all[q]["side_gross_short"] = {nm_: float(np.abs(np.where(ww < 0, ww, 0)).sum(1).mean()) for nm_, ww in (("D_K", wD), ("R_K", wR))}
            sh_all[q]["R_ftrim_kills_mean"] = float(np.mean([len(RB[("REG", t)][1][CAL[k]]["kill_idx"]) for k in kW])); sh_all[q]["R_nsel_mean"] = float(np.mean([RB[("REG", t)][1][CAL[k]]["nsel"] for k in kW]))
            sh_all[q]["R_ftrim_kills_mean_T5C"] = float(np.mean([len(RB[("T5C", t)][1][CAL[k]]["kill_idx"]) for k in kW]))
            dR_ = DUMP[("REG", t)]; sh_all[q]["R_stop_blocks"] = dict(names_blocked_mean=float(np.mean([dR_["bl"][k + 1].sum() for k in kW])), new_fires_in_window=int(sum(((dR_["bl"][k + 1]) & ~(dR_["bl"][k])).sum() for k in kW)))
    BR[t] = sh_all
G_CLOSE = dict(max_abs=max(CLOSE.values()), PASS=bool(max(CLOSE.values()) <= 1e-6)); print("G-CLOSE", G_CLOSE, flush=True); assert G_CLOSE["PASS"]
KBREAD = {t: {q: readings(DK["FIX"][q][kW], RB[("REG", t)][0][q][kW], KIND[q]) for q in OUTC} for t in ("KB_s42", "KB_s2027")}
LEVELS = {cal: {name: {q: boot(src[q][kW], one, 81) for q in OUTC} for name, src in (("D_K", DK[cal]), ("D_B", DB[cal]), ("D_F", DF[cal]))} for cal in ("T5C", "FIX")}
LEVELS["R_K"] = {t: {cal: {q: boot(src[q][kW], one, 81) for q in OUTC} for cal, src in (("T5C", RB[("T5C", t)][0]), ("FIX", FIXR[t]), ("REG", RB[("REG", t)][0]))} for t in TAGS}
DBDK = dict(corr=float(np.corrcoef(DB["FIX"]["P"][kW], DK["FIX"]["P"][kW])[0, 1]), mean_diff=boot(DB["FIX"]["P"][kW] - DK["FIX"]["P"][kW], one, 81))
np.savez_compressed(R + "/receipts/T5d_bridge_components.npz", CAL=np.array(CAL), WIN=np.array(WIN), C4X=C4X, C4C=C4C, **{f"DK_{c}_{q}": DK[c][q] for c in DK for q in OUTC},
                    **{f"R_{cal}_{t}_{q}": (RB[(cal, t)][0][q] if cal != "FIX" else FIXR[t][q]) for cal in ("T5C", "FIX", "REG") for t in TAGS for q in OUTC}, **NPZ)
GPU1 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID1 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2")
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, delta_equivalence_bps=DELTA_EQ,
          gates=dict(G_PRED=G_PRED, G_RAW=G_RAW, G_SIM_R=G_SIM_R, G_T1c=G_T1c, G_ARCH_D=G_ARCH_D, G_FIXW=G_FIXW, G_T5C=dict(max_abs=G_T5C["max_abs"], PASS=G_T5C["PASS"]), G_CLOSE=G_CLOSE,
                     G_Xprime=DRV["gate_G_Xprime"]["PASS"], G_R6=PRC["gate_G_R6"]["PASS"], G_SCOPE=PRC["gate_G_SCOPE"]["PASS"]),
          window=[utc(WIN[0]), utc(WIN[-1])], deltas=DELTAS, readings=READ, readings_KB_REG=KBREAD, levels=LEVELS, D_B_vs_D_K_price=DBDK, ftrim_and_weights=FTR, bridge_REG=BR, node_skips=SK, synthetic_label_checks=syn,
          inputs=INPUTS, components_npz_sha256=sha(R + "/receipts/T5d_bridge_components.npz"), env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}),
          gpu_before=GPU0, gpu_after=GPU1, pids_before=PID0, pids_after=PID1, built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=round(time.time() - t0, 1))
json.dump(RC, open(R + "/receipts/RECEIPT_T5d_bridge.json", "w"), indent=1, default=lambda o: (o.tolist() if isinstance(o, np.ndarray) else float(o) if isinstance(o, np.floating) else int(o) if isinstance(o, np.integer) else bool(o) if isinstance(o, np.bool_) else str(o)))
print("DONE_t5d_bridge", RC["wall_s"])

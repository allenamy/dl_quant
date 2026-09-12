#!/usr/bin/env python3
"""r13-A · FORM A (half-scaling) built as a MEASUREMENT ONLY.

Frozen by PREREG_r13A_halfscale_2026-09-12.md sha256 ecc929ff... (asserted below, before any number).
Upstream deployability verdict: FORM A is NOT expressible through the live chain (the executor's
w -> (w-mean w)/L1(w-mean w) annihilates any half dollar tilt exactly). Every number this device
produces is therefore labelled NOT DEPLOYABLE AS-IS. Two paths are built and reported separately:
  AM_* (A_MEAS) : overlay on the ALREADY-reshaped smr, no further redemean
                  = counterfactual executor with RESHAPE_REDEMEAN=False.  <- FORM A's real body
  AS_* (A_SHIP) : overlay on the producer's on-disk form sm (net -5.9%), then TODAY'S executor
                  reshape. The dollar tilt dies; only the concentration tilt d(|w|-mean|w|) lives.

Caliber v4. CAL='log' => yv = y4 with NO expm1 (E-0904-F). g = net_ex/gross_total.
Read-only. CPU only. No GPU. Touches no live path.
"""
import os, sys, json, time, calendar, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _env_pod import assert_env
ENV = assert_env(sys.argv)
import numpy as np

T0 = time.time()
U    = "/workspace/uplift_2026-09-11"
D    = "/workspace/review_scratch/health_check/dev_v4/pod_backup_2026-08-21"
MASK = "/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"
PIN  = f"{U}/r3k/arms/A0_PWR230k_s42.npz"
DEV  = f"{U}/r13_A_halfscale/w10_sleeve.py"
COSTJ= f"{U}/r3k/costb_PWR_G230k.json"
R12  = f"{U}/r12_regime/causal_primitives_r12_v2.npz"
PRE  = f"{U}/r13_A_halfscale/PREREG_r13A_halfscale_2026-09-12.md"
OUT  = f"{U}/r13_A_halfscale/receipts"
os.makedirs(OUT, exist_ok=True)

def sha(p, n=64):
    h = hashlib.sha256()
    with open(os.path.realpath(p), 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): h.update(b)
    return h.hexdigest()[:n]

SHAS = {k: sha(v) for k, v in dict(prereg=PRE, book=PIN, device_w10=DEV, cost=COSTJ, r12_prim=R12).items()}
assert SHAS['prereg'] == 'ecc929fff68f43e3c9d435a12cfb2186f22a48faea6fc698d5f7158e4607b12a', SHAS['prereg']
assert SHAS['book']  == '352ac36fb319532756da71e7cc405fb0dcde6f36f6e28a57f1f681177bcfd339', SHAS['book']
assert SHAS['device_w10'] == 'b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650', SHAS['device_w10']
assert SHAS['cost'] == '295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53', SHAS['cost']
SELF = hashlib.sha256(open(os.path.abspath(__file__), 'rb').read()).hexdigest()
print("PREREG_SHA_OK", SHAS['prereg'], flush=True)

# ---------------------------------------------------------------- book artifact
Z = np.load(PIN, allow_pickle=True); C = [str(c) for c in Z['cols']]; RC = Z['rec']; WMAT = Z['W']
cfg = json.loads(str(Z['config_json']))
assert cfg['CAL'] == 'log' and cfg['PHI'] == 0.45 and cfg['LEGS'] == '101' and cfg['WRULE'] == 'msharpe' \
   and cfg['W3FIX'] is None and cfg['UMASK_SCOPE'] == 'm1' and cfg['LOOK'] == 900 \
   and cfg['MEMBERS_TOPN'] == 829 and cfg['FTRIM'] == 'zero', cfg
assert cfg['UPLIFT']['self_sha256'] == SHAS['device_w10']
col = lambda k: RC[:, C.index(k)].astype(np.float64)
bts = col('ts').astype(np.int64); GT = col('gross_total')
PEX, CEX, KEX, NEX = col('pnl_ex'), col('carry_ex'), col('cost_ex'), col('net_ex')
TURN_RAW = col('turnover')
NBK = len(bts)
UB = calendar.timegm((2026, 8, 30, 20, 0, 0))
W_TAIL = bts <= UB; W_ALPHA = W_TAIL.copy(); W_ALPHA[:900] = False
assert int(W_TAIL.sum()) == 10038 and int(W_ALPHA.sum()) == 9138, (W_TAIL.sum(), W_ALPHA.sum())

# ---------------------------------------------------------------- inputs
MT = np.load(f"{D}/wide_fea_hist_meta.npz", allow_pickle=True)
E_ts = MT['E_ts'].astype(np.int64); y4 = MT['y4']; qvk = MT['qvk']
META_REAL = os.path.realpath(f"{D}/wide_fea_hist_meta.npz")
assert META_REAL == "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz", META_REAL
PW = np.load(f"{D}/wide_panel_4h_hist_v2.npz", allow_pickle=True)
pwrow = {int(t): j for j, t in enumerate(PW['ts'].astype(np.int64))}
FN = PW['f_fund_now']; IV = PW['f_fund_iv']
IVf = np.where(np.isfinite(IV) & (IV > 0), IV, 8.0)
UZ = np.load(MASK, allow_pickle=True)
assert [str(x) for x in UZ['symbols']] == [str(x) for x in PW['symbols']]
umap = {int(t): k for k, t in enumerate(UZ['ts'].astype(np.int64))}; UM = np.asarray(UZ['mask'])
CB = json.load(open(COSTJ))['tiers']
RATES = np.array([t['maker_share'] * t['maker_bps'] + (1 - t['maker_share']) * t['taker_bps'] for t in CB])
T, N = y4.shape
assert N == 829

# ---------------------------------------------------------------- A_ew benchmark + parity vs r12
Y = np.full((T, N), np.nan, np.float64); A = np.full(T, np.nan); MEMS = [None] * T
for i in range(T):
    q = np.nan_to_num(qvk[i], nan=-1.0); o = np.argsort(-q); o = o[q[o] > -0.5]
    m = np.sort(o[:829]).astype(np.int64)
    t = int(E_ts[i])
    if t in umap: m = m[UM[umap[t]][m]]
    MEMS[i] = m
    yv32 = y4[i, m]                       # float32 caliber, exactly as r12 L53 / r13 do
    Y[i, m] = yv32.astype(np.float64)
    ok = np.isfinite(yv32)
    if ok.sum() >= 30: A[i] = float(yv32[ok].mean())
P12 = np.load(R12); PC = [str(c) for c in P12['cols']]; PR = P12['rec']
prow = {int(t): k for k, t in enumerate(PR[:, 0].astype(np.int64))}
Aar = np.array([PR[prow[int(t)], PC.index('A_ew')] if int(t) in prow else np.nan for t in E_ts])
bth = np.isfinite(A) & np.isfinite(Aar)
A_PARITY = float(np.abs(A[bth] - Aar[bth]).max())
assert A_PARITY == 0.0, ("A_ew PARITY vs r12 archive", A_PARITY)
print(f"A_ew parity vs r12 = {A_PARITY} (bit-exact)  [{time.time()-T0:.0f}s]", flush=True)

M = np.isfinite(Y); Yz = np.where(M, Y, 0.0)
mrow = {int(t): i for i, t in enumerate(E_ts)}
BIDX = np.array([mrow[int(t)] for t in bts], int)      # book anchor -> meta row
assert len(set(BIDX.tolist())) == NBK and (np.diff(BIDX) > 0).all()

# ---------------------------------------------------------------- pass 1: rolling betas + per-anchor cache
WBETA = 250; LAM = 0.86
BB   = np.full((NBK, N), np.nan, np.float32)     # SHRUNK beta used by the overlay
SMR  = np.zeros((NBK, N), np.float64)            # executor-caliber weights (baseline)
SM   = np.zeros((NBK, N), np.float64)            # producer on-disk form
CACHE = []                                        # per anchor: (m, yv, fn, rate)
isbook = np.zeros(T, bool); isbook[BIDX] = True
bk_of = {int(i): k for k, i in enumerate(BIDX)}
n_ = np.zeros(N); Sa = np.zeros(N); Saa = np.zeros(N); Sy = np.zeros(N); Say = np.zeros(N)
nbeta_cov = np.zeros(NBK)
for i in range(T):
    if i - WBETA >= 0:
        k0 = i - WBETA
        if np.isfinite(A[k0]):
            mk = M[k0]; n_ -= mk; Sa -= A[k0] * mk; Saa -= A[k0] * A[k0] * mk
            Sy -= Yz[k0]; Say -= Yz[k0] * A[k0]
    if isbook[i]:
        k = bk_of[i]; t = int(E_ts[i]); j = pwrow[t]; m = MEMS[i]
        with np.errstate(invalid='ignore', divide='ignore'):
            ma = Sa / n_; my = Sy / n_
            cov = Say / n_ - ma * my; var = Saa / n_ - ma * ma
            bb = cov / var
        good = (n_ >= 0.8 * WBETA) & np.isfinite(bb) & (var > 0)
        bb = np.where(good, bb, np.nan)
        if good.sum() >= 100:
            bbar = float(np.nanmean(bb))
            BB[k] = (bbar + LAM * (bb - bbar)).astype(np.float32)
            nbeta_cov[k] = int(good.sum())
        sm = WMAT[k].astype(np.float64); SM[k] = sm
        nz = np.abs(sm) > 1e-12; smr = sm.copy()
        if nz.any():
            smr[nz] -= smr[nz].mean()
            g0 = np.abs(sm).sum(); g1 = np.abs(smr).sum()
            if g1 > 1e-9: smr *= g0 / g1
        SMR[k] = smr
        yv = np.nan_to_num(y4[i, m], nan=0.0).astype(np.float64)
        fn = np.nan_to_num(FN[j, m], nan=0.0) * (4.0 / IVf[j, m])
        qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48
        tr = np.full(len(m), 2, np.int8); tr[qv4h >= 1e6] = 1; tr[qv4h >= 5e6] = 0
        CACHE.append((m, yv, fn, RATES[tr]))
    if np.isfinite(A[i]):
        mi = M[i]; n_ += mi; Sa += A[i] * mi; Saa += A[i] * A[i] * mi
        Sy += Yz[i]; Say += Yz[i] * A[i]
    if i % 2500 == 0: print("pass1", i, T, f"{time.time()-T0:.0f}s", flush=True)
del Y, Yz, M
print(f"pass1 done, beta coverage anchors {int((nbeta_cov>0).sum())}/{NBK} [{time.time()-T0:.0f}s]", flush=True)

# ---------------------------------------------------------------- accounting kernel
def account(Wseq):
    """Wseq: (NBK, N) final weight vectors. Returns pnl, car, cost, net, gross, turn (all per anchor)."""
    pn = np.empty(NBK); ca = np.empty(NBK); ks = np.empty(NBK); gr = np.empty(NBK); tu = np.empty(NBK)
    HR = np.zeros(N)
    for k in range(NBK):
        m, yv, fn, rt = CACHE[k]
        w = Wseq[k]
        pn[k] = float((w[m] * yv).sum() * 1e4)
        ca[k] = float((w[m] * fn).sum() * 1e4)
        trr = w - HR
        ks[k] = float((np.abs(trr[m]) * rt).sum())
        gr[k] = float(np.abs(w).sum())
        tu[k] = float(np.abs(trr).sum())
        HR = w
    return pn, ca, ks, pn - ca - ks, gr, tu

# ---------------------------------------------------------------- GATE P
bpn, bca, bks, bne, bgr, btu = account(SMR)
GP = dict(
    maxabs_pnl_ex = float(np.abs(bpn - PEX).max()),
    maxabs_carry_ex = float(np.abs(bca - CEX).max()),
    maxabs_cost_ex = float(np.abs(bks - KEX).max()),
    maxabs_net_ex = float(np.abs(bne - NEX).max()),
    maxabs_gross_total = float(np.abs(bgr - GT).max()),
    halves_gross_equal_maxrel = float(np.abs(
        np.array([np.abs(SMR[k][SMR[k] > 0]).sum() - np.abs(SMR[k][SMR[k] < 0]).sum() for k in range(NBK)]) / GT).max()),
)
gb = bne / GT
xa = gb[W_ALPHA]
GP['mean_g_W_ALPHA'] = float(xa.mean())
GP['sharpe_W_ALPHA'] = float(xa.mean() / xa.std(ddof=1) * np.sqrt(2190))
GP['abs_dev_mean_g_vs_r12'] = abs(GP['mean_g_W_ALPHA'] - 0.6341957)
GP['abs_dev_sharpe_vs_r12'] = abs(GP['sharpe_W_ALPHA'] - 1.2912234)
GP['turn_matched_W_ALPHA_file_caliber'] = float((TURN_RAW / GT)[W_ALPHA].mean())
GP['turn_matched_W_ALPHA_ex_caliber'] = float((btu / GT)[W_ALPHA].mean())
for kk in ('maxabs_pnl_ex', 'maxabs_carry_ex', 'maxabs_cost_ex', 'maxabs_net_ex'):
    assert GP[kk] <= 1e-3, ('GATE P (a) FAILED', kk, GP[kk])
assert GP['abs_dev_mean_g_vs_r12'] <= 1e-5 and GP['abs_dev_sharpe_vs_r12'] <= 1e-5, ('GATE P (c) FAILED', GP)
assert GP['halves_gross_equal_maxrel'] <= 1e-12, ('halves gross not equal', GP['halves_gross_equal_maxrel'])
print("GATE P (a)(c): " + json.dumps(GP), flush=True)

# ---------------------------------------------------------------- overlay
ABS = np.abs(SMR)
def halves_beta(BBx):
    """B_L, B_S, beta_book, beta_L, beta_S, gross coverage of finite beta, per anchor."""
    BL = np.zeros(NBK); BS = np.zeros(NBK); covL = np.zeros(NBK); covS = np.zeros(NBK)
    for k in range(NBK):
        b = BBx[k].astype(np.float64); w = SMR[k] / GT[k]
        ok = np.isfinite(b) & (np.abs(SMR[k]) > 0)
        L = ok & (SMR[k] > 0); S = ok & (SMR[k] < 0)
        BL[k] = float((w[L] * b[L]).sum()); BS[k] = float((w[S] * b[S]).sum())
        gl = np.abs(w[SMR[k] > 0]).sum(); gs = np.abs(w[SMR[k] < 0]).sum()
        covL[k] = float(np.abs(w[L]).sum() / gl) if gl > 0 else 0.0
        covS[k] = float(np.abs(w[S]).sum() / gs) if gs > 0 else 0.0
    return BL, BS, BL + BS, 2 * BL, -2 * BS, covL, covS

def dstar_from(BBx):
    BL, BS, bbk, bL, bS, cL, cS = halves_beta(BBx)
    den = BL - BS
    d = np.where(np.abs(den) >= 0.2, -bbk / np.where(np.abs(den) >= 0.2, den, 1.0), 0.0)
    d = np.where(np.isfinite(d), d, 0.0)
    return d, dict(BL=BL, BS=BS, beta_book=bbk, beta_L=bL, beta_S=bS, den=den, covL=cL, covS=cS)

DSTAR, BD = dstar_from(BB)
FIRE = np.abs(DSTAR) > 0     # anchors where a beta was available and non-degenerate

def build_AM(d):
    Wq = SMR + d[:, None] * ABS
    return Wq
def build_AS(d):
    Wq = np.empty_like(SMR)
    for k in range(NBK):
        sm = SM[k]; raw = sm + d[k] * np.abs(sm)
        nz = np.abs(sm) > 1e-12; w = raw.copy()
        if nz.any():
            w[nz] -= w[nz].mean()
            g0 = np.abs(sm).sum(); g1 = np.abs(w).sum()
            if g1 > 1e-9: w *= g0 / g1   # executor restores the ORIGINAL gross (live: sizing_gross)
        Wq[k] = w
    return Wq

# expanding causal mean of d* (>=900 history)
dstat = np.zeros(NBK); cs = np.cumsum(DSTAR); cn = np.cumsum(FIRE.astype(float))
for k in range(900, NBK):
    if cn[k - 1] >= 900: dstat[k] = cs[k - 1] / cn[k - 1]

ARMS = {}
ARMS['AM_f025']    = ('AM', 0.25 * DSTAR)
ARMS['AM_f050']    = ('AM', 0.50 * DSTAR)
ARMS['AM_f100']    = ('AM', 1.00 * DSTAR)
ARMS['AM_f100c10'] = ('AM', np.clip(DSTAR, -0.10, 0.10))
ARMS['AM_cond']    = ('AM', np.where(np.abs(DSTAR) > 0.05, DSTAR, 0.0))
ARMS['AM_static']  = ('AM', dstat)
ARMS['AM_flip']    = ('AM', -DSTAR)
ARMS['AS_f025']    = ('AS', 0.25 * DSTAR)
ARMS['AS_f050']    = ('AS', 0.50 * DSTAR)
ARMS['AS_f100']    = ('AS', 1.00 * DSTAR)
ARMS['AS_f100c10'] = ('AS', np.clip(DSTAR, -0.10, 0.10))
ARMS['AS_cond']    = ('AS', np.where(np.abs(DSTAR) > 0.05, DSTAR, 0.0))

# ---- nulls: beta matrix shifted in time / relabelled across names; d recomputed from them
NULLD = {}
for s in (101, 503, 1009):
    Bx = np.full_like(BB, np.nan); Bx[s:] = BB[:-s]
    NULLD[f'AM_SHIFT{s}'] = dstar_from(Bx)[0]
for r in (1, 2, 3):
    pi = np.random.default_rng([4242, r]).permutation(N)
    NULLD[f'AM_RELAB{r}'] = dstar_from(BB[:, pi])[0]
NULL_FIRE = FIRE.copy()
for v in NULLD.values(): NULL_FIRE &= (np.abs(v) > 0)
NULL_WIN = NULL_FIRE & W_ALPHA
print("null common firing set (W_ALPHA):", int(NULL_WIN.sum()), flush=True)

# turnover-match each null to AM_f100 ON THE COMMON FIRING SET, by a scalar kappa (bisection)
def marg_turn(d, kind='AM', mask=None):
    Wq = build_AM(d) if kind == 'AM' else build_AS(d)
    _, _, _, _, _, tu = account(Wq)
    mk = W_ALPHA if mask is None else mask
    return float(((tu - btu) / GT)[mk].mean()), Wq
TGT_TURN, _ = marg_turn(DSTAR, 'AM', NULL_WIN)
KAPPA = {}; NULL_MATCH = {}
for nm, d0 in NULLD.items():
    lo_, hi_ = 0.0, 8.0; best = 1.0; bestv = None
    for _ in range(24):
        mid = 0.5 * (lo_ + hi_)
        v, _ = marg_turn(mid * d0, 'AM', NULL_WIN)
        best, bestv = mid, v
        if abs(v - TGT_TURN) <= 0.01 * abs(TGT_TURN): break
        if v < TGT_TURN: lo_ = mid
        else: hi_ = mid
    KAPPA[nm] = best; NULL_MATCH[nm] = dict(kappa=best, dturn=bestv, target=TGT_TURN,
                                            rel_err=abs(bestv - TGT_TURN) / abs(TGT_TURN))
    ARMS[nm] = ('AM', best * d0)
    assert NULL_MATCH[nm]['rel_err'] <= 0.01, ('turnover match failed', nm, NULL_MATCH[nm])
    print("null", nm, json.dumps(NULL_MATCH[nm]), f"[{time.time()-T0:.0f}s]", flush=True)
assert len(ARMS) == 18, len(ARMS)

# ---------------------------------------------------------------- GATE P (b): overlay off == baseline, bitwise
z0 = build_AM(np.zeros(NBK))
GP['gateP_b_AM_d0_maxabs_vs_baseline'] = float(np.abs(z0 - SMR).max())
z1 = build_AS(np.zeros(NBK))
GP['gateP_b_AS_d0_maxabs_vs_baseline'] = float(np.abs(z1 - SMR).max())
assert GP['gateP_b_AM_d0_maxabs_vs_baseline'] == 0.0, GP
p0 = account(z0); GP['gateP_b_AM_d0_net_maxabs'] = float(np.abs(p0[3] - bne).max())
assert GP['gateP_b_AM_d0_net_maxabs'] == 0.0, GP
print("GATE P (b): AM d=0 bitwise 0.0; AS d=0 maxabs %.3e" % GP['gateP_b_AS_d0_maxabs_vs_baseline'], flush=True)

# ---------------------------------------------------------------- run every arm
SER = dict(ts=bts, gross_total=GT, base_pnl=bpn, base_car=bca, base_cost=bks, base_net=bne,
           base_turn=btu, dstar=DSTAR, fire=FIRE.astype(np.int8), null_win=NULL_WIN.astype(np.int8),
           beta_book=BD['beta_book'], beta_L=BD['beta_L'], beta_S=BD['beta_S'],
           BL=BD['BL'], BS=BD['BS'], den=BD['den'], covL=BD['covL'], covS=BD['covS'],
           A_ew=np.array([A[i] for i in BIDX]), nbeta=nbeta_cov)
MECH = {}
for nm, (kind, d) in ARMS.items():
    Wq = build_AM(d) if kind == 'AM' else build_AS(d)
    pn, ca, ks, ne, gr, tu = account(Wq)
    SER[f'{nm}__net'] = ne; SER[f'{nm}__pnl'] = pn; SER[f'{nm}__car'] = ca
    SER[f'{nm}__cost'] = ks; SER[f'{nm}__gross'] = gr; SER[f'{nm}__turn'] = tu; SER[f'{nm}__d'] = d
    # mechanism check: post-overlay book beta and half-basket betas, using the SAME shrunk betas
    bbk2 = np.zeros(NBK); bL2 = np.zeros(NBK); bS2 = np.zeros(NBK); net_over_gross = np.zeros(NBK)
    for k in range(NBK):
        b = BB[k].astype(np.float64); w = Wq[k] / GT[k]
        ok = np.isfinite(b) & (np.abs(Wq[k]) > 0)
        L = ok & (Wq[k] > 0); S = ok & (Wq[k] < 0)
        gl = np.abs(w[Wq[k] > 0]).sum(); gs = np.abs(w[Wq[k] < 0]).sum()
        bbk2[k] = float((w[ok] * b[ok]).sum())
        bL2[k] = float((w[L] * b[L]).sum() / gl) if gl > 0 else np.nan
        bS2[k] = float((w[S] * b[S]).sum() / -gs) if gs > 0 else np.nan
        net_over_gross[k] = float(w.sum() / np.abs(w).sum()) if np.abs(w).sum() > 0 else np.nan
    SER[f'{nm}__beta_book'] = bbk2; SER[f'{nm}__beta_L'] = bL2; SER[f'{nm}__beta_S'] = bS2
    SER[f'{nm}__nog'] = net_over_gross
    MECH[nm] = dict(kind=kind,
        mean_abs_d=float(np.abs(d[W_ALPHA]).mean()), sd_d=float(d[W_ALPHA].std()),
        max_abs_d=float(np.abs(d[W_ALPHA]).max()),
        fire_frac_W_ALPHA=float((np.abs(d) > 0)[W_ALPHA].mean()),
        mean_abs_beta_book_pre=float(np.abs(BD['beta_book'][W_ALPHA]).mean()),
        mean_abs_beta_book_post=float(np.abs(bbk2[W_ALPHA]).mean()),
        gap_pre=float((BD['beta_L'] - BD['beta_S'])[W_ALPHA].mean()),
        gap_post=float(np.nanmean((bL2 - bS2)[W_ALPHA])),
        gap_shift_maxabs=float(np.nanmax(np.abs((bL2 - bS2) - (BD['beta_L'] - BD['beta_S']))[W_ALPHA])),
        net_over_gross_mean=float(np.nanmean(net_over_gross[W_ALPHA])),
        gross_rel_dev_max=float(np.abs(gr / GT - 1).max()),
        dturn_matched=float(((tu - btu) / GT)[W_ALPHA].mean()),
        dcost_g=float(((ks - bks) / GT)[W_ALPHA].mean()),
        dg=float(((ne - bne) / GT)[W_ALPHA].mean()))
    print("ARM", nm, json.dumps({k: round(v, 6) if isinstance(v, float) else v for k, v in MECH[nm].items()}),
          f"[{time.time()-T0:.0f}s]", flush=True)

np.savez_compressed(f"{OUT}/r13A_arms.npz", **{k: np.asarray(v) for k, v in SER.items()},
                    arm_names=np.array(sorted(ARMS)), cost_rates=RATES)
RCP = dict(device=os.path.basename(__file__), device_sha256=SELF, prereg_sha256=SHAS['prereg'],
           input_sha256=SHAS, meta_realpath=META_REAL,
           A_ew_parity_vs_r12_maxabs=A_PARITY, gate_P=GP,
           beta=dict(W=WBETA, shrink_lambda=LAM, rule="cov(y,A)/var(A), pairwise-complete, >=0.8W obs, "
                                                     "window [t-W,t) strictly before t, I0 guard on the accumulator",
                     anchors_with_beta=int((nbeta_cov > 0).sum()),
                     mean_names_with_beta=float(nbeta_cov[nbeta_cov > 0].mean())),
           null_kappa=KAPPA, null_match=NULL_MATCH, null_target_dturn=TGT_TURN, null_common_fire_n=int(NULL_WIN.sum()),
           arms=MECH, K=len(ARMS), env=ENV,
           cost_model=dict(json=COSTJ, sha256=SHAS['cost'], rates_bps_per_unit_turnover=RATES.tolist(),
                           repricing_contested=3.2167),
           windows=dict(W_ALPHA=int(W_ALPHA.sum()), W_TAIL=int(W_TAIL.sum())),
           live_touch="none: read-only; no order, no restart, no account API; CPU only",
           built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), secs=round(time.time() - T0, 1))
json.dump(RCP, open(f"{OUT}/RECEIPT_r13A_build.json", "w"), indent=1, default=float)
print("DONE", round(time.time() - T0, 1), "s", flush=True)

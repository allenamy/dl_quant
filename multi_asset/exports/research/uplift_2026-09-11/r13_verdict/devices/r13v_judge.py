#!/usr/bin/env python3
"""r13 VERDICT STAGE judge. Frozen by PREREG_r13_verdict_2026-09-12.md (sha asserted below).
Adds NO arm. Consumes ONLY already-archived per-anchor series. READ-ONLY. No network, no GPU,
no live path touched."""
import os, sys, json, time, hashlib
WHITE = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else None
assert WHITE, "explicit env whitelist required"
BANNED = ('CAL','JUDGE','UPLIFT','PANEL','LOOK','WRULE','LEGS','PHI','FSEED','W3FIX','FTRIM',
          'UMASK','SLOW','FPRED','MEMBERS_TOPN','COSTB','SLEEVE','KMOD','SEAT','RNSM','LTRIM',
          'CDAMP','FUNDSCALE','FEMAT','TRADE_TOPN','REF_SKIP','PYTHON','OMP','MKL')
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV", EXTRA)
BAN = sorted(k for k in os.environ if k.startswith(BANNED)); assert BAN == [], ("FLAG", BAN)
ENV = dict(env_whitelist=sorted(WHITE), env_extra=EXTRA, env_banned=BAN,
           env_actual={k: os.environ[k] for k in sorted(os.environ)},
           env_banned_prefixes=sorted(BANNED), launch_cmdline=" ".join(sys.argv))
import numpy as np
ENV.update(python=sys.version.split()[0], numpy=np.__version__)
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.abspath(os.path.join(H, '..'))
U = os.path.abspath(os.path.join(R, '..'))
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): h.update(b)
    return h.hexdigest()
PRE = os.path.join(R, "PREREG_r13_verdict_2026-09-12.md")
PRE_SHA = "8767f3b746f55675e8f4a5d52dbc73cd6a50be8aee2ced5c9ed7f20d96604c07"
assert sha(PRE) == PRE_SHA, ("PREREG HASH", sha(PRE))
INP = {
 os.path.join(U,"r13_B_withinhalf/receipts/r13B_series.npz"):"f1b84e2796cf59d7036f229d6a9ba432daec53632f1b1570814391259bd68aa1",
 os.path.join(U,"r13_B_withinhalf/receipts/RECEIPT_r13B_stage2.json"):"73d4db8960b7e13d2961174a03a9fb4c2766de60e1ff76ef8bd22e66df060db4",
 os.path.join(U,"r13_B_withinhalf/receipts/RECEIPT_r13B_full.json"):"c8614f7a45ad9dd9eb702fe310f1b373e93a2239a6aab0f068995194fa6f24f8",
 os.path.join(U,"r13_A_halfscale/receipts/r13A_arms.npz"):"c9a58719d57c0acffa3034bd46a2a6c80ac3c58af6184cd6117584d95c956784",
 os.path.join(U,"r13_A_halfscale/w10_sleeve.py"):"b88e35a46b93d712422e6b6d60bf163b841be147d49278131b63f0f47a490650",
 os.path.join(U,"r13_A_halfscale/costb_PWR_G230k.json"):"295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53",
}
INP_OK = {}
for p, s in INP.items():
    a = sha(p); assert a == s, ("INPUT HASH", p, a); INP_OK[os.path.relpath(p, U)] = a
BANNED_PATHS = ('dlw_ext','_ext','pod_fea_ext','pod_legs_ext','shadow_bundle_v3','wide_fea_v2ext_meta')
for p in INP:
    rp = os.path.realpath(p)
    assert not any(b in os.path.basename(rp) for b in ('pod_fea_ext','pod_legs_ext','shadow_bundle_v3','wide_fea_v2ext_meta')), rp

Z = np.load(os.path.join(U,"r13_B_withinhalf/receipts/r13B_series.npz"))
ts = Z['ts'].astype(np.int64); gb = Z['g_base']; go = Z['g_primary']
WA = Z['WA'].astype(bool); WT = Z['WT'].astype(bool); Aew = Z['A_ew']
assert WA.sum() == 9138 and WT.sum() == 10038, (int(WA.sum()), int(WT.sum()))
DAY = np.array([time.strftime('%Y%m%d', time.gmtime(int(t))) for t in ts])
YR  = np.array([time.gmtime(int(t)).tm_year for t in ts])
NB = 2000
OUT = dict(prereg_sha256=PRE_SHA, device_sha256=sha(os.path.abspath(__file__)),
           inputs=INP_OK, env=ENV, K_checks=6, adds_no_arm=True,
           windows=dict(W_ALPHA=int(WA.sum()), W_TAIL=int(WT.sum())))

def days_of(mask):
    dd = {}
    for k in np.nonzero(mask)[0]: dd.setdefault(DAY[k], []).append(k)
    return [np.array(v) for _, v in sorted(dd.items())]
def boot_paired(x, mask):
    by = days_of(mask); tot = np.array([x[b].sum() for b in by]); cnt = np.array([len(b) for b in by], float)
    nd = len(by); ms = np.empty(NB)
    for k in range(NB):
        r = np.random.default_rng([20260905, k]).integers(0, nd, nd)
        ms[k] = tot[r].sum()/cnt[r].sum()
    return ms
def dayret(g, mask, L):
    by = {}
    for k in np.nonzero(mask)[0]: by.setdefault(DAY[k], []).append(k)
    ks = sorted(by)
    return ks, np.array([np.prod(1.0 + L*g[np.array(by[d])]*1e-4) - 1.0 for d in ks])
def maxdd_from_daily(dr):
    eq = np.concatenate([[1.0], np.cumprod(1.0+dr)])
    return float((1 - eq/np.maximum.accumulate(eq)).max())
def maxdd_anchor(g, L):
    eq = np.concatenate([[1.0], np.cumprod(1.0 + L*g*1e-4)])
    return float((1 - eq/np.maximum.accumulate(eq)).max())

# ---------------- V1 parity ----------------
mb = float(gb[WA].mean()); mo = float(go[WA].mean()); dg = mo - mb
ms = boot_paired(go-gb, WA)
sb = float(gb[WA].mean()/gb[WA].std(ddof=1)*np.sqrt(2190))
so = float(go[WA].mean()/go[WA].std(ddof=1)*np.sqrt(2190))
OUT['V1_parity'] = dict(
  mean_g_base=mb, archive_mean_g=0.6341957, dev_mean=abs(mb-0.6341957),
  sharpe_base=sb, archive_sharpe=1.2912234, dev_sharpe=abs(sb-1.2912234),
  mean_g_overlay=mo, dg=dg, build_reported_dg=0.0077, dev_dg=abs(dg-0.0077),
  dg_ci95=[float(np.percentile(ms,2.5)), float(np.percentile(ms,97.5))],
  dg_bonf12=[float(np.percentile(ms,100*(0.05/12)/2)), float(np.percentile(ms,100*(1-(0.05/12)/2)))],
  sharpe_overlay=so, sharpe_SE=float(np.sqrt(2190/WA.sum())),
  boot_resolution_bps=0.23,
  PASS=bool(abs(mb-0.6341957)<=1e-6 and abs(sb-1.2912234)<=1e-6 and abs(dg-0.0077)<=1e-3))

# ---------------- V2 de-levering disguise ----------------
x = gb[WA]; y = go[WA]
X = np.column_stack([np.ones(len(x)), x]); bb,*_ = np.linalg.lstsq(X, y, rcond=None)
res = y - X@bb
OUT['V2_delever'] = dict(
  slope_b=float(bb[1]), intercept_a=float(bb[0]), corr=float(np.corrcoef(x,y)[0,1]),
  sd_base=float(x.std(ddof=1)), sd_overlay=float(y.std(ddof=1)),
  sd_rel_change_pct=float(100*(y.std(ddof=1)/x.std(ddof=1)-1)),
  resid_sd=float(res.std(ddof=1)), resid_sd_over_sd_base=float(res.std(ddof=1)/x.std(ddof=1)),
  sd_if_pure_delever=float(bb[1]*x.std(ddof=1)),
  mean_if_pure_delever=float(bb[1]*mb), actual_mean_overlay=mo,
  dg_if_pure_delever=float(bb[1]*mb-mb),
  PASS_not_pure_delever=bool(res.std(ddof=1)/x.std(ddof=1) >= 0.05))

# ---------------- V3 halt criterion at 2.0x and 1.40x ----------------
def risk_block(g, L):
    ks, dr = dayret(g, WT, L)
    nd = len(dr); halt = int((dr<=-0.04).sum()); alert = int((dr<=-0.0268).sum())
    yrs = nd/365.0
    W = 365; dds = np.array([maxdd_from_daily(dr[i:i+W]) for i in range(nd-W+1)])
    return dict(lev=L, n_days=nd, halt=halt, halt_per_yr=halt/yrs, alert=alert,
                alert_per_yr=alert/yrs, worst_day=ks[int(np.argmin(dr))],
                worst_day_ret=float(dr.min()),
                maxDD_daily=maxdd_from_daily(dr), maxDD_anchor=maxdd_anchor(g[WT], L),
                n_1y_windows=int(len(dds)), P_1y_maxDD_ge_25=float((dds>=0.25).mean()),
                median_1y_maxDD=float(np.median(dds)), p90_1y_maxDD=float(np.percentile(dds,90)),
                crit_halt_le_1=bool(halt/yrs <= 1.0),
                crit_P25_le_10pct=bool((dds>=0.25).mean() <= 0.10),
                CRITERION_PASS=bool(halt/yrs <= 1.0 and (dds>=0.25).mean() <= 0.10))
OUT['V3_halt_criterion'] = {}
for L in (2.0, 1.40):
    OUT['V3_halt_criterion']['base@%.2fx'%L] = risk_block(gb, L)
    OUT['V3_halt_criterion']['overlay@%.2fx'%L] = risk_block(go, L)

# ---------------- V4 leverage equivalences ----------------
def annual(g, L, mask=WA):
    return float(np.prod(1.0 + L*g[mask]*1e-4)**(2190/mask.sum()) - 1.0)
ks_b, dr_b2 = dayret(gb, WT, 2.0); base_halt_2p0 = int((dr_b2<=-0.04).sum())
def halts_at(g, L):
    _, dr = dayret(g, WT, L); return int((dr<=-0.04).sum())
lo_, hi_ = 0.5, 12.0
for _ in range(60):
    mid = 0.5*(lo_+hi_)
    if halts_at(go, mid) <= base_halt_2p0: lo_ = mid
    else: hi_ = mid
L_eqhalt = lo_
def crit_ok(g, L):
    b = risk_block(g, L); return b['CRITERION_PASS']
def max_L_crit(g):
    if not crit_ok(g, 0.25): return None
    lo2, hi2 = 0.25, 6.0
    for _ in range(30):
        m = 0.5*(lo2+hi2)
        if crit_ok(g, m): lo2 = m
        else: hi2 = m
    return lo2
LmB = max_L_crit(gb); LmO = max_L_crit(go)
tgtdd = maxdd_anchor(gb[WT], 2.0)
lo3, hi3 = 0.5, 12.0
for _ in range(60):
    m = 0.5*(lo3+hi3)
    if maxdd_anchor(go[WT], m) < tgtdd: lo3 = m
    else: hi3 = m
L_eqdd = lo3
OUT['V4_leverage'] = dict(
  base_halt_count_at_2p0=base_halt_2p0,
  L_equal_halt_count=L_eqhalt, overlay_halts_at_L_equal=halts_at(go, L_eqhalt),
  ann_base_2p0=annual(gb,2.0), ann_overlay_2p0=annual(go,2.0),
  ann_overlay_at_L_equal_halt=annual(go, L_eqhalt),
  L_equal_maxDD=L_eqdd, ann_overlay_at_L_equal_maxDD=annual(go, L_eqdd),
  halts_overlay_at_L_equal_maxDD=halts_at(go, L_eqdd),
  max_L_passing_criterion_base=LmB, max_L_passing_criterion_overlay=LmO,
  ann_base_at_maxL=annual(gb, LmB) if LmB else None,
  ann_overlay_at_maxL=annual(go, LmO) if LmO else None,
  note="DIAGNOSTIC ONLY. Leverage is a separate user ruling; the cost model is not refitted at higher gross; halts are counted on the UNHALTED path (a real halt truncates the day and changes the path).")

# ---------------- V5 per-year vol stability ----------------
lo_r = boot_paired(np.zeros_like(gb), WA)  # placeholder to keep rng call pattern explicit
by = days_of(WA); nd = len(by)
rel = np.empty(NB)
for k in range(NB):
    r = np.random.default_rng([20260905, k]).integers(0, nd, nd)
    idx = np.concatenate([by[i] for i in r])
    rel[k] = go[idx].std(ddof=1)/gb[idx].std(ddof=1) - 1.0
OUT['V5_vol_stability'] = dict(
  pooled_sd_rel_change_pct=float(100*(go[WA].std(ddof=1)/gb[WA].std(ddof=1)-1)),
  pooled_ci95_pct=[float(100*np.percentile(rel,2.5)), float(100*np.percentile(rel,97.5))],
  by_year={}, )
nneg = 0
for yv in sorted(set(YR[WA].tolist())):
    m = WA & (YR==yv)
    sbb = float(gb[m].std(ddof=1)); soo = float(go[m].std(ddof=1))
    OUT['V5_vol_stability']['by_year'][str(yv)] = dict(n=int(m.sum()), sd_base=sbb, sd_overlay=soo,
        rel_pct=float(100*(soo/sbb-1)),
        mean_base=float(gb[m].mean()), mean_overlay=float(go[m].mean()),
        sharpe_base=float(gb[m].mean()/sbb*np.sqrt(2190)), sharpe_overlay=float(go[m].mean()/soo*np.sqrt(2190)))
    nneg += int(soo < sbb)
OUT['V5_vol_stability']['years_with_lower_sd'] = nneg
OUT['V5_vol_stability']['PASS_5of5'] = bool(nneg == 5)
OUT['V5_vol_stability']['PASS_ci_excludes_zero'] = bool(np.percentile(rel,97.5) < 0)

# ---------------- V6 turnover caliber ----------------
ZA = np.load(os.path.join(U,"r13_A_halfscale/receipts/r13A_arms.npz"))
gt = ZA['gross_total']; tr = ZA['base_turn']; ce = ZA['base_cost']
WAa = np.zeros(len(gt), bool)
tsA = ZA['ts'].astype(np.int64)
assert np.array_equal(tsA, ts), "ts axis mismatch between A and B archives"
WAa = WA
m_g = float(np.nanmean(gt[WAa])); m_t = float(np.nanmean(tr[WAa]))
m_tg = float(np.nanmean((tr/gt)[WAa])); m_cg = float(np.nanmean((ce/gt)[WAa]))
OUT['V6_turnover_caliber'] = dict(
  mean_gross_total=m_g, mean_turnover_raw=m_t, mean_turnover_matched=m_tg,
  mean_cost_over_gross=m_cg,
  cost_per_unit_MATCHED_turnover_bps=m_cg/m_tg, cost_per_unit_RAW_turnover_bps=m_cg/m_t,
  ratio_matched_over_raw=m_tg/m_t, one_over_mean_gross=1.0/m_g,
  task_brief_claimed_ratio=1.4375,
  VERDICT="the ratio between the two turnover calibers is mean(t/g)/mean(t), NOT 1/mean(g)",
  brief_claim_correct=bool(abs(m_tg/m_t - 1.4375) < 1e-3))

# ---------------- regime cells recount ----------------
S2 = json.load(open(os.path.join(U,"r13_B_withinhalf/receipts/RECEIPT_r13B_stage2.json")))
rt = S2['regime_table_primary']
def cnt(key, se_key='sharpe_se'):
    p = sum(1 for r in rt if r[key] > 3.0)
    c = sum(1 for r in rt if r[key] - 1.96*r[se_key] > 3.0)
    return p, c
pb, cb = cnt('sharpe_base'); po, co = cnt('sharpe_ov')
OUT['regime_recount'] = dict(n_cells=len(rt),
  base_point_gt3=pb, base_ci95lo_gt3=cb, overlay_point_gt3=po, overlay_ci95lo_gt3=co,
  cells_point_gt3_base=[r['cell'] for r in rt if r['sharpe_base']>3.0],
  cells_point_gt3_overlay=[r['cell'] for r in rt if r['sharpe_ov']>3.0],
  dg_ci_excludes_zero=sum(1 for r in rt if r['dg_ci'][0]>0 or r['dg_ci'][1]<0),
  dg_positive=sum(1 for r in rt if r['dg']>0), dg_negative=sum(1 for r in rt if r['dg']<0),
  best_cell_by_sharpe_ov=max(rt, key=lambda r: r['sharpe_ov'])['cell'],
  receipt_reported=dict(base=S2['regime_sharpe_over3_base'], ov=S2['regime_sharpe_over3_ov'], ci=S2['regime_ci_over3_ov']))

json.dump(OUT, open(os.path.join(R,"receipts","RECEIPT_r13_verdict.json"),'w'), indent=1, default=float)
print(json.dumps({k:OUT[k] for k in ('V1_parity','V2_delever','V5_vol_stability','V6_turnover_caliber','regime_recount')}, indent=1, default=float))
print("---V3---"); print(json.dumps(OUT['V3_halt_criterion'], indent=1, default=float))
print("---V4---"); print(json.dumps(OUT['V4_leverage'], indent=1, default=float))
print("DONE_verdict")

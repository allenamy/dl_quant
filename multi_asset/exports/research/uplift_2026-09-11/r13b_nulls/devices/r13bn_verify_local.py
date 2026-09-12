#!/usr/bin/env python3
"""Second instrument (local Mac, different Python/numpy than pod2): recompute the headline numbers of
every arm from r13bn_series.npz with independently written code and compare to the pod receipt.
Consumes ONLY the pulled receipts. READ-ONLY."""
import os, sys, json, time, hashlib
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "explicit non-empty env whitelist required as argv[1]"
BANNED = ('CAL','JUDGE','UPLIFT','PANEL','LOOK','WRULE','LEGS','PHI','FSEED','W3FIX','FTRIM',
          'UMASK','SLOW','FPRED','MEMBERS_TOPN','COSTB','SLEEVE','KMOD','SEAT','RNSM','LTRIM',
          'CDAMP','FUNDSCALE','FEMAT','TRADE_TOPN','REF_SKIP','PYTHON','OMP','MKL')
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV", EXTRA)
BAN = sorted(k for k in os.environ if k.startswith(BANNED)); assert BAN == [], ("FLAG", BAN)
ENV = dict(env_whitelist=sorted(WHITE), env_whitelist_n=len(WHITE), env_extra=EXTRA, env_banned=BAN,
           env_actual={k: os.environ[k] for k in sorted(os.environ)}, env_banned_prefixes=sorted(BANNED),
           launch_cmdline=" ".join(sys.argv))
import numpy as np
ENV.update(python=sys.version.split()[0], numpy=np.__version__)
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.abspath(os.path.join(H, '..'))
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): h.update(b)
    return h.hexdigest()
PRE = os.path.join(R, "PREREG_r13b_nulls_on_sd_2026-09-12.md")
assert sha(PRE) == "de9d981465ff93b874cc49c924997e2c3132a8e6d401a9e36df5aa46a7f8395f", "PREREG HASH"
REC = json.load(open(os.path.join(R, "receipts", "RECEIPT_r13bn_nulls_on_sd.json")))
Z = np.load(os.path.join(R, "receipts", "r13bn_series.npz"), allow_pickle=True)
ts = Z['ts'].astype(np.int64); WA = Z['WA'].astype(bool); WT = Z['WT'].astype(bool)
order = [str(x) for x in Z['arm_order']]
assert WA.sum() == 9138 and WT.sum() == 10038
day = np.array([time.strftime('%Y%m%d', time.gmtime(int(t))) for t in ts])
yr = np.array([time.gmtime(int(t)).tm_year for t in ts])
# independent implementations (loop forms, no shared helpers with the pod device)
def daily(g, mask, L):
    out = {}
    for k in np.nonzero(mask)[0]:
        out[day[k]] = out.get(day[k], 1.0) * (1.0 + L * g[k] * 1e-4)
    ks = sorted(out); return ks, np.array([out[d] - 1.0 for d in ks])
def mdd_path(x):
    peak, worst, eq = 1.0, 0.0, 1.0
    for r in x:
        eq *= (1.0 + r); peak = max(peak, eq); worst = max(worst, 1.0 - eq / peak)
    return worst
def p25(dr, W=365):
    return float(np.mean([mdd_path(dr[i:i+W]) >= 0.25 for i in range(len(dr) - W + 1)]))
gB = Z['g_BASE']; sdB = gB[WA].std(ddof=1)
CMP = {}; worst_dev = 0.0
for nm in order:
    g = Z['g_' + nm]; S = REC['stats'][nm]
    sd = g[WA].std(ddof=1); red = 1 - sd / sdB
    ks, dr = daily(g, WT, 2.0)
    halt = int((dr <= -0.04).sum()); alert = int((dr <= -0.0268).sum()); w = int(np.argmin(dr))
    mdd_a = mdd_path(2.0 * g[WT] * 1e-4); mdd_d = mdd_path(dr); P = p25(dr)
    yfe = np.concatenate([g[WA & (yr == y)] - g[WA & (yr == y)].mean() for y in sorted(set(yr[WA]))])
    row = dict(sd=(sd, S['W_ALPHA']['sd']), sd_reduction=(red, S['W_ALPHA']['sd_reduction']),
               sd_yearFE=(yfe.std(ddof=1), S['W_ALPHA']['sd_yearFE']),
               halt=(halt, S['W_TAIL_at_2p00']['halt']), alert=(alert, S['W_TAIL_at_2p00']['alert']),
               worst_day=(ks[w], S['W_TAIL_at_2p00']['worst_day']), worst_day_ret=(float(dr[w]), S['W_TAIL_at_2p00']['worst_day_ret']),
               maxDD_anchor=(mdd_a, S['W_TAIL_at_2p00']['maxDD_anchor']), maxDD_daily=(mdd_d, S['W_TAIL_at_2p00']['maxDD_daily']),
               P25=(P, S['W_TAIL_at_2p00']['P_1y_maxDD_ge_25']))
    dev = {}
    for k, (a, b) in row.items():
        if isinstance(a, str): dev[k] = 0.0 if a == b else 1.0
        else: dev[k] = abs(float(a) - float(b))
    worst_dev = max(worst_dev, max(dev.values()))
    CMP[nm] = dict(values={k: [a, b] for k, (a, b) in row.items()}, abs_dev=dev)
    print("%-14s sd %.4f red %+.4f%% halt %d worst %s %.3f%% mddA %.4f P25 %.2f%% | max dev %.2e"
          % (nm, sd, 100*red, halt, ks[w], 100*dr[w], mdd_a, 100*P, max(dev.values())))
# the de-levering control, independently
gR = Z['g_REAL']; L_sd = 2.0 * gR[WA].std(ddof=1) / sdB
ks, drC = daily(gB, WT, L_sd)
ctrl = dict(L_sd=L_sd, halt=int((drC <= -0.04).sum()), worst_day_ret=float(drC.min()), maxDD_anchor=mdd_path(L_sd * gB[WT] * 1e-4), P25=p25(drC))
rc = REC['R3_delever']['BASE_at_L_sd']
ctrl_dev = max(abs(ctrl['L_sd'] - REC['R3_delever']['L_sd']), abs(ctrl['halt'] - rc['halt']), abs(ctrl['worst_day_ret'] - rc['worst_day_ret']),
               abs(ctrl['maxDD_anchor'] - rc['maxDD_anchor']), abs(ctrl['P25'] - rc['P_1y_maxDD_ge_25']))
worst_dev = max(worst_dev, ctrl_dev)
print("BASE@L_sd", ctrl, "dev %.2e" % ctrl_dev)
# frozen rules re-derived from the independent numbers
dREAL = CMP['REAL']['values']['sd_reduction'][0]
r1 = {nm: CMP[nm]['values']['sd_reduction'][0] / dREAL for nm in REC['null_names']}
c1 = CMP['C1_VOL']['values']['sd_reduction'][0] / dREAL
print("R1 ratios", {k: round(v, 4) for k, v in r1.items()}, "FIRES", any(v >= 0.70 for v in r1.values()))
print("C1 ratio %.4f FIRES %s" % (c1, c1 >= 0.70))
OUT = dict(env=ENV, receipt_sha256=sha(os.path.join(R, "receipts", "RECEIPT_r13bn_nulls_on_sd.json")),
           series_sha256=sha(os.path.join(R, "receipts", "r13bn_series.npz")), device_sha256=sha(os.path.abspath(__file__)),
           comparison=CMP, delever_control_independent=ctrl, worst_abs_deviation=worst_dev,
           R1_ratios_independent=r1, R1_fires_independent=bool(any(v >= 0.70 for v in r1.values())),
           C1_ratio_independent=c1, C1_fires_independent=bool(c1 >= 0.70),
           agrees_with_pod=dict(R1=bool(any(v >= 0.70 for v in r1.values())) == REC['RULES']['R1']['FIRES'],
                                C1=bool(c1 >= 0.70) == REC['RULES']['C1']['FIRES'],
                                LIVE_WIRE=REC['RULES']['LIVE_WIRE']),
           PASS=bool(worst_dev < 1e-9))
json.dump(OUT, open(os.path.join(R, "receipts", "RECEIPT_r13bn_verify_local.json"), "w"), indent=1, default=float)
print("WORST ABS DEVIATION %.3e  PASS=%s" % (worst_dev, OUT['PASS']))

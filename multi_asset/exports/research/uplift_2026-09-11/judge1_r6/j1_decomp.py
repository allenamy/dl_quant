"""R6 JUDGE-1 — exact additive decomposition of the replay-vs-realized gap + era splits.
CHAIN (all per unit gross, bps/anchor):
  g_replay(A0)   = w_replay  . r_replay     (replay's own book, replay's return model)
  g_D2           = w_deployed. r_replay     (book-construction step removed)
  g_HELD         = w_held    . r_replay     (fill shortfall removed)
  g_realized     = w_held    . r_realized   (return-model / price-source / universe residual)
Steps: BOOK = g_D2-g_replay ; FILL = g_HELD-g_D2 ; RETMODEL = g_realized-g_HELD.
"""
import json, os, time, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(f'{HERE}/j1_recon_rows.json')); rows = D['rows']
NB = 2000; SEEDBASE = 20260911
def dayblk(A): return time.strftime('%Y%m%d', time.gmtime(A))
def bootci(x, days, k):
    rng = np.random.default_rng([SEEDBASE, k])
    ud = sorted(set(days)); idx = {d: np.where(np.array(days) == d)[0] for d in ud}
    o = np.empty(NB)
    for b in range(NB):
        p = rng.integers(0, len(ud), len(ud))
        o[b] = x[np.concatenate([idx[ud[q]] for q in p])].mean()
    return float(x.mean()), float(o.std(ddof=1)), [float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))]

WINS = {
 'W5_COMBO 2026-08-26 04Z..09-10 00Z': (1787716800, 1788998400),
 'W4_LIVE  2026-08-01 00Z..09-10 00Z': (1785542400, 1788998400),
 'SEP_ONLY 2026-09-01 00Z..09-10 00Z': (1788220800, 1788998400),
 'D1W 2026-08-26 04Z..08-30 20Z': (1787716800, 1788120000),
 'PRECOMBO 2026-08-01 00Z..08-25 20Z': (1785542400, 1787702400),
}
OUT = {}
k = 100
for wn, (lo, hi) in WINS.items():
    S = [r for r in rows if lo <= r['A'] <= hi and r.get('realized') and 'D2' in r and 'HELD' in r]
    if not S: OUT[wn] = dict(n=0); continue
    days = [dayblk(r['A']) for r in S]
    gD2 = np.array([r['D2']['price_y4s'] for r in S])
    gHE = np.array([r['HELD']['price_y4s'] for r in S])
    gRE = np.array([r['realized']['price_bps'] for r in S])
    fD2 = np.array([r['D2']['fund_model'] for r in S])
    fRE = np.array([r['realized']['fund_bps'] for r in S])
    feeRE = np.array([r['realized']['fee_bps'] for r in S])
    timRE = np.array([r['realized']['timing_bps'] for r in S])
    ent = {}
    for nm, x in (('FILL  (w_held-w_dep).r_replay', gHE - gD2),
                  ('RETMODEL w_held.(r_real-r_replay)', gRE - gHE),
                  ('TOTAL price gap realized-D2', gRE - gD2),
                  ('FUND gap realized-model', fRE - fD2),
                  ('FEES realized (commission)', feeRE),
                  ('TIMING realized (fill vs anchor mid)', timRE)):
        k += 1; m, se, ci = bootci(x, days, k); ent[nm] = dict(mean=m, boot_se=se, ci95=ci)
    # replay's own book where it exists
    for arm in ('A0_PWR230k_s42', 'A0_PWR230k_s2027'):
        Sa = [r for r in S if arm in r]
        if len(Sa) >= 5:
            da = [dayblk(r['A']) for r in Sa]
            gR = np.array([r[arm]['price_bps'] for r in Sa]); gD = np.array([r['D2']['price_y4s'] for r in Sa])
            k += 1; m, se, ci = bootci(gD - gR, da, k)
            ent[f'BOOK  (w_dep-w_rep).r_replay [{arm}]'] = dict(mean=m, boot_se=se, ci95=ci, n=len(Sa))
            fR = np.array([r[arm]['fund_bps'] for r in Sa]); cR = np.array([r[arm]['cost_bps'] for r in Sa])
            fRa = np.array([r['realized']['fund_bps'] for r in Sa])
            feeA = np.array([r['realized']['fee_bps'] for r in Sa]); timA = np.array([r['realized']['timing_bps'] for r in Sa])
            k += 1; m, se, ci = bootci(fRa - fR, da, k); ent[f'FUND replay-book gap [{arm}]'] = dict(mean=m, boot_se=se, ci95=ci)
            k += 1; m, se, ci = bootci((feeA + timA) - cR, da, k); ent[f'COST realized(fee+timing) - replay cost [{arm}]'] = dict(mean=m, boot_se=se, ci95=ci, replay_cost_mean=float(cR.mean()), realized_mean=float((feeA+timA).mean()))
    OUT[wn] = dict(n=len(S), levels=dict(
        g_D2_price=float(gD2.mean()), g_HELD_price=float(gHE.mean()), g_realized_price=float(gRE.mean()),
        fund_model=float(fD2.mean()), fund_realized=float(fRE.mean()),
        fee_realized=float(feeRE.mean()), timing_realized=float(timRE.mean()),
        net_model=float(gD2.mean() + fD2.mean()), net_realized=float(gRE.mean() + fRE.mean() + feeRE.mean())),
        terms=ent)
json.dump(OUT, open(f'{HERE}/j1_decomp.json', 'w'), indent=1)
for wn, v in OUT.items():
    print(f"\n=== {wn}   n={v.get('n')}")
    if not v.get('n'): continue
    L = v['levels']
    print("  LEVELS bps/anchor: D2(w_dep.r_rep) %+.4f -> HELD(w_held.r_rep) %+.4f -> REALIZED %+.4f | fund model %+.4f vs realized %+.4f | fee %+.4f timing %+.4f" %
          (L['g_D2_price'], L['g_HELD_price'], L['g_realized_price'], L['fund_model'], L['fund_realized'], L['fee_realized'], L['timing_realized']))
    print("  NET  model(price+fund) %+.4f   realized(price+fund+fee) %+.4f" % (L['net_model'], L['net_realized']))
    for nm, e in v['terms'].items():
        print(f"    {nm:46s} {e['mean']:+8.4f}  SE {e['boot_se']:6.4f}  CI95 [{e['ci95'][0]:+.4f},{e['ci95'][1]:+.4f}]")

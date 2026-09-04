"""carry_composition step 1+2 (Mac, READ-ONLY on ~/wide_shadow).
Reproduce the +1.21 bps/anchor per-gross live-vs-replay carry gap on the 28 overlapping anchors and decompose it
by constructing intermediate books. Rates = pod panel f_fund_now x (4/f_fund_iv) (bitwise == producer ledger, gap_1),
sign: + = book pays. Two weight calibers per book: raw (file) and dm (device smr / executor exec_reshape:
demean over the non-zero set, rescale to the original gross)."""
import json, os, time, sys, numpy as np
SP = "/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/review_caliber"
G1 = f"{SP}/gap_1"; OUT = f"{SP}/carry_composition"; WS = "/Users/haosiyu/wide_shadow"
def f(t): return time.strftime("%m-%d %HZ", time.gmtime(int(t)))
P = np.load(f"{G1}/panel_fund_tail.npz", allow_pickle=True)
pts = P["ts"].astype(np.int64); psym = [str(s) for s in P["symbols"]]; NW = len(psym)
FN = P["f_fund_now"].astype(np.float64); IV = P["f_fund_iv"].astype(np.float64); FE = P["f_fund_ema_v1"].astype(np.float64)
prow = {int(t): i for i, t in enumerate(pts)}
cfg = json.load(open(f"{WS}/shadow_bundle/config.json")); assert cfg["symbols_panel"] == psym
live450 = np.array([s in set(cfg["symbols_live"]) for s in psym]); sidx = {s: j for j, s in enumerate(psym)}
R = json.load(open(f"{G1}/replay_tail_rows.json"))
TAGS = ["pod_live_w3fix_callog_s42", "pod_live_callog_s42", "pod_canon_w3fix_callog_s42"]
def rates(N):
    i = prow[N]; iv = np.where(np.isfinite(IV[i]) & (IV[i] > 0), IV[i], 8.0)
    return np.nan_to_num(FN[i]) * (4.0 / iv)
def dm(w):
    nz = np.abs(w) > 1e-12; o = w.copy()
    if nz.any():
        o[nz] -= o[nz].mean(); g0 = np.abs(w).sum(); g1 = np.abs(o).sum()
        if g1 > 1e-9: o *= g0 / g1
    return o
def expo(w, r):
    g = np.abs(w).sum()
    if g < 1e-12: return None
    c = (w * r).sum() / g * 1e4
    return {"carry": c, "net": w.sum() / g,
            "LP": np.abs(w[(w > 0) & (r > 0)]).sum() / g, "SN": np.abs(w[(w < 0) & (r < 0)]).sum() / g,
            "LN": np.abs(w[(w > 0) & (r < 0)]).sum() / g, "SP": np.abs(w[(w < 0) & (r > 0)]).sum() / g,
            "pay_LP": (w * r)[(w > 0) & (r > 0)].sum() / g * 1e4, "pay_SN": (w * r)[(w < 0) & (r < 0)].sum() / g * 1e4,
            "recv_LN": -(w * r)[(w > 0) & (r < 0)].sum() / g * 1e4, "recv_SP": -(w * r)[(w < 0) & (r > 0)].sum() / g * 1e4,
            "gross": g, "n": int((np.abs(w) > 1e-12).sum())}
def vec_from_json(path):
    w = np.zeros(NW)
    for s, v in json.load(open(path))["weights"].items(): w[sidx[s]] = float(v)
    return w
def vec_from_npz(path):
    z = np.load(path); w = np.zeros(NW); w[z["idx"].astype(np.int64)] = z["val"].astype(np.float64); return w
wts = {tag: [int(t) for t in R[tag]["W_ts"]] for tag in TAGS}
common = [N for N in wts[TAGS[0]] if N >= 1787716800 and N in prow and os.path.exists(f"{WS}/state/target_live/{N}.json")]
print(f"common anchors {len(common)} {f(common[0])} -> {f(common[-1])}")
books = {}   # name -> {N: vec}
contrib = {}  # name -> per-name mean |w*r|/g contributions
rows = []
for N in common:
    r = rates(N)
    Wrep = {tag: np.array(R[tag]["W"][wts[tag].index(N)], np.float64) for tag in TAGS}
    tl = vec_from_json(f"{WS}/state/target_live/{N}.json")
    tk = vec_from_json(f"{WS}/state/target_live_king/{N}.json") if os.path.exists(f"{WS}/state/target_live_king/{N}.json") else None
    tc = vec_from_json(f"{WS}/state/target_combo/{N}.json") if os.path.exists(f"{WS}/state/target_combo/{N}.json") else None
    kc = vec_from_npz(f"{WS}/fea171/state_H_kc_{N}.npz") if os.path.exists(f"{WS}/fea171/state_H_kc_{N}.npz") else None
    fc = vec_from_npz(f"{WS}/fea171/state_H_fc_{N}.npz") if os.path.exists(f"{WS}/fea171/state_H_fc_{N}.npz") else None
    z = np.load(f"{WS}/state/weights/{N}.npz"); mem = z["members"].astype(np.int64); king_sm = np.zeros(NW); king_sm[z["idx"].astype(np.int64)] = z["val"].astype(np.float64)
    memmask = np.zeros(NW, bool); memmask[mem] = True
    if tk is not None: assert np.abs(tk - king_sm).max() < 1e-6, "target_live_king != weights npz"
    if kc is not None and fc is not None: assert np.abs(0.55 * kc + 0.45 * fc - tl).max() < 1e-7, f"target_live != 0.55kc+0.45fc @ {f(N)}"
    if tc is not None: assert np.abs(dm(tl) - tc).max() < 1e-6, f"target_combo != dm(target_live) @ {f(N)}"
    Wr = Wrep[TAGS[0]]
    B = {"a_replay_raw": Wr, "a_replay_dm": dm(Wr),
         "a_replaydyn_dm": dm(Wrep[TAGS[1]]), "a_canonw3fix_dm": dm(Wrep[TAGS[2]]),
         "b_replay_in450_raw": np.where(live450, Wr, 0.0), "b_replay_in450_dm": dm(np.where(live450, Wr, 0.0)),
         "c_replay_inmembers_raw": np.where(memmask, Wr, 0.0), "c_replay_inmembers_dm": dm(np.where(memmask, Wr, 0.0)),
         "d_live_king_raw": tk, "d_live_king_dm": (dm(tk) if tk is not None else None),
         "d1_live_kc_raw": kc, "d1_live_kc_dm": (dm(kc) if kc is not None else None),
         "d2_live_fc_raw": fc, "d2_live_fc_dm": (dm(fc) if fc is not None else None),
         "e_live_target_raw": tl, "e_live_target_dm": dm(tl)}
    row = {"N": N, "when": f(N), "n_members": len(mem), "rep_outside450": float(np.abs(Wr[~live450]).sum() / np.abs(Wr).sum()),
           "rep_outside_members": float(np.abs(Wr[~memmask]).sum() / np.abs(Wr).sum()),
           "live_outside_members": float(np.abs(tl[~memmask]).sum() / np.abs(tl).sum()),
           "overlap_names": int(((np.abs(Wr) > 1e-12) & (np.abs(tl) > 1e-12)).sum()), "n_rep": int((np.abs(Wr) > 1e-12).sum()), "n_live": int((np.abs(tl) > 1e-12).sum()),
           "sign_agree": float((np.sign(Wr) == np.sign(tl))[(np.abs(Wr) > 1e-12) & (np.abs(tl) > 1e-12)].mean()),
           "corr_raw": float(np.corrcoef(Wr, tl)[0, 1]), "corr_dm": float(np.corrcoef(dm(Wr), dm(tl))[0, 1]),
           "rate_mean_members": float(r[memmask].mean() * 1e4), "rate_pos_frac_members": float((r[memmask] > 0).mean())}
    for k, w in B.items():
        e = expo(w, r) if w is not None else None
        row[k] = e
        if w is not None:
            contrib.setdefault(k, np.zeros(NW)); contrib[k] += np.abs(w * r) / np.abs(w).sum() * 1e4
            books.setdefault(k, {})[N] = w
    rows.append(row)
n = len(rows)
def st(vals):
    a = np.array([v for v in vals if v is not None], float); return a.mean(), a.std(ddof=1), a.std(ddof=1) / np.sqrt(len(a)), len(a)
print("\n== step 1: reproduce the gap (bps/anchor per gross, + = pays; mean of per-anchor ratio) ==")
gap = [x["e_live_target_raw"]["carry"] - x["a_replay_dm"]["carry"] for x in rows]
print("gap_1 definition  live target_live RAW  minus  replay W3FIX DM : mean %+.3f sd %.3f se %.3f n %d" % st(gap))
for a_, b_ in (("e_live_target_dm", "a_replay_dm"), ("e_live_target_raw", "a_replay_raw"), ("e_live_target_dm", "a_replaydyn_dm"), ("e_live_target_dm", "a_canonw3fix_dm")):
    print(f"  {a_:22s} minus {b_:20s}: mean %+.3f sd %.3f se %.3f n %d" % st([x[a_]["carry"] - x[b_]["carry"] for x in rows]))
print("\n== step 2: decomposition ladder (per-gross carry; net = sum(w)/gross; LP = gross share long&rate>0, SN = short&rate<0, LN long&rate<0 (receives), SP short&rate>0 (receives)) ==")
keys = ["a_replay_raw", "a_replay_dm", "a_replaydyn_dm", "a_canonw3fix_dm", "b_replay_in450_raw", "b_replay_in450_dm", "c_replay_inmembers_raw", "c_replay_inmembers_dm",
        "d_live_king_raw", "d_live_king_dm", "d1_live_kc_raw", "d1_live_kc_dm", "d2_live_fc_raw", "d2_live_fc_dm", "e_live_target_raw", "e_live_target_dm"]
hdr = f"{'book':24s} {'carry':>7s} {'se':>5s} {'net':>6s} {'LP':>5s} {'SN':>5s} {'LN':>5s} {'SP':>5s} {'payLP':>6s} {'paySN':>6s} {'rcvLN':>6s} {'rcvSP':>6s} {'gross':>6s} {'n':>4s}"
print(hdr)
summ = {}
for k in keys:
    es = [x[k] for x in rows if x[k] is not None]
    if not es: print(f"{k:24s} (none)"); continue
    m = {q: float(np.mean([e[q] for e in es])) for q in es[0]}; se = float(np.std([e["carry"] for e in es], ddof=1) / np.sqrt(len(es)))
    summ[k] = dict(m, se=se, n_anchors=len(es))
    print(f"{k:24s} {m['carry']:+7.3f} {se:5.3f} {m['net']:+6.3f} {m['LP']:5.3f} {m['SN']:5.3f} {m['LN']:5.3f} {m['SP']:5.3f} {m['pay_LP']:+6.3f} {m['pay_SN']:+6.3f} {m['recv_LN']:+6.3f} {m['recv_SP']:+6.3f} {m['gross']:6.3f} {m['n']:4.0f}")
print("\nincrements (dm caliber unless noted):")
lad = [("a_replay_dm", "b_replay_in450_dm", "restrict replay to live 450 universe"), ("b_replay_in450_dm", "c_replay_inmembers_dm", "restrict replay to live members(400)"),
       ("c_replay_inmembers_dm", "d_live_king_dm", "replay-on-live-members -> live KING-form book (producer)"), ("d_live_king_dm", "e_live_target_dm", "live king-form -> live combo target (dm)"),
       ("e_live_target_dm", "e_live_target_raw", "dm -> raw (net exposure of file weights)")]
for a_, b_, lab in lad:
    d = [x[b_]["carry"] - x[a_]["carry"] for x in rows if x[a_] is not None and x[b_] is not None]
    print(f"  {lab:60s}: %+.3f (se %.3f, n %d)" % (np.mean(d), np.std(d, ddof=1) / np.sqrt(len(d)), len(d)))
print("\nreplay gross outside live-450: mean %.4f max %.4f | replay gross outside live members: mean %.4f | live gross outside its members: %.4f" % (
    np.mean([x["rep_outside450"] for x in rows]), np.max([x["rep_outside450"] for x in rows]), np.mean([x["rep_outside_members"] for x in rows]), np.mean([x["live_outside_members"] for x in rows])))
print("book overlap: names in both mean %.1f (replay %.1f, live %.1f); sign agreement on common names %.3f; corr raw %.3f dm %.3f" % (
    np.mean([x["overlap_names"] for x in rows]), np.mean([x["n_rep"] for x in rows]), np.mean([x["n_live"] for x in rows]), np.mean([x["sign_agree"] for x in rows]), np.mean([x["corr_raw"] for x in rows]), np.mean([x["corr_dm"] for x in rows])))
print("members' mean 4h rate %.3f bps, frac positive %.3f" % (np.mean([x["rate_mean_members"] for x in rows]), np.mean([x["rate_pos_frac_members"] for x in rows])))
# sub-periods: clean combo 08-26 04Z..08-29 16Z (22), king-form 08-30 00Z (1), degraded fc 08-30 04Z..20Z (5)
print("\nsub-periods (live target dm vs replay dm, per gross):")
for lab, lo, hi in (("clean combo 08-26 04Z..08-29 16Z", 1787716800, 1788019200), ("king-form anchor 08-30 00Z", 1788048000, 1788048000), ("fc-reset 08-30 04Z..20Z", 1788062400, 1788120000)):
    sub = [x for x in rows if lo <= x["N"] <= hi]
    if sub: print(f"  {lab:36s} n={len(sub):2d} live_dm %+.3f live_raw %+.3f replay_dm %+.3f gap_dm %+.3f | king_dm %s kc_dm %s fc_dm %s" % (
        np.mean([x["e_live_target_dm"]["carry"] for x in sub]), np.mean([x["e_live_target_raw"]["carry"] for x in sub]), np.mean([x["a_replay_dm"]["carry"] for x in sub]),
        np.mean([x["e_live_target_dm"]["carry"] - x["a_replay_dm"]["carry"] for x in sub]),
        "%+.3f" % np.mean([x["d_live_king_dm"]["carry"] for x in sub if x["d_live_king_dm"]]) if any(x["d_live_king_dm"] for x in sub) else "na",
        "%+.3f" % np.mean([x["d1_live_kc_dm"]["carry"] for x in sub if x["d1_live_kc_dm"]]) if any(x["d1_live_kc_dm"] for x in sub) else "na",
        "%+.3f" % np.mean([x["d2_live_fc_dm"]["carry"] for x in sub if x["d2_live_fc_dm"]]) if any(x["d2_live_fc_dm"] for x in sub) else "na"))
# top-20 contributors by mean |w x r| per gross (bps/anchor), live vs replay, with membership
print("\n== top-20 names by mean |w x rate| contribution (bps/anchor per gross), live target (dm) ==")
def top(k, other):
    c = contrib[k] / n; o = contrib[other] / n; idx = np.argsort(-c)[:20]
    for j in idx:
        # signed mean contribution and mean weight/rate
        sw = np.mean([books[k][N][j] for N in books[k]]); ow = np.mean([books[other][N][j] for N in books[other]])
        sr = np.mean([rates(N)[j] for N in books[k]]) * 1e4
        print(f"  {psym[j]:16s} |w r| {c[j]:5.3f}  w_mean {sw:+.4f}  rate4h {sr:+7.2f}bps  in450 {int(live450[j])}  {other[:8]} |w r| {o[j]:5.3f} w_mean {ow:+.4f}  both {'Y' if (abs(sw) > 1e-6 and abs(ow) > 1e-6) else 'N'}")
    print(f"  top-20 share of total |w r| in {k}: {c[idx].sum() / c.sum():.3f}; same names' share in {other}: {o[idx].sum() / o.sum():.3f}")
top("e_live_target_dm", "a_replay_dm")
print("\n== top-20 names, replay W3FIX (dm) ==")
top("a_replay_dm", "e_live_target_dm")
json.dump({"common": common, "rows": rows, "summary": summ}, open(f"{OUT}/decompose_mac_rows.json", "w"), indent=1, default=float)
print("\nper-anchor table (per gross): N when | replay_dm | rep_in450_dm | rep_inmem_dm | live_king_dm | kc_dm | fc_dm | live_dm | live_raw | net_live_raw")
for x in rows:
    g = lambda k: ("%+6.2f" % x[k]["carry"]) if x[k] else "   na "
    print(f"{x['N']} {x['when']} {g('a_replay_dm')} {g('b_replay_in450_dm')} {g('c_replay_inmembers_dm')} {g('d_live_king_dm')} {g('d1_live_kc_dm')} {g('d2_live_fc_dm')} {g('e_live_target_dm')} {g('e_live_target_raw')} {x['e_live_target_raw']['net']:+.3f}")

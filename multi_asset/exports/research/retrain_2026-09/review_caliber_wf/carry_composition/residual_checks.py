"""carry_composition residual checks (Mac, READ-ONLY on ~/wide_shadow):
1. ladder live vs V1 (no-FTRIM replay) with ONGUSDT excluded from both books (single-name idiosyncrasy test);
2. sel-count mechanism: from meta qvk at the 28 anchors, how many of the frozen 450 pass qv4h>=2.5e5 vs how many of the
   top-400-of-829 pass; producer's own qvm (rolling.npz, same formula as run_anchor) vs meta qvk at the same anchors;
3. ONGUSDT diagnostics: replay sel status, king pinned rank, fund rank, weight trajectories live vs V1 vs deployed-form replay."""
import json, os, time, numpy as np
from scipy.stats import rankdata, spearmanr
SP = "/Users/haosiyu/cc_tmp/claude-501/-Users-haosiyu-Desktop-quant-research/b9646a9e-31a1-4eb3-a08b-e8ea13fdceb0/scratchpad/review_caliber"
G1 = f"{SP}/gap_1"; OUT = f"{SP}/carry_composition"; WS = "/Users/haosiyu/wide_shadow"
def f(t): return time.strftime("%m-%d %HZ", time.gmtime(int(t)))
P = np.load(f"{G1}/panel_fund_tail.npz", allow_pickle=True); pts = P["ts"].astype(np.int64); psym = [str(s) for s in P["symbols"]]; NW = len(psym); sidx = {s: j for j, s in enumerate(psym)}
FN = P["f_fund_now"].astype(np.float64); IV = P["f_fund_iv"].astype(np.float64); FE = P["f_fund_ema_v1"].astype(np.float64); prow = {int(t): i for i, t in enumerate(pts)}
cfg = json.load(open(f"{WS}/shadow_bundle/config.json")); live450 = np.array([s in set(cfg["symbols_live"]) for s in psym])
INP = json.load(open(f"{OUT}/replay_inputs_overlap.json")); ARMS = json.load(open(f"{OUT}/W_overlap_4arms.json"))
OV = [N for N in range(1787716800, 1788120000 + 1, 14400) if N != 1788033600]
sig = {r["anchor_ts"]: r for r in (json.loads(l) for l in open(f"{WS}/shadow_log.jsonl") if l.strip()) if r.get("e") == "signal"}
def rates(N):
    i = prow[N]; iv = np.where(np.isfinite(IV[i]) & (IV[i] > 0), IV[i], 8.0); return np.nan_to_num(FN[i]) * (4.0 / iv)
def dm(w):
    nz = np.abs(w) > 1e-12; o = w.copy()
    if nz.any():
        o[nz] -= o[nz].mean(); g0 = np.abs(w).sum(); g1 = np.abs(o).sum()
        if g1 > 1e-9: o *= g0 / g1
    return o
def carry(w, r): s = dm(w); return (s * r).sum() / np.abs(w).sum() * 1e4
def vec(path):
    w = np.zeros(NW)
    for s, v in json.load(open(path))["weights"].items(): w[sidx[s]] = float(v)
    return w
def W(tag, N): a = ARMS[tag]; return np.array(a["W"][a["W_ts"].index(N)], np.float64)
jO = sidx["ONGUSDT"]
print("== 1. ladder with ONGUSDT excluded (zeroed in both books, renormalised) ==")
d_all, d_x, d_mem_all, d_mem_x, d_dep, d_dep_x = [], [], [], [], [], []
for N in OV:
    r = rates(N); tl = vec(f"{WS}/state/target_live/{N}.json"); v1 = W("V1_live_w3fix_noftrim", N); dep = W("live_w3fix_ftrim", N)
    z = np.load(f"{WS}/state/weights/{N}.npz"); mem = np.zeros(NW, bool); mem[z["members"].astype(np.int64)] = True
    v1m = np.where(mem, v1, 0.0)
    tlx, v1x, v1mx, depx = tl.copy(), v1.copy(), v1m.copy(), dep.copy(); tlx[jO] = v1x[jO] = v1mx[jO] = depx[jO] = 0.0
    d_all.append(carry(tl, r) - carry(v1, r)); d_x.append(carry(tlx, r) - carry(v1x, r)); d_mem_all.append(carry(tl, r) - carry(v1m, r)); d_mem_x.append(carry(tlx, r) - carry(v1mx, r))
    d_dep.append(carry(tl, r) - carry(dep, r)); d_dep_x.append(carry(tlx, r) - carry(depx, r))
def st(a): a = np.array(a); return "%+.3f (se %.3f)" % (a.mean(), a.std(ddof=1) / np.sqrt(len(a)))
print(f"  live - V1:              all names {st(d_all)} | ex-ONG {st(d_x)}")
print(f"  live - V1|live members: all names {st(d_mem_all)} | ex-ONG {st(d_mem_x)}")
print(f"  live - deployed(FTRIM): all names {st(d_dep)} | ex-ONG {st(d_dep_x)}")
print("\n== 2. sel-count mechanism (meta qvk at the 28 anchors; gate qv4h = expm1(clip(qvk,0,30))*48 >= 2.5e5) ==")
rows = []
Rz = np.load(f"{WS}/state/rolling.npz", allow_pickle=True); rts = Rz["ts"].astype(np.int64); RD = Rz["data"]; rrow = {int(t): i for i, t in enumerate(rts)}
for N in OV:
    a = INP["anchors"][str(N)]; qvk = np.array(a["qvk"], float); y4ok = np.array(a["y4ok"], bool); qv4h = np.expm1(np.clip(qvk, 0, 30)) * 48
    rk = np.empty(NW, int); rk[np.argsort(-qvk)] = np.arange(NW)
    pass_ = qv4h >= 2.5e5
    n450_pass = int((live450 & pass_).sum()); n450_pass_y4 = int((live450 & pass_ & y4ok).sum()); ntop400_pass = int(((rk < 400) & pass_ & y4ok).sum()); ntop400_in450 = int(((rk < 400) & live450).sum())
    nout450_top400_pass = int(((rk < 400) & ~live450 & pass_ & y4ok).sum())
    # producer's own qvm from rolling cache (same formula as run_anchor: mean of channel 3 over last 2016 rows)
    ai = rrow.get(N); prod_sel = None; rho = None; n_prod_pass_members = None
    if ai is not None and ai >= 2015:
        CD = RD[max(ai + 1 - 2016, 0):ai + 1, :, 3].astype(np.float32); fin = np.isfinite(CD); qvm = np.where(fin, CD, 0).sum(0) / np.maximum(fin.sum(0), 1)
        qv4h_p = np.expm1(np.clip(qvm, 0, 30)) * 48
        z = np.load(f"{WS}/state/weights/{N}.npz"); mem = z["members"].astype(np.int64)
        n_prod_pass_members = int((qv4h_p[mem] >= 2.5e5).sum()); both = live450 & (fin.sum(0) > 0) & (qvk > 0)
        rho = float(spearmanr(qvm[both], qvk[both])[0]); ratio_med = float(np.median((qvm[both] - qvk[both])))
        n_meta_pass_members = int((qv4h[mem] >= 2.5e5).sum())
    rows.append((N, n450_pass, n450_pass_y4, ntop400_pass, ntop400_in450, nout450_top400_pass, sig.get(N, {}).get("sel"), n_prod_pass_members, n_meta_pass_members if ai is not None else None, rho, ratio_med if ai is not None else None))
print("  when | 450 names passing gate | (+y4ok) | top400-of-829 passing (+y4ok) [= replay nsel] | top400 that are in 450 | top400 outside 450 passing | live sel (signal) | producer-cache gate on live members | meta-qvk gate on live members | spearman(producer qvm, meta qvk) | median(qvm - qvk)")
for x in rows: print(f"   {f(x[0])} {x[1]:4d} {x[2]:4d} {x[3]:4d} {x[4]:4d} {x[5]:4d} | {x[6]} {x[7]} {x[8]} | {x[9] if x[9] is None else round(x[9],4)} {x[10] if x[10] is None else round(x[10],3)}")
print("  means: 450 passing %.1f | replay-style nsel %.1f | top400 in 450 %.1f | outside-450 passing %.1f | live sel %.1f | producer-cache gate on live members %.1f | meta-qvk gate on live members %.1f" % tuple(np.mean([x[k] for x in rows if x[k] is not None]) for k in (1, 3, 4, 5, 6, 7, 8)))
print("\n== 3. ONGUSDT diagnostics ==")
print("  when | rate4h bps | fund rank z(829) | king pinned z | qvk rank | y4ok | replay sel? | w live | w V1 | w deployed(FTRIM) | w m1t400")
for N in OV:
    a = INP["anchors"][str(N)]; qvk = np.array(a["qvk"], float); y4ok = np.array(a["y4ok"], bool); slow = np.array(a["slow"], float); i = prow[N]
    rk = np.empty(NW, int); rk[np.argsort(-qvk)] = np.arange(NW); qv4h = np.expm1(np.clip(qvk, 0, 30)) * 48
    ok = np.isfinite(slow); zk = np.full(NW, np.nan); zk[ok] = rankdata(slow[ok]) / (ok.sum() - 1) - 0.5
    okf = np.isfinite(FE[i]); zf = np.full(NW, np.nan); zf[okf] = rankdata(FE[i][okf]) / (okf.sum() - 1) - 0.5
    tl = vec(f"{WS}/state/target_live/{N}.json"); g = lambda w: w[jO] / np.abs(w).sum()
    print(f"   {f(N)} {rates(N)[jO]*1e4:+8.2f} {zf[jO]:+.3f} {zk[jO]:+.3f} {rk[jO]:4d} {int(y4ok[jO])} {int(y4ok[jO] and qv4h[jO] >= 2.5e5 and rk[jO] < 400)} {g(tl):+.5f} {g(W('V1_live_w3fix_noftrim', N)):+.5f} {g(W('live_w3fix_ftrim', N)):+.5f} {g(W('m1t400_dyn_noftrim', N)):+.5f}")
# producer-side ONG history: weight in target_live from the first file
print("  live ONG weight/gross history (target_live, all anchors):", " ".join(f"{f(N)}:{vec(f'{WS}/state/target_live/{N}.json')[jO]/np.abs(vec(f'{WS}/state/target_live/{N}.json')).sum():+.4f}" for N in sorted(int(x[:-5]) for x in os.listdir(f"{WS}/state/target_live") if x.endswith('.json') and x[:-5].isdigit())[::3]))

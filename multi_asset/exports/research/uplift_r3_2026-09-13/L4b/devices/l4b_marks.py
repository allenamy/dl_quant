#!/usr/bin/env python3
"""l4b_marks.py -- L4b step 2 (pod2, CPU only). Implements PREREG_L4b_executable_marks_2026-09-13.md (sha256 bd7ad1e4..., frozen 2026-09-13T12:28:31Z,
commit ff41b981) sections 2, 4, 5 (G-L4REPRO, G-HARNESS, G-B1REPRO, G-PREMPARSE, G-SYN2), 6 (R1-R3) and 7 (F2 N and survival).
Inputs (sha asserted): L4 committed core (l4_run.py), L4 inputs and series, FEAS_L4b.json, RECEIPT_L4b_pull.json (G-ARCHIVE must be PASS) and the
per-symbol anchor/minute files it lists (sha per file). Gates run before any mark is printed; a failed gate stops the run (exit 4).
Writes <out>/RECEIPT_L4b_marks.json, <out>/L4b_F2_SERIES.npz; prints one SUMMARY line.
Usage: python3 l4b_marks.py <env_whitelist_csv> <L4_work_dir> <l4_run.py> <L4b_work_dir>
"""
import os, sys, json, time, math, hashlib, calendar
WHITE = set(x for x in sys.argv[1].split(",") if x); assert WHITE, "non-empty env whitelist required"
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
L4W, RUNDEV, W = [os.path.abspath(x) for x in sys.argv[2:5]]
assert W.startswith("/workspace/uplift_r3_2026-09-13/L4b/"), W
import numpy as np
T_START = time.time()
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def ut(y, m, d, h=0, mi=0): return calendar.timegm((y, m, d, h, mi, 0))
def iso(t): return None if t is None or t < 0 else time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def fl(x): return None if x is None or (isinstance(x, float) and not math.isfinite(x)) else float(x)
PREREG_SHA = "bd7ad1e45be81647ce923e1117ca533439266edd8de4614946b52b8cd70e5586"
KNOWN = dict(run="cfa2517120979a46881eae42e4968a34a8d529e8fc817a0a54e16e45a0fc8a22", inputs="3d9d3466ce0078730c3630876d3767ba69da0135cfad9edf42fbfe59bfce05dd",
             series="8ba4ba1fa6220d9763443a920ea37a9abcba0536f55954a6d5d7fa05c2bb4473")
got = dict(run=sha(RUNDEV), inputs=sha(os.path.join(L4W, "l4_inputs.npz")), series=sha(os.path.join(L4W, "L4_SERIES.npz")))
assert got == KNOWN, ("L4 input sha mismatch", got)
PR = json.load(open(os.path.join(W, "RECEIPT_L4b_pull.json"))); assert PR["gates"]["G-ARCHIVE"]["pass_"] is True and PR["prereg_sha256"] == PREREG_SHA
FEAS = json.load(open(os.path.join(W, "FEAS_L4b.json"))); assert sha(os.path.join(W, "FEAS_L4b.json")) == PR["feas_sha256"]
for perp, o in PR["outputs"].items(): assert sha(os.path.join(W, "sym", perp + ".npz")) == o["sha256"], perp
REC = dict(device="l4b_marks.py", device_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, run_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           l4_inputs=got, pull_receipt_sha256=sha(os.path.join(W, "RECEIPT_L4b_pull.json")), python=sys.version.split()[0], numpy=np.__version__,
           affinity=sorted(os.sched_getaffinity(0)), env_actual={k: os.environ[k] for k in sorted(os.environ)}, gates={})
assert len(REC["affinity"]) <= 8
print("CONFIG " + json.dumps(dict(self_sha256=REC["device_sha256"], prereg=PREREG_SHA, l4=got)), flush=True)

# ---------------------------------------------------------------- L4 core (exec of the committed constants/core section)
src = open(RUNDEV).read(); a_ = src.index("# ---------------------------------------------------------------- constants"); b_ = src.index("# ---------------------------------------------------------------- G-SYN")
NS_ = {"np": np, "math": math, "REC": {"gates": {}}}; exec(compile(src[a_:b_], "l4_run_core", "exec"), NS_)
ARMS = NS_["ARMS"][:8]; CP = NS_["CP"]; CS = NS_["CS_BASE"]; M = NS_["M"]; ANN = math.sqrt(2190.0); H4 = 14400
STRESS_STOP = 0.10; STRESS_CONT = 0.005; STALE = 3600; STOPGAP = 20 * 3600
Zf = np.load(os.path.join(L4W, "l4_inputs.npz"), allow_pickle=True); Z = {k: Zf[k] for k in Zf.files}; SER = np.load(os.path.join(L4W, "L4_SERIES.npz"))
EG = Z["EG"].astype(np.int64); SYM = [str(s) for s in Z["SYM"]]; kof = {s: k for k, s in enumerate(SYM)}; iW0 = int(Z["iW0"]); iW1 = int(Z["iW1"]); gi = {int(t): i for i, t in enumerate(EG)}
A = Z["A"].astype(np.float64); NEV = Z["NEV"]; B1 = Z["B1"].astype(np.float64); B2 = Z["B2"].astype(np.float64)
D = NS_["prepare"](A, NEV.astype(np.int16), Z["ELIG"].astype(bool), Z["TRAD"].astype(bool), Z["SPOT_OK"].astype(bool), B2, B1)
TW = iW1 - iW0 + 1; TSW = EG[iW0:iW1 + 1]
NFALLBACK = [0]
import gzip
FUND = "/workspace/fund_aug.json.gz"; assert sha(FUND) == "8a9e771577602dd1875a87fb07f982bc2c255e740966f911469420a44a53a8c2"
_pf_syms = set(h["sym"] for h in FEAS["holds"] if h["reason"] in ("forced_a", "forced_b"))
FEV = {}
for s_, rows_ in json.load(gzip.open(FUND, "rt"))["rates"].items():
    if s_ not in _pf_syms: continue
    tt_ = np.array([r[0] for r in rows_], np.int64) // 1000; FEV[s_] = ((tt_ // 3600) * 3600, np.array([r[1] for r in rows_], np.float64))
for s_, (evS_, evR_) in FEV.items():            # sanity: window sums of the event table equal L4's A on every window of the symbol
    k_ = kof[s_]; j_ = (evS_ - int(EG[0]) - 1) // H4; ok_ = (evS_ > int(EG[0])) & (j_ >= 0) & (j_ < len(EG)); acc_ = np.zeros(len(EG)); np.add.at(acc_, j_[ok_], evR_[ok_])
    assert np.abs(acc_ - A[:, k_]).max() <= 1e-12, ("fund event table != L4 A", s_)

# ---------------------------------------------------------------- G-L4REPRO + hold list
SIM = {}; HOLDS = []; eq = {}
for arm in ARMS:
    POS, hl, oh = NS_["simulate"](arm, D, iW0, iW1); acc = NS_["account"](POS, D, iW0, arm["K"], CS); SIM[arm["id"]] = (POS, acc)
    eq[arm["id"]] = bool(np.array_equal(acc["net"], SER["%s_net" % arm["id"]]))
    for (k, t0, t1, why) in hl + oh:
        HOLDS.append(dict(arm=arm["id"], K=arm["K"], k=k, sym=SYM[k], t0=t0, t1=t1, reason=why, entry_ts=int(EG[iW0 + t0]), exit_ts=(int(EG[iW0 + t1]) if t1 is not None else None)))
feas_keys = sorted((h["arm"], h["sym"], h["entry_ts"], h["exit_ts"] if h["exit_ts"] is not None else -1, h["reason"]) for h in FEAS["holds"])
my_keys = sorted((h["arm"], h["sym"], h["entry_ts"], h["exit_ts"] if h["exit_ts"] is not None else -1, h["reason"]) for h in HOLDS)
G_L4 = bool(all(eq.values()) and feas_keys == my_keys)
REC["gates"]["G-L4REPRO"] = dict(pass_=G_L4, series_equal=eq, holds=len(HOLDS), holds_equal_feas=feas_keys == my_keys)
print("G-L4REPRO %s holds=%d" % (G_L4, len(HOLDS)), flush=True)
if not G_L4: json.dump(REC, open(os.path.join(W, "RECEIPT_L4b_marks.json"), "w"), indent=1); sys.exit(4)

# ---------------------------------------------------------------- per-symbol anchor values and P_F minute stores
MAP = {}
for h in FEAS["holds"]: MAP[h["sym"]] = (h["spot"], float(h["price_mult"]))
ANCOLS = ("S", "tS", "P", "tP", "MARK", "tMARK", "INDEX", "tINDEX", "PREM", "tPREM", "S5", "tS5", "P5", "tP5", "SN", "tSN", "PN", "tPN")
ANC = {}; MIN = {}
for perp in PR["outputs"]:
    S_ = np.load(os.path.join(W, "sym", perp + ".npz"), allow_pickle=True); nseg = int(S_["n_seg"])
    rows = {}
    for q in range(nseg):
        E = S_["seg%d_a_E" % q].astype(np.int64)
        colv = [S_["seg%d_a_%s" % (q, c)].astype(np.float64) for c in ANCOLS]
        stack = np.stack(colv, 1)
        for i, t in enumerate(E):
            rows[int(t)] = tuple(stack[i].tolist())
        if bool(S_["is_pf"]):
            MIN.setdefault(perp, []).append(dict(s0=int(S_["seg%d_s0" % q]), **{c: S_["seg%d_m_%s" % (q, c)] for c in ("spot_close", "spot_cnt", "perp_close", "perp_cnt", "mark_close", "index_close", "premium_close")}))
    ANC[perp] = rows
COL = {c: i for i, c in enumerate(ANCOLS)}
def av(perp, E, c):
    r = ANC.get(perp, {}).get(int(E)); return float("nan") if r is None else r[COL[c]]

# ---------------------------------------------------------------- M-EXEC calculator (PREREG section 4) -- pure functions used by both real data and G-SYN2
def minute_series(perp):
    """concatenated minute arrays for a P_F symbol: returns dict of arrays indexed by absolute minute start times."""
    segs = MIN[perp]; out = {}
    for c in ("spot_close", "spot_cnt", "perp_close", "perp_cnt", "index_close", "premium_close", "mark_close"):
        out[c] = np.concatenate([s[c] for s in segs])
    out["t"] = np.concatenate([s["s0"] + 60 * np.arange(len(s["spot_close"]), dtype=np.int64) for s in segs])
    return out
def last_trade(ms, leg, t_end, t_lo=None):
    """(price, bar_end) of the latest traded minute of leg with bar end <= t_end (and bar start >= t_lo if given)."""
    tt = ms["t"]; c = ms[leg + "_close"]; n = ms[leg + "_cnt"]
    ok = (tt + 60 <= t_end) & (n > 0) & np.isfinite(c)
    if t_lo is not None: ok &= tt >= t_lo
    w = np.nonzero(ok)[0]
    if not len(w): return float("nan"), -1
    j = w[-1]; return float(c[j]), int(tt[j] + 60)
def first_trade_after(ms, leg, t0, t1):
    tt = ms["t"]; c = ms[leg + "_close"]; n = ms[leg + "_cnt"]
    w = np.nonzero((tt >= t0) & (tt + 60 <= t1) & (n > 0) & np.isfinite(c))[0]
    if not len(w): return float("nan"), -1
    j = w[0]; return float(c[j]), int(tt[j] + 60)
def exec_plan(h, variant, ms, SE, PE, E_out):
    """Exit plan for a P_F hold. SE/PE: (price, bar_end) of S(E_out), P(E_out). Returns dict with per-leg exit (price, time), stopped leg, flags."""
    E_in = h["entry_ts"]
    pS, tauS = last_trade(ms, "spot", E_out, E_in); pP, tauP = last_trade(ms, "perp", E_out, E_in)
    stopS = (tauS < 0) or (E_out - tauS >= STOPGAP); stopP = (tauP < 0) or (E_out - tauP >= STOPGAP)
    info = dict(tauS=tauS, tauP=tauP, stopS=bool(stopS), stopP=bool(stopP))
    if not stopS and not stopP:
        info.update(nostop=True, stopped=None, exit=dict(spot=(SE[0], E_out), perp=(PE[0], E_out)), stress=dict(spot=0.0, perp=0.0)); return info
    if stopS and stopP: stopped = "spot" if tauS <= tauP else "perp"
    else: stopped = "spot" if stopS else "perp"
    cont = "perp" if stopped == "spot" else "spot"; tau = tauS if stopped == "spot" else tauP; ptau = pS if stopped == "spot" else pP
    info.update(nostop=False, stopped=stopped, tau_stop=tau)
    if tau < 0:
        info.update(unpriceable_stop=True); return info
    st = dict(spot=0.0, perp=0.0)
    if variant in ("X1s1", "X2s1", "X3s1"): st[stopped] = STRESS_STOP; st[cont] = STRESS_CONT
    if variant == "X3s1" and stopped == "perp": st["perp"] = STRESS_CONT          # settlement at index TWAP x 1.005 (PREREG 4)
    if variant in ("X1s1", "X1s0"):
        pc, tc = last_trade(ms, cont, tau, E_in)
        if not (tc >= 0 and tau - tc <= STALE):
            pa, ta = first_trade_after(ms, cont, tau, tau + STALE + 60)
            if ta >= 0: pc, tc = pa, ta
        ex = {stopped: (ptau, tau), cont: (pc, tc)}; info.update(cont_stale_s=(tau - tc) if tc >= 0 else None)
    elif variant == "X2s1":
        ex = {stopped: (ptau, tau), cont: ((SE if cont == "spot" else PE)[0], E_out)}
    elif variant == "X3s1":
        if stopped == "spot":
            ix = ms["index_close"]; tt = ms["t"]; w = np.nonzero((tt + 60 <= E_out) & np.isfinite(ix))[0]
            ex = {"spot": ((float(ix[w[-1]]) if len(w) else float("nan")), E_out), "perp": (PE[0], E_out)}
        else:
            ix = ms["index_close"]; tt = ms["t"]; w = np.nonzero((tt + 60 <= tau) & (tt + 60 > tau - 1800) & np.isfinite(ix))[0]
            ex = {"perp": ((float(np.mean(ix[w])) if len(w) else float("nan")), tau), "spot": (SE[0], E_out)}
    info.update(exit=ex, stress=st, variant=variant); return info

def hold_increments(h, n, S0, P0, path_S, path_P, exit_plan, E_list):
    """Per-anchor basis increments (bps per unit capital) for anchors E_list[j] -> E_list[j+1] of a hold, buy-and-hold units.
    path_S/P: price at each anchor in E_list (last traded). exit_plan: None (exit at E_list[-1] marks) or dict with per-leg (price, time) and stress."""
    uS = n / S0; uP = n / P0; inc = np.zeros(len(E_list) - 1)
    if exit_plan is None or exit_plan.get("nostop"):
        V = uS * np.asarray(path_S) - uP * np.asarray(path_P); inc[:] = np.diff(V) * 1e4; return inc, float((V[-1] - V[0]) * 1e4)
    exS = exit_plan["exit"]["spot"]; exP = exit_plan["exit"]["perp"]; st = exit_plan["stress"]
    xS = exS[0] * (1.0 - st["spot"]); xP = exP[0] * (1.0 + st["perp"])
    def Vat(j):
        t = E_list[j]
        s_ = xS if t >= exS[1] else path_S[j]; p_ = xP if t >= exP[1] else path_P[j]
        return uS * s_ - uP * p_
    Vs = [Vat(j) for j in range(len(E_list))]
    t_final = max(exS[1], exP[1])
    # the anchor grid ends at the first anchor >= t_final (caller guarantees E_list[-1] >= t_final); value there uses exit prices
    for j in range(len(E_list) - 1): inc[j] = (Vs[j + 1] - Vs[j]) * 1e4
    total = (uS * (xS - S0) - uP * (xP - P0)) * 1e4
    return inc, float(total)

# ---------------------------------------------------------------- G-SYN2 (independent reference for the calculator)
def ref_hold_pnl(n, S0, P0, sx, px, s_st, p_st): return (n / S0 * (sx * (1 - s_st) - S0) - n / P0 * (px * (1 + p_st) - P0)) * 1e4
def syn_ms(t0, T, spot_stop=None, perp_stop=None):
    t = t0 + 60 * np.arange(T, dtype=np.int64)
    sc = 1.0 + 0.001 * np.arange(T); pc = 1.001 + 0.001 * np.arange(T)
    scnt = np.ones(T); pcnt = np.ones(T)
    if spot_stop is not None: scnt[t >= spot_stop] = 0
    if perp_stop is not None: pcnt[t >= perp_stop] = 0
    return dict(t=t, spot_close=sc, spot_cnt=scnt, perp_close=pc, perp_cnt=pcnt, index_close=0.999 + 0.001 * np.arange(T), premium_close=np.zeros(T), mark_close=pc.copy())
gs = []
t0 = ut(2025, 1, 1); T = 6 * 24 * 60
cases = [("both_trade", None, None), ("spot_stops", t0 + 2 * 86400 + 123 * 60, None), ("perp_stops", None, t0 + 3 * 86400 + 7 * 60), ("both_stop", t0 + 2 * 86400, t0 + 2 * 86400 + 600 * 60)]
for name, ss, ps in cases:
    ms = syn_ms(t0, T, ss, ps); h = dict(entry_ts=t0 + 4 * 3600); E_out = t0 + 5 * 86400; n = 1 / 15.0
    SE = last_trade(ms, "spot", E_out, h["entry_ts"]); PE = last_trade(ms, "perp", E_out, h["entry_ts"])
    S0, _ = last_trade(ms, "spot", h["entry_ts"]); P0, _ = last_trade(ms, "perp", h["entry_ts"])
    for var in ("X1s1", "X1s0", "X2s1", "X3s1"):
        plan = exec_plan(h, var, ms, SE, PE, E_out)
        E_list = list(range(h["entry_ts"], E_out + 1, H4))
        path_S = [last_trade(ms, "spot", e)[0] for e in E_list]; path_P = [last_trade(ms, "perp", e)[0] for e in E_list]
        inc, tot = hold_increments(h, n, S0, P0, path_S, path_P, plan, E_list)
        # reference: independent closed form from the spec
        if name == "both_trade":
            exp_tot = ref_hold_pnl(n, S0, P0, SE[0], PE[0], 0, 0); exp_stop = None
        else:
            # stopped leg and last prints by direct index arithmetic
            idxS = (min(ss, E_out) - t0) // 60 - 1 if ss is not None else None; idxP = (min(ps, E_out) - t0) // 60 - 1 if ps is not None else None
            lastS = (1.0 + 0.001 * idxS, t0 + 60 * idxS + 60) if ss is not None else (SE[0], SE[1]); lastP = (1.001 + 0.001 * idxP, t0 + 60 * idxP + 60) if ps is not None else (PE[0], PE[1])
            stopped = "spot" if (ss is not None and (ps is None or lastS[1] <= lastP[1])) else "perp"
            tau = lastS[1] if stopped == "spot" else lastP[1]
            sst, pst = ((0.10, 0.005) if stopped == "spot" else (0.005, 0.10)) if var != "X1s0" else (0.0, 0.0)
            if var == "X3s1" and stopped == "perp": sst, pst = 0.005, 0.005
            if var in ("X1s1", "X1s0"):
                j = (tau - 60 - t0) // 60
                if stopped == "spot": sx, px = lastS[0], (1.001 + 0.001 * j if ps is None or tau <= ps else lastP[0])
                else: px, sx = lastP[0], (1.0 + 0.001 * j if ss is None or tau <= ss else lastS[0])
            elif var == "X2s1":
                if stopped == "spot": sx, px = lastS[0], PE[0]
                else: px, sx = lastP[0], SE[0]
            else:
                if stopped == "spot": sx, px = 0.999 + 0.001 * ((E_out - 60 - t0) // 60), PE[0]
                else:
                    jj = np.arange((tau - 1800 - t0) // 60, (tau - 60 - t0) // 60 + 1); px, sx = float(np.mean(0.999 + 0.001 * jj)), SE[0]
            exp_tot = ref_hold_pnl(n, S0, P0, sx, px, sst, pst); exp_stop = stopped
        ok_sum = abs(inc.sum() - tot) <= 1e-9 and abs(tot - exp_tot) <= 1e-9
        ok_stop = (exp_stop is None and plan.get("nostop")) or (plan.get("stopped") == exp_stop)
        gs.append(dict(case=name, variant=var, total=tot, expected=exp_tot, telescoped_ok=bool(abs(inc.sum() - tot) <= 1e-9), total_ok=bool(abs(tot - exp_tot) <= 1e-9), stopped_ok=bool(ok_stop)))
# microsecond timestamp and stale-entry checks on the minute-level helpers
ms = syn_ms(t0, 600); ms["spot_cnt"][:230] = 0
pe, te = last_trade(ms, "spot", t0 + 200 * 60); pa, ta = first_trade_after(ms, "spot", t0 + 200 * 60, t0 + 200 * 60 + STALE + 60)
pz, tz = first_trade_after(ms, "spot", t0 + 100 * 60, t0 + 100 * 60 + STALE + 60)      # first trade 130 min later: outside the 60-min window
gs.append(dict(case="stale_entry_fallback", variant="-", total_ok=bool(np.isnan(pe) and te == -1 and ta == t0 + 231 * 60 and abs(pa - (1.0 + 0.001 * 230)) < 1e-12 and np.isnan(pz) and tz == -1), telescoped_ok=True, stopped_ok=True))
G_SYN2 = all(g["telescoped_ok"] and g["total_ok"] and g["stopped_ok"] for g in gs)
REC["gates"]["G-SYN2"] = dict(pass_=bool(G_SYN2), cases=gs)
print("G-SYN2 %s cases=%d fails=%s" % (G_SYN2, len(gs), [g for g in gs if not (g["telescoped_ok"] and g["total_ok"] and g["stopped_ok"])][:3]), flush=True)
if not G_SYN2: json.dump(REC, open(os.path.join(W, "RECEIPT_L4b_marks.json"), "w"), indent=1); sys.exit(4)

# ---------------------------------------------------------------- population P_F and matched controls P_C (PREREG 2)
PF = [h for h in HOLDS if h["reason"] in ("forced_a", "forced_b")]
PF.sort(key=lambda h: (h["exit_ts"], kof[h["sym"]], h["entry_ts"]))
used = {a["id"]: set() for a in ARMS}; PC = []
for h in PF:
    cands = [c for c in HOLDS if c["arm"] == h["arm"] and c["reason"] == "normal" and c["sym"] != h["sym"] and (c["sym"], c["entry_ts"]) not in used[h["arm"]]]
    L0 = (h["exit_ts"] - h["entry_ts"]) // H4
    cands.sort(key=lambda c: (abs(c["exit_ts"] - h["exit_ts"]), abs((c["exit_ts"] - c["entry_ts"]) // H4 - L0), kof[c["sym"]], c["entry_ts"]))
    for c in cands[:2]:
        used[h["arm"]].add((c["sym"], c["entry_ts"])); PC.append(dict(c, control_for=(h["sym"], h["entry_ts"], h["exit_ts"])))
REC["population"] = dict(P_F=len(PF), P_C=len(PC))

# ---------------------------------------------------------------- gates on data alignment: G-B1REPRO, G-PREMPARSE
b1c = []; b1_bad = []
for h in PF + PC:
    t_end = h["exit_ts"]
    for i in range(gi[h["entry_ts"]], gi[t_end] + 1):
        E = int(EG[i]); l4 = B1[i, h["k"]]
        if not np.isfinite(l4): continue
        s5 = av(h["sym"], E, "S5"); p5 = av(h["sym"], E, "P5"); ts5 = av(h["sym"], E, "tS5"); tp5 = av(h["sym"], E, "tP5")
        if not (np.isfinite(s5) and np.isfinite(p5)) or (E - 300 - ts5) > STALE or (E - 300 - tp5) > STALE: continue
        d = abs((p5 / s5 - 1.0) - l4); b1c.append(d)
        if d > 1e-6 and len(b1_bad) < 50: b1_bad.append(dict(sym=h["sym"], E=iso(E), recon=p5 / s5 - 1.0, l4=l4))
b1c = np.array(b1c); share_b1 = float((b1c <= 1e-6).mean()) if len(b1c) else float("nan")
G_B1 = bool(len(b1c) > 1000 and share_b1 >= 0.99)
REC["gates"]["G-B1REPRO"] = dict(pass_=G_B1, cells=int(len(b1c)), share_within_1e6=share_b1, max_abs=float(b1c.max()) if len(b1c) else None, examples=b1_bad)
pp = []; pb = []
for h in PF:
    for i in range(gi[h["entry_ts"]] + 1, gi[h["exit_ts"]] + 1):
        E = int(EG[i]); v = B2[i, h["k"]]; vp = B2[i - 1, h["k"]]
        if not (np.isfinite(v) and np.isfinite(vp)) or v == vp: continue
        pr = av(h["sym"], E, "PREM")
        if not np.isfinite(pr): continue
        pp.append(abs(pr - v))
        if abs(pr - v) > 1e-7 and len(pb) < 50: pb.append(dict(sym=h["sym"], E=iso(E), prem_1m=pr, b2=v))
pp = np.array(pp); share_p = float((pp <= 1e-7).mean()) if len(pp) else float("nan")
G_PREM = bool(len(pp) > 100 and share_p >= 0.95)
REC["gates"]["G-PREMPARSE"] = dict(pass_=G_PREM, cells=int(len(pp)), share_within_1e7=share_p, examples=pb)
print("G-B1REPRO %s cells=%d share=%.4f | G-PREMPARSE %s cells=%d share=%.4f" % (G_B1, len(b1c), share_b1, G_PREM, len(pp), share_p), flush=True)

# ---------------------------------------------------------------- F2 harness: per-anchor series for A01..A08 under a mark function
VARIANTS = ("X1s1", "X1s0", "X2s1", "X3s1")
MSC = {}
def ms_for(perp):
    if perp not in MSC: MSC[perp] = minute_series(perp)
    return MSC[perp]
def build_series(arm, mode, variant=None, zero_flagged=None):
    """mode 'B2': L4 increments (harness check). mode 'EXEC': M-EXEC per PREREG 4."""
    POS, acc = SIM[arm["id"]]; n = 1.0 / (arm["K"] * (1.0 + M))
    inc = acc["inc"].copy(); cost = acc["cost"].copy(); bas = np.zeros(TW); unp = 0; flags = []; per_hold = []
    for h in [x for x in HOLDS if x["arm"] == arm["id"]]:
        t0_, t1_ = h["t0"], (h["t1"] if h["t1"] is not None else TW)
        k = h["k"]
        if mode == "B2":
            dB = D["B2F"][iW0 + t0_:iW0 + t1_, k] - D["B2F"][iW0 + t0_ + 1:iW0 + t1_ + 1, k]
            bas[t0_:t1_] += n * 1e4 * dB; continue
        E_list = [int(EG[iW0 + t]) for t in range(t0_, t1_ + 1)]
        S0 = av(h["sym"], E_list[0], "S"); P0 = av(h["sym"], E_list[0], "P")
        tS0 = av(h["sym"], E_list[0], "tS"); tP0 = av(h["sym"], E_list[0], "tP")
        is_pf = h["reason"] in ("forced_a", "forced_b")
        if not (np.isfinite(S0) and E_list[0] - tS0 <= STALE and np.isfinite(P0) and E_list[0] - tP0 <= STALE):
            if not (np.isfinite(S0) and E_list[0] - tS0 <= STALE): S0 = av(h["sym"], E_list[0], "SN"); NFALLBACK[0] += 1
            if not (np.isfinite(P0) and E_list[0] - tP0 <= STALE): P0 = av(h["sym"], E_list[0], "PN"); NFALLBACK[0] += 1
            if not (np.isfinite(S0) and np.isfinite(P0)):
                unp += 1
                dB = D["B2F"][iW0 + t0_:iW0 + t1_, k] - D["B2F"][iW0 + t0_ + 1:iW0 + t1_ + 1, k]; bas[t0_:t1_] += n * 1e4 * dB
                per_hold.append(dict(sym=h["sym"], entry=h["entry_ts"], exit=h["exit_ts"], reason=h["reason"], exec_pnl=None, unpriceable=True)); continue
        path_S = [av(h["sym"], e, "S") for e in E_list]; path_P = [av(h["sym"], e, "P") for e in E_list]
        path_S[0] = S0; path_P[0] = P0
        for j in range(1, len(E_list)):                     # carry the last known price where an anchor value is missing
            if not np.isfinite(path_S[j]): path_S[j] = path_S[j - 1]
            if not np.isfinite(path_P[j]): path_P[j] = path_P[j - 1]
        plan = None
        if is_pf and h["t1"] is not None:
            ms = ms_for(h["sym"]); E_out = E_list[-1]
            plan = exec_plan(h, variant, ms, (path_S[-1], E_out), (path_P[-1], E_out), E_out)
            bad = bool(plan.get("unpriceable_stop")) or any(not np.isfinite(plan["exit"][lg][0]) for lg in ("spot", "perp"))
            if bad:
                unp += 1; dB = D["B2F"][iW0 + t0_:iW0 + t1_, k] - D["B2F"][iW0 + t0_ + 1:iW0 + t1_ + 1, k]; bas[t0_:t1_] += n * 1e4 * dB
                per_hold.append(dict(sym=h["sym"], entry=h["entry_ts"], exit=h["exit_ts"], reason=h["reason"], exec_pnl=None, unpriceable=True)); continue
        hi, tot = hold_increments(h, n, S0, P0, path_S, path_P, plan, E_list)
        if zero_flagged is not None and (h["sym"], h["entry_ts"]) in zero_flagged: hi = hi * 0.0; tot = 0.0
        bas[t0_:t1_] += hi
        if plan is not None and not plan.get("nostop"):
            # income and cost timing: income only for events up to the perp leg's exit time; exit cost booked in the window containing the last leg exit
            t_perp = plan["exit"]["perp"][1]
            evS, evR = FEV.get(h["sym"], (np.zeros(0, np.int64), np.zeros(0)))
            for t in range(t0_, t1_):
                lo_, hi_ = int(EG[iW0 + t]), int(EG[iW0 + t]) + H4
                if hi_ <= t_perp: continue
                sel = (evS > max(lo_, t_perp)) & (evS <= hi_)
                inc[t] -= n * 1e4 * float(evR[sel].sum())
            t_last = max(plan["exit"]["spot"][1], plan["exit"]["perp"][1]); tx = min(max(int((t_last - int(EG[iW0 + t0_]) - 1) // H4) + t0_, t0_), t1_ - 1)
            exit_cost = (CP + CS) * n
            cost[t1_] -= exit_cost if t1_ < TW else 0.0
            cost[tx] += exit_cost if t1_ < TW else 0.0
        per_hold.append(dict(sym=h["sym"], entry=h["entry_ts"], exit=h["exit_ts"], reason=h["reason"], exec_pnl=tot, plan=({k_: v_ for k_, v_ in plan.items() if k_ not in ("exit",)} if plan else None),
                             exit_prices=({lg: [plan["exit"][lg][0], plan["exit"][lg][1]] for lg in ("spot", "perp")} if plan and "exit" in plan else None), S0=S0, P0=P0, S_out=path_S[-1], P_out=path_P[-1]))
    net = inc + bas - cost
    return dict(net=net, inc=inc, bas=bas, cost=cost, unpriceable=unp, holds=per_hold)
harn = {}
for arm in ARMS:
    s_ = build_series(arm, "B2"); harn[arm["id"]] = float(np.abs(s_["net"] - SER["%s_net" % arm["id"]]).max())
G_H = all(v <= 1e-9 for v in harn.values())
REC["gates"]["G-HARNESS"] = dict(pass_=bool(G_H), max_abs_by_arm=harn)
print("G-HARNESS %s %s" % (G_H, json.dumps(harn)), flush=True)
ALLG = G_L4 and G_SYN2 and G_B1 and G_PREM and G_H
if not ALLG:
    json.dump(REC, open(os.path.join(W, "RECEIPT_L4b_marks.json"), "w"), indent=1, default=str); print("SUMMARY l4b_marks GATES FAIL %s" % {k: v["pass_"] for k, v in REC["gates"].items()}); sys.exit(4)
print("ALL L4b GATES PASS; marks follow %.0fs" % (time.time() - T_START), flush=True)

# ---------------------------------------------------------------- F2 series, all variants
F2 = {}
for arm in ARMS:
    F2[arm["id"]] = {v: build_series(arm, "EXEC", v) for v in VARIANTS}
print("F2 built %.0fs" % (time.time() - T_START), flush=True)

# ---------------------------------------------------------------- R1 per event (P_F) and R2 controls
def mclose_prem(h, n):
    i0 = gi[h["entry_ts"]]; i1 = gi[h["exit_ts"]]; k = h["k"]
    return (n * 1e4 * (D["B2F"][i0, k] - D["B2F"][i1, k]), n * 1e4 * (D["B1F"][i0, k] - D["B1F"][i1, k]) if np.isfinite(D["B1F"][i0, k]) and np.isfinite(D["B1F"][i1, k]) else None)
def hold_record(h, arm, v):
    for r in F2[arm["id"]][v]["holds"]:
        if r["sym"] == h["sym"] and r["entry"] == h["entry_ts"]: return r
    return None
def blowout(h, t_stop):
    ms = ms_for(h["sym"]) if h["sym"] in MIN else None
    best = None; peak = 0.0
    for i in range(gi[h["entry_ts"]] + 1, gi[h["exit_ts"]] + 1):
        E = int(EG[i])
        if t_stop is not None and E > t_stop + H4: break
        s = av(h["sym"], E, "S"); p = av(h["sym"], E, "P"); ts = av(h["sym"], E, "tS"); tp = av(h["sym"], E, "tP")
        if np.isfinite(s) and np.isfinite(p) and E - ts <= STALE and E - tp <= STALE:
            b = abs(p / s - 1.0); peak = max(peak, b)
            if best is None and b >= 0.05: best = E
    return best, peak
def prem_frozen_run(h):
    if h["sym"] not in MIN: return None
    ms = ms_for(h["sym"]); w = (ms["t"] >= h["exit_ts"] - 7 * 86400) & (ms["t"] + 60 <= h["exit_ts"]) & np.isfinite(ms["premium_close"])
    v = ms["premium_close"][w]
    if not len(v): return None
    run = best = 1
    for j in range(1, len(v)):
        run = run + 1 if v[j] == v[j - 1] else 1; best = max(best, run)
    return int(best)
def discontinuity(h):
    if h["sym"] not in MIN: return None
    ms = ms_for(h["sym"]); w = (ms["t"] >= h["entry_ts"]) & (ms["t"] + 60 <= h["exit_ts"])
    out = []
    for leg, oth in (("spot", "perp"), ("perp", "spot")):
        c = ms[leg + "_close"][w]; n_ = ms[leg + "_cnt"][w]; co = ms[oth + "_close"][w]; no = ms[oth + "_cnt"][w]
        ix = np.nonzero((n_ > 0) & np.isfinite(c))[0]
        for a0, a1 in zip(ix[:-1], ix[1:]):
            r = c[a1] / c[a0]
            if r < 0.2 or r > 5:
                io = np.nonzero((no[:a1 + 1] > 0) & np.isfinite(co[:a1 + 1]))[0]; io0 = np.nonzero((no[:a0 + 1] > 0) & np.isfinite(co[:a0 + 1]))[0]
                if len(io) and len(io0):
                    ro = co[io[-1]] / co[io0[-1]]
                    if 0.8 <= ro <= 1.25: out.append(dict(leg=leg, t=iso(int(ms["t"][w][a1])), ratio=float(r)))
    return out
events = {}
for h in PF:
    arm = [a for a in ARMS if a["id"] == h["arm"]][0]; n = 1.0 / (arm["K"] * 1.5)
    key = (h["sym"], h["entry_ts"], h["exit_ts"])
    prem, close_ = mclose_prem(h, n)
    rec_v = {v: hold_record(h, arm, v) for v in VARIANTS}
    r1 = rec_v["X1s1"]; plan = r1.get("plan") if r1 else None
    t_stop = plan.get("tau_stop") if plan else None
    bo, peak = blowout(h, t_stop)
    ev = events.setdefault(key, dict(sym=h["sym"], spot=MAP[h["sym"]][0], reason=h["reason"], entry=iso(h["entry_ts"]), exit=iso(h["exit_ts"]),
                                     tau_spot=iso(plan.get("tauS")) if plan else None, tau_perp=iso(plan.get("tauP")) if plan else None,
                                     stopped=(plan.get("stopped") if plan else None), nostop=(plan.get("nostop") if plan else None),
                                     gap_h=(round((h["exit_ts"] - plan["tau_stop"]) / 3600, 1) if plan and plan.get("tau_stop") else None),
                                     b2_exit_bps=fl(B2[gi[h["exit_ts"]], h["k"]] * 1e4), b1_exit_bps=fl(B1[gi[h["exit_ts"]], h["k"]] * 1e4),
                                     exec_exit={v: (rec_v[v]["exit_prices"] if rec_v[v] else None) for v in VARIANTS},
                                     blowout=iso(bo) if bo else None, peak_abs_basis_bps=round(peak * 1e4, 1), prem_1m_longest_identical_run_last7d=prem_frozen_run(h),
                                     discontinuities=discontinuity(h), mark_index_present=bool(h["sym"] in MIN and np.isfinite(ms_for(h["sym"])["index_close"]).any()),
                                     announcement="PENDING L3", arms={}))
    ev["arms"][h["arm"]] = dict(n=n, M_PREM=prem, M_CLOSE=close_, **{"M_EXEC_" + v: (rec_v[v]["exec_pnl"] if rec_v[v] else None) for v in VARIANTS},
                                income_L4=float(n * 1e4 * A[gi[h["entry_ts"]]:gi[h["exit_ts"]], h["k"]].sum()), cost_L4=float(2 * (CP + CS) * n))
ctl = []
for h in PC:
    arm = [a for a in ARMS if a["id"] == h["arm"]][0]; n = 1.0 / (arm["K"] * 1.5)
    prem, close_ = mclose_prem(h, n); r = hold_record(h, arm, "X1s1")
    ctl.append(dict(arm=h["arm"], sym=h["sym"], entry=iso(h["entry_ts"]), exit=iso(h["exit_ts"]), M_PREM=prem, M_CLOSE=close_, M_EXEC=(r["exec_pnl"] if r else None)))
def agree(rows, key_a, key_b):
    x = [(r[key_a], r[key_b]) for r in rows if r[key_a] is not None and r[key_b] is not None]
    if len(x) < 3: return None
    a_ = np.array([u for u, _ in x]); b__ = np.array([v for _, v in x])
    from scipy import stats as st_
    return dict(n=len(x), median_abs_diff=float(np.median(np.abs(a_ - b__))), spearman=float(st_.spearmanr(a_, b__).statistic), sum_a=float(a_.sum()), sum_b=float(b__.sum()))
pf_rows = [dict(M_PREM=v["M_PREM"], M_CLOSE=v["M_CLOSE"], M_EXEC=v["M_EXEC_X1s1"]) for e in events.values() for v in e["arms"].values()]
R2 = dict(controls=dict(exec_vs_close=agree(ctl, "M_EXEC", "M_CLOSE"), exec_vs_prem=agree(ctl, "M_EXEC", "M_PREM"), close_vs_prem=agree(ctl, "M_CLOSE", "M_PREM")),
          forced=dict(exec_vs_close=agree(pf_rows, "M_EXEC", "M_CLOSE"), exec_vs_prem=agree(pf_rows, "M_EXEC", "M_PREM"), close_vs_prem=agree(pf_rows, "M_CLOSE", "M_PREM")))

# ---------------------------------------------------------------- R3 F2 readings and survival (PREREG 6, 7)
SPANS = dict(Y22=(ut(2022, 1, 31), ut(2023, 1, 1)), Y23=(ut(2023, 1, 1), ut(2024, 1, 1)), Y24=(ut(2024, 1, 1), ut(2025, 1, 1)), Y25=(ut(2025, 1, 1), ut(2026, 1, 1)),
             Y26=(ut(2026, 1, 1), ut(2026, 8, 30, 20) + 1), S2426=(ut(2024, 1, 1), ut(2026, 8, 30, 20) + 1), FULL=(ut(2022, 1, 31), ut(2026, 8, 30, 20) + 1))
SCODE = dict(Y22=22, Y23=23, Y24=24, Y25=25, Y26=26, S2426=2426, FULL=1)
SM = {k: (TSW >= lo) & (TSW < hi) for k, (lo, hi) in SPANS.items()}; DAY = TSW // 86400
a42 = 2.0 * Z["A0_G42"].astype(np.float64); a27 = 2.0 * Z["A0_G2027"].astype(np.float64)
def sharpe(x):
    s = x.std(ddof=1) if len(x) > 2 else 0.0
    return float(x.mean() / s * ANN) if s > 0 else float("nan")
def corr(x, y): return float(np.corrcoef(x, y)[0, 1]) if x.std() > 0 and y.std() > 0 else float("nan")
def daysums(x, mask):
    ud, inv = np.unique(DAY[mask], return_inverse=True); return np.bincount(inv, x[mask]), np.bincount(inv).astype(np.float64)
def boot_mean(x, mask, seed, qs):
    s, c = daysums(x, mask); nd = len(c); r = np.random.default_rng(seed); nb = -(-nd // 30)
    st = r.integers(0, nd, (20000, nb)); idx = ((st[:, :, None] + np.arange(30)[None, None, :]) % nd).reshape(20000, nb * 30)[:, :nd]
    mb = s[idx].sum(1) / c[idx].sum(1); return {("q%.4f" % p): float(np.percentile(mb, p)) for p in qs}
QS = (2.5, 97.5, 100 * 0.025 / 8, 100 * 0.025 / 20)
R3 = {}; SURV = {}
for ai, arm in enumerate(ARMS):
    aid = arm["id"]; POS, acc = SIM[aid]; npos = acc["npos"]; R3[aid] = {}
    for v in VARIANTS:
        s_ = F2[aid][v]; net = s_["net"]; tab = {}
        for sp, mk in SM.items():
            d = dict(net_mean=float(net[mk].mean()), sharpe=sharpe(net[mk]), bas_mean=float(s_["bas"][mk].mean()), inc_mean=float(s_["inc"][mk].mean()), cost_mean=float(s_["cost"][mk].mean()),
                     position_share=float((npos[mk] > 0).mean()))
            if v == "X1s1" or sp == "S2426": d["ci"] = boot_mean(net, mk, [20260913, 42, ai + 1, SCODE[sp], VARIANTS.index(v) + 1], QS)
            tab[sp] = d
        rho = {s: dict(per_anchor=corr(net, a), per_day=corr(daysums(net, SM["FULL"])[0], daysums(a, SM["FULL"])[0])) for s, a in (("42", a42), ("2027", a27))}
        R3[aid][v] = dict(table=tab, rho=rho, unpriceable_holds=s_["unpriceable"])
    t = R3[aid]["X1s1"]["table"]; rho = R3[aid]["X1s1"]["rho"]
    P0 = t["S2426"]["position_share"] >= 0.30
    P1 = all(t[y]["position_share"] < 0.30 or t[y]["net_mean"] > 0 for y in ("Y22", "Y23", "Y24", "Y25", "Y26"))
    P3 = all(math.isfinite(x) and x <= 0.30 for s in rho.values() for x in s.values())
    ci = t["S2426"]["ci"]; P2_8 = ci["q0.3125"] > 0; P2_un = ci["q2.5000"] > 0; P2_20 = ci["q0.1250"] > 0
    sens = all(R3[aid][v]["table"]["S2426"]["net_mean"] > 0 for v in ("X1s0", "X2s1", "X3s1"))
    SURV[aid] = dict(P0=bool(P0), P1=bool(P1), P2_bonf8=bool(P2_8), P2_unadj=bool(P2_un), P2_cum20=bool(P2_20), P3=bool(P3), sensitivities_S2426_positive=bool(sens),
                     survives=bool(P0 and P1 and P2_8 and P3 and sens), survives_unadj=bool(P0 and P1 and P2_un and P3 and sens), survives_cum20=bool(P0 and P1 and P2_20 and P3 and sens))
surv = [a for a, v in SURV.items() if v["survives"]]
# descriptive: discontinuity-flagged P_F holds zeroed (primary)
flagged = set((e["sym"], calendar.timegm(time.strptime(e["entry"], "%Y-%m-%dT%H:%MZ"))) for e in events.values() if e["discontinuities"])
R3_flag = {a["id"]: {sp: float(build_series(a, "EXEC", "X1s1", zero_flagged=flagged)["net"][mk].mean()) for sp, mk in (("S2426", SM["S2426"]), ("FULL", SM["FULL"]))} for a in ARMS} if flagged else None

REC.update(population=dict(P_F=len(PF), P_C=len(PC), unique_events=len(events)), events=list(events.values()), controls=ctl, R2=R2, R3=R3, F2_survival=SURV,
           F2_statement=("no arm survives" if not surv else "surviving arms: " + ", ".join(surv)), R3_flagged_zeroed=R3_flag, N_F2=8, cumulative_ledger=20,
           F3="NOT RUN at this step (conditional on L3 census; separate device)", elapsed_s=round(time.time() - T_START, 1))
ser = dict(TSW=TSW)
for a in ARMS:
    for v in VARIANTS:
        for c in ("net", "bas", "inc", "cost"): ser["%s_%s_%s" % (a["id"], v, c)] = F2[a["id"]][v][c]
np.savez_compressed(os.path.join(W, "L4b_F2_SERIES.npz"), **ser); REC["series_sha256"] = sha(os.path.join(W, "L4b_F2_SERIES.npz"))
json.dump(REC, open(os.path.join(W, "RECEIPT_L4b_marks.json"), "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print("SUMMARY l4b_marks gates=%s | P_F=%d P_C=%d events=%d | F2 %s | S2426 net X1s1 %s | elapsed=%.0fs self_sha256=%s" % (
    {k: v["pass_"] for k, v in REC["gates"].items()}, len(PF), len(PC), len(events), REC["F2_statement"],
    {a["id"]: round(R3[a["id"]]["X1s1"]["table"]["S2426"]["net_mean"], 4) for a in ARMS}, REC["elapsed_s"], REC["device_sha256"][:16]), flush=True)

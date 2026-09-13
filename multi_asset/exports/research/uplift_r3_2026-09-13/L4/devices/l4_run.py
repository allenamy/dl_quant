#!/usr/bin/env python3
"""l4_run.py -- L4 step 2 (pod2, CPU only). Implements PREREG_L4_carry_sleeve_hysteresis_2026-09-13.md (sha256 ced2f73f..., frozen
2026-09-13T11:24:12Z, commit deb3af82) + PREREG_AMENDMENT_1_L4_2026-09-13.md (entry also requires a funding event in the last 24h): section 2.6-2.7 state machine and accounting, section 3 arms, section 4 readings, section 5 frozen
pass rule and verdict, section 6 gates G-SYN, G-CAUSAL, G-ACCT. Reads only <work>/l4_inputs.npz after asserting its sha256 against
<work>/RECEIPT_L4_build.json (which must report all build gates PASS). Gates run before any reading; a failed gate stops the run.
Writes <work>/RECEIPT_L4_run.json and <work>/L4_SERIES.npz; prints one SUMMARY line.
Usage: python3 l4_run.py <env_whitelist_csv> <work_dir>
"""
import os, sys, json, time, math, hashlib, calendar
WHITE = set(x for x in sys.argv[1].split(",") if x); assert WHITE, "non-empty env whitelist required"
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
WORK = os.path.abspath(sys.argv[2]); assert WORK.startswith("/workspace/uplift_r3_2026-09-13/L4/"), WORK
import numpy as np
import scipy
from scipy import stats
T_START = time.time()
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def ut(y, m, d, h=0): return calendar.timegm((y, m, d, h, 0, 0))
def iso(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def fl(x): return None if x is None or (isinstance(x, float) and not math.isfinite(x)) else float(x)

PREREG_SHA = "ced2f73f10b1d32377d469ddd64b4ee6614d0925c9be182bd09ff2f16a52cc8b"
BR_PATH = os.path.join(WORK, "RECEIPT_L4_build.json"); BR = json.load(open(BR_PATH))
assert BR["all_gates_pass"] is True and BR["prereg_sha256"] == PREREG_SHA, "build gates not all PASS"
INP = os.path.join(WORK, "l4_inputs.npz"); INP_SHA = sha(INP); assert INP_SHA == BR["output"]["sha256"], "inputs sha mismatch vs build receipt"
REC = dict(device="l4_run.py", device_sha256=sha(os.path.abspath(__file__)), run_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), prereg_sha256=PREREG_SHA,
           env_actual={k: os.environ[k] for k in sorted(os.environ)}, python=sys.version.split()[0], numpy=np.__version__, scipy=scipy.__version__,
           affinity=sorted(os.sched_getaffinity(0)), build_receipt_sha256=sha(BR_PATH), inputs_sha256=INP_SHA, gates={})
assert len(REC["affinity"]) <= 8
print("CONFIG " + json.dumps(dict(self_sha256=REC["device_sha256"], prereg=PREREG_SHA, inputs_sha256=INP_SHA, affinity=REC["affinity"])), flush=True)

# ---------------------------------------------------------------- constants (PREREG 2, 3)
ALPHA = 1.0 - 2.0 ** (-1.0 / 6.0); WARM_N = 18; FX_N = 6; M = 0.5; G_A = 2.0; CP = 3.92; CS_BASE = 10.0; CS_SENS = (5.0, 15.0)
ANN = math.sqrt(2190.0); BOOT = 20000; BLOCK = 30; GAMMA = 0.5772156649015329
ARMS = []
for hi, ho in ((2.0, 0.5), (5.0, 2.0), (10.0, 4.0)):
    for mh in (3, 9):
        for K in (10, 20):
            ARMS.append(dict(id="A%02d" % (len(ARMS) + 1), h_in=hi, h_out=ho, min_hold=mh, K=K))
assert len(ARMS) == 12 and ARMS[0] == dict(id="A01", h_in=2.0, h_out=0.5, min_hold=3, K=10) and ARMS[11] == dict(id="A12", h_in=10.0, h_out=4.0, min_hold=9, K=20)
HINS = sorted(set(a["h_in"] for a in ARMS))
REC["constants"] = dict(alpha=ALPHA, half_life_h=24, warm_anchors=WARM_N, forced_exit_anchors=FX_N, m=M, G_A=G_A, c_perp=CP, c_spot_base=CS_BASE, c_spot_sens=CS_SENS,
                        boot=BOOT, block_days=BLOCK, arms=ARMS)

# ---------------------------------------------------------------- core (PREREG 2.2, 2.6, 2.7)
def prepare(A, NEV, ELIG, TRAD, SPOT_OK, B2, B1=None):
    nG, NS = A.shape
    has = NEV > 0
    first_j = np.where(has.any(0), has.argmax(0), -1)
    init = np.where(first_j >= 0, first_j + 1, -1)
    EMA = np.full((nG, NS), np.nan); e = np.full(NS, np.nan)
    for i in range(1, nG):
        x = 2.0 * A[i - 1] * 1e4
        e = e + ALPHA * (x - e)
        nw = init == i
        if nw.any(): e[nw] = x[nw]
        EMA[i] = e
    ii = np.arange(nG)[:, None]
    WARM = (init[None, :] >= 0) & (ii - init[None, :] >= WARM_N)
    cN = np.vstack([np.zeros((1, NS), np.int64), np.cumsum(NEV.astype(np.int64), 0)])
    NEV24 = np.full((nG, NS), -1, np.int64); NEV24[FX_N:] = cN[FX_N:nG] - cN[0:nG - FX_N]            # sum NEV[i-6 .. i-1]
    cT = np.vstack([np.zeros((1, NS), np.int64), np.cumsum(TRAD.astype(np.int64), 0)])
    TN = np.zeros((nG, NS), bool); TN[FX_N - 1:] = (cT[FX_N:nG + 1] - cT[0:nG - FX_N + 1]) == 0      # no TRAD in i-5 .. i
    fin = np.isfinite(B2)
    cB = np.vstack([np.zeros((1, NS), np.int64), np.cumsum(fin.astype(np.int64), 0)])
    BN = np.zeros((nG, NS), bool); BN[FX_N - 1:] = (cB[FX_N:nG + 1] - cB[0:nG - FX_N + 1]) == 0
    def ffill(X):
        F = X.copy()
        for i in range(1, nG):
            mm = ~np.isfinite(F[i]); F[i, mm] = F[i - 1, mm]
        return F
    B2F = ffill(B2); B1F = ffill(B1) if B1 is not None else None
    base = ELIG & SPOT_OK & WARM & fin & (NEV24 > 0)          # AMENDMENT 1: not in forced-exit condition (b)
    with np.errstate(invalid="ignore"):
        CAND = {h: base & (EMA >= h) for h in HINS}
    return dict(A=A, NEV=NEV, EMA=EMA, WARM=WARM, INIT=init, NEV24=NEV24, TN=TN, BN=BN, B2F=B2F, B1F=B1F, CAND=CAND, B2=B2)

def simulate(arm, D, i_start, i_end):
    NS = D["EMA"].shape[1]; K = arm["K"]; hout = arm["h_out"]; mh = arm["min_hold"]
    EMA = D["EMA"]; NEV = D["NEV"]; TN = D["TN"]; BN = D["BN"]; N24 = D["NEV24"]; CAND = D["CAND"][arm["h_in"]]
    held = np.zeros(NS, bool); nsett = np.zeros(NS, np.int64); t_in = np.full(NS, -1, np.int64)
    T = i_end - i_start + 1; POS = np.zeros((T, NS), bool); holds = []
    for t in range(T):
        i = i_start + t; ex = None
        if held.any():
            if t > 0: nsett[held] += NEV[i - 1, held]
            fa = held & TN[i]; fb = held & (N24[i] == 0); fc = held & BN[i]
            forced = fa | fb | fc
            with np.errstate(invalid="ignore"):
                normal = held & ~forced & (EMA[i] < hout) & (nsett >= mh)
            ex = forced | normal
            if ex.any():
                for k in np.nonzero(ex)[0]:
                    holds.append((int(k), int(t_in[k]), t, "forced_a" if fa[k] else "forced_b" if fb[k] else "forced_c" if fc[k] else "normal"))
                held = held & ~ex; nsett[ex] = 0; t_in[ex] = -1
        free = K - int(held.sum())
        if free > 0:
            c = CAND[i] & ~held
            if ex is not None: c = c & ~ex
            cand = np.nonzero(c)[0]
            if len(cand):
                take = cand[np.lexsort((cand, -EMA[i, cand]))][:free]
                held[take] = True; nsett[take] = 0; t_in[take] = t
        POS[t] = held
    open_holds = [(int(k), int(t_in[k]), None, "open") for k in np.nonzero(held)[0]]
    return POS, holds, open_holds

def account(POS, D, i_start, K, c_spot, marker="B2"):
    n = 1.0 / (K * (1.0 + M)); T = POS.shape[0]
    inc = n * 1e4 * np.where(POS, D["A"][i_start:i_start + T], 0.0).sum(1)
    BF = D["B2F"] if marker == "B2" else D["B1F"]
    dB = BF[i_start:i_start + T] - BF[i_start + 1:i_start + T + 1]
    use = POS & np.isfinite(dB)
    bas = n * 1e4 * np.where(use, dB, 0.0).sum(1)
    n_nan = int((POS & ~np.isfinite(dB)).sum())
    prev = np.vstack([np.zeros((1, POS.shape[1]), bool), POS[:-1]])
    turn = n * (POS != prev).sum(1).astype(np.float64)
    cost = (CP + c_spot) * turn
    return dict(net=inc + bas - cost, inc=inc, bas=bas, cost=cost, turn=turn, npos=POS.sum(1).astype(np.int64), n=n, nan_marks=n_nan)

# ---------------------------------------------------------------- G-SYN: independent pure-Python reference (PREREG 2.6 text) on synthetic worlds
def ref_sim(arm, A, NEV, ELIG, TRAD, SPOT_OK, B2, i_start, i_end):
    nG, NS = len(A), len(A[0]); K = arm["K"]
    first = []
    for k in range(NS):
        f = None
        for j in range(nG):
            if NEV[j][k] > 0: f = j; break
        first.append(f)
    ema = [[None] * NS for _ in range(nG)]
    for k in range(NS):
        if first[k] is None: continue
        init = first[k] + 1; e = None
        for i in range(init, nG):
            x = 2.0 * A[i - 1][k] * 1e4
            e = x if i == init else e + ALPHA * (x - e)
            ema[i][k] = e
    held = {}; pos = []; n = 1.0 / (K * (1.0 + M)); inc = []; bas = []; cost = []; prev = set()
    bt = [[None] * NS for _ in range(nG)]
    for k in range(NS):
        last = None
        for i in range(nG):
            if math.isfinite(B2[i][k]): last = B2[i][k]
            bt[i][k] = last
    for i in range(i_start, i_end + 1):
        if i > i_start:
            for k in held: held[k] += NEV[i - 1][k]
        exited = set()
        for k in sorted(held):
            fa = all(not TRAD[j][k] for j in range(i - 5, i + 1))
            fb = sum(NEV[j][k] for j in range(i - 6, i)) == 0
            fc = all(not math.isfinite(B2[j][k]) for j in range(i - 5, i + 1))
            if fa or fb or fc: exited.add(k); continue
            if ema[i][k] < arm["h_out"] and held[k] >= arm["min_hold"]: exited.add(k)
        for k in exited: del held[k]
        free = K - len(held)
        cands = [k for k in range(NS) if k not in held and k not in exited and ELIG[i][k] and SPOT_OK[i][k] and first[k] is not None
                 and i - (first[k] + 1) >= WARM_N and math.isfinite(B2[i][k]) and ema[i][k] is not None and ema[i][k] >= arm["h_in"]
                 and sum(NEV[j][k] for j in range(i - 6, i)) > 0]
        cands.sort(key=lambda k: (-ema[i][k], k))
        for k in cands[:max(free, 0)]: held[k] = 0
        cur = set(held); pos.append(cur)
        inc.append(sum(n * A[i][k] * 1e4 for k in cur))
        bas.append(sum(n * (bt[i][k] - bt[i + 1][k]) * 1e4 for k in cur))
        cost.append((CP + CS_BASE) * n * len(cur.symmetric_difference(prev))); prev = cur
    return pos, inc, bas, cost, ema

def syn_world(kind):
    nG = 220; NS = 4
    A = np.zeros((nG, NS)); NEV = np.zeros((nG, NS), np.int16)
    ELIG = np.zeros((nG, NS), bool); TRAD = np.ones((nG, NS), bool); SPOT_OK = np.ones((nG, NS), bool); B2 = np.zeros((nG, NS))
    for j in range(nG - 1):                      # name 0: 8h events at E_{j+1} for odd j  (+10 bps, -10 bps after anchor 120)
        if j % 2 == 1:
            A[j, 0] = 0.001 if j < 120 else -0.001; NEV[j, 0] = 1
        A[j, 1] = 0.005; NEV[j, 1] = 1              # name 1: 4h events +50 bps, never eligible
        if kind == "S4":
            A[j, 3] = 4 * 0.0002; NEV[j, 3] = 4     # name 3: 1h events +2 bps each (x = 16 bps/8h)
    ELIG[:, 0] = True; ELIG[:, 2] = True           # name 2 eligible, no events
    if kind == "S4": ELIG[:, 3] = True
    B2[60:, 0] = 1e-4 * np.sin(np.arange(60, nG)); B2[:, 3] = 2e-4 * np.cos(np.arange(nG))
    if kind == "S2": TRAD[80:, 0] = False; SPOT_OK[80:, 0] = False
    if kind == "S3": A[100:, 0] = 0.0; NEV[100:, 0] = 0
    if kind == "S5": B2[90:, 0] = np.nan
    return A, NEV, ELIG, TRAD, SPOT_OK, B2
SYN_ARMS = [ARMS[0], ARMS[4], ARMS[8], ARMS[11], dict(id="SYN_K1", h_in=2.0, h_out=0.5, min_hold=9, K=1)]
gsyn = dict(cases=[], explicit={})
I0S, I1S = 30, 218
for kind in ("S1", "S2", "S3", "S4", "S5"):
    A_, NEV_, EL_, TR_, SO_, B2_ = syn_world(kind); Dsy = prepare(A_, NEV_, EL_, TR_, SO_, B2_)
    for arm in SYN_ARMS:
        POS, holds, openh = simulate(arm, Dsy, I0S, I1S); acc = account(POS, Dsy, I0S, arm["K"], CS_BASE)
        rp, ri, rb, rc, _ = ref_sim(arm, A_.tolist(), NEV_.tolist(), EL_.tolist(), TR_.tolist(), SO_.tolist(), B2_.tolist(), I0S, I1S)
        pos_eq = all(set(np.nonzero(POS[t])[0].tolist()) == rp[t] for t in range(len(rp)))
        md = max(np.abs(acc["inc"] - np.array(ri)).max(), np.abs(acc["bas"] - np.array(rb)).max(), np.abs(acc["cost"] - np.array(rc)).max())
        gsyn["cases"].append(dict(world=kind, arm=arm["id"], positions_equal=bool(pos_eq), max_abs_acct_diff=float(md), n_holds=len(holds), reasons=sorted(set(h[3] for h in holds)), held_anchors=int(POS.sum())))
# explicit closed-form checks on S1 / A01 and forced-exit reasons on S2/S3/S5 / A01, slot limit on S4 / SYN_K1
A_, NEV_, EL_, TR_, SO_, B2_ = syn_world("S1"); Dsy = prepare(A_, NEV_, EL_, TR_, SO_, B2_); arm = ARMS[0]; n = 1.0 / (arm["K"] * 1.5)
POS, holds, _ = simulate(arm, Dsy, I0S, I1S); acc = account(POS, Dsy, I0S, arm["K"], CS_BASE)
e = None; emas = {}
for i in range(1, 220):                                      # independent scalar EMA for name 0 (first event window j=1 -> init anchor 2)
    x = 2.0 * A_[i - 1, 0] * 1e4
    if i == 2: e = x
    elif i > 2: e = e + ALPHA * (x - e)
    emas[i] = e
exit_expect = None; ns = 0
for i in range(I0S + 1, I1S + 1):
    ns += int(NEV_[i - 1, 0])
    if emas[i] < arm["h_out"] and ns >= arm["min_hold"]: exit_expect = i; break
t_exit = exit_expect - I0S
inc_expect = np.array([n * (10.0 if (I0S + t) < 120 else -10.0) if (POS[t, 0] and (I0S + t) % 2 == 1) else 0.0 for t in range(I1S - I0S + 1)])
held_ok = bool(POS[:t_exit, 0].all() and not POS[t_exit:, 0].any() and POS[:, 1].sum() == 0 and POS[:, 2].sum() == 0)
cost_expect = np.zeros(I1S - I0S + 1); cost_expect[0] = 13.92 * n; cost_expect[t_exit] = 13.92 * n
bas_hold = float(acc["bas"][:t_exit].sum()); bas_expect = n * 1e4 * (B2_[I0S, 0] - B2_[exit_expect, 0])
gsyn["explicit"]["S1_A01"] = dict(entry_t0=bool(POS[0, 0]), ema_at_entry=emas[I0S], exit_anchor_expected=exit_expect, exit_anchor_device=(I0S + int(np.argmin(POS[:, 0])) if not POS[-1, 0] else None),
                                  held_pattern_ok=held_ok, income_maxdiff=float(np.abs(acc["inc"] - inc_expect).max()), cost_maxdiff=float(np.abs(acc["cost"] - cost_expect).max()),
                                  basis_telescope_diff=abs(bas_hold - bas_expect), n_holds=len(holds), reason=(holds[0][3] if holds else None))
for kind, want in (("S2", "forced_a"), ("S3", "forced_b"), ("S5", "forced_c")):
    A_, NEV_, EL_, TR_, SO_, B2_ = syn_world(kind); Dk = prepare(A_, NEV_, EL_, TR_, SO_, B2_); P_, h_, _ = simulate(ARMS[0], Dk, I0S, I1S)
    gsyn["explicit"][kind + "_A01"] = dict(reasons=[x[3] for x in h_], exit_anchor=[I0S + x[2] for x in h_], want=want, ok=bool(len(h_) >= 1 and h_[0][3] == want and (kind != "S3" or (len(h_) == 1 and not P_[h_[0][2]:, 0].any()))))
A_, NEV_, EL_, TR_, SO_, B2_ = syn_world("S4"); Dk = prepare(A_, NEV_, EL_, TR_, SO_, B2_); P_, h_, _ = simulate(SYN_ARMS[4], Dk, I0S, I1S)
gsyn["explicit"]["S4_K1"] = dict(max_names_held=int(P_.sum(1).max()), first_pick=int(np.nonzero(P_[0])[0][0]) if P_[0].any() else None,
                                 ema_name0=float(Dk["EMA"][I0S, 0]), ema_name3=float(Dk["EMA"][I0S, 3]))
ex = gsyn["explicit"]
G_SYN = bool(all(c["positions_equal"] and c["max_abs_acct_diff"] <= 1e-9 for c in gsyn["cases"])
             and ex["S1_A01"]["entry_t0"] and ex["S1_A01"]["held_pattern_ok"] and ex["S1_A01"]["exit_anchor_device"] == ex["S1_A01"]["exit_anchor_expected"]
             and ex["S1_A01"]["income_maxdiff"] <= 1e-9 and ex["S1_A01"]["cost_maxdiff"] <= 1e-9 and ex["S1_A01"]["basis_telescope_diff"] <= 1e-9 and ex["S1_A01"]["reason"] == "normal"
             and ex["S2_A01"]["ok"] and ex["S3_A01"]["ok"] and ex["S5_A01"]["ok"] and ex["S4_K1"]["max_names_held"] == 1
             and ex["S4_K1"]["first_pick"] == (0 if ex["S4_K1"]["ema_name0"] > ex["S4_K1"]["ema_name3"] else 3))
REC["gates"]["G-SYN"] = dict(pass_=G_SYN, detail=gsyn)
print("G-SYN %s cases=%d all_pos_eq=%s explicit=%s" % (G_SYN, len(gsyn["cases"]), all(c["positions_equal"] for c in gsyn["cases"]), json.dumps(ex)), flush=True)
assert G_SYN, "G-SYN FAIL"

# ---------------------------------------------------------------- real inputs
Z = np.load(INP, allow_pickle=True)
EG = Z["EG"].astype(np.int64); SYM = [str(s) for s in Z["SYM"]]; iW0 = int(Z["iW0"]); iW1 = int(Z["iW1"]); nG, NS = Z["A"].shape
RAW = dict(A=Z["A"].astype(np.float64), NEV=Z["NEV"].astype(np.int16), ELIG=Z["ELIG"].astype(bool), TRAD=Z["TRAD"].astype(bool), SPOT_OK=Z["SPOT_OK"].astype(bool),
           B2=Z["B2"].astype(np.float64), B1=Z["B1"].astype(np.float64))
DUPCELL = Z["DUPCELL"]; SPACE_LAST = Z["SPACE_LAST"]; QVR24 = Z["QVR24"]
g42 = Z["A0_G42"].astype(np.float64); g27 = Z["A0_G2027"].astype(np.float64)
TSW = EG[iW0:iW1 + 1]; TW = len(TSW); assert TW == 10038 and TSW[0] == ut(2022, 1, 31) and TSW[-1] == ut(2026, 8, 30, 20)
D = prepare(RAW["A"], RAW["NEV"], RAW["ELIG"], RAW["TRAD"], RAW["SPOT_OK"], RAW["B2"], RAW["B1"])
SIM = {}
for arm in ARMS:
    SIM[arm["id"]] = simulate(arm, D, iW0, iW1)
print("SIMULATED 12 arms %.0fs" % (time.time() - T_START), flush=True)

# ---------------------------------------------------------------- G-CAUSAL
rng_c = np.random.default_rng([20260913, 4, 99])
cuts = np.sort(rng_c.choice(np.arange(iW0 + 10, iW1 - 10), 20, replace=False))
gc = dict(cuts=[iso(EG[c]) for c in cuts], draws=[], neg_changed_draws=0)
for d_, cst in enumerate(cuts):
    cst = int(cst); r = np.random.default_rng([20260913, 4, 99, d_ + 1])
    Ap = RAW["A"].copy(); Np = RAW["NEV"].copy(); Ep = RAW["ELIG"].copy(); Tp = RAW["TRAD"].copy(); Sp = RAW["SPOT_OK"].copy(); Bp = RAW["B2"].copy(); B1p = RAW["B1"].copy()
    nf = nG - cst
    Ap[cst:] = r.normal(0.0005, 0.002, (nf, NS)); Np[cst:] = r.integers(0, 5, (nf, NS))
    Ep[cst + 1:] = r.random((nf - 1, NS)) < 0.3; Tp[cst + 1:] = r.random((nf - 1, NS)) < 0.7; Sp[cst + 1:] = r.random((nf - 1, NS)) < 0.5
    Bq = r.normal(0, 0.001, (nf - 1, NS)); Bq[r.random((nf - 1, NS)) < 0.05] = np.nan; Bp[cst + 1:] = Bq; B1p[cst + 1:] = r.normal(0, 0.001, (nf - 1, NS))
    Dp = prepare(Ap, Np, Ep, Tp, Sp, Bp, B1p)
    same = True; ndiff = 0
    for arm in ARMS:
        Pp, _, _ = simulate(arm, Dp, iW0, cst)
        eq = np.array_equal(Pp, SIM[arm["id"]][0][:cst - iW0 + 1]); same &= eq; ndiff += int(not eq)
    An = RAW["A"].copy(); An[cst - 1] += 0.005
    Dn = prepare(An, RAW["NEV"], RAW["ELIG"], RAW["TRAD"], RAW["SPOT_OK"], RAW["B2"], RAW["B1"])
    chg = 0
    for arm in ARMS:
        Pn, _, _ = simulate(arm, Dn, iW0, cst)
        chg += int(not np.array_equal(Pn[-1], SIM[arm["id"]][0][cst - iW0]))
    gc["draws"].append(dict(cut=iso(EG[cst]), future_perturbed_positions_identical=bool(same), arms_differing=ndiff, neg_control_arms_changed_at_cut=chg))
    gc["neg_changed_draws"] += int(chg > 0)
    del Ap, Np, Ep, Tp, Sp, Bp, B1p, Dp, An, Dn
G_CAUSAL = bool(all(x["future_perturbed_positions_identical"] for x in gc["draws"]) and gc["neg_changed_draws"] >= 1)
REC["gates"]["G-CAUSAL"] = dict(pass_=G_CAUSAL, detail=gc)
print("G-CAUSAL %s identical=%d/20 neg_control_changed_draws=%d %.0fs" % (G_CAUSAL, sum(x["future_perturbed_positions_identical"] for x in gc["draws"]), gc["neg_changed_draws"], time.time() - T_START), flush=True)
assert G_CAUSAL, "G-CAUSAL FAIL"

# ---------------------------------------------------------------- accounting + G-ACCT
ACC = {}; HOLDS = {}; gacc = {}
for arm in ARMS:
    POS, holds, openh = SIM[arm["id"]]; acc = account(POS, D, iW0, arm["K"], CS_BASE); ACC[arm["id"]] = acc; HOLDS[arm["id"]] = (holds, openh)
    n = acc["n"]; dB = D["B2F"][iW0:iW1 + 1] - D["B2F"][iW0 + 1:iW1 + 2]
    tel = 0.0; tot = 0.0
    for (k, a, b, _) in holds:
        s_ = n * 1e4 * dB[a:b, k].sum(); tv = n * 1e4 * (D["B2F"][iW0 + a, k] - D["B2F"][iW0 + b, k]); tel = max(tel, abs(s_ - tv)); tot += s_
    for (k, a, _, _) in openh: tot += n * 1e4 * dB[a:, k].sum()
    n_events = 2 * len(holds) + len(openh)
    gacc[arm["id"]] = dict(identity=float(np.abs(acc["net"] - (acc["inc"] + acc["bas"] - acc["cost"])).max()), turnover_vs_holds=abs(acc["turn"].sum() - n * n_events),
                           telescope_max=tel, basis_total_vs_holds=abs(acc["bas"].sum() - tot), basis_nan_marks=acc["nan_marks"], completed_holds=len(holds), open_at_end=len(openh))
G_ACCT = bool(all(v["identity"] <= 1e-9 and v["turnover_vs_holds"] <= 1e-9 and v["telescope_max"] <= 1e-9 and v["basis_total_vs_holds"] <= 1e-6 and v["basis_nan_marks"] == 0 for v in gacc.values()))
REC["gates"]["G-ACCT"] = dict(pass_=G_ACCT, detail=gacc)
print("G-ACCT %s" % G_ACCT, flush=True)
assert G_ACCT, "G-ACCT FAIL"
print("ALL RUN GATES PASS; readings follow", flush=True)

# ---------------------------------------------------------------- spans, helpers (PREREG 2.1, 4.1)
SPANS = dict(Y22=(ut(2022, 1, 31), ut(2023, 1, 1)), Y23=(ut(2023, 1, 1), ut(2024, 1, 1)), Y24=(ut(2024, 1, 1), ut(2025, 1, 1)), Y25=(ut(2025, 1, 1), ut(2026, 1, 1)),
             Y26=(ut(2026, 1, 1), ut(2026, 8, 30, 20) + 1), S2426=(ut(2024, 1, 1), ut(2026, 8, 30, 20) + 1), FULL=(ut(2022, 1, 31), ut(2026, 8, 30, 20) + 1))
SPAN_CODE = dict(Y22=22, Y23=23, Y24=24, Y25=25, Y26=26, S2426=2426, FULL=1)
YEARS = ("Y22", "Y23", "Y24", "Y25", "Y26")
SM = {k: (TSW >= lo) & (TSW < hi) for k, (lo, hi) in SPANS.items()}
assert SM["FULL"].sum() == TW
DAY = TSW // 86400
a42 = G_A * g42; a27 = G_A * g27; A0S = {"42": a42, "2027": a27}
def sharpe(x):
    s = x.std(ddof=1) if len(x) > 2 else 0.0
    return float(x.mean() / s * ANN) if s > 0 else float("nan")
def maxdd(x):
    nav = np.cumprod(1.0 + x / 1e4); return float((1.0 - nav / np.maximum.accumulate(nav)).max() * 100)
def corr(x, y):
    if x.std() == 0 or y.std() == 0: return float("nan")
    return float(np.corrcoef(x, y)[0, 1])
def daysums(x, mask):
    ud, inv = np.unique(DAY[mask], return_inverse=True)
    return np.bincount(inv, x[mask]), np.bincount(inv, x[mask] ** 2), np.bincount(inv).astype(np.float64)
def boot_idx(nd, seed, block=BLOCK, iid=False):
    r = np.random.default_rng(seed)
    if iid: return r.integers(0, nd, (BOOT, nd), dtype=np.int32)
    nb = -(-nd // block); st = r.integers(0, nd, (BOOT, nb), dtype=np.int64)
    idx = ((st[:, :, None] + np.arange(block)[None, None, :]) % nd).reshape(BOOT, nb * block)[:, :nd]
    return idx.astype(np.int32)
def boot_mean(x, mask, seed, block=BLOCK, iid=False, qs=(2.5, 97.5, 100 * 0.025 / 12)):
    s, q, c = daysums(x, mask); idx = boot_idx(len(c), seed, block, iid)
    mb = s[idx].sum(1) / c[idx].sum(1)
    return {("q%.4f" % p): float(np.percentile(mb, p)) for p in qs}
def boot_dsr(x, y, mask, seed):      # paired Sharpe difference SR(x) - SR(y) and mean difference
    sx, qx, c = daysums(x, mask); sy, qy, _ = daysums(y, mask); idx = boot_idx(len(c), seed)
    n = c[idx].sum(1)
    def srb(s_, q_):
        m_ = s_[idx].sum(1) / n; v = (q_[idx].sum(1) - n * m_ * m_) / (n - 1); return m_ / np.sqrt(np.maximum(v, 1e-300)) * ANN, m_
    a_, ma = srb(sx, qx); b_, mb_ = srb(sy, qy); dd = a_ - b_; dm = ma - mb_
    return dict(dSR_ci95=[float(np.percentile(dd, 2.5)), float(np.percentile(dd, 97.5))], dmean_ci95=[float(np.percentile(dm, 2.5)), float(np.percentile(dm, 97.5))])

def span_table(acc, arm_no, K, cand_any, holds_all, with_ci=True, ci_spans=None, purpose=1):
    out = {}
    for sp, mk in SM.items():
        net = acc["net"][mk]; tu = acc["turn"][mk]; npos = acc["npos"][mk]
        d = dict(n=int(mk.sum()), net_mean=float(net.mean()), inc_mean=float(acc["inc"][mk].mean()), bas_mean=float(acc["bas"][mk].mean()), cost_mean=float(acc["cost"][mk].mean()),
                 turnover_mean=float(tu.mean()), deployed_share=float((npos / K).mean()), position_share=float((npos > 0).mean()), empty_share=float((npos == 0).mean()),
                 no_candidate_share=float((~cand_any[mk]).mean()), sharpe=sharpe(net), sigma=float(net.std(ddof=1)), maxdd_pct=maxdd(net), apr_pct=float(net.mean() * 2190 / 100))
        lo, hi = np.nonzero(mk)[0][[0, -1]]
        comp = [h for h in holds_all if h[2] is not None and lo <= h[2] <= hi]
        d["completed_holds"] = len(comp); d["median_hold_anchors"] = float(np.median([h[2] - h[1] for h in comp])) if comp else None
        d["forced_exits"] = {r_: sum(1 for h in comp if h[3] == r_) for r_ in ("forced_a", "forced_b", "forced_c")}
        tm = tu.mean()
        d["breakeven_allin"] = float((acc["inc"][mk].mean() + acc["bas"][mk].mean()) / tm) if tm > 0 else None
        d["breakeven_spot"] = (d["breakeven_allin"] - CP) if d["breakeven_allin"] is not None else None
        d["breakeven_income_only"] = float(acc["inc"][mk].mean() / tm) if tm > 0 else None
        if with_ci and (ci_spans is None or sp in ci_spans):
            d["ci"] = boot_mean(acc["net"], mk, [20260913, 4, arm_no, SPAN_CODE[sp], purpose])
        out[sp] = d
    return out

def rho_table(net):
    o = {}
    for s, a in A0S.items():
        o[s] = {}
        for sp, mk in SM.items():
            sx, _, _ = daysums(net, mk); sa, _, _ = daysums(a, mk)
            o[s][sp] = dict(per_anchor=corr(net[mk], a[mk]), per_day=corr(sx, sa))
    return o

def combo_table(net, arm_no, m_scale=1.0, with_ci=True):
    o = {}
    for s, a in A0S.items():
        o[s] = {}
        for sp, mk in SM.items():
            x = m_scale * net[mk]; aa = a[mk]; ec = 0.5 * aa + 0.5 * x
            d = dict(A0_sharpe=sharpe(aa), EC_sharpe=sharpe(ec), EC_mean=float(ec.mean()), A0_mean=float(aa.mean()), EC_maxdd_pct=maxdd(ec), A0_maxdd_pct=maxdd(aa))
            d["dSR"] = (d["EC_sharpe"] - d["A0_sharpe"]) if math.isfinite(d["EC_sharpe"]) else None
            sd = x.std(ddof=1); lam = float(aa.std(ddof=1) / sd) if sd > 0 else float("inf")
            kmax = (1.0 + M) / (1.0 / 3.0 + M)
            d["EV_lambda_needed"] = lam if math.isfinite(lam) else None; d["EV_k_max"] = kmax; d["EV_feasible"] = bool(math.isfinite(lam) and lam <= kmax)
            d["EV_sharpe"] = sharpe(0.5 * aa + 0.5 * lam * x) if d["EV_feasible"] else "INFEASIBLE"
            if with_ci:
                full = np.zeros(TW); full[mk] = ec; fa = np.zeros(TW); fa[mk] = aa
                d["paired"] = boot_dsr(full, fa, mk, [20260913, 4, arm_no, SPAN_CODE[sp], 2 if s == "42" else 3])
            o[s][sp] = d
    return o

def rule_eval(tab, rho, ci_key_unadj="q2.5000", ci_key_adj="q0.2083"):
    P0 = tab["S2426"]["position_share"] >= 0.30
    yrs = {y: dict(position_share=tab[y]["position_share"], net_mean=tab[y]["net_mean"], applies=tab[y]["position_share"] >= 0.30) for y in YEARS}
    P1 = all((not v["applies"]) or v["net_mean"] > 0 for v in yrs.values())
    ci = tab["S2426"].get("ci", {})
    P2a = ci.get(ci_key_unadj, -1) > 0; P2b = ci.get(ci_key_adj, -1) > 0
    rh = [rho[s]["FULL"]["per_anchor"] for s in rho] + [rho[s]["FULL"]["per_day"] for s in rho]
    P3 = all(v is not None and math.isfinite(v) and v <= 0.30 for v in rh)
    return dict(P0=bool(P0), P1=bool(P1), P1_years=yrs, P2a=bool(P2a), P2b=bool(P2b), P3=bool(P3), rho_full=rh, PASS_adj=bool(P0 and P1 and P2b and P3), PASS_unadj=bool(P0 and P1 and P2a and P3))

# ---------------------------------------------------------------- readings per arm
CAND_ANY = {h: D["CAND"][h][iW0:iW1 + 1].any(1) for h in HINS}
R = {}
for ai, arm in enumerate(ARMS):
    arm_no = ai + 1; aid = arm["id"]; acc = ACC[aid]; POS, holds, openh = SIM[aid]; hall = holds + openh
    tab = span_table(acc, arm_no, arm["K"], CAND_ANY[arm["h_in"]], hall)
    rho = rho_table(acc["net"])
    combo = combo_table(acc["net"], arm_no)
    rule = rule_eval(tab, rho)
    sens = {}
    for cs, pc in ((5.0, 4), (15.0, 5)):
        ac2 = account(POS, D, iW0, arm["K"], cs); t2 = span_table(ac2, arm_no, arm["K"], CAND_ANY[arm["h_in"]], hall, ci_spans=("S2426",), purpose=pc)
        sens["c_spot_%g" % cs] = dict(table={sp: {k: t2[sp][k] for k in ("net_mean", "sharpe", "apr_pct") } | ({"ci": t2[sp]["ci"]} if "ci" in t2[sp] else {}) for sp in t2},
                                       rule=rule_eval(t2, rho_table(ac2["net"])))
    nb = acc["inc"] - acc["cost"]
    sens["basis_excluded"] = {sp: dict(net_mean=float(nb[mk].mean()), sharpe=sharpe(nb[mk])) for sp, mk in SM.items()}
    ab1 = account(POS, D, iW0, arm["K"], CS_BASE, marker="B1"); n1 = ab1["net"]
    sens["B1_marking"] = dict(nan_marks=ab1["nan_marks"], spans={sp: dict(net_mean=float(n1[mk].mean()), sharpe=sharpe(n1[mk]), bas_mean=float(ab1["bas"][mk].mean())) for sp, mk in SM.items()},
                              corr_basis_B1_B2_invested=corr(ab1["bas"][acc["npos"] > 0], acc["bas"][acc["npos"] > 0]) if (acc["npos"] > 0).sum() > 10 else None)
    sens["m_1.0"] = dict(level_scale=0.75, combo={s: {sp: dict(EC_sharpe=v["EC_sharpe"], A0_sharpe=v["A0_sharpe"]) for sp, v in d_.items()} for s, d_ in combo_table(acc["net"], arm_no, m_scale=0.75, with_ci=False).items()})
    mk = SM["S2426"]
    sens["ci_S2426_iid_day"] = boot_mean(acc["net"], mk, [20260913, 4, arm_no, 2426, 6], iid=True)
    sens["ci_S2426_7day"] = boot_mean(acc["net"], mk, [20260913, 4, arm_no, 2426, 7], block=7)
    held_cells = POS; win = slice(iW0, iW1 + 1)
    spc = SPACE_LAST[win][held_cells & (RAW["NEV"][win] > 0)]
    desc = dict(interval_mix_by_spacing={str(k): float((spc == k).mean()) for k in (1.0, 2.0, 4.0, 8.0)} if len(spc) else None,
                median_qvr24_held=float(np.nanmedian(QVR24[win][held_cells])) if held_cells.any() else None,
                dup_event_cells_held=int((DUPCELL[win] & held_cells).sum()),
                exits_with_stale_b2=int(sum(1 for (k, a, b, _) in holds if not np.isfinite(RAW["B2"][iW0 + b, k]))),
                held_name_anchor_cells=int(held_cells.sum()), distinct_names_held=int(held_cells.any(0).sum()))
    y23 = {s: combo[s]["Y23"]["dSR"] for s in combo}
    r7 = dict(Y23_net_mean=tab["Y23"]["net_mean"], Y23_position_share=tab["Y23"]["position_share"], Y23_dSR_EC_minus_A0=y23,
              adds_in_2023=bool(tab["Y23"]["net_mean"] > 0 and all(v is not None and v > 0 for v in y23.values())))
    R[aid] = dict(arm=arm, R1=tab, R4=rho, R5=combo, rule=rule, R7=r7, R8=sens, desc=desc)
    print("ARM %s h_in=%g h_out=%g mh=%d K=%d | S2426 net %.4f [%.4f adj %.4f] SR %.2f pos %.2f | FULL SR %.2f rho42 %.3f/%.3f | P0 %s P1 %s P2a %s P2b %s P3 %s => adj %s unadj %s  %.0fs" % (
        aid, arm["h_in"], arm["h_out"], arm["min_hold"], arm["K"], tab["S2426"]["net_mean"], tab["S2426"]["ci"]["q2.5000"], tab["S2426"]["ci"]["q0.2083"], tab["S2426"]["sharpe"],
        tab["S2426"]["position_share"], tab["FULL"]["sharpe"], rho["42"]["FULL"]["per_anchor"], rho["42"]["FULL"]["per_day"], rule["P0"], rule["P1"], rule["P2a"], rule["P2b"], rule["P3"],
        rule["PASS_adj"], rule["PASS_unadj"], time.time() - T_START), flush=True)

# ---------------------------------------------------------------- R6 T6 framing: nested selection, DSR, increment
SEG = [(ut(2023, 1, 1), ut(2024, 1, 1)), (ut(2024, 1, 1), ut(2025, 1, 1)), (ut(2025, 1, 1), ut(2026, 1, 1)), (ut(2026, 1, 1), ut(2026, 8, 30, 20) + 1)]
NETM = np.stack([ACC[a["id"]]["net"] for a in ARMS], 1); NPOSM = np.stack([ACC[a["id"]]["npos"] for a in ARMS], 1)
nested = dict(segments=[]); nest_net = np.zeros(TW); nest_npos = np.zeros(TW, np.int64); span = np.zeros(TW, bool)
for lo, hi in SEG:
    tr = TSW < lo; sg = (TSW >= lo) & (TSW < hi); span |= sg
    srt = np.array([sharpe(NETM[tr, j]) for j in range(12)]); srt_sel = np.where(np.isfinite(srt), srt, -np.inf)
    k = int(np.argmax(srt_sel)); nest_net[sg] = NETM[sg, k]; nest_npos[sg] = NPOSM[sg, k]
    nested["segments"].append(dict(segment="%s..%s" % (iso(TSW[sg][0]), iso(TSW[sg][-1])), train_n=int(tr.sum()), train_sharpe=[fl(v) for v in srt], selected=ARMS[k]["id"],
                                   oos_net_mean=float(NETM[sg, k].mean()), oos_sharpe=sharpe(NETM[sg, k]), oos_position_share=float((NPOSM[sg, k] > 0).mean())))
NY = dict(Y23=SM["Y23"], Y24=SM["Y24"], Y25=SM["Y25"], Y26=SM["Y26"])
ny = {y: dict(position_share=float((nest_npos[mk] > 0).mean()), net_mean=float(nest_net[mk].mean()), sharpe=sharpe(nest_net[mk])) for y, mk in NY.items()}
nci = boot_mean(nest_net, SM["S2426"], [20260913, 4, 13, 2426, 1])
nrho = {}
for s, a in A0S.items():
    sx, _, _ = daysums(nest_net, span); sa, _, _ = daysums(a, span)
    nrho[s] = dict(per_anchor=corr(nest_net[span], a[span]), per_day=corr(sx, sa))
nP0 = float((nest_npos[SM["S2426"]] > 0).mean()) >= 0.30
nP1 = all((v["position_share"] < 0.30) or v["net_mean"] > 0 for v in ny.values())
nP2 = nci["q2.5000"] > 0
nP3 = all(math.isfinite(v) and v <= 0.30 for d_ in nrho.values() for v in d_.values())
nested.update(years=ny, S2426=dict(net_mean=float(nest_net[SM["S2426"]].mean()), sharpe=sharpe(nest_net[SM["S2426"]]), position_share=float((nest_npos[SM["S2426"]] > 0).mean()), ci=nci),
              rho_nested_span=nrho, P0=bool(nP0), P1=bool(nP1), P2a=bool(nP2), P3=bool(nP3), PASS=bool(nP0 and nP1 and nP2 and nP3))
inc_ = {}
for s, a in A0S.items():
    ec = np.where(span, 0.5 * a + 0.5 * nest_net, 0.0); aa = np.where(span, a, 0.0)
    inc_[s] = dict(EC_sharpe=sharpe(ec[span]), A0_sharpe=sharpe(aa[span]), dSR=sharpe(ec[span]) - sharpe(aa[span]), **boot_dsr(ec, aa, span, [20260913, 4, 13, 1, 8 if s == "42" else 9]))
nested["EC_increment_nested_span"] = inc_
def psr(sr_pp, T, g3, g4, sr_star):
    den = 1.0 - g3 * sr_pp + (g4 - 1.0) / 4.0 * sr_pp ** 2
    return float(stats.norm.cdf((sr_pp - sr_star) * math.sqrt(T - 1) / math.sqrt(den)))
def sr0(V, N):
    N = max(N, 2.0); return float(math.sqrt(V) * ((1 - GAMMA) * stats.norm.ppf(1 - 1.0 / N) + GAMMA * stats.norm.ppf(1 - 1.0 / (N * math.e))))
X = NETM[SM["S2426"]]; sd = X.std(0, ddof=1); ok = sd > 0
srpp = np.where(ok, X.mean(0) / np.where(ok, sd, 1.0), np.nan); V = float(np.nanvar(srpp[ok], ddof=1)) if ok.sum() > 1 else float("nan")
Cm = np.corrcoef(X[:, ok].T); ev = np.linalg.eigvalsh(Cm); Neff = float(ev.sum() ** 2 / (ev ** 2).sum())
kb = int(np.nanargmax(srpp)); g = X[:, kb]; g3 = float(stats.skew(g, bias=False)); g4 = float(stats.kurtosis(g, fisher=False, bias=False)); T_ = X.shape[0]
dsr = dict(best_arm=ARMS[kb]["id"], SR_annual=float(srpp[kb] * ANN), T=T_, skew=g3, kurt=g4, N_eff=Neff, arms_with_variance=int(ok.sum()), V_SR_pp=V, PSR_0=psr(srpp[kb], T_, g3, g4, 0.0))
for nl, nv in (("N_eff", Neff), ("N_12", 12.0), ("N_18", 18.0)):
    z = sr0(V, nv); dsr["SR0_annual_" + nl] = z * ANN; dsr["P_true_SR_gt_0_" + nl] = psr(srpp[kb], T_, g3, g4, z)

# ---------------------------------------------------------------- verdict (PREREG 5.3)
adj = [a["id"] for a in ARMS if R[a["id"]]["rule"]["PASS_adj"]]; unadj = [a["id"] for a in ARMS if R[a["id"]]["rule"]["PASS_unadj"]]
if adj and nested["PASS"]: verdict = "PASS"
elif not unadj: verdict = "FAIL"
else: verdict = "NOT PASS (multiplicity)"
REC["readings"] = dict(per_arm=R, no_candidate_share={str(h): {sp: float((~CAND_ANY[h][mk]).mean()) for sp, mk in SM.items()} for h in HINS}, nested=nested, dsr=dsr)
REC["verdict"] = dict(study=verdict, arms_PASS_adj=adj, arms_PASS_unadj=unadj, nested_PASS=nested["PASS"])
REC["elapsed_s"] = round(time.time() - T_START, 1)
ser = dict(TSW=TSW, A0_a42=a42, A0_a2027=a27, nested_net=nest_net, nested_npos=nest_npos)
for a in ARMS:
    for k in ("net", "inc", "bas", "cost", "turn", "npos"): ser["%s_%s" % (a["id"], k)] = ACC[a["id"]][k]
np.savez_compressed(os.path.join(WORK, "L4_SERIES.npz"), **ser)
REC["series_sha256"] = sha(os.path.join(WORK, "L4_SERIES.npz"))
json.dump(REC, open(os.path.join(WORK, "RECEIPT_L4_run.json"), "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print("SUMMARY l4_run G-SYN=%s G-CAUSAL=%s G-ACCT=%s | arms PASS_adj=%s PASS_unadj=%s | nested PASS=%s (picks %s) | DSR best %s SR %.2f P(SR>0) N_eff %.3f N12 %.3f N18 %.3f | VERDICT=%s | elapsed=%.0fs self_sha256=%s" % (
    G_SYN, G_CAUSAL, G_ACCT, adj, unadj, nested["PASS"], [s_["selected"] for s_ in nested["segments"]], dsr["best_arm"], dsr["SR_annual"], dsr["P_true_SR_gt_0_N_eff"], dsr["P_true_SR_gt_0_N_12"],
    dsr["P_true_SR_gt_0_N_18"], verdict, REC["elapsed_s"], REC["device_sha256"][:16]), flush=True)

"""t8_common.py — PREREG_T8 (sha 53da0bcc…) shared definitions: inputs §2, alignment/windows/folds §3, targets §3.1, features §4,
family §5, statistics §6. Imported by every T8 device; never run alone. Pure functions of their arguments (the G3 shuffle-future gate
re-evaluates exactly these functions on perturbed copies, so nothing here may read a module-level cache of data)."""
import os, sys, json, time, hashlib, subprocess, calendar
import numpy as np
from scipy.stats import rankdata

T8 = "/workspace/uplift_r2_2026-09-13/T8"
PREREG = T8 + "/PREREG_T8.md"
FREEZE = T8 + "/receipts/PREREG_FREEZE_sha.txt"
PREREG_SHA = "53da0bcc948b2ed417ec505888f95c96c615e201ad2c57bdf549ea4ece884f8a"
AMEND1 = T8 + "/PREREG_AMENDMENT_1_T8.md"
AMEND1_SHA = "d5928ee3272c30b1ceb64a9c675b3d0d900cea7160e474d9538f6f266340be56"   # G2a: c_N reported only (AMENDMENT 1 §C.1)
INPUTS = {
    "ARM_R18_s42": ("/workspace/uplift_2026-09-11/r18_foundation/arms/C0_s42.npz", "d6298deb8d89df54149d82df72d1fe606062cc74a2bfe6b93d0a27ffed3f5340"),
    "ARM_R18_s2027": ("/workspace/uplift_2026-09-11/r18_foundation/arms/C0_s2027.npz", "fa5ed19a546c4230d673c4d922ac1c98c1888bf032280fb4da1dbee1d1258f2b"),
    "ARM_T1_s42": ("/workspace/uplift_r2_2026-09-13/T1/arms/C0_s42.npz", "93484e8186cabc7ab4d739b283665453542b4ea32eb00e9334be5c7879d0dd09"),
    "ARM_T1_s2027": ("/workspace/uplift_r2_2026-09-13/T1/arms/C0_s2027.npz", "d23e4503dfcb44cccf4d9d0ae4ffa0fd1735fba5516d425b8d1b733f7901623c"),
    "META": ("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz", "0e3c09ac86c727ac1a7893889918e3b367463fd059a154f5e320eed47f5725c3"),
    "PANEL": ("/workspace/data/wide_panel_4h_v2ext.npz", "5e67c0559daa904d8f0526b6e268e93dcb45aab89d82646cf79a794445481116"),
    "UMASK": ("/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz", "47d87b5165b695a7d9b340134a189dd6a2165c837bab35808b699ffac3f7f1b5"),
}
SEEDS = ("42", "2027")
FEATS = ["BTC4", "BTC24", "BTC72", "ALT4", "ALT24", "ALT72", "BR4", "BR24", "DISP4", "DISP24", "RVM24", "RVM168",
         "MUF", "SIGF", "DMUF24", "DSIGF24", "TKR24", "CSF", "CSR72", "CLF", "CLR72", "TR1", "TR6", "TR42"]
NF = 24; NMKT = 17
TARGETS = ("NET", "LONG", "SHORT", "CARRY"); SUBST = ("NET", "LONG", "SHORT"); MODELS = ("R", "L")
META_OFF = 138; N_REC = 10039; N_FULL = 10038; N_ALPHA = 9138; ALPHA0 = 900; MINSET = 50
UB = calendar.timegm((2026, 8, 30, 20, 0, 0))
FOLDS = [("F1", calendar.timegm((2022, 6, 30, 0, 0, 0)), calendar.timegm((2022, 12, 31, 20, 0, 0)), 1110),
         ("F2", calendar.timegm((2023, 1, 1, 0, 0, 0)), calendar.timegm((2023, 12, 31, 20, 0, 0)), 2190),
         ("F3", calendar.timegm((2024, 1, 1, 0, 0, 0)), calendar.timegm((2024, 12, 31, 20, 0, 0)), 2196),
         ("F4", calendar.timegm((2025, 1, 1, 0, 0, 0)), calendar.timegm((2025, 12, 31, 20, 0, 0)), 2190),
         ("F5", calendar.timegm((2026, 1, 1, 0, 0, 0)), UB, 1452)]
LGB_PARAMS = dict(objective="regression", learning_rate=0.02, num_leaves=7, max_depth=3, min_data_in_leaf=200, feature_fraction=0.8,
                  bagging_fraction=0.8, bagging_freq=1, lambda_l2=10.0, max_bin=63, seed=20260913, deterministic=True, force_row_wise=True,
                  num_threads=8, verbosity=-1)
LGB_ROUNDS = 300; NB = 2000; NNULL = 500; NDAYS_FULL = 1673; NDAYS_ALPHA = 1523
WHITE = {"PATH", "HOME", "LC_CTYPE", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"}
WHITE_VAL = {"OMP_NUM_THREADS": "8", "OPENBLAS_NUM_THREADS": "8", "MKL_NUM_THREADS": "8"}
BANNED = ("CAL", "LEGS", "PHI", "FSEED", "FTRIM", "UMASK", "SLOW", "FPRED", "MEMBERS_TOPN", "COSTB", "R18", "T1_", "SMA", "SBAND", "OUT_TAG",
          "JUDGE", "PANEL", "PYTHON", "LOOK", "WRULE", "W3FIX", "SEAT", "KMOD", "LGB", "T8_", "CUDA", "NVIDIA")


# ------------------------------------------------------------------ discipline (§10)
def sha256(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def check_env(argv):
    white = set(x for x in argv[1].split(",") if x) if len(argv) > 1 else set()
    assert white == WHITE, ("launch whitelist argv[1] must be exactly", sorted(WHITE), "got", sorted(white))
    extra = sorted(k for k in os.environ if k not in white)
    assert extra == [], ("ENV WHITELIST VIOLATION", extra)
    ban = sorted(k for k in os.environ if k.startswith(BANNED))
    assert ban == [], ("CONFIG FLAG PRESENT IN ENV", ban)
    for k, v in WHITE_VAL.items():
        assert os.environ.get(k) == v, ("thread env", k, os.environ.get(k))
    aff = sorted(os.sched_getaffinity(0))
    assert len(aff) <= 8, ("more than 8 cores visible to the process", aff)
    return dict(env_whitelist=sorted(white), env_actual={k: os.environ[k] for k in sorted(os.environ)}, launch_cmdline=" ".join(argv), affinity=aff,
                python=sys.version.split()[0], numpy=np.__version__)


def check_prereg():
    s = sha256(PREREG); a = sha256(AMEND1); fr = open(FREEZE).read()
    assert s == PREREG_SHA, ("PREREG_T8.md sha changed", s)
    assert a == AMEND1_SHA, ("PREREG_AMENDMENT_1_T8.md sha changed", a)
    assert PREREG_SHA in fr and AMEND1_SHA in fr, "freeze receipt does not carry the frozen shas"
    return dict(prereg=s, amendment_1=a)


def sysstate():
    def run(cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout.strip()
        except Exception as e:  # recorded, never silent
            return "ERR " + repr(e)
    return dict(utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                gpu=run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader"]),
                protected_pids=run(["ps", "-o", "pid,stat", "-p", "333197,339489"]), loadavg=open("/proc/loadavg").read().strip())


def gpu_idle(st):
    return st["gpu"].replace(" ", "") == "0%,2MiB"


def jdump(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, sort_keys=False, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    os.replace(tmp, path)


def utc(t):
    return time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))


# ------------------------------------------------------------------ inputs (§2, §3.2–3.4)
def load_inputs(check_sha=True):
    """Returns (D, rep). D holds float64 copies of every array the features / targets read."""
    rep = {"inputs": {}}
    for key, (p, s) in INPUTS.items():
        got = sha256(p) if check_sha else None
        if check_sha:
            assert got == s, ("input sha mismatch", key, got)
        rep["inputs"][key] = dict(path=p, realpath=os.path.realpath(p), sha256=got, size=os.path.getsize(p))
    M = np.load(INPUTS["META"][0], allow_pickle=True)
    P = np.load(INPUTS["PANEL"][0], allow_pickle=True)
    Um = np.load(INPUTS["UMASK"][0], allow_pickle=True)
    D = {"OFF": META_OFF}
    psym = [str(x) for x in P["symbols"]]
    assert psym == [str(x) for x in Um["symbols"]], "PANEL vs UMASK symbols"
    D["SYM"] = psym; D["BTC"] = psym.index("BTCUSDT")
    pts = P["ts"].astype(np.int64); uts = Um["ts"].astype(np.int64)
    assert pts.shape == (N_REC,) and np.array_equal(pts, uts), "PANEL ts vs UMASK ts"
    D["Y"] = np.asarray(M["y4"], np.float64); D["QVK"] = np.asarray(M["qvk"], np.float32)
    ets = M["E_ts"].astype(np.int64)
    assert D["Y"].shape == (10182, 829) and D["QVK"].shape == (10182, 829) and ets.shape == (10182,)
    D["FN"] = np.asarray(P["f_fund_now"], np.float64); D["IV"] = np.asarray(P["f_fund_iv"], np.float64); D["TBF"] = np.asarray(P["f_tbf_24h"], np.float64)
    D["U"] = np.asarray(Um["mask"], bool)
    assert D["FN"].shape == (N_REC, 829) and D["U"].shape == (N_REC, 829)
    cfgs = {}
    for s in SEEDS:
        A = np.load(INPUTS["ARM_R18_s" + s][0], allow_pickle=False)
        T = np.load(INPUTS["ARM_T1_s" + s][0], allow_pickle=False)
        assert [str(x) for x in A["symbols"]] == psym and [str(x) for x in T["symbols"]] == psym, "ARM symbols vs PANEL"
        cols = [str(c) for c in A["cols"]]; assert cols == [str(c) for c in T["cols"]]
        for nm, Z in (("R18", A), ("T1", T)):
            cfg = json.loads(str(Z["config_json"]))
            assert cfg["CAL"] == "log" and cfg["PHI"] == 0.45 and cfg["LEGS"] == "101" and cfg["WRULE"] == "msharpe" and cfg["LOOK"] == 900, (nm, s, cfg)
            assert cfg["UMASK_SCOPE"] == "m1" and cfg["FTRIM"] == "zero" and cfg["MEMBERS_TOPN"] == 829 and str(cfg["FSEED"]) == s, (nm, s, cfg)
            assert str(cfg["COSTB_JSON"]).endswith("costb_PWR_G230k.json") and str(cfg["SLOW_NPY"]).endswith("SLOW_v3_on_v4axis.npy"), (nm, s, cfg)
            assert cfg["R18"]["R18_ELIG"] == 0 and cfg["R18"]["R18_WARM"] == 0, (nm, s, cfg["R18"])
            cfgs[nm + "_s" + s] = dict(CAL=cfg["CAL"], PHI=cfg["PHI"], LEGS=cfg["LEGS"], WRULE=cfg["WRULE"], LOOK=cfg["LOOK"], UMASK_SCOPE=cfg["UMASK_SCOPE"],
                                       FTRIM=cfg["FTRIM"], MEMBERS_TOPN=cfg["MEMBERS_TOPN"], FSEED=cfg["FSEED"], COSTB_JSON=cfg["COSTB_JSON"], SLOW_NPY=cfg["SLOW_NPY"],
                                       FPRED=cfg.get("FPRED"), R18=cfg["R18"], T1=cfg.get("T1"))
        rec = np.asarray(A["d30_n2_c42_rec"], np.float64); recT = np.asarray(T["d30_n2_c42_rec"], np.float64)
        assert rec.shape == (N_REC, 23) and rec.tobytes() == recT.tobytes(), ("G-IN rec R18 vs T1 not bitwise", s)
        ts = rec[:, cols.index("ts")].astype(np.int64)
        assert np.array_equal(ts, pts), ("rec ts vs PANEL ts", s)
        assert np.array_equal(ets[META_OFF:META_OFF + N_REC], ts), ("META E_ts[i+138] vs rec ts", s)
        W = np.asarray(A["d30_n2_c42_W"]); assert W.dtype == np.float32 and W.shape == (N_REC, 829)
        agg = np.asarray(T["d30_n2_c42_T1AGG"], np.float64); assert agg.shape == (N_REC, 6, 4)
        axes = [str(x) for x in T["d30_n2_c42_T1AGG_axes"]]
        assert axes[0].startswith("rows: pnlL,pnlS,carL,carS,costL,costS") and axes[1].startswith("cols: king,rev24,fund,f10"), axes
        gt = rec[:, cols.index("gross_total")]
        c = lambda k: rec[:, cols.index(k)]
        D["W_" + s] = W
        D["GT_" + s] = gt
        D["NET_" + s] = c("net_ex") / gt
        D["PRICE_" + s] = c("pnl_ex") / gt
        D["CARRY_" + s] = c("carry_ex") / gt
        D["COST_" + s] = c("cost_ex") / gt
        D["LONG_" + s] = agg[:, 0, :].sum(axis=1) / gt
        D["SHORT_" + s] = agg[:, 1, :].sum(axis=1) / gt
        if s == SEEDS[0]:
            D["TS"] = ts
        else:
            assert np.array_equal(D["TS"], ts)
    rep["arm_config"] = cfgs
    ts = D["TS"]
    assert ts[0] % 86400 == 0 and np.array_equal(ts, ts[0] + 14400 * np.arange(N_REC, dtype=np.int64)), "rec axis not contiguous 4h from 00Z"
    assert int((ts <= UB).sum()) == N_FULL and bool((ts[:N_FULL] <= UB).all()), "W_FULL count"
    assert ts[ALPHA0] == calendar.timegm((2022, 6, 30, 0, 0, 0)), "W_ALPHA start"
    assert (N_FULL - ALPHA0) == N_ALPHA and N_FULL % 6 == 0 and N_ALPHA % 6 == 0 and N_FULL // 6 == NDAYS_FULL and N_ALPHA // 6 == NDAYS_ALPHA
    rep["axis"] = dict(first=utc(ts[0]), w_full_last=utc(ts[N_FULL - 1]), w_alpha_first=utc(ts[ALPHA0]), n_rec=N_REC, n_full=N_FULL, n_alpha=N_ALPHA)
    return D, rep


def folds(ts_full):
    """ts_full: W_FULL ts (length 10038). Returns [(name, train_bool, test_bool)] per §3.4 with count assertions."""
    assert len(ts_full) == N_FULL
    out = []; union = np.zeros(N_FULL, bool)
    for name, lo, hi, n in FOLDS:
        te = (ts_full >= lo) & (ts_full <= hi); tr = ts_full < lo
        assert int(te.sum()) == n, (name, int(te.sum()), n)
        assert not (union & te).any(); union |= te
        out.append((name, tr, te))
    assert int(union.sum()) == N_ALPHA and bool(union[ALPHA0:].all()) and not union[:ALPHA0].any()
    return out


# ------------------------------------------------------------------ features (§4)
def comp(D, k, q):
    """R24 (q=6) / R72 (q=18) at meta row k: Π_{rows k-q..k-1}(1+y) − 1, NaN unless all q finite."""
    blk = D["Y"][k - q:k]
    fin = np.isfinite(blk).all(axis=0)
    out = np.full(blk.shape[1], np.nan)
    out[fin] = np.prod(1.0 + blk[:, fin], axis=0) - 1.0
    return out


def mkt4(D, i):
    """EW 4h market return that closed at E_i over A4_i (U row i ∧ finite y4[k(i)−1])."""
    if i < 0:
        return np.nan
    r = D["Y"][i + D["OFF"] - 1]
    A = D["U"][i] & np.isfinite(r)
    return float(r[A].mean()) if int(A.sum()) >= MINSET else np.nan


def fund_stats(D, j):
    if j < 0:
        return np.nan, np.nan
    fn = D["FN"][j]; iv = D["IV"][j]
    with np.errstate(invalid="ignore"):
        ivf = np.where(np.isfinite(iv) & (iv > 0), iv, 8.0)
    F = D["U"][j] & np.isfinite(fn)
    if int(F.sum()) < MINSET:
        return np.nan, np.nan
    rn8 = fn[F] * 8.0 / ivf[F]
    return float(1e4 * rn8.mean()), float(1e4 * rn8.std())


def market_row(D, i):
    """Columns 1–17 of §4.2 at rec row i (k = i + OFF, j = i)."""
    k = i + D["OFF"]; j = i; Y = D["Y"]; U = D["U"][j]; b = D["BTC"]
    r4 = Y[k - 1]; r24 = comp(D, k, 6); r72 = comp(D, k, 18)
    A4 = U & np.isfinite(r4); A24 = U & np.isfinite(r24); A72 = U & np.isfinite(r72)
    out = np.full(NMKT, np.nan)
    out[0] = r4[b]; out[1] = r24[b]; out[2] = r72[b]
    for c, v, A in ((3, r4, A4), (4, r24, A24), (5, r72, A72)):
        Aa = A.copy(); Aa[b] = False
        if int(Aa.sum()) >= MINSET and np.isfinite(v[b]):
            out[c] = float(v[Aa].mean()) - float(v[b])
    if int(A4.sum()) >= MINSET:
        out[6] = float((r4[A4] > 0).mean()); out[8] = float(r4[A4].std())
    if int(A24.sum()) >= MINSET:
        out[7] = float((r24[A24] > 0).mean()); out[9] = float(r24[A24].std())
    m6 = np.array([mkt4(D, i - q) for q in range(6)])
    m42 = np.array([mkt4(D, i - q) for q in range(42)])
    if np.isfinite(m6).all():
        out[10] = float(np.sqrt(np.sum(m6 ** 2)))
    if np.isfinite(m42).all():
        out[11] = float(np.sqrt(np.sum(m42 ** 2)))
    mu, sg = fund_stats(D, j); mu6, sg6 = fund_stats(D, j - 6)
    out[12] = mu; out[13] = sg; out[14] = mu - mu6; out[15] = sg - sg6
    tb = D["TBF"][j]; At = A24 & np.isfinite(tb)
    if int(At.sum()) >= MINSET:
        out[16] = float((tb[At] - 0.5).mean())
    return out


def reshape_row(w32):
    """Executor reshape of the arm's sm row (A0 device semantics): demean over |sm|>1e-12, rescale L1 back to Σ|sm|."""
    w = np.asarray(w32, np.float64)
    smr = w.copy(); nz = np.abs(w) > 1e-12
    if nz.any():
        smr[nz] -= smr[nz].mean()
        g0 = np.abs(w).sum(); g1 = np.abs(smr).sum()
        if g1 > 1e-9:
            smr *= g0 / g1
    return smr


def member_row(D, i):
    """Device member set m_i: MEMBERS_TOPN=829 rebuild from META qvk (nan→−1, keep > −0.5; 829 = all) ∩ UMASK row j."""
    q = np.nan_to_num(D["QVK"][i + D["OFF"]], nan=-1.0)
    return (q > -0.5) & D["U"][i]


def book_row(D, i, s):
    """Columns 18–24 of §4.2 at rec row i for arm seed s."""
    k = i + D["OFF"]; j = i
    smr = reshape_row(D["W_" + s][i]); mem = member_row(D, i)
    fn = D["FN"][j]; iv = D["IV"][j]
    with np.errstate(invalid="ignore"):
        ivf = np.where(np.isfinite(iv) & (iv > 0), iv, 8.0)
    rn8 = fn * 8.0 / ivf
    r72 = comp(D, k, 18)
    out = np.full(NF - NMKT, np.nan)
    for c, side in ((0, smr < 0), (2, smr > 0)):
        S1 = mem & side & np.isfinite(rn8); w1 = np.abs(smr[S1])
        if w1.sum() > 0:
            out[c] = float(1e4 * (w1 * rn8[S1]).sum() / w1.sum())
        S2 = mem & side & np.isfinite(r72); w2 = np.abs(smr[S2])
        if w2.sum() > 0:
            out[c + 1] = float((w2 * r72[S2]).sum() / w2.sum())
    net = D["NET_" + s]
    if i >= 1:
        out[4] = float(net[i - 1])
    if i >= 6:
        out[5] = float(net[i - 6:i].mean())
    if i >= 42:
        out[6] = float(net[i - 42:i].mean())
    return out


def features_row(D, i, s):
    return np.concatenate([market_row(D, i), book_row(D, i, s)])


def forward_spread_mkt(D, i):
    """Forward (E_i, E_i+4h] EW alt−BTC spread S_i and EW market MKT_i (decomposition / G2a only, never a feature)."""
    r = D["Y"][i + D["OFF"]]; b = D["BTC"]
    A = D["U"][i] & np.isfinite(r)
    Aa = A.copy(); Aa[b] = False
    S = float(r[Aa].mean()) - float(r[b]) if (int(Aa.sum()) >= MINSET and np.isfinite(r[b])) else np.nan
    MK = float(r[A].mean()) if int(A.sum()) >= MINSET else np.nan
    return S, MK


# ------------------------------------------------------------------ family (§5)
def clip_target(t):
    lo, hi = np.quantile(t, [0.005, 0.995])
    return np.clip(t, lo, hi)


class FoldPrep:
    """§5.1 P1–P3 for one fold on a fixed feature matrix F (rows = W_FULL)."""
    def __init__(self, F, tr, te):
        fin = np.isfinite(F[tr]).all(axis=1)
        self.tr_idx = np.nonzero(tr)[0][fin]; self.te_idx = np.nonzero(te)[0]
        Xtr = F[self.tr_idx].copy(); Xte = F[self.te_idx].copy()
        med = np.median(Xtr, axis=0)
        bad = ~np.isfinite(Xte)
        self.n_drop = int(tr.sum() - fin.sum()); self.n_imp = int(bad.sum())
        self.n_imp_by_feat = [int(x) for x in bad.sum(axis=0)]
        if bad.any():
            Xte[bad] = np.take(med, np.nonzero(bad)[1])
        lo = np.quantile(Xtr, 0.005, axis=0); hi = np.quantile(Xtr, 0.995, axis=0)
        Xtr = np.clip(Xtr, lo, hi); Xte = np.clip(Xte, lo, hi)
        mu = Xtr.mean(axis=0); sd = Xtr.std(axis=0)
        zero = sd < 1e-12; sds = np.where(zero, 1.0, sd)
        Xtr = (Xtr - mu) / sds; Xte = (Xte - mu) / sds
        Xtr[:, zero] = 0.0; Xte[:, zero] = 0.0
        self.zero = [int(x) for x in np.nonzero(zero)[0]]
        self.Xtr = Xtr; self.Xte = Xte; self.XtX = Xtr.T @ Xtr


def fit_ridge(P, y):
    yc = clip_target(y[P.tr_idx]); yb = float(yc.mean()); alpha = float(len(P.tr_idx))
    beta = np.linalg.solve(P.XtX + alpha * np.eye(P.Xtr.shape[1]), P.Xtr.T @ (yc - yb))
    return yb + P.Xte @ beta, yb + P.Xtr @ beta, dict(beta=beta, intercept=yb, alpha=alpha)


def fit_lgbm(P, y):
    import lightgbm as lgb
    yc = clip_target(y[P.tr_idx])
    bst = lgb.train(dict(LGB_PARAMS), lgb.Dataset(P.Xtr, label=yc), num_boost_round=LGB_ROUNDS)
    return bst.predict(P.Xte), bst.predict(P.Xtr), dict(gain=bst.feature_importance(importance_type="gain"), num_trees=bst.num_trees())


def oos(preps, y, model):
    """Pooled OOS predictions on W_FULL rows (NaN outside W_ALPHA) + per-fold training predictions and model info."""
    p = np.full(N_FULL, np.nan); trp = []; info = []
    for P in preps:
        pt, pin, inf = (fit_ridge if model == "R" else fit_lgbm)(P, y)
        p[P.te_idx] = pt; trp.append(pin); info.append(inf)
    return p, trp, info


# ------------------------------------------------------------------ statistics (§6)
def pearson(x, y):
    x = np.asarray(x, np.float64) - np.mean(x); y = np.asarray(y, np.float64) - np.mean(y)
    d = np.sqrt((x * x).sum() * (y * y).sum())
    return float((x * y).sum() / d) if d > 0 else float("nan")


def spearman(x, y):
    return pearson(rankdata(x), rankdata(y))


def draw_counts(nd, base):
    """r18_judge.py L65/L74 stream convention: replicate b uses default_rng([20260905, base + b]).integers(0, nd, nd)."""
    C = np.zeros((NB, nd))
    for b in range(NB):
        C[b] = np.bincount(np.random.default_rng([20260905, base + b]).integers(0, nd, nd), minlength=nd)
    return C


def day_moments(x, y, day, nd):
    x = np.asarray(x, np.float64); y = np.asarray(y, np.float64)
    return np.stack([np.bincount(day, minlength=nd).astype(np.float64), np.bincount(day, x, nd), np.bincount(day, y, nd),
                     np.bincount(day, x * x, nd), np.bincount(day, y * y, nd), np.bincount(day, x * y, nd)], axis=1)


def boot_r(C, mom):
    S = C @ mom
    n, sx, sy, sxx, syy, sxy = (S[:, q] for q in range(6))
    cov = sxy - sx * sy / n; vx = sxx - sx * sx / n; vy = syy - sy * sy / n
    den = np.sqrt(np.clip(vx, 0, None) * np.clip(vy, 0, None))
    return np.where(den > 0, cov / np.where(den > 0, den, 1.0), 0.0)   # §6: undefined replicate counted as 0


def ci95(v):
    lo, hi = np.percentile(v, [2.5, 97.5])
    return [float(lo), float(hi)]

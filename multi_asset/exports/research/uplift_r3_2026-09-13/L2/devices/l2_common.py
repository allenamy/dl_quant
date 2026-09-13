"""l2_common.py — L2 (squeeze-risk name-level direction gate) shared definitions for the pod2 devices.
Stage A scope: inputs + sha pins, run discipline (env whitelist, <= 8 cores, GPU / protected-PID state), rec axis,
A0 arm loading (r18 C0 == archived A0; T1 per-leg component books), the fund-leg short population.
Stage A reads NO return array: META is opened through LoggedNpz and every device asserts 'y4' was never fetched;
the PANEL return-like keys (Y4, Y24, f_rev_*, f_mom_*) are never fetched either. Never run alone."""
import os, sys, json, time, hashlib, subprocess, calendar
import numpy as np

L2 = "/workspace/uplift_r3_2026-09-13/L2"
INPUTS = {   # identical paths / shas to T8 PREREG §2 (A0 = r18 C0 = archived A0; T1 arms carry the per-leg smr components)
    "ARM_R18_s42": ("/workspace/uplift_2026-09-11/r18_foundation/arms/C0_s42.npz", "d6298deb8d89df54149d82df72d1fe606062cc74a2bfe6b93d0a27ffed3f5340"),
    "ARM_R18_s2027": ("/workspace/uplift_2026-09-11/r18_foundation/arms/C0_s2027.npz", "fa5ed19a546c4230d673c4d922ac1c98c1888bf032280fb4da1dbee1d1258f2b"),
    "ARM_T1_s42": ("/workspace/uplift_r2_2026-09-13/T1/arms/C0_s42.npz", "93484e8186cabc7ab4d739b283665453542b4ea32eb00e9334be5c7879d0dd09"),
    "ARM_T1_s2027": ("/workspace/uplift_r2_2026-09-13/T1/arms/C0_s2027.npz", "d23e4503dfcb44cccf4d9d0ae4ffa0fd1735fba5516d425b8d1b733f7901623c"),
    "META": ("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz", "0e3c09ac86c727ac1a7893889918e3b367463fd059a154f5e320eed47f5725c3"),
    "PANEL": ("/workspace/data/wide_panel_4h_v2ext.npz", "5e67c0559daa904d8f0526b6e268e93dcb45aab89d82646cf79a794445481116"),
    "UMASK": ("/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz", "47d87b5165b695a7d9b340134a189dd6a2165c837bab35808b699ffac3f7f1b5"),
}
SEEDS = ("42", "2027")
LEGS = ("king", "rev24", "fund", "f10"); FUND = 2
META_OFF = 138; N_REC = 10039; N_FULL = 10038; NW = 829
UB = calendar.timegm((2026, 8, 30, 20, 0, 0))
DUST = 1e-12                       # |weight| below this is numerical zero (device nz rule uses the same 1e-12)
FTRIM_TH = -0.0010                 # A0 config FTRIM=zero, FTRIM_TH default -0.0010 (8h-equivalent rate); asserted from config_json
WHITE = {"PATH", "HOME", "LC_CTYPE", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"}
WHITE_VAL = {"OMP_NUM_THREADS": "8", "OPENBLAS_NUM_THREADS": "8", "MKL_NUM_THREADS": "8"}
BANNED = ("CAL", "LEGS", "PHI", "FSEED", "FTRIM", "UMASK", "SLOW", "FPRED", "MEMBERS_TOPN", "COSTB", "R18", "T1_", "SMA", "SBAND", "OUT_TAG",
          "JUDGE", "PANEL", "PYTHON", "LOOK", "WRULE", "W3FIX", "SEAT", "KMOD", "LGB", "T8_", "L2_", "CUDA", "NVIDIA")


def sha256(p):
    h = hashlib.sha256(); n = 0
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b); n += len(b)
    assert n == os.path.getsize(p) and n > 0, ("short or empty read", p, n)
    d = h.hexdigest()
    assert d != "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", ("empty-content sha on", p)
    return d


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
    assert os.nice(0) >= 10, ("process niceness below 10", os.nice(0))
    return dict(env_whitelist=sorted(white), env_actual={k: os.environ[k] for k in sorted(os.environ)}, launch_cmdline=" ".join(argv), affinity=aff,
                nice=os.nice(0), python=sys.version.split()[0], numpy=np.__version__)


def sysstate():
    def run(cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout.strip()
        except Exception as e:  # recorded, never silent
            return "ERR " + repr(e)
    return dict(utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                gpu=run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader"]),
                protected_pids=run(["ps", "-o", "pid,stat", "-p", "333197,339489"]), loadavg=open("/proc/loadavg").read().strip())


def jdump(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, sort_keys=False, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    os.replace(tmp, path)


def utc(t):
    return time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))


def year_of(ts):
    return np.array([time.gmtime(int(t)).tm_year for t in ts], np.int64)


class LoggedNpz:
    """np.load(npz) wrapper recording every member fetched (receipts prove which arrays a device read)."""
    def __init__(self, path, **kw):
        self.z = np.load(path, **kw); self.read = []
    def __getitem__(self, k):
        self.read.append(k); return self.z[k]
    def keys(self):
        return list(self.z.keys())


def input_shas(check=True):
    rep = {}
    for key, (p, s) in INPUTS.items():
        got = sha256(p) if check else None
        if check:
            assert got == s, ("input sha mismatch", key, got)
        rep[key] = dict(path=p, realpath=os.path.realpath(p), sha256=got, size=os.path.getsize(p))
    return rep


def reshape_row(w32):
    """Executor reshape of the arm's sm row (A0 device semantics; = t8_common.reshape_row)."""
    w = np.asarray(w32, np.float64)
    smr = w.copy(); nz = np.abs(w) > DUST
    if nz.any():
        smr[nz] -= smr[nz].mean()
        g0 = np.abs(w).sum(); g1 = np.abs(smr).sum()
        if g1 > 1e-9:
            smr *= g0 / g1
    return smr


def load_axis_and_masks():
    """META (E_ts, qvk only), PANEL (ts, symbols, f_fund_now, f_fund_iv only), UMASK. Returns (D, readers)."""
    M = LoggedNpz(INPUTS["META"][0], allow_pickle=False)
    P = LoggedNpz(INPUTS["PANEL"][0], allow_pickle=True)
    Um = LoggedNpz(INPUTS["UMASK"][0], allow_pickle=True)
    D = {}
    psym = [str(x) for x in P["symbols"]]
    assert len(psym) == NW and psym == [str(x) for x in Um["symbols"]], "PANEL vs UMASK symbols"
    D["SYM"] = psym
    pts = P["ts"].astype(np.int64); uts = Um["ts"].astype(np.int64)
    assert pts.shape == (N_REC,) and np.array_equal(pts, uts), "PANEL ts vs UMASK ts"
    ets = M["E_ts"].astype(np.int64); qvk = np.asarray(M["qvk"], np.float32)
    assert ets.shape == (10182,) and qvk.shape == (10182, NW)
    D["E_TS"] = ets; D["QVK"] = qvk; D["PTS"] = pts
    D["FN"] = np.asarray(P["f_fund_now"], np.float64); D["IV"] = np.asarray(P["f_fund_iv"], np.float64)
    D["U"] = np.asarray(Um["mask"], bool)
    assert D["FN"].shape == (N_REC, NW) and D["IV"].shape == (N_REC, NW) and D["U"].shape == (N_REC, NW)
    return D, dict(META=M, PANEL=P, UMASK=Um)


def assert_no_returns_read(readers):
    rd = {k: list(v.read) for k, v in readers.items()}
    assert "y4" not in rd["META"], ("META y4 was fetched", rd["META"])
    bad = [k for k in rd["PANEL"] if k in ("Y4", "Y24", "elig") or k.startswith(("f_rev", "f_mom"))]
    assert bad == [], ("PANEL return-like keys fetched", bad)
    return rd


def load_arm(seed, D):
    """One seed: r18 C0 arm (rec, W) + T1 C0 arm (rec, W bitwise equal; T1SMR per-leg smr components; T1MEM; T1RN; T1ID)."""
    A = np.load(INPUTS["ARM_R18_s" + seed][0], allow_pickle=False)
    T = np.load(INPUTS["ARM_T1_s" + seed][0], allow_pickle=False)
    assert [str(x) for x in A["symbols"]] == D["SYM"] and [str(x) for x in T["symbols"]] == D["SYM"], "ARM symbols vs PANEL"
    cols = [str(c) for c in A["cols"]]; assert cols == [str(c) for c in T["cols"]]
    cfg_out = {}
    for nm, Z in (("R18", A), ("T1", T)):
        cfg = json.loads(str(Z["config_json"]))
        assert cfg["CAL"] == "log" and cfg["PHI"] == 0.45 and cfg["LEGS"] == "101" and cfg["WRULE"] == "msharpe" and cfg["LOOK"] == 900, (nm, seed, cfg)
        assert cfg["UMASK_SCOPE"] == "m1" and cfg["FTRIM"] == "zero" and cfg["MEMBERS_TOPN"] == 829 and str(cfg["FSEED"]) == seed, (nm, seed, cfg)
        assert str(cfg["COSTB_JSON"]).endswith("costb_PWR_G230k.json") and str(cfg["SLOW_NPY"]).endswith("SLOW_v3_on_v4axis.npy"), (nm, seed, cfg)
        assert cfg["R18"]["R18_ELIG"] == 0 and cfg["R18"]["R18_WARM"] == 0, (nm, seed, cfg["R18"])
        assert "FTRIM_TH" in cfg and float(cfg["FTRIM_TH"]) == FTRIM_TH and cfg["RNSM"] == 0, (nm, seed, cfg.get("FTRIM_TH"), cfg.get("RNSM"))
        cfg_out[nm] = {k: cfg.get(k) for k in ("CAL", "PHI", "LEGS", "WRULE", "LOOK", "UMASK_SCOPE", "FTRIM", "FTRIM_TH", "MEMBERS_TOPN", "FSEED",
                                               "COSTB_JSON", "SLOW_NPY", "FPRED", "RNSM", "LTRIM_TH")}
        cfg_out[nm]["R18"] = cfg["R18"]; cfg_out[nm]["T1"] = cfg.get("T1")
    assert cfg_out["T1"]["T1"] and cfg_out["T1"]["T1"]["T1_INSTR"] == 1, cfg_out["T1"]["T1"]
    rec = np.asarray(A["d30_n2_c42_rec"], np.float64); recT = np.asarray(T["d30_n2_c42_rec"], np.float64)
    assert rec.shape == (N_REC, 23) and rec.tobytes() == recT.tobytes(), ("rec R18 vs T1 not bitwise", seed)
    W = np.asarray(A["d30_n2_c42_W"]); WT = np.asarray(T["d30_n2_c42_W"])
    assert W.dtype == np.float32 and W.shape == (N_REC, NW) and W.tobytes() == WT.tobytes(), ("W R18 vs T1 not bitwise", seed)
    ts = rec[:, cols.index("ts")].astype(np.int64)
    assert np.array_equal(ts, D["PTS"]), ("rec ts vs PANEL ts", seed)
    assert np.array_equal(D["E_TS"][META_OFF:META_OFF + N_REC], ts), ("META E_ts[i+138] vs rec ts", seed)
    assert ts[0] % 86400 == 0 and np.array_equal(ts, ts[0] + 14400 * np.arange(N_REC, dtype=np.int64)), "rec axis not contiguous 4h from 00Z"
    assert int((ts <= UB).sum()) == N_FULL and bool((ts[:N_FULL] <= UB).all()), "W_FULL count"
    smrc = np.asarray(T["d30_n2_c42_T1SMR"]); assert smrc.shape == (N_REC, 4, NW) and smrc.dtype == np.float32
    mem = np.asarray(T["d30_n2_c42_T1MEM"]); assert mem.shape == (N_REC, NW) and mem.dtype == bool
    rn = np.asarray(T["d30_n2_c42_T1RN"]); assert rn.shape == (N_REC, NW)
    t1id = np.asarray(T["d30_n2_c42_T1ID"], np.float64); assert t1id.shape[0] == N_REC
    return dict(rec=rec, cols=cols, ts=ts, W=W, SMRC=smrc, MEM=mem, RN=rn, T1ID=t1id, cfg=cfg_out)


def rn8_device(D, j):
    """A0 device _fnp at panel row j over ALL names: FN*(8/IV if IV>0 else 8), NaN -> 0 (w10_sleeve L246)."""
    iv = D["IV"][j]
    with np.errstate(invalid="ignore"):
        r = D["FN"][j] * (8.0 / np.where(iv > 0, iv, 8.0))
    return np.where(np.isfinite(r), r, 0.0)


def population_row(smrc_row, mem_row):
    """Fund-leg short population at one rec row: member ∧ book executed smr < -DUST ∧ fund-leg smr component < -DUST.
    smrc_row: (4, NW) per-leg components of the executed reshaped position (king, rev24, fund, f10); Σ_legs = smr."""
    c = np.asarray(smrc_row, np.float64)
    smr = c.sum(axis=0)
    P = mem_row & (smr < -DUST) & (c[FUND] < -DUST)
    return P, smr, c[FUND]

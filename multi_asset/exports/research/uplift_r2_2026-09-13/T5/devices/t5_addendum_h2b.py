#!/usr/bin/env python3
"""t5_addendum_h2b.py — pod2, ADDENDUM 1 (spec `ADDENDUM_1_SPEC_T5_2026-09-13.md`, sha asserted). POST-HOC descriptive proxy for (e):
replay king score K0 (= SLOW_v3_on_v4axis, col80 v0) -> T4 K1 (same boosters, col80 v1) on every one of the 1024 bridge nodes.
`xz` and `simulate` are taken verbatim from t5_bridge.py by AST (sha asserted); data loading mirrors t5_bridge.py.
Launch: env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root /workspace/venv/bin/python devices/t5_addendum_h2b.py PATH,HOME,LC_CTYPE
"""
import os, sys, json, time, hashlib, subprocess, math, ast
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE and sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
from scipy.stats import rankdata
R = "/workspace/uplift_r2_2026-09-13/T5"; T4K = "/workspace/uplift_r2_2026-09-13/T4/kings"
SPEC_SHA = "54c4d8fb6e021b510f97095ea4996c4e8d300b81d0ce243c9e69176d2a9d88ae"; BRIDGE_SHA = "d5e84953e24f523125b831a1908731ed19953e744230619efa8d41a873d58f38"
K0_SHA = "647673183e6af44ac5b2570b856692c9d2d51ab9f17194bfebb7a0d3dbbd9009"; K1_SHA = "a41d9027ea633c92a0bd712d89a86b7cf3cdfa65402c06f831570b86acdca605"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def sh(cmd):
    try: return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as e: return "ERR %s" % e
assert sha(R + "/ADDENDUM_1_SPEC_T5_2026-09-13.md") == SPEC_SHA, "spec sha"
assert sha(R + "/devices/t5_bridge.py") == BRIDGE_SHA, "bridge sha"
assert sha(T4K + "/K0_v4axis.npy") == K0_SHA and sha(T4K + "/K1_v4axis.npy") == K1_SHA, "T4 king arrays sha"
GPU0 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID0 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2")
assert GPU0.replace(" ", "") == "0%,2MiB", ("GPU NOT IDLE, QUEUE", GPU0)
t0 = time.time(); B = 2000
utc = lambda t: time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
MAIN = json.load(open(R + "/receipts/RECEIPT_T5_bridge.json")); COMP = np.load(R + "/receipts/T5_bridge_components.npz")
assert sha(R + "/receipts/T5_bridge_components.npz") == MAIN["components_npz_sha256"]
ING = np.load(R + "/receipts/T5_live_ingredients.npz", allow_pickle=True)
SYM = [str(s) for s in ING["symbols"]]; NW = len(SYM); CAL = [int(x) for x in ING["cal"]]; AT5 = [int(x) for x in ING["at5"]]; nC = len(CAL)
PM = ING["PM"]; LIVE = ING["LIVE"]; W3M = ING["W3M"]; SEL = ING["SEL"]; FED = ING["FED"]; KC = ING["KC"]; FC = ING["FC"]; WTL = ING["WTL"]
WARM = {1787702400: (ING["WARM_0826_kc"], ING["WARM_0826_fc"]), 1788062400: (ING["WARM_0830_kc"], ING["WARM_0830_fc"])}
NONCOMBO = (1788033600, 1788048000); A0826_00 = 1787702400; A0830_04 = 1788062400
kAT5 = [k for k, A in enumerate(CAL) if A in AT5]
PXz = np.load("/workspace/uplift_2026-09-11/r6/out/wide_panel_4h_v2ext_x0910.npz", allow_pickle=True); assert [str(s) for s in PXz["symbols"]] == SYM
tsP = PXz["ts"].astype(np.int64); prow = {int(t): j for j, t in enumerate(tsP)}
FNx = PXz["f_fund_now"].astype(np.float64); IVx = PXz["f_fund_iv"].astype(np.float64); IVfx = np.where(np.isfinite(IVx) & (IVx > 0), IVx, 8.0)
C4x = np.nan_to_num(FNx, nan=0.0) * (4.0 / IVfx); C4 = np.stack([C4x[prow[A]] for A in CAL])
SMA = 0.1; SBAND = 2.5e-4; PHI = 0.45; FTRIM_TH = float("-0.0010")
GROUPS = ["T", "W", "B", "V", "M", "X", "S", "P", "H", "Z"]; NG = len(GROUPS); GI = {g: q for q, g in enumerate(GROUPS)}; FULL = (1 << NG) - 1; KD = None
src = open(R + "/devices/t5_bridge.py").read(); tree = ast.parse(src)
mod = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ("xz", "simulate")], type_ignores=[])
exec(compile(mod, "t5_bridge_functions", "exec"), globals())
K0 = np.load(T4K + "/K0_v4axis.npy", mmap_mode="r"); K1 = np.load(T4K + "/K1_v4axis.npy", mmap_mode="r")
DUMP = {}
GA1 = {}
for s in ("42", "2027"):
    Z = np.load(R + "/arms/C0_s%s_t5.npz" % s, allow_pickle=True); pre = "d30_n2_c42_T5_"
    d = {k[len(pre):]: Z[k] for k in Z.files if k.startswith(pre)}
    rows = d["i"].astype(np.int64)
    k0 = np.array(K0[rows]); k1 = np.array(K1[rows])
    same = bool(np.array_equal(np.isnan(k0), np.isnan(d["SLOW"])) and np.array_equal(k0[~np.isnan(k0)], d["SLOW"][~np.isnan(d["SLOW"])]) and k0.dtype == d["SLOW"].dtype)
    GA1[s] = dict(K0_rows_equal_dump_SLOW=same, dtype=str(k0.dtype), K1_dtype=str(k1.dtype))
    DUMP[s] = d; d1 = dict(d); d1["SLOW"] = k1.astype(d["SLOW"].dtype); DUMP[s + "k1"] = d1
    # descriptive: king score change on the window (member rank correlation, A_T5)
    rho = []
    for k in kAT5:
        r = k + 1; m = np.where(d["mem"][r])[0]; a = xz(d["SLOW"][r][m]); b = xz(DUMP[s + "k1"]["SLOW"][r][m]); ok = np.isfinite(a) & np.isfinite(b)
        rho.append(float(np.corrcoef(a[ok], b[ok])[0, 1]))
    GA1[s]["king_rank_corr_K0_K1_mean"] = float(np.mean(rho)); GA1[s]["king_rank_corr_K0_K1_min"] = float(np.min(rho))
G_A1 = dict(per_seed=GA1, PASS=all(v["K0_rows_equal_dump_SLOW"] for v in GA1.values()))
print("G-A1", json.dumps(G_A1), flush=True); assert G_A1["PASS"]
from multiprocessing import Pool
def task(args):
    s, bits = args; v, _, dg, _ = simulate(s, bits); return s, bits, v, len(dg["skipped"])
V = {s: np.full((1 << NG, nC), np.nan) for s in DUMP}; SK = {s: 0 for s in DUMP}
with Pool(40) as pool:
    for s, bits, v, nsk in pool.imap_unordered(task, [(s, b) for s in DUMP for b in range(1 << NG)], chunksize=8):
        V[s][bits] = v; SK[s] += nsk
ki = np.array(kAT5); days = np.array([A // 86400 for A in AT5])
def boot_ratio(num, den, k):
    u, inv = np.unique(days, return_inverse=True); nd = len(u)
    sn = np.bincount(inv, weights=num, minlength=nd); sdn = np.bincount(inv, weights=den, minlength=nd)
    rng = np.random.default_rng([20260905, k]); dr = rng.integers(0, nd, size=(B, nd))
    rep = sn[dr].sum(1) / sdn[dr].sum(1)
    return [float(sn.sum() / sdn.sum()), float(np.percentile(rep, 2.5)), float(np.percentile(rep, 97.5))]
popc = np.array([bin(b).count("1") for b in range(1 << NG)]); c11 = [math.factorial(q) * math.factorial(10 - q) / math.factorial(11) for q in range(11)]
OUT = {}
for s in ("42", "2027"):
    V0 = V[s][:, ki]; V1 = V[s + "k1"][:, ki]
    g_main = bool(np.array_equal(V0, COMP["s%s_V" % s][:, ki]))
    DEL = COMP["s%s_DEL" % s]
    dK = V1 - V0
    phiK1 = sum(c11[popc[b]] * dK[b] for b in range(1 << NG))
    OUT[s] = dict(gate_K0_nodes_equal_main_run=g_main, n_nodes=1 << NG, skips_k0=SK[s], skips_k1=SK[s + "k1"],
                  dK1_at_R=dict(mean=boot_ratio(dK[0], np.ones(len(ki)), 58), share=boot_ratio(dK[0], DEL, 58)),
                  dK1_at_N=dict(mean=boot_ratio(dK[FULL], np.ones(len(ki)), 58), share=boot_ratio(dK[FULL], DEL, 58)),
                  phi_K1=dict(mean=boot_ratio(phiK1, np.ones(len(ki)), 58), share=boot_ratio(phiK1, DEL, 58)),
                  dK1_node_range=[float(dK.mean(1).min()), float(dK.mean(1).max())])
    sh_ = OUT[s]["phi_K1"]["share"][0]
    OUT[s]["reading"] = ("NEGLIGIBLE" if abs(sh_) <= 0.05 else ("NOT NEGLIGIBLE" if abs(sh_) >= 0.20 else "SMALL"))
    assert g_main, "K0 nodes differ from the main run"
print(json.dumps(OUT, indent=1), flush=True)
GPU1 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID1 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2")
RC = dict(self_sha256=sha(os.path.abspath(__file__)), spec_sha256=SPEC_SHA, bridge_sha256=BRIDGE_SHA, label="ADDENDUM 1 (post-hoc proxy for (e); replay king model, col80 v0->v1; not the served 29ffaf58)",
          gate_A1=G_A1, result=OUT, inputs={p: sha(p) for p in (T4K + "/K0_v4axis.npy", T4K + "/K1_v4axis.npy", R + "/receipts/T5_bridge_components.npz", R + "/receipts/T5_live_ingredients.npz")},
          env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), gpu_before=GPU0, gpu_after=GPU1, pids_before=PID0, pids_after=PID1,
          built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=round(time.time() - t0, 1))
json.dump(RC, open(R + "/receipts/RECEIPT_T5_addendum1_h2b.json", "w"), indent=1, default=str)
print("DONE_t5_addendum_h2b", RC["wall_s"])

#!/usr/bin/env python3
"""t4_facts_booster_sample.py — pod2, READ-ONLY, CALIBER IDENTIFICATION ONLY (no return, no IC, no book number).
Question: which caliber (v0 raw-rate EMA / v1 rate*8/iv EMA) was in training column 80 of the two in-service king
boosters? The 9-01 booster's training file still exists (T1: v0 bitwise). The 08-16 booster 29ffaf58's training file
(the August wide_fea_v2ext.npy) was overwritten on 09-01 (retrain MANIFEST D1), so only its model file remains.
LightGBM writes feature_infos=[min:max] per feature from the bin-construction SAMPLE (bin_construct_sample_cnt=200000,
data_random_seed=1 defaults) — a deterministic function of (row count, data). Method: rebuild the training matrix with
the exporter's own rules (pod_export_bundle_v3.py L38-47 == pod_export_shadow_bundle.py L28-36), fit ONE tree with the
exporter's params, read feature_infos, and compare all 78 entries with each booster:
  S-v0   = the 9-01 feature file as stored (col 80 = v0 per T1)
  S-v1   = same, col 80 replaced by float16(nan->0(f_fund_ema_v1)) of the same panel (cells with a panel row only)
  A-v0/A-v1 = the 9-01 feature file with cols 80/81 re-cast from the CANONICAL August panel wide_panel_4h_v1.npz (v0 or
           v1 in col 80; raw now in col 81) — an APPROXIMATION of the August file (kline columns and members from 9-01).
Counts of training cells beyond each booster's recorded extremes are reported under v0 and v1 as a second reading.
"""
import os, sys, json, time, hashlib
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "whitelist argv[1]"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
from scipy.stats import rankdata
T4 = "/workspace/uplift_r2_2026-09-13/T4"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
t0 = time.time()
FEA_P = "/workspace/data/wide_fea_v2ext.npy"; META_P = "/workspace/data/wide_fea_v2ext_meta.npz"
PAN_P = "/workspace/data/wide_panel_4h_v2ext.npz"; PAN1_P = "/workspace/data/wide_panel_4h_v1.npz"
B_SEP = "/workspace/shadow_bundle_v3/slow2026.txt"; B_AUG = T4 + "/private_inputs/slow2026_aug_29ffaf58.txt"
INPUTS = {p: sha(p) for p in (FEA_P, META_P, PAN_P, PAN1_P, B_SEP, B_AUG)}
assert INPUTS[B_SEP].startswith("8d79186b6380132c") and INPUTS[B_AUG].startswith("29ffaf58bcb7281b"), INPUTS
assert INPUTS[FEA_P] == "f88b07205bf19870aefd1ea6f8eaf6f14e78f3587c973f36514b43ea691d4097"
def finfo_str(s):
    for l in s.split("\n"):
        if l.startswith("feature_infos="): return l.strip().split("=", 1)[1].split(" ")
def finfo_file(p): return finfo_str(open(p).read(400000))
FI = {"sep_8d79186b": finfo_file(B_SEP), "aug_29ffaf58": finfo_file(B_AUG)}
F = np.load(FEA_P, mmap_mode="r"); M = np.load(META_P, allow_pickle=True)
names = [str(x) for x in M["names"]]; E = M["E_ts"].astype(np.int64); MS = M["members"]; Y4 = M["y4"]
yrs = np.array([time.gmtime(int(t)).tm_year for t in E])
keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
assert keep.index(80) == 76 and keep.index(81) == 77 and len(keep) == 78
def pan(p):
    P = np.load(p, allow_pickle=True)
    return dict(row={int(t): j for j, t in enumerate(P["ts"].astype(np.int64))}, v0=P["f_fund_ema"], v1=P["f_fund_ema_v1"], now=P["f_fund_now"], sym=[str(s) for s in P["symbols"]])
PV = pan(PAN_P); P1 = pan(PAN1_P); assert PV["sym"] == P1["sym"]
f16 = lambda a: np.float16(np.nan_to_num(a, nan=0.0)).astype(np.float32)
rows = {k: [] for k in ("X", "c80_v1", "a80_v0", "a80_v1", "a81_now")}; Ys = []; YRA = []
for i in range(len(E)):
    m = np.asarray(MS[i], dtype=np.int64); yv = Y4[i, m]; ok = np.isfinite(yv)
    if ok.sum() < 50: continue
    mk = m[ok]
    rows["X"].append(np.asarray(F[i, mk][:, keep], np.float32))
    j = PV["row"].get(int(E[i])); j1 = P1["row"].get(int(E[i]))
    nanc = np.full(len(mk), np.nan, np.float32)
    rows["c80_v1"].append(f16(PV["v1"][j, mk]) if j is not None else nanc)
    rows["a80_v0"].append(f16(P1["v0"][j1, mk]) if j1 is not None else nanc)
    rows["a80_v1"].append(f16(P1["v1"][j1, mk]) if j1 is not None else nanc)
    rows["a81_now"].append(f16(P1["now"][j1, mk]) if j1 is not None else nanc)
    Ys.append((rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5).astype(np.float32)); YRA.append(np.full(ok.sum(), yrs[i], np.int32))
X = np.concatenate(rows["X"]); Y = np.concatenate(Ys); YRA = np.concatenate(YRA); tr = YRA < 2026
C = {k: np.concatenate(v)[tr] for k, v in rows.items() if k != "X"}
Xtr = X[tr]; Ytr = Y[tr]; n_tr = int(tr.sum()); del X
print("train rows", n_tr, round(time.time() - t0, 1), flush=True)
import lightgbm as lgb
def infos(Xv):
    g = lgb.LGBMRegressor(n_estimators=1, learning_rate=0.05, num_leaves=63, subsample=0.8, colsample_bytree=0.8, n_jobs=100, verbose=-1).fit(Xv, Ytr)
    return finfo_str(g.booster_.model_to_string())
VAR = {}
VAR["S_v0_stored"] = infos(Xtr)
x76 = Xtr[:, 76].copy(); x77 = Xtr[:, 77].copy()
Xtr[:, 76] = C["c80_v1"]; VAR["S_v1"] = infos(Xtr)
Xtr[:, 76] = C["a80_v0"]; Xtr[:, 77] = C["a81_now"]; VAR["A_v0_canon"] = infos(Xtr)
Xtr[:, 76] = C["a80_v1"]; VAR["A_v1_canon"] = infos(Xtr)
Xtr[:, 76] = x76; Xtr[:, 77] = x77
def cmp(a, b):
    eq = [k for k in range(78) if a[k] == b[k]]
    return dict(n_equal=len(eq), equal_76=a[76] == b[76], equal_77=a[77] == b[77], kline_cols_equal=sum(1 for k in range(76) if a[k] == b[k]), v76=a[76], v77=a[77])
CMP = {f"{v}_vs_{b}": cmp(VAR[v], FI[b]) for v in VAR for b in FI}
def rng(s): lo, hi = s.strip("[]").split(":"); return float(lo), float(hi)
beyond = {}
for b in FI:
    lo, hi = rng(FI[b][76])
    for lab, arr in (("v0_stored_0901", x76), ("v1_0901panel", C["c80_v1"]), ("v0_canon_aug", C["a80_v0"]), ("v1_canon_aug", C["a80_v1"])):
        fin = np.isfinite(arr)
        beyond[f"{b}|{lab}"] = dict(n_below_min=int((arr[fin] < lo).sum()), n_above_max=int((arr[fin] > hi).sum()), p_sample_misses_all=float((1 - 200000 / n_tr) ** int((arr[fin] < lo).sum() + (arr[fin] > hi).sum())))
OUT = dict(n_train_rows=n_tr, sample_fraction=200000 / n_tr, booster_feature_infos_76_77={b: [FI[b][76], FI[b][77]] for b in FI}, variants_76_77={v: [VAR[v][76], VAR[v][77]] for v in VAR}, compare=CMP, cells_beyond_recorded_extremes=beyond)
RC = dict(self_sha256=sha(os.path.abspath(__file__)), inputs=INPUTS, lightgbm=lgb.__version__, result=OUT, env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}),
          built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=round(time.time() - t0, 1))
json.dump(RC, open(T4 + "/receipts/RECEIPT_T4_facts_booster_sample.json", "w"), indent=1, default=str)
print(json.dumps(OUT, indent=1, default=str)); print("DONE_t4_facts_booster_sample", RC["wall_s"])

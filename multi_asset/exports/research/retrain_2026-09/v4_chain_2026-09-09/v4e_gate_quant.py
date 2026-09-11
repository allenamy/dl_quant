"""PREREG_king_clock_E_2026-09-09 §3 G4 (report only, no verdict): does the float16 storage of training features vs the float32
features the producer feeds the booster change the king's SCORES materially?

For the six frozen anchors: booster = the v4 bundle's slow2026.txt (keep_idx from its config.json). Inputs:
  A  archived offline features (float16 -> float32), the training representation
  B  production-operator float32 values (wstat AST from the read-only producer copy, E-INCLUSIVE clock) + archived fund columns
  C  B rounded through float16 (quantisation only, clock aligned)
  D  offline E-1 clock in float64, rounded through float16 = A recomputed (sanity: must equal A bitwise on the 80 cache columns)
Reports per anchor: Spearman(pred_A, pred_B), Spearman(pred_C, pred_B) [quantisation only], Spearman(pred_A, pred_C) [clock only],
top/bottom-decile overlap, and max |Δpred|. Paths via env like v4e_gate_parity.py; OUT default /workspace/review_scratch/v4_gates/G4_king_quant.json."""
import os, sys, json, ast, time, hashlib, zipfile
import numpy as np
from scipy.stats import rankdata, spearmanr
import lightgbm as lgb

CACHE = os.environ.get("CACHE", "/workspace/data/dlnative_5m_wide829_f16_holefix2.npz")
OLD_FEA = os.environ.get("OLD_FEA", "/workspace/data/wide_fea_v4.npy"); OLD_META = os.environ.get("OLD_META", "/workspace/data/wide_fea_v4_meta.npz")
BUNDLE = os.environ.get("BUNDLE", "/workspace/shadow_bundle_v4")
PROD_SRC = os.environ.get("PROD_SRC", "/workspace/review_scratch/prod_shadow_loop_v3_readonly.py")
OUT = os.environ.get("OUT", "/workspace/review_scratch/v4_gates/G4_king_quant.json")
ANCHORS = [1641600000, 1743825600, 1787184000, 1685577600, 1731657600, 1764604800]
WINDOWS = (48, 288, 864, 2016, 8640); BUF = 11520


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(16 << 20), b""): h.update(b)
    return h.hexdigest()


t0 = time.time()
cfg = json.load(open(f"{BUNDLE}/config.json")); keep = list(cfg["keep_idx"])
booster = lgb.Booster(model_file=f"{BUNDLE}/slow2026.txt")
z = np.load(CACHE); ts = z["ts"].astype(np.int64); symbols = z["symbols"]; nw = len(symbols)
mo = np.load(OLD_META, allow_pickle=True); Eo = mo["E_ts"].astype(np.int64); names = [str(x) for x in mo["names"]]
assert [names[k] for k in keep] == list(cfg["keep_names"]), "keep_names mismatch vs bundle config"
fo = np.load(OLD_FEA, mmap_mode="r")
tree = ast.parse(open(PROD_SRC, encoding="utf-8").read()); wst = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "wstat"]; assert len(wst) == 1
er = np.searchsorted(ts, ANCHORS); assert np.array_equal(ts[er], ANCHORS)
ranges = [(max(0, int(e) + 1 - BUF), int(e) + 1) for e in er]
zf = zipfile.ZipFile(CACHE); f = zf.open("data.npy"); v = np.lib.format.read_magic(f)
shape, fort, dtype = np.lib.format.read_array_header_1_0(f) if v == (1, 0) else np.lib.format.read_array_header_2_0(f)
bufs = {r: np.empty((r[1] - r[0], nw, 7), "f2") for r in ranges}
for st in range(0, shape[0], 4096):
    nn = min(4096, shape[0] - st); data = np.frombuffer(f.read(nn * nw * 7 * 2), "f2").reshape(nn, nw, 7)
    for (lo, hi) in ranges:
        a = max(st, lo); b = min(st + nn, hi)
        if a < b: bufs[(lo, hi)][a - lo:b - lo] = data[a - st:b - st]
f.close(); zf.close()


def prod_values(buf, ai, dtype="f4"):
    env = {"np": np, "CDf": buf.astype(dtype), "ai": ai}
    exec(compile(ast.Module(body=wst, type_ignores=[]), "pure_wstat", "exec"), env); raw = []
    for c in range(7):
        for w in WINDOWS: raw.append(env["wstat"](c, w, "sum" if c == 0 else "mean"))
    for w in WINDOWS:
        seg = env["CDf"][max(ai + 1 - w, 0):ai + 1, :, 0]; fin = np.isfinite(seg); n = np.maximum(fin.sum(0), 1)
        mm = np.where(fin, seg, 0).sum(0) / n; raw.append(np.sqrt(np.maximum(np.where(fin, seg ** 2, 0).sum(0) / n - mm ** 2, 0)))
    return raw


def offline64(buf, exclusive_end):
    raw = []
    for c in range(7):
        for w in WINDOWS:
            seg = buf[max(exclusive_end - w, 0):exclusive_end, :, c].astype("f8"); fin = np.isfinite(seg); n = np.maximum(fin.sum(0), 1); ss = np.where(fin, seg, 0).sum(0)
            raw.append((ss if c == 0 else ss / n).astype("f4"))
    for w in WINDOWS:
        seg = buf[max(exclusive_end - w, 0):exclusive_end, :, 0].astype("f8"); fin = np.isfinite(seg); n = np.maximum(fin.sum(0), 1); mm = np.where(fin, seg, 0).sum(0) / n
        raw.append(np.sqrt(np.maximum(np.where(fin, seg ** 2, 0).sum(0) / n - mm ** 2, 0)).astype("f4"))
    return raw


def assemble(raw, member):
    out = np.zeros((len(member), 80), "f4")
    for j, vv in enumerate(raw):
        x = vv[member]; out[:, j * 2] = np.clip(np.nan_to_num(x, nan=0), -1e4, 1e4); ok = np.isfinite(x)
        if ok.sum() >= 10: out[ok, j * 2 + 1] = rankdata(x[ok]) / (ok.sum() - 1) - .5
    return out


def dec_overlap(a, b, q=0.1):
    k = max(int(len(a) * q), 1); ta = set(np.argsort(-a)[:k]); tb = set(np.argsort(-b)[:k]); ba = set(np.argsort(a)[:k]); bb = set(np.argsort(b)[:k])
    return {"top": len(ta & tb) / k, "bottom": len(ba & bb) / k}


rows = []
for t, e, r in zip(ANCHORS, er, ranges):
    ao = int(np.searchsorted(Eo, t))
    if not (ao < len(Eo) and Eo[ao] == t): rows.append({"anchor": t, "skipped": "not on old axis"}); continue
    mem = mo["members"][ao]; buf = bufs[r]; i = int(e) - r[0]
    full = np.asarray(fo[ao, mem, :], "f4")                                  # 82 cols: 80 cache + 2 fund (float16 -> float32)
    A = full.copy()
    B = full.copy(); B[:, :80] = assemble(prod_values(buf, i, "f4"), mem)      # production clock + float32
    Cq = full.copy(); Cq[:, :80] = B[:, :80].astype("f2").astype("f4")         # quantised production values
    D = full.copy(); D[:, :80] = assemble(offline64(buf, i), mem).astype("f2").astype("f4")   # offline E-1 clock recomputed, quantised
    pA, pB, pC, pD = (booster.predict(X[:, keep]) for X in (A, B, Cq, D))
    rows.append({"anchor": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t)), "n_members": int(len(mem)),
                 "sanity_D_equals_A_cells80_f16": int((D[:, :80].astype("f2").view("u2") != A[:, :80].astype("f2").view("u2")).sum()),
                 "spearman_A_vs_B(train_repr_vs_production)": float(spearmanr(pA, pB).correlation),
                 "spearman_C_vs_B(quantisation_only)": float(spearmanr(pC, pB).correlation),
                 "spearman_A_vs_C(clock_only)": float(spearmanr(pA, pC).correlation),
                 "decile_overlap_A_vs_B": dec_overlap(pA, pB), "decile_overlap_C_vs_B": dec_overlap(pC, pB),
                 "maxabs_dpred_A_vs_B": float(np.abs(pA - pB).max()), "maxabs_dpred_C_vs_B": float(np.abs(pC - pB).max()), "pred_std": float(pB.std())})
    print(json.dumps(rows[-1]), flush=True)
res = {"gate": "G4_king_quant_report_only", "rows": rows, "bundle": BUNDLE, "booster_sha256": sha(f"{BUNDLE}/slow2026.txt"), "prod_src_sha256": sha(PROD_SRC),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_s": round(time.time() - t0, 1), "self_sha256": sha(__file__)}
os.makedirs(os.path.dirname(OUT), exist_ok=True); json.dump(res, open(OUT, "w"), indent=1)
print("G4_KING_QUANT_DONE", flush=True)

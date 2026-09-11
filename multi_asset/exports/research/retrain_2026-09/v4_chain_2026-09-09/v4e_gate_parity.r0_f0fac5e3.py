"""PREREG_king_clock_E_2026-09-09 §3 G1: train/serve parity of the E-version king features against the PRODUCTION operator.

Production operator = the pure `wstat` function AST-extracted from a read-only copy of ~/wide_shadow/shadow_loop_v3.py
(sha recorded), run in float32 on the same cache rows with the NEW meta's members (operator isolation, as in the
independent review's clamp_clock harness). 80 columns (40 value + 40 rank) compared at float16 bit level.
  (a) new builder archive vs production operator:   changed cells <= 0.1%  AND  production operator in float64 vs new archive == 0 cells
  (b) positive control: OLD archive (wide_fea_v4) vs production operator:  >= 1000 changed cells (the gate can see the defect)
  (c) axis / member deltas reported.
FAIL -> exit 3. Paths via env: NEW_FEA/NEW_META/OLD_FEA/OLD_META/CACHE/PROD_SRC/OUT."""
import os, sys, json, ast, time, hashlib, zipfile
import numpy as np
from scipy.stats import rankdata

CACHE = os.environ.get("CACHE", "/workspace/data/dlnative_5m_wide829_f16_holefix2.npz")
NEW_FEA = os.environ.get("NEW_FEA", "/workspace/data/wide_fea_v4e.npy"); NEW_META = os.environ.get("NEW_META", "/workspace/data/wide_fea_v4e_meta.npz")
OLD_FEA = os.environ.get("OLD_FEA", "/workspace/data/wide_fea_v4.npy"); OLD_META = os.environ.get("OLD_META", "/workspace/data/wide_fea_v4_meta.npz")
PROD_SRC = os.environ.get("PROD_SRC", "/workspace/review_scratch/prod_shadow_loop_v3_readonly.py")
OUT = os.environ.get("OUT", "/workspace/review_scratch/v4_gates/G1_king_clock_parity.json")
# frozen anchors (PREREG §3): the review's three + three pre-declared
ANCHORS = [1641600000, 1743825600, 1787184000, 1685577600, 1731657600, 1764604800]
WINDOWS = (48, 288, 864, 2016, 8640); BUF = 11520


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(16 << 20), b""): h.update(b)
    return h.hexdigest()


def utc(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


t0 = time.time()
z = np.load(CACHE); ts = z["ts"].astype(np.int64); symbols = z["symbols"]; nw = len(symbols)
mn = np.load(NEW_META, allow_pickle=True); mo = np.load(OLD_META, allow_pickle=True)
En = mn["E_ts"].astype(np.int64); Eo = mo["E_ts"].astype(np.int64); names = [str(x) for x in mn["names"]]
assert names == [str(x) for x in mo["names"]]
fn = np.load(NEW_FEA, mmap_mode="r"); fo = np.load(OLD_FEA, mmap_mode="r")
# production operator: pure wstat from the read-only producer copy (no import of the producer)
tree = ast.parse(open(PROD_SRC, encoding="utf-8").read())
wst = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "wstat"]; assert len(wst) == 1
PROD_WSTAT_SHA = hashlib.sha256(ast.unparse(wst[0]).encode()).hexdigest()
# cache rows for the six anchors, read as a streaming slice of data.npy (no full load)
er = np.searchsorted(ts, ANCHORS); assert np.array_equal(ts[er], ANCHORS), "anchor ts not on the cache grid"
ranges = [(max(0, int(e) + 1 - BUF), int(e) + 1) for e in er]
zf = zipfile.ZipFile(CACHE); f = zf.open("data.npy"); v = np.lib.format.read_magic(f)
shape, fort, dtype = np.lib.format.read_array_header_1_0(f) if v == (1, 0) else np.lib.format.read_array_header_2_0(f)
assert not fort and dtype == np.float16 and shape[1:] == (nw, 7)
bufs = {r: np.empty((r[1] - r[0], nw, 7), "f2") for r in ranges}
for st in range(0, shape[0], 4096):
    nn = min(4096, shape[0] - st); data = np.frombuffer(f.read(nn * nw * 7 * 2), "f2").reshape(nn, nw, 7)
    for (lo, hi) in ranges:
        a = max(st, lo); b = min(st + nn, hi)
        if a < b: bufs[(lo, hi)][a - lo:b - lo] = data[a - st:b - st]
f.close(); zf.close()


def prod_values(buf, ai, dtype="f4"):
    env = {"np": np, "CDf": buf.astype(dtype), "ai": ai}
    exec(compile(ast.Module(body=wst, type_ignores=[]), "pure_wstat", "exec"), env)
    raw = []
    for c in range(7):
        for w in WINDOWS: raw.append(env["wstat"](c, w, "sum" if c == 0 else "mean"))
    for w in WINDOWS:
        seg = env["CDf"][max(ai + 1 - w, 0):ai + 1, :, 0]; fin = np.isfinite(seg); n = np.maximum(fin.sum(0), 1)
        mm = np.where(fin, seg, 0).sum(0) / n; vv = np.sqrt(np.maximum(np.where(fin, seg ** 2, 0).sum(0) / n - mm ** 2, 0)); raw.append(vv)
    return raw


def assemble(raw, member):
    out = np.zeros((len(member), 80), "f4")
    for j, vv in enumerate(raw):
        x = vv[member]; out[:, j * 2] = np.clip(np.nan_to_num(x, nan=0), -1e4, 1e4); ok = np.isfinite(x)
        if ok.sum() >= 10: out[ok, j * 2 + 1] = rankdata(x[ok]) / (ok.sum() - 1) - .5
    return out


def cmp(x, y):
    a = x.astype("f2"); b = y.astype("f2"); d = a.view("u2") != b.view("u2")
    return {"cells": int(a.size), "changed": int(d.sum()), "changed_pct": float(100.0 * d.sum() / a.size),
            "value_cells_changed": int(d[:, ::2].sum()), "rank_cells_changed": int(d[:, 1::2].sum()),
            "maxabs_f16": float(np.nanmax(np.abs(a.astype("f8") - b.astype("f8")))) if d.any() else 0.0}


rows = []; ok_a = True; ok_b = True
for t, e, r in zip(ANCHORS, er, ranges):
    buf = bufs[r]; i = int(e) - r[0]
    an = int(np.searchsorted(En, t)); ao = int(np.searchsorted(Eo, t))
    in_new = an < len(En) and En[an] == t; in_old = ao < len(Eo) and Eo[ao] == t
    row = {"anchor": utc(t), "E_row": int(e), "in_new_axis": bool(in_new), "in_old_axis": bool(in_old), "buffer_rows": int(len(buf))}
    if in_new:
        mem = mn["members"][an]; new = np.asarray(fn[an, mem, :80], "f4")
        p32 = assemble(prod_values(buf, i, "f4"), mem); p64 = assemble(prod_values(buf, i, "f8"), mem)
        row["members_new"] = int(len(mem)); row["a_new_vs_prod32"] = cmp(new, p32); row["a_new_vs_prod64"] = cmp(new, p64)
        ok_a &= (row["a_new_vs_prod32"]["changed_pct"] <= 0.1) and (row["a_new_vs_prod64"]["changed"] == 0)
        if in_old:
            memo = mo["members"][ao]; row["members_old"] = int(len(memo)); row["members_symdiff"] = int(len(set(mem.tolist()) ^ set(memo.tolist())))
            old = np.asarray(fo[ao, memo, :80], "f4"); p32o = assemble(prod_values(buf, i, "f4"), memo)
            row["b_old_vs_prod32_positive_control"] = cmp(old, p32o); ok_b &= row["b_old_vs_prod32_positive_control"]["changed"] >= 1000
    rows.append(row); print(json.dumps(row), flush=True)
res = {"gate": "G1_king_clock_parity", "PASS": bool(ok_a and ok_b), "a_pass": bool(ok_a), "b_positive_control_pass": bool(ok_b),
       "axis": {"n_new": int(len(En)), "n_old": int(len(Eo)), "new_not_in_old": [utc(t) for t in np.setdiff1d(En, Eo)][:10], "old_not_in_new": [utc(t) for t in np.setdiff1d(Eo, En)][:10],
                "n_new_not_in_old": int(len(np.setdiff1d(En, Eo))), "n_old_not_in_new": int(len(np.setdiff1d(Eo, En)))},
       "rows": rows, "prod_src": PROD_SRC, "prod_src_sha256": sha(PROD_SRC), "prod_wstat_ast_sha256": PROD_WSTAT_SHA,
       "inputs_sha256": {"new_meta": sha(NEW_META), "old_meta": sha(OLD_META), "cache": None}, "new_fea_size": os.path.getsize(NEW_FEA), "old_fea_size": os.path.getsize(OLD_FEA),
       "utc": utc(time.time()), "wall_s": round(time.time() - t0, 1), "self_sha256": sha(__file__)}
os.makedirs(os.path.dirname(OUT), exist_ok=True); json.dump(res, open(OUT, "w"), indent=1)
print("G1_KING_CLOCK_PARITY", "PASS" if res["PASS"] else "FAIL", json.dumps({k: res[k] for k in ("a_pass", "b_positive_control_pass", "axis")}))
sys.exit(0 if res["PASS"] else 3)

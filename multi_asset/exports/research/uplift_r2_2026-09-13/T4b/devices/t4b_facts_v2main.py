#!/usr/bin/env python3
"""t4b_facts_v2main.py — pod2, CPU (nice, <=16 threads), READ-ONLY, CALIBER IDENTIFICATION ONLY (no return, IC or book number).
Written before the T4b prereg, to fix the arm set.
F1  served V2MAIN model f10_live_s42_np.npz (= ~/wide_shadow/fea171 copy, sha 351ae26b…): recompute its normalisation with the
    refit's own rule (pod_f10_refit_ext.py L89-93: anchors with >= 50 pairs, first 85%, every 7th anchor, every 3rd row;
    mu = mean(nan->0), sd = std(nan->0, torch N-1) + 1e-6, float32) from the files the yearly V2MAIN run recorded
    (fea82 9bc111a4…, fea89 bebf2720…); compare all 171 columns. Alternative: column 80 re-cast as v1 (float16 of
    f_fund_ema_v1 of wide_panel_4h_v2ext.npz) on the rows where the stored value is non-zero.
F2  what the stored zeros in column 80/81 are: share of zero cells whose symbol is in the pinned live-450 list, share whose panel
    v0 is finite and non-zero (i.e. the build panel lacked funding for the name), by year.
Launch: nice -n 19 taskset -c 0-15 env -i PATH=... HOME=/root OMP_NUM_THREADS=16 MKL_NUM_THREADS=16 OPENBLAS_NUM_THREADS=16 /workspace/venv/bin/python devices/t4b_facts_v2main.py <whitelist>
"""
import os, sys, json, time, hashlib
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "whitelist argv[1]"
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"): assert int(os.environ[k]) <= 16, k
import numpy as np
import torch
torch.set_num_threads(16)
T4B = "/workspace/uplift_r2_2026-09-13/T4b"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
t0 = time.time()
TGP = "/workspace/dlw_ext/data/dlw_targets.npz"; F82P = "/workspace/dlw_ext/data/dlw_fea82.npz"; F89P = "/workspace/f8_ext/data/f8_fea89.npz"
MP = "/workspace/f8_ext/models/f10_live_s42_np.npz"; PANP = "/workspace/data/wide_panel_4h_v2ext.npz"; CFGP = T4B + "/private_inputs/bundle_config.json"
EXP = {TGP: "31d043e8f160a1d4475d5992a069c4b602419d78c7916f710d1e56ae8915caf9", F82P: "9bc111a47cee54fc26193165258a83eb11f59df79bebcd69452532bb4c59678e",
       F89P: "bebf2720315499707e54b53c26d889cbf6f2d2d3184a42455284636c0c5e4d67", MP: "351ae26bd6b4a203431a280427fc0bbc968c66e903532168765d654e7e57b3a4",
       PANP: "5e67c0559daa904d8f0526b6e268e93dcb45aab89d82646cf79a794445481116", CFGP: "3a8422f377519cac77b0c42305d2ba40a4b7a42a830f0542bda844f66647c94e"}
INPUTS = {p: sha(p) for p in EXP}
for p, h in EXP.items(): assert INPUTS[p] == h, ("INPUT SHA", p, INPUTS[p])
TG = np.load(TGP, allow_pickle=True); E_ts = TG["E_ts"].astype(np.int64); nA = len(E_ts); TSYM = [str(s) for s in TG["symbols"]]
FE = np.load(F82P, allow_pickle=True); names82 = [str(n) for n in FE["names"]]; assert names82[80] == "fund_ema" and names82[81] == "fund_now"
pa = FE["pair_a"].astype(np.int64); ps = FE["pair_s"].astype(np.int64); X82 = FE["X"]
F9 = np.load(F89P, allow_pickle=True); assert np.array_equal(F9["pair_a"].astype(np.int64), pa); X89 = F9["X"]
print("loaded", X82.shape, X89.shape, round(time.time() - t0, 1), flush=True)
ST = np.searchsorted(pa, np.arange(nA + 1))
tr_idx = np.array([i for i in range(nA) if ST[i + 1] - ST[i] >= 50]); cut = int(len(tr_idx) * 0.85); tr1 = tr_idx[:cut]
rowsel = np.concatenate([np.arange(ST[i], ST[i + 1]) for i in tr1[::7]]); rows = rowsel[::3]
XS = np.concatenate([X82[rows].astype(np.float32), X89[rows].astype(np.float32)], 1)
def stats(Xn):
    T = torch.nan_to_num(torch.from_numpy(Xn)); return T.mean(0).numpy().astype(np.float64), (T.std(0) + 1e-6).numpy().astype(np.float64)
mu_s, sd_s = stats(XS)
M = np.load(MP); mu_m = M["mu"].astype(np.float64); sd_m = M["sd_"].astype(np.float64)
rel = lambda a, b: np.abs(a - b) / np.maximum(np.abs(b), 1e-12)
F1 = dict(n_rows=int(len(rows)), n_anchors_tr1=int(len(tr1)), trained_through_model=int(M["trained_through"]), targets_last_ts=int(E_ts.max()),
          mu_relmax_all171=float(rel(mu_s, mu_m).max()), sd_relmax_all171=float(rel(sd_s, sd_m).max()),
          mu_relmax_ex80_81=float(np.delete(rel(mu_s, mu_m), [80, 81]).max()), sd_relmax_ex80_81=float(np.delete(rel(sd_s, sd_m), [80, 81]).max()),
          col80=dict(model_mu=float(mu_m[80]), model_sd=float(sd_m[80]), stored_mu=float(mu_s[80]), stored_sd=float(sd_s[80])),
          col81=dict(model_mu=float(mu_m[81]), model_sd=float(sd_m[81]), stored_mu=float(mu_s[81]), stored_sd=float(sd_s[81])))
PW = np.load(PANP, allow_pickle=True); PSYM = [str(s) for s in PW["symbols"]]; assert PSYM == TSYM
prow = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}; V1 = PW["f_fund_ema_v1"]; V0 = PW["f_fund_ema"]
jr = np.array([prow.get(int(E_ts[a]), -1) for a in pa[rows]]); sr = ps[rows]
x80 = XS[:, 80].copy(); nz = (x80 != 0) & (jr >= 0)
alt = x80.copy(); alt[nz] = np.float16(np.nan_to_num(V1[jr[nz], sr[nz]], nan=0.0)).astype(np.float32)
XS[:, 80] = alt; mu_a, sd_a = stats(XS)
F1["col80"].update(v1_alt_mu=float(mu_a[80]), v1_alt_sd=float(sd_a[80]), rows_recast=int(nz.sum()),
                   stored_vs_model_rel=[float(rel(mu_s, mu_m)[80]), float(rel(sd_s, sd_m)[80])], v1alt_vs_model_rel=[float(abs(mu_a[80] - mu_m[80]) / abs(mu_m[80])), float(abs(sd_a[80] - sd_m[80]) / abs(sd_m[80]))])
F1["verdict_col80_caliber"] = ("stored (v0 with zeros)" if (F1["col80"]["stored_vs_model_rel"][0] < 1e-3 and F1["col80"]["stored_vs_model_rel"][1] < 1e-3 and F1["col80"]["v1alt_vs_model_rel"][1] > 0.05) else "NOT DECIDABLE")
del XS
cfg = json.load(open(CFGP)); live = set(cfg["symbols_live"])
live_col = np.array([s in live for s in TSYM])
yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
F2 = {}
for lab, c in (("col80", 80), ("col81", 81)):
    col = X82[:, c]; zero = col == 0
    jall = np.array([prow.get(int(t), -1) for t in E_ts])[pa]; okp = jall >= 0
    v0z = np.zeros(len(col), bool); v0z[okp] = np.isfinite(V0[jall[okp], ps[okp]]) & (V0[jall[okp], ps[okp]] != 0)
    F2[lab] = dict(n_pairs=int(len(col)), zero_share=float(zero.mean()), zero_cells_in_live450_share=float(live_col[ps[zero]].mean()) if zero.any() else None,
                   nonzero_cells_in_live450_share=float(live_col[ps[~zero]].mean()), zero_cells_with_panel_v0_nonzero_share=float(v0z[zero].mean()) if zero.any() else None,
                   zero_share_among_live450_cells=float(zero[live_col[ps]].mean()), zero_share_among_nonlive_cells=float(zero[~live_col[ps]].mean()) if (~live_col[ps]).any() else None,
                   zero_share_by_year={int(y): float(zero[yrs[pa] == y].mean()) for y in sorted(set(yrs[pa].tolist()))},
                   zero_share_live450_by_year={int(y): float(zero[(yrs[pa] == y) & live_col[ps]].mean()) for y in sorted(set(yrs[pa].tolist()))})
OUT = dict(F1_served_model_normalisation=F1, F2_stored_zeros=F2)
RC = dict(self_sha256=sha(os.path.abspath(__file__)), inputs=INPUTS, torch=torch.__version__, numpy=np.__version__, result=OUT,
          env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=round(time.time() - t0, 1))
json.dump(RC, open(T4B + "/receipts/RECEIPT_T4b_facts_v2main.json", "w"), indent=1, default=str)
print(json.dumps(OUT, indent=1, default=str)); print("DONE_t4b_facts_v2main", RC["wall_s"])

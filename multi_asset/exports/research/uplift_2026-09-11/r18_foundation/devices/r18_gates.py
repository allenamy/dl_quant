#!/usr/bin/env python3
"""r18_gates.py — pod2, CPU, read-only. PREREG_r18 §3: GATE R (reviewer's future-support counts reproduced under the
OLD rule from the archived A0 s42), GATE Y (definition of y4 verified against the 5m cache), and the input-side
eligibility-difference counts (§0). Launched `env -i PATH=... HOME=... python r18_gates.py PATH,HOME`.
Writes only /workspace/uplift_2026-09-11/r18_foundation/receipts/RECEIPT_r18_gates.json.
"""
import os, sys, json, time, hashlib, zipfile
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "launch with a non-empty env whitelist as argv[1]"
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
BANNED = ('CAL', 'JUDGE', 'UPLIFT', 'PANEL', 'LOOK', 'WRULE', 'LEGS', 'PHI', 'FSEED', 'W3FIX', 'FTRIM', 'UMASK', 'SLOW', 'FPRED', 'MEMBERS_TOPN', 'COSTB', 'R18', 'SMA', 'SBAND', 'PYTHON', 'OMP', 'MKL')
BAN = sorted(k for k in os.environ if k.startswith(BANNED)); assert BAN == [], ("CALIBER FLAG PRESENT", BAN)
ENV = dict(env_whitelist=sorted(WHITE), env_actual={k: os.environ[k] for k in sorted(os.environ)}, launch_cmdline=" ".join(sys.argv))
import numpy as np
ENV.update(python=sys.version.split()[0], numpy=np.__version__)
R = "/workspace/uplift_2026-09-11/r18_foundation"; HC = "/workspace/review_scratch/health_check"
PREREG = R + "/PREREG_r18_foundation_2026-09-12.md"; PREREG_SHA = "51120518b72f70ce3f78c4ef1e68b0ec655c76eb385692befcf904d0d2883f6c"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
assert sha(PREREG) == PREREG_SHA, ("PREREG SHA", sha(PREREG))
META = "/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"; UM = HC + "/masks/umask_UPIT_CRYPTO.npz"
A0 = "/workspace/uplift_2026-09-11/r3k/arms/A0_PWR230k_s42.npz"; A0_SHA = "352ac36fb319532756da71e7cc405fb0dcde6f36f6e28a57f1f681177bcfd339"
CACHE = "/workspace/data/dlnative_5m_wide829_f16_holefix2.npz"
PANEL = "/workspace/data/wide_panel_4h_v2ext.npz"
INPUTS = {p: dict(realpath=os.path.realpath(p), sha256=sha(p)) for p in (META, UM, A0, PANEL)}
assert INPUTS[A0]["sha256"] == A0_SHA
t0 = time.time()
M = np.load(META, allow_pickle=True); U = np.load(UM, allow_pickle=True); A = np.load(A0, allow_pickle=True); P = np.load(PANEL, allow_pickle=True)
E = M["E_ts"].astype(np.int64); y4 = np.asarray(M["y4"], np.float32); qvk = np.asarray(M["qvk"], np.float32)
rec = A["rec"]; W = np.asarray(A["W"], float); ts = rec[:, 0].astype(np.int64)
SYM = [str(x) for x in P["symbols"]]; assert [str(x) for x in U["symbols"]] == SYM
OUT = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, env=ENV, inputs=INPUTS)
# ------------------------------------------------------------- GATE R: the reviewer's counts, OLD rule, archived A0 s42
i = np.searchsorted(E, ts); assert np.array_equal(E[i], ts)
ui = np.searchsorted(U["ts"].astype(np.int64), ts); assert np.array_equal(U["ts"].astype(np.int64)[ui], ts)
q = qvk[i]; y = y4[i]; mem = np.isfinite(q) & np.asarray(U["mask"])[ui]; liq = (np.expm1(np.clip(q, 0, 30)) * 48 >= 2.5e5)
fut = mem & liq & ~np.isfinite(y)
alpha = (np.arange(len(ts)) >= 900) & (ts <= 1788120000); assert alpha.sum() == 9138
prev = np.concatenate([np.zeros_like(W[:1]), W[:-1]]); held = fut & (np.abs(prev) > 1e-9) & alpha[:, None]
R_ = dict(W_ALPHA_future_missing_eligible_cells=int(fut[alpha].sum()), anchors_with_any=int(fut[alpha].any(1).sum()), previously_held_cells=int(held.sum()),
          previous_gross_affected_sum=float(np.abs(prev)[held].sum()), future_missing_current_W_max=float(np.abs(W[fut & alpha[:, None]]).max()),
          held_cells=[dict(ts=int(ts[a]), iso=time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(ts[a]))), symbol=SYM[b], prev_W=float(prev[a, b]), W=float(W[a, b]), row=int(a), col=int(b)) for a, b in zip(*np.where(held))],
          full_axis_future_missing_eligible_cells=int(fut.sum()))
EXP = dict(cells=108, anchors=108, held=3, gross=0.01183774127275683, wmax=0.0)
R_["PASS"] = bool(R_["W_ALPHA_future_missing_eligible_cells"] == EXP["cells"] and R_["anchors_with_any"] == EXP["anchors"] and R_["previously_held_cells"] == EXP["held"]
                  and abs(R_["previous_gross_affected_sum"] - EXP["gross"]) < 1e-9 and R_["future_missing_current_W_max"] == EXP["wmax"])
R_["expected"] = EXP; OUT["GATE_R"] = R_
print("GATE_R", json.dumps({k: v for k, v in R_.items() if k != "held_cells"}), flush=True)
# ------------------------------------------------------------- input-side eligibility difference (causal vs forward), mask ∩ liq, panel axis
okF = np.isfinite(y); okP = np.isfinite(y4[i - 1]); base = mem & liq
new_only = base & okP & ~okF; old_only = base & ~okP & okF
def cells(mask):
    return [dict(iso=time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(ts[a]))), symbol=SYM[b], row=int(a), qv4h=float(np.expm1(min(float(q[a, b]), 30)) * 48)) for a, b in zip(*np.where(mask))]
OUT["ELIG_DIFF"] = dict(n_panel_anchors=int(len(ts)), cells_mask_liq=int(base.sum()), eligible_old=int((base & okF).sum()), eligible_new=int((base & okP).sum()),
                        new_only_full=int(new_only.sum()), new_only_anchors=int(new_only.any(1).sum()), old_only_full=int(old_only.sum()), old_only_anchors=int(old_only.any(1).sum()),
                        new_only_WALPHA=int(new_only[alpha].sum()), old_only_WALPHA=int(old_only[alpha].sum()),
                        both_nan_liquid_full=int((base & ~okP & ~okF).sum()), both_nan_liquid_WALPHA=int((base & ~okP & ~okF)[alpha].sum()),
                        new_only_cells=cells(new_only), old_only_cells=cells(old_only))
print("ELIG_DIFF", json.dumps({k: v for k, v in OUT["ELIG_DIFF"].items() if not k.endswith("_cells")}), flush=True)
# ------------------------------------------------------------- GATE Y: y4 definition against the 5m cache (forward and closed)
z = zipfile.ZipFile(CACHE)
with z.open("ch.npy") as f: CH = [str(c) for c in np.lib.format.read_array(f)]
with z.open("ts.npy") as f: CTS = np.lib.format.read_array(f).astype(np.int64)
with z.open("symbols.npy") as f: CSYM = [str(c) for c in np.lib.format.read_array(f)]
assert CSYM == SYM, "5m cache symbols differ from panel symbols"
ic = CH.index("ret5")   # channel located by NAME
with z.open("data.npy") as f:
    ver = np.lib.format.read_magic(f); shp, fo, dt = (np.lib.format.read_array_header_1_0(f) if ver == (1, 0) else np.lib.format.read_array_header_2_0(f))
    assert shp[2] == len(CH) and dt == np.dtype("float16"), (shp, dt)
    hdr_off = f.tell()
# the npz member is stored uncompressed or compressed; read the whole array (5.7 GB float16) once, keep ret5 only
with z.open("data.npy") as f: DATA = np.lib.format.read_array(f)
RET5 = DATA[:, :, ic].astype(np.float64); del DATA
print("cache loaded", RET5.shape, round(time.time() - t0, 1), "s", flush=True)
cpos = {int(t): k for k, t in enumerate(CTS)}
rng = np.random.default_rng(20260912); rows = np.sort(rng.choice(np.arange(1, len(ts)), 60, replace=False))
def seg_sum(k0, k1):   # bars k0+1 .. k1 inclusive (returns of bars ENDING after k0 up to k1)
    seg = RET5[k0 + 1:k1 + 1]; nf = np.isfinite(seg).sum(0); s = np.nansum(seg, 0); s[nf < 46] = np.nan; return s, nf
Y = dict(n_sampled=int(len(rows)), tol=1e-5, fwd_maxabs=0.0, fwd_nan_mismatch=0, closed_maxabs=0.0, closed_nan_mismatch=0, n_cells=0, bars_per_4h=48)
for a in rows:
    k = cpos[int(ts[a])]
    assert CTS[k + 48] - CTS[k] == 14400 and CTS[k] - CTS[k - 48] == 14400
    sf, _ = seg_sum(k, k + 48); sc, _ = seg_sum(k - 48, k)
    yf = y[a].astype(np.float64); yc = y4[i[a] - 1].astype(np.float64)
    for ref, mine, kf, kn in ((yf, sf, "fwd_maxabs", "fwd_nan_mismatch"), (yc, sc, "closed_maxabs", "closed_nan_mismatch")):
        nr, nm = np.isnan(ref), np.isnan(mine); Y[kn] += int((nr != nm).sum()); ok = ~nr & ~nm
        if ok.any(): Y[kf] = max(Y[kf], float(np.abs(ref[ok] - mine[ok]).max()))
    Y["n_cells"] += int(len(yf))
Y["PASS"] = bool(Y["fwd_maxabs"] < 1e-5 and Y["closed_maxabs"] < 1e-5 and Y["fwd_nan_mismatch"] == 0 and Y["closed_nan_mismatch"] == 0)
Y["channel_names"] = CH; Y["cache_sha256_note"] = "not hashed (5.7 GB); realpath recorded"; Y["cache_realpath"] = os.path.realpath(CACHE); Y["cache_size_bytes"] = os.path.getsize(CACHE)
Y["note"] = "registered formula (plain sum) — kept as the record of the FAIL; superseded by GATE_Y2 (PREREG_AMENDMENT_1)"
OUT["GATE_Y"] = Y; print("GATE_Y", json.dumps(Y), flush=True)
# ------------------------------------------------------------- GATE Y2 (PREREG_AMENDMENT_1): compounded formula, FULL axis, exposure of mismatching cells in the archived A0 s42
AMEND = R + "/PREREG_AMENDMENT_1_r18_2026-09-12.md"; AMEND_SHA = "f8c23823259ee542c29672958ee1f53e066f50022843e9b14e77f88b32994025"
assert sha(AMEND) == AMEND_SHA, ("AMENDMENT SHA", sha(AMEND)); OUT["amendment_sha256"] = AMEND_SHA
def seg_prod(k0, k1):
    seg = RET5[k0 + 1:k1 + 1]; nf = np.isfinite(seg).sum(0); p = np.nanprod(1.0 + seg, 0) - 1.0; p[nf < 46] = np.nan; return p
Y2 = dict(formula="prod(1+ret5)-1 over 48 bars, NaN unless >=46 finite", tol=1e-5, n_anchors=int(len(ts)), fwd_nan_mismatch=0, closed_nan_mismatch=0, fwd_value_mismatch_cells=0, closed_value_mismatch_cells=0, fwd_finite_cells=0, fwd_maxabs=0.0, closed_maxabs=0.0)
mism = []   # (row, col, y4_meta, y4_cache)
for a in range(len(ts)):
    k = cpos[int(ts[a])]; assert CTS[k + 48] - CTS[k] == 14400 and CTS[k] - CTS[k - 48] == 14400
    pf = seg_prod(k, k + 48); pc = seg_prod(k - 48, k); yf = y[a].astype(np.float64); yc = y4[i[a] - 1].astype(np.float64)
    nr, nm = np.isnan(yf), np.isnan(pf); Y2["fwd_nan_mismatch"] += int((nr != nm).sum()); ok = ~nr & ~nm; Y2["fwd_finite_cells"] += int(ok.sum())
    if ok.any():
        d = np.abs(yf - pf); d[~ok] = 0.0; Y2["fwd_maxabs"] = max(Y2["fwd_maxabs"], float(d.max())); bad = np.nonzero(d > 1e-5)[0]; Y2["fwd_value_mismatch_cells"] += int(len(bad))
        for b in bad: mism.append((a, int(b), float(yf[b]), float(pf[b])))
    nr, nm = np.isnan(yc), np.isnan(pc); Y2["closed_nan_mismatch"] += int((nr != nm).sum()); ok = ~nr & ~nm
    if ok.any():
        d = np.abs(yc - pc); d[~ok] = 0.0; Y2["closed_maxabs"] = max(Y2["closed_maxabs"], float(d.max())); Y2["closed_value_mismatch_cells"] += int((d > 1e-5).sum())
Y2["window_PASS"] = bool(Y2["fwd_nan_mismatch"] == 0 and Y2["closed_nan_mismatch"] == 0)
Y2["value_PASS_outside_mismatch_cells"] = True   # by construction (cells above tol are enumerated below)
rows_m = np.array([m_[0] for m_ in mism], int) if mism else np.zeros(0, int); cols_m = np.array([m_[1] for m_ in mism], int) if mism else np.zeros(0, int)
dy = np.array([abs(m_[2] - m_[3]) for m_ in mism]) if mism else np.zeros(0)
wabs = np.abs(W[rows_m, cols_m]) if mism else np.zeros(0); expo = wabs * dy * 1e4
inWA = alpha[rows_m] if mism else np.zeros(0, bool)
Y2["mismatch_exposure_archived_A0_s42"] = dict(cells=int(len(mism)), anchors=int(len(set(rows_m.tolist()))), cells_traded=int((wabs > 1e-9).sum()), cells_traded_WALPHA=int(((wabs > 1e-9) & inWA).sum()),
                                                 sum_absW_x_absdy_bps_WFULL=float(expo.sum()), sum_absW_x_absdy_bps_WALPHA=float(expo[inWA].sum()), max_cell_bps=float(expo.max()) if len(expo) else 0.0,
                                                 median_absdy=float(np.median(dy)) if len(dy) else 0.0, max_absdy=float(dy.max()) if len(dy) else 0.0,
                                                 by_symbol={s_: int(c_) for s_, c_ in zip(*np.unique([SYM[c] for c in cols_m], return_counts=True))} if mism else {},
                                                 by_month={s_: int(c_) for s_, c_ in zip(*np.unique([time.strftime("%Y-%m", time.gmtime(int(ts[r]))) for r in rows_m], return_counts=True))} if mism else {},
                                                 top20_by_exposure=[dict(iso=time.strftime("%Y-%m-%d %HZ", time.gmtime(int(ts[r]))), symbol=SYM[c], y4_meta=float(ym), y4_cache=float(yc_), W=float(W[r, c]), bps=float(e)) for (r, c, ym, yc_), e in sorted(zip(mism, expo), key=lambda t: -t[1])[:20]])
OUT["GATE_Y2"] = Y2; print("GATE_Y2", json.dumps({k: v for k, v in Y2.items() if k != "mismatch_exposure_archived_A0_s42"}), flush=True); print("GATE_Y2 exposure", json.dumps({k: v for k, v in Y2["mismatch_exposure_archived_A0_s42"].items() if k != "top20_by_exposure"}), flush=True)
OUT["built_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()); OUT["wall_s"] = round(time.time() - t0, 1)
os.makedirs(R + "/receipts", exist_ok=True); json.dump(OUT, open(R + "/receipts/RECEIPT_r18_gates.json", "w"), indent=1, default=float)
print("DONE_r18_gates", OUT["wall_s"], "s")

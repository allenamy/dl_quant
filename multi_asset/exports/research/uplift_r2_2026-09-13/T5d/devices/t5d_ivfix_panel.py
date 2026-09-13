#!/usr/bin/env python3
"""t5d_ivfix_panel.py — pod2, CPU (nice), READ-ONLY inputs (PREREG_T5d §2; gates G-R6, G-IV-LEDGER, G-IV-EXEC, G-SCOPE).
For every panel symbol the funding event stream is rebuilt with the code of r6_panel_splice.py (zips + fund_aug + r6_fund_sep, same dedupe).
Pass 1 recomputes the x0910 tail cells with r6's own iv_full and must equal the x0910 panel bitwise (G-R6). Pass 2 replaces iv_full by iv_true
(producer ledger iv where the settlement is in the ledger, else the timestamp gap snapped to {1,2,4,6,8}) and writes the corrected tail cells into
a copy of the x0910 panel. Only cells that r6 itself writes are recomputed; everything else is copied.
Launch: bash devices/launch_pod2.sh t5d_ivfix_panel.py
"""
import os, io, csv, sys, json, glob, gzip, zipfile, time, hashlib, subprocess
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE and sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
R = "/workspace/uplift_r2_2026-09-13/T5d"; PREREG_SHA = "a1ef16cdba5e95def27f77b180cba3f1ac954ad04c7b0a17f59c24e1a0c85a4f"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()
def sh(cmd):
    try: return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as e: return "ERR %s" % e
U = lambda t: time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
assert sha(R + "/PREREG_T5d_iv_corrected_replay_2026-09-13.md") == PREREG_SHA
GPU0 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID0 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); assert GPU0.replace(" ", "") == "0%,2MiB", GPU0
t0 = time.time()
R6 = "/workspace/uplift_2026-09-11/r6"; SPLICE = R6 + "/r6_panel_splice.py"; BASEP = "/workspace/data/wide_panel_4h_v2ext.npz"; XP = R6 + "/out/wide_panel_4h_v2ext_x0910.npz"
XRC = json.load(open(R6 + "/out/wide_panel_4h_v2ext_x0910_RECEIPT.json")); FSEP = XRC["fund_sep"]; AUGP = "/workspace/fund_aug.json.gz"; FDIR = "/workspace/wide_multisrc/funding"
SRCJ = R + "/inputs/t5d_interval_sources.json"
EXP = {SPLICE: "cccc5b6be9248671ac9370b6313eaa8a3e9b397414d86db18db2b344e836743d", BASEP: "5e67c0559daa904d8f0526b6e268e93dcb45aab89d82646cf79a794445481116",
       XP: "042478f7d8e9f9476341a2acb310828fcf1f5d4a855c2ad0105a08e78f604549", FSEP: XRC["fund_sep_sha256"], SRCJ: "0006e2afffa2c618a033fd1b362680d60444997cc1a696c33f1709eddf9127fd"}
INPUTS = {p: sha(p) for p in list(EXP) + [AUGP]}
for p, h in EXP.items(): assert INPUTS[p] == h, ("INPUT SHA", p, INPUTS[p])
assert XRC["base_sha256"] == INPUTS[BASEP] and XRC["out_sha256"] == INPUTS[XP]
HL = 3 * 86400.0; ALLOWED = np.array([1.0, 2.0, 4.0, 6.0, 8.0])
CAN = np.load(BASEP, allow_pickle=True); X = np.load(XP, allow_pickle=True)
syms = [str(s) for s in X["symbols"]]; assert syms == [str(s) for s in CAN["symbols"]]
ct = CAN["ts"].astype(np.int64); xt = X["ts"].astype(np.int64); nC = len(ct); cut = int(ct[-1]); tail_ts = xt[nC:]
assert np.array_equal(xt[:nC], ct) and len(tail_ts) == 60 and U(cut) == "2026-08-31 00:00Z"
KEYS = ("f_fund_now", "f_fund_iv", "f_fund_ema", "f_fund_ema_v1", "f_fund_ema_v2")
XA = {k: X[k] for k in X.files}
FIX = {k: XA[k].copy() for k in KEYS}
AUG = json.loads(gzip.open(AUGP, "rt").read()); AUG_IV = {k: float(v) for k, v in (AUG.get("intervals") or {}).items() if v}
SEP = json.loads(gzip.open(FSEP, "rt").read()); SEP_IV = {k: float(v) for k, v in (SEP.get("intervals") or {}).items() if v}
SRC = json.load(open(SRCJ)); LED = {s: {int(r[0]): r[1] for r in rows} for s, rows in SRC["ledger"].items()}; EXE = {s: {int(r[0]): r[1] for r in rows} for s, rows in SRC["executor"].items()}
def snap(x): return ALLOWED[np.argmin(np.abs(np.asarray(x, float)[:, None] - ALLOWED[None, :]), axis=1)]
def tail_cells(ft, fr, ivv, seeds):
    """r6_panel_splice.py L102-L128 algebra for one symbol, with the interval vector as input."""
    rate_nf = fr * (8.0 / ivv); sel = ft > cut
    pos = np.searchsorted(ft, tail_ts, side="right") - 1; okp = pos >= 0
    fn = np.full(len(tail_ts), np.nan); fi = np.full(len(tail_ts), np.nan)
    fn[okp] = fr[pos[okp]]; fi[okp] = ivv[pos[okp]]
    stale = okp & ((tail_ts - np.where(okp, ft[np.maximum(pos, 0)], 0)) > 12*3600)
    fn[stale] = np.nan; fi[stale] = np.nan
    out = dict(f_fund_now=fn.astype(np.float32), f_fund_iv=fi.astype(np.float32), inforce=np.where(okp & ~stale, pos, -1))
    if seeds["v1"] is None: return out
    e0, e1, e2 = seeds["v0"], seeds["v1"], seeds["v2"]; prev_t = cut
    ivm = np.median(ivv[sel]) if sel.any() else 8.0
    span = max(2, round(24 / ivm)); al2 = 2.0 / (span + 1.0)
    ptr = np.where(sel)[0]; k2 = 0; E0 = np.full(len(tail_ts), np.nan, np.float32); E1 = E0.copy(); E2 = E0.copy()
    for r_row, t_anchor in enumerate(tail_ts):
        while k2 < len(ptr) and ft[ptr[k2]] <= t_anchor:
            i_ = ptr[k2]
            a = 1 - 0.5 ** (max(ft[i_] - prev_t, 1) / HL)
            e0 = e0 + a * (fr[i_] - e0); e1 = e1 + a * (rate_nf[i_] - e1)
            e2 = e2 + al2 * (rate_nf[i_] - e2) if e2 is not None else rate_nf[i_]
            prev_t = ft[i_]; k2 += 1
        E0[r_row] = np.float32(e0); E1[r_row] = np.float32(e1)
        if e2 is not None: E2[r_row] = np.float32(e2)
    out.update(f_fund_ema=E0, f_fund_ema_v1=E1, f_fund_ema_v2=E2, has_v2=e2 is not None or seeds["v2"] is not None)
    return out
def eqf(a, b): return bool(np.array_equal(np.isnan(a), np.isnan(b)) and np.array_equal(a[~np.isnan(a)], b[~np.isnan(b)]))
G_R6 = dict(symbols_with_rows=0, symbols_seeded=0, mismatch={k: [] for k in KEYS})
IVL = dict(tail_events=0, ledger_source=0, gap_source=0, ledger_vs_gap_mismatch=[], changed_events=0, changed_symbols=[])
IVE = dict(checked=0, mismatch=[], no_stream_event=0)
t_scan0 = time.time()
for j, s in enumerate(syms):
    rows = []
    for zp in sorted(glob.glob(f"{FDIR}/{s}/*.zip")):           # verbatim r6_panel_splice.py L63-L77
        try:
            zf = zipfile.ZipFile(zp)
            with zf.open(zf.namelist()[0]) as fh:
                for row in csv.reader(io.TextIOWrapper(fh)):
                    if not row or not row[0].strip().isdigit() and "time" in row[0].lower(): continue
                    try:
                        ts_ = int(row[0]); rate = float(row[-1]) if abs(float(row[-1])) < 0.2 else float(row[1])
                        iv = np.nan
                        if len(row) >= 3:
                            try:
                                cand = float(row[1])
                                if 1 <= cand <= 24 and abs(cand - round(cand)) < 1e-9 and abs(float(row[-1])) < 0.2: iv = cand
                            except Exception: pass
                        rows.append((ts_ // 1000, rate, iv))
                    except Exception: continue
        except Exception: continue
    for t_ms, rate in (AUG.get("rates") or {}).get(s, []): rows.append((int(t_ms)//1000, float(rate), AUG_IV.get(s, np.nan)))
    for t_ms, rate in (SEP.get("rates") or {}).get(s, []): rows.append((int(t_ms)//1000, float(rate), SEP_IV.get(s, np.nan)))
    if not rows: continue
    rows.sort(); ded = {}
    for t_, r_, i_ in rows:
        if t_ not in ded or np.isfinite(i_): ded[t_] = (r_, i_)
    ft = np.array(sorted(ded), np.int64); fr = np.array([ded[t][0] for t in ft]); fiv = np.array([ded[t][1] for t in ft])
    dt_h = np.round(np.diff(ft) / 3600.0)
    dv = np.full(len(ft), np.nan); dv[1:] = np.where((dt_h > 0) & (dt_h <= 24), dt_h, np.nan)
    iv_full = np.where(np.isfinite(fiv), fiv, dv); iv_full = np.where(np.isfinite(iv_full), iv_full, 8.0)
    iv_full = ALLOWED[np.argmin(np.abs(iv_full[:, None] - ALLOWED[None, :]), axis=1)]
    G_R6["symbols_with_rows"] += 1
    seeds = {nm: (float(CAN[col][-1, j]) if np.isfinite(CAN[col][-1, j]) else None) for nm, col in (("v0", "f_fund_ema"), ("v1", "f_fund_ema_v1"), ("v2", "f_fund_ema_v2"))}
    # ---- pass 1: r6 reproduction
    c1 = tail_cells(ft, fr, iv_full, seeds)
    for k in ("f_fund_now", "f_fund_iv"):
        if not eqf(c1[k], XA[k][nC:, j]): G_R6["mismatch"][k].append(s)
    if seeds["v1"] is not None:
        G_R6["symbols_seeded"] += 1
        for k in ("f_fund_ema", "f_fund_ema_v1", "f_fund_ema_v2"):
            if k == "f_fund_ema_v2" and not c1["has_v2"]: continue
            if not eqf(c1[k], XA[k][nC:, j]): G_R6["mismatch"][k].append(s)
    # ---- iv_true: producer ledger where present, else snapped timestamp gap
    gap = np.where(np.isfinite(dv), ALLOWED[np.argmin(np.abs(np.nan_to_num(dv, nan=8.0)[:, None] - ALLOWED[None, :]), axis=1)], np.nan)
    iv_true = iv_full.copy(); led = LED.get(s, {})
    relevant = ft > cut - 24 * 3600
    for i in np.nonzero(relevant)[0]:
        lv = led.get(int(ft[i]))
        if lv is not None and lv is not False:
            IVL["ledger_source"] += int(ft[i] > cut); iv_true[i] = float(lv)
            if np.isfinite(gap[i]) and float(lv) != float(gap[i]): IVL["ledger_vs_gap_mismatch"].append((s, U(ft[i]), float(lv), float(gap[i])))
        elif np.isfinite(gap[i]):
            IVL["gap_source"] += int(ft[i] > cut); iv_true[i] = float(gap[i])
        IVL["tail_events"] += int(ft[i] > cut)
    chg = relevant & (iv_true != iv_full)
    if chg.any(): IVL["changed_events"] += int(chg.sum()); IVL["changed_symbols"].append(s)
    ex = EXE.get(s, {})
    pos_of = {int(t): i for i, t in enumerate(ft)}
    for t, eiv in ex.items():
        i = pos_of.get(int(t))
        if i is None: IVE["no_stream_event"] += 1; continue
        IVE["checked"] += 1
        if float(iv_true[i]) != float(eiv): IVE["mismatch"].append((s, U(t), float(iv_true[i]), float(eiv), float(iv_full[i]), float(gap[i]) if np.isfinite(gap[i]) else None))
    # ---- pass 2: corrected tail cells (only cells r6 writes)
    c2 = tail_cells(ft, fr, iv_true, seeds)
    FIX["f_fund_now"][nC:, j] = c2["f_fund_now"]; FIX["f_fund_iv"][nC:, j] = c2["f_fund_iv"]
    if seeds["v1"] is not None:
        FIX["f_fund_ema"][nC:, j] = c2["f_fund_ema"]; FIX["f_fund_ema_v1"][nC:, j] = c2["f_fund_ema_v1"]
        if c2["has_v2"]: FIX["f_fund_ema_v2"][nC:, j] = c2["f_fund_ema_v2"]
    if j % 100 == 0: print("sym", j, round(time.time() - t_scan0, 1), flush=True)
G_R6["n_mismatch"] = {k: len(v) for k, v in G_R6["mismatch"].items()}; G_R6["PASS"] = all(v == 0 for v in G_R6["n_mismatch"].values())
print("G-R6", json.dumps(G_R6["n_mismatch"]), G_R6["PASS"], flush=True); assert G_R6["PASS"], "G-R6 failed: stop"
# ---- G-SCOPE
scope = {}
for k in XA:
    if k in ("symbols",): continue
    a = XA[k]; b = FIX[k] if k in FIX else a
    if a.dtype.kind == "f" and a.ndim == 2:
        d = ~((a == b) | (np.isnan(a) & np.isnan(b)))
        scope[k] = dict(cells=int(d.sum()), prefix_cells=int(d[:nC].sum()), names=sorted({syms[q] for q in np.nonzero(d.any(0))[0]}))
    else:
        scope[k] = dict(cells=0 if np.array_equal(a, b) else -1)
allowed = {"f_fund_iv", "f_fund_ema_v1", "f_fund_ema_v2"}
G_SCOPE = dict(per_key={k: v for k, v in scope.items() if v.get("cells")}, PASS=bool(all((v["cells"] == 0) or (k in allowed and v.get("prefix_cells", 0) == 0) for k, v in scope.items())))
print("G-SCOPE", json.dumps({k: (v["cells"], len(v.get("names", []))) for k, v in G_SCOPE["per_key"].items()}), G_SCOPE["PASS"], flush=True); assert G_SCOPE["PASS"], "G-SCOPE failed: stop"
os.makedirs(R + "/panel", exist_ok=True); OUTP = R + "/panel/wide_panel_4h_v2ext_x0910_ivfix.npz"
out = {k: (FIX[k] if k in FIX else XA[k]) for k in XA}
np.savez_compressed(OUTP, **out)
chk = np.load(OUTP, allow_pickle=True); assert sorted(chk.files) == sorted(XA.keys()) and all(chk[k].dtype == XA[k].dtype and chk[k].shape == XA[k].shape for k in XA)
GPU1 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID1 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2")
IVL["n_ledger_vs_gap_mismatch"] = len(IVL["ledger_vs_gap_mismatch"]); IVE["n_mismatch"] = len(IVE["mismatch"])
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, inputs=INPUTS, gate_G_R6=G_R6, gate_G_IV_LEDGER=IVL, gate_G_IV_EXEC=IVE, gate_G_SCOPE=G_SCOPE,
          out=OUTP, out_sha256=sha(OUTP), env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), gpu_before=GPU0, gpu_after=GPU1, pids_before=PID0, pids_after=PID1,
          built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=round(time.time() - t0, 1))
json.dump(RC, open(R + "/receipts/RECEIPT_T5d_ivfix_panel.json", "w"), indent=1, default=str)
print(json.dumps(dict(changed_events=IVL["changed_events"], changed_symbols=IVL["changed_symbols"], ledger_vs_gap=IVL["n_ledger_vs_gap_mismatch"], exec_checked=IVE["checked"], exec_mismatch=IVE["n_mismatch"], out_sha256=RC["out_sha256"])))
print("DONE_t5d_ivfix_panel", RC["wall_s"])

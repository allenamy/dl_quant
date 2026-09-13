#!/usr/bin/env python3
"""t5d_posthoc_seed.py — pod2, CPU (nice, single process), READ-ONLY. POST-HOC (after RECEIPT_T5d_posthoc.json showed 68 pre-cut event-stream settlements
on COTI, IOST and ZKC whose stream interval differs from the producer ledger while the base panel's in-force f_fund_iv matches the ledger everywhere).
Question: which interval vector reproduces the stored incumbent f_fund_ema_v1 path of the base panel (the seed that T5c and T5d both continue)?
For every panel name with ledger rows: start from the stored v1 at 2026-08-28 00Z and run the r6 recursion e += a (rate·8/iv − e), a = 1 − 0.5^(max(Δt,1)/3d),
over the settlements up to 08-31 00Z with (L) ledger/gap intervals and (S) event-stream intervals, under two conventions for the first Δt
(anchor time, as r6 continues; previous settlement time). Compare with the stored float32 v1 at each anchor.
Launch: bash devices/launch_pod2.sh t5d_posthoc_seed.py
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
PRC = json.load(open(R + "/receipts/RECEIPT_T5d_ivfix_panel.json")); PH = json.load(open(R + "/receipts/RECEIPT_T5d_posthoc.json"))
R6 = "/workspace/uplift_2026-09-11/r6"; BASEP = "/workspace/data/wide_panel_4h_v2ext.npz"; XRC = json.load(open(R6 + "/out/wide_panel_4h_v2ext_x0910_RECEIPT.json"))
FSEP = XRC["fund_sep"]; AUGP = "/workspace/fund_aug.json.gz"; FDIR = "/workspace/wide_multisrc/funding"; SRCJ = R + "/inputs/t5d_interval_sources.json"
EXP = {BASEP: PRC["inputs"][BASEP], FSEP: PRC["inputs"][FSEP], AUGP: PRC["inputs"][AUGP], SRCJ: PRC["inputs"][SRCJ]}
INPUTS = {p: sha(p) for p in EXP}
for p, h in EXP.items(): assert INPUTS[p] == h, ("INPUT SHA", p)
HL = 3 * 86400.0; ALLOWED = np.array([1.0, 2.0, 4.0, 6.0, 8.0]); LO = 1787875200   # 2026-08-28 00Z
CAN = np.load(BASEP, allow_pickle=True); syms = [str(s) for s in CAN["symbols"]]; ct = CAN["ts"].astype(np.int64); cut = int(ct[-1]); V1 = CAN["f_fund_ema_v1"]; FIV = CAN["f_fund_iv"]
r0 = int(np.nonzero(ct == LO)[0][0]); rows_ = np.arange(r0, len(ct))
AUG = json.loads(gzip.open(AUGP, "rt").read()); AUG_IV = {k: float(v) for k, v in (AUG.get("intervals") or {}).items() if v}
SEP = json.loads(gzip.open(FSEP, "rt").read()); SEP_IV = {k: float(v) for k, v in (SEP.get("intervals") or {}).items() if v}
SRC = json.load(open(SRCJ)); LED = {s: {int(r[0]): r[1] for r in rows} for s, rows in SRC["ledger"].items()}
MIS = set(PH["B"]["stream_events"]["names"])
res = {}; summary = {}
for j, s in enumerate(syms):
    led = LED.get(s)
    if not led or not np.isfinite(V1[r0, j]): continue
    rows = []
    for zp in sorted(glob.glob(f"{FDIR}/{s}/*.zip")):           # verbatim stream construction (as t5d_ivfix_panel.py)
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
    dt_h = np.round(np.diff(ft) / 3600.0); dv = np.full(len(ft), np.nan); dv[1:] = np.where((dt_h > 0) & (dt_h <= 24), dt_h, np.nan)
    iv_S = np.where(np.isfinite(fiv), fiv, dv); iv_S = np.where(np.isfinite(iv_S), iv_S, 8.0); iv_S = ALLOWED[np.argmin(np.abs(iv_S[:, None] - ALLOWED[None, :]), axis=1)]
    gap = np.where(np.isfinite(dv), ALLOWED[np.argmin(np.abs(np.nan_to_num(dv, nan=8.0)[:, None] - ALLOWED[None, :]), axis=1)], np.nan)
    iv_L = iv_S.copy()
    for i in range(len(ft)):
        lv = led.get(int(ft[i]))
        if lv is not None: iv_L[i] = float(lv)
        elif np.isfinite(gap[i]): iv_L[i] = float(gap[i])
    sel = np.nonzero((ft > LO) & (ft <= cut))[0]
    if len(sel) == 0: continue
    out = {}
    for ivn, ivv in (("L", iv_L), ("S", iv_S)):
        for conv in ("anchor", "prev_settlement"):
            e = float(V1[r0, j]); prev_t = LO if conv == "anchor" else int(ft[sel[0] - 1]) if sel[0] > 0 else LO
            k2 = 0; errs = []
            for r_ in rows_[1:]:
                A = int(ct[r_])
                while k2 < len(sel) and ft[sel[k2]] <= A:
                    i_ = sel[k2]; a = 1 - 0.5 ** (max(ft[i_] - prev_t, 1) / HL); e = e + a * (fr[i_] * 8.0 / ivv[i_] - e); prev_t = ft[i_]; k2 += 1
                st = V1[r_, j]
                if np.isfinite(st): errs.append(abs(float(np.float32(e)) - float(st)) / max(abs(float(st)), 1e-8))
            out[ivn + "_" + conv] = float(max(errs)) if errs else None
    n_diff = int((iv_L[sel] != iv_S[sel]).sum())
    res[s] = dict(out, n_events=int(len(sel)), n_iv_differs=n_diff)
for conv in ("anchor", "prev_settlement"):
    for ivn in ("L", "S"):
        k = ivn + "_" + conv; vals = [v[k] for v in res.values() if v[k] is not None and v["n_iv_differs"] == 0]
        summary["controls_" + k] = dict(n=len(vals), median_rel_err=float(np.median(vals)) if vals else None, p99=float(np.percentile(vals, 99)) if vals else None, share_le_1e6=float(np.mean(np.array(vals) <= 1e-6)) if vals else None)
MISR = {s: res.get(s) for s in sorted(MIS)}
GPU1 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID1 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2")
RC = dict(label="POST-HOC descriptive; not a gate, not a reading", self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, inputs=INPUTS, window=[U(LO), U(cut)],
          controls_names_without_interval_difference=summary, names_with_stream_ledger_difference=MISR, n_names=len(res),
          gpu_before=GPU0, gpu_after=GPU1, pids_before=PID0, pids_after=PID1, env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=round(time.time() - t0, 1))
json.dump(RC, open(R + "/receipts/RECEIPT_T5d_posthoc_seed.json", "w"), indent=1)
print(json.dumps(dict(summary=summary, mis=MISR), indent=1)); print("DONE_t5d_posthoc_seed", RC["wall_s"])

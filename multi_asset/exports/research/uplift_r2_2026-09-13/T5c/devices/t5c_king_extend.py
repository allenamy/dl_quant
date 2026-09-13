#!/usr/bin/env python3
"""t5c_king_extend.py — pod2, CPU (nice, <= 16 threads), READ-ONLY inputs (PREREG_T5c §3.2).
KA king array on the x0910 axis (10242 x 829, float32): rows for anchors <= 2026-08-30 20Z copied bitwise from SLOW_v3_on_v4axis.npy; rows
2026-08-31 00Z..2026-09-10 20Z = booster 8d79186b (shadow_bundle_v3/slow2026.txt) on the x0910 research features wide_fea_v4_x0910.npy
(column 80 = stored v0), cell rule verbatim from T4 t4_kings.py (members[i][isfinite(y4)] >= 50; float32 of stored float16; 78 keep columns;
PRED[a, cells] = pv). Gate G-KC (not blocking): the same scoring on 2026-01-01..08-30 20Z against SLOW_v3_on_v4axis.
Launch: env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python devices/t5c_king_extend.py PATH,HOME,LC_CTYPE
"""
import os, sys, json, time, hashlib, subprocess, calendar
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE and sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
from scipy.stats import spearmanr
R = "/workspace/uplift_r2_2026-09-13/T5c"
PREREG_SHA = "a669c62782c58d424eed17cf3c7b2a8ad78050c059f43cb2e6496737eaf56a48"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def sh(cmd):
    try: return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as e: return "ERR %s" % e
assert sha(R + "/PREREG_T5c_september_replay_vs_deployed_2026-09-13.md") == PREREG_SHA, "prereg sha"
GPU0 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID0 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2")
assert GPU0.replace(" ", "") == "0%,2MiB", ("GPU NOT IDLE", GPU0)
t0 = time.time()
BOOST = "/workspace/shadow_bundle_v3/slow2026.txt"; FEA = "/workspace/uplift_2026-09-11/r6/out/wide_fea_v4_x0910.npy"; FMETA = "/workspace/uplift_2026-09-11/r6/out/wide_fea_v4_meta_x0910.npz"
K3 = "/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"; XMETA = "/workspace/uplift_2026-09-11/r6/out/meta_newprod_v4_x0910.npz"
EXP = {BOOST: "8d79186b6380132cb67684acf1ebfcdb2c53261c850f46a4908b06bfa7a81282", K3: "647673183e6af44ac5b2570b856692c9d2d51ab9f17194bfebb7a0d3dbbd9009",
       XMETA: "a8eb359701c71acfe853a295eb055bdbb04e1c29b6534ccdf23aeaff69907245", FMETA: "ec791d1f2fb455c3e73381b7f5f828384ed65dbd3c5e1ab3c62ea9f3d182f21d"}
INPUTS = {p: sha(p) for p in (BOOST, K3, XMETA, FMETA, FEA)}
for p, h in EXP.items(): assert INPUTS[p] == h, ("INPUT SHA", p, INPUTS[p])
F = np.load(FEA, mmap_mode="r"); MT = np.load(FMETA, allow_pickle=True); XM = np.load(XMETA, allow_pickle=True)
E = MT["E_ts"].astype(np.int64); members = MT["members"]; y4f = MT["y4"]; names = [str(n) for n in MT["names"]]
assert np.array_equal(E, XM["E_ts"].astype(np.int64)) and F.shape[:2] == (len(E), 829), (F.shape, len(E))
keep = [k for k, nm in enumerate(names) if not (nm.startswith("ret5_sum_48") or nm.startswith("ret5_sum_288"))]
assert len(keep) == 78 and keep.index(80) == 76 and keep.index(81) == 77
S3 = np.load(K3); n4 = S3.shape[0]; assert S3.shape == (10182, 829)
E4 = np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz", allow_pickle=True)["E_ts"].astype(np.int64); assert np.array_equal(E4, E[:n4])
T26 = calendar.timegm((2026, 1, 1, 0, 0, 0)); T_LAST_A0 = calendar.timegm((2026, 8, 30, 20, 0, 0)); T_EXT_LO = calendar.timegm((2026, 8, 31, 0, 0, 0)); T_EXT_HI = calendar.timegm((2026, 9, 10, 20, 0, 0))
assert (T_LAST_A0, T_EXT_LO) == (1788120000, 1788134400)
import lightgbm as lgb
b = lgb.Booster(model_file=BOOST)
def score_rows(idx):
    X, cells, aidx = [], [], []
    nfin_mismatch = 0
    for i in idx:
        m = np.asarray(members[i], dtype=np.int64); yv = y4f[i, m]; ok = np.isfinite(yv)
        nfin_mismatch += int((np.isfinite(XM["y4"][i, m]) != ok).sum())
        if ok.sum() < 50: continue
        mk = m[ok]; X.append(np.asarray(F[i, mk][:, keep]).astype(np.float32)); cells.append(mk); aidx.append(np.full(len(mk), i, np.int64))
    X = np.concatenate(X); C = np.concatenate(cells); Aa = np.concatenate(aidx)
    pv = b.predict(X, num_threads=16)
    return Aa, C, pv, nfin_mismatch
ov = [i for i in range(n4) if T26 <= E[i] <= T_LAST_A0]
Aa, C, pv, nm_ov = score_rows(ov)
P_ov = np.full((len(E), 829), np.nan, np.float32); P_ov[Aa, C] = pv
a = P_ov[ov]; bb = S3[ov]; na, nb = np.isnan(a), np.isnan(bb); both = ~na & ~nb
rho = []
for q, i in enumerate(ov):
    ok = both[q]
    if ok.sum() >= 50: rho.append(float(spearmanr(a[q][ok], bb[q][ok])[0]))
GKC = dict(anchors=len(ov), cells_both_finite=int(both.sum()), nan_pattern_equal=bool(np.array_equal(na, nb)), bitwise_equal_share=float((a[both] == bb[both]).mean()), maxabs=float(np.abs(a[both] - bb[both]).max()),
           spearman_min=float(np.min(rho)), spearman_median=float(np.median(rho)), share_anchors_spearman_ge_0p999=float(np.mean(np.array(rho) >= 0.999)), finiteness_mismatch_fea_vs_newprod_y4=nm_ov)
by_month = {}
for q, i in enumerate(ov):
    mo = time.strftime("%Y-%m", time.gmtime(int(E[i])))
    ok = both[q]
    if ok.sum() >= 50: by_month.setdefault(mo, []).append(float(spearmanr(a[q][ok], bb[q][ok])[0]))
GKC["spearman_median_by_month"] = {mo: float(np.median(v)) for mo, v in sorted(by_month.items())}
print("G-KC", json.dumps(GKC), round(time.time() - t0, 1), flush=True)
ext = [i for i in range(len(E)) if T_EXT_LO <= E[i] <= T_EXT_HI]
assert len(ext) == 66, len(ext)
Ae, Ce, pve, nm_ext = score_rows(ext)
KA = np.full((len(E), 829), np.nan, np.float32); KA[:n4] = S3
assert np.isnan(KA[ext[:6]]).all(), "A0 rows 08-31 expected NaN"
KA[Ae, Ce] = pve
assert np.array_equal(KA[:n4][E[:n4] <= T_LAST_A0], S3[E4 <= T_LAST_A0]) or np.array_equal(np.isnan(KA[:n4][E[:n4] <= T_LAST_A0]), np.isnan(S3[E4 <= T_LAST_A0]))
pre_eq = KA[:n4][E[:n4] <= T_LAST_A0]; s3p = S3[E4 <= T_LAST_A0]
PREFIX = dict(bitwise=bool(np.array_equal(np.isnan(pre_eq), np.isnan(s3p)) and np.array_equal(pre_eq[~np.isnan(pre_eq)], s3p[~np.isnan(s3p)])))
os.makedirs(R + "/kings", exist_ok=True); out = R + "/kings/KA_x0910.npy"; np.save(out, KA)
EXT = dict(anchors=len(ext), first=time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(E[ext[0]]))), last=time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(E[ext[-1]]))), cells=int(len(pve)),
           finite_per_anchor_min=int(np.isfinite(KA[ext]).sum(1).min()), finite_per_anchor_max=int(np.isfinite(KA[ext]).sum(1).max()), finiteness_mismatch_fea_vs_newprod_y4=nm_ext)
GPU1 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID1 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2")
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, inputs=INPUTS, lightgbm=lgb.__version__, numpy=np.__version__, gate_G_KC=GKC, prefix_copy=PREFIX, extension=EXT,
          out=out, out_sha256=sha(out), env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), gpu_before=GPU0, gpu_after=GPU1, pids_before=PID0, pids_after=PID1,
          built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=round(time.time() - t0, 1))
json.dump(RC, open(R + "/receipts/RECEIPT_T5c_king_extend.json", "w"), indent=1, default=str)
print(json.dumps(dict(prefix=PREFIX, extension=EXT, out_sha256=RC["out_sha256"]))); print("DONE_t5c_king_extend", RC["wall_s"])

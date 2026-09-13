#!/usr/bin/env python3
"""S2 A1-NW runner — PREREG_producer_parity_phase2_oos_2026-09-12 AMENDMENT 6 (sha bc57266e…) §A6.4 / §A6.8 GATE S2-P-NW.
Runs the byte-identical r18 research device w10_sleeve_r18.py (9b8a6323…, read in place, never copied or edited) from a dev tree under the P2 root.
Phase 1 (GATE S2-P-NW): the archived r18 NW knobs for both seeds — outputs must equal r18_foundation/arms/NW_s{seed}.npz BITWISE on S0_rec, S0_W,
d30_n2_c42_rec, d30_n2_c42_W, cols, symbols (NaN-aware array equality; the other stored keys are compared and reported, not gated).
Phase 2 (only if phase 1 passes): A1-NW = the identical env dict with exactly two keys changed, SLOW_NPY -> SLOW_v4.npy and FPRED -> f10_v4RAW_s{seed}.npy
(asserted). Env dicts are built exactly as r18_drive.py (BASE + A0(seed) + NW arm keys + OUT_TAG=s{seed}); nothing is inherited.
Writes only under /workspace/uplift_r2_2026-09-13/P2 (work/r18dev, work/r18arms, receipts/S2_R18_runner.json). Prints one S2_R18_RUNNER summary line.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B p2_r18_runner.py PATH,HOME,LC_CTYPE"""
import os, sys, json, time, hashlib, subprocess, shutil
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
import numpy as np
P2 = "/workspace/uplift_r2_2026-09-13/P2"; R18 = "/workspace/uplift_2026-09-11/r18_foundation"; HC = "/workspace/review_scratch/health_check"
PY = "/workspace/venv/bin/python"; DER = R18 + "/devices/w10_sleeve_r18.py"; DER_SHA = "9b8a6323e8f0ac31ecb4046f6759dce09ba89645cbfc356db71f51c662b2c5c4"
PREREG_SHA = "bc57266e5abf103926b2231facb4b12b28137565760ea34b4e8fc49c2cf15769"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def under(p):
    assert os.path.realpath(p).startswith(P2 + "/") or os.path.abspath(p).startswith(P2 + "/"), f"write outside P2 root refused: {p}"
    return p
def sh(cmd):
    try: return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as e: return f"ERR {e}"
T0 = time.time(); SELF_SHA = sha(os.path.abspath(__file__))
IN = {"device": (DER, DER_SHA),
      "meta_newprod_v4": ("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz", "0e3c09ac86c727ac1a7893889918e3b367463fd059a154f5e320eed47f5725c3"),
      "panel_v2ext": ("/workspace/data/wide_panel_4h_v2ext.npz", "5e67c0559daa904d8f0526b6e268e93dcb45aab89d82646cf79a794445481116"),
      "SLOW_v4": ("/workspace/review_scratch/king_v4/SLOW_v4.npy", "dde19142d017c37dd9bae564ab4a32a4b9b068f6aef8acc91e7ea329f4f1c8a6"),
      "SLOW_v3_on_v4axis": ("/workspace/review_scratch/king_v4/SLOW_v3_on_v4axis.npy", "647673183e6af44ac5b2570b856692c9d2d51ab9f17194bfebb7a0d3dbbd9009"),
      "umask_UPIT_CRYPTO": (HC + "/masks/umask_UPIT_CRYPTO.npz", "47d87b5165b695a7d9b340134a189dd6a2165c837bab35808b699ffac3f7f1b5"),
      "costb_PWR_G230k": ("/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json", "295b4e7b462373e495fe995ca993fd7a96ab64d050a66ada0d670acf7e9b3d53"),
      "dlw_v4raw_targets": ("/workspace/dlw_v4raw/data/dlw_targets.npz", "d1976cf6246cdc25054d21b1a9fa7f8fd02ee43278720d81ce2a35686d63c6f8"),
      "f10_A0_s42": (HC + "/dev_v4/f8_2026-08-22/preds/f10_A0_s42.npy", "ff109711f5526c68cebb23599e299041a2310caa7857b5ff9aa50464d2e6077b"),
      "f10_A0_s2027": (HC + "/dev_v4/f8_2026-08-22/preds/f10_A0_s2027.npy", "98bfe779261b550f15bbd511dc4637403b7341b25ccc2d4ee15521cb33787f18"),
      "f10_v4RAW_s42": (HC + "/dev_v4/f8_2026-08-22/preds/f10_v4RAW_s42.npy", "58d64a6ff968458924f53193d2dac20c4541be65d267e108bb43445032bfbdcd"),
      "f10_v4RAW_s2027": (HC + "/dev_v4/f8_2026-08-22/preds/f10_v4RAW_s2027.npy", "47046ccd6dc7937ce39d9d9a880a34984ad4b6f966889505af0255da8adc136d"),
      "nets_stub_d30": ("/workspace/port_w10/pod_backup_2026-08-21/nets_histv2_-30_2_42.npy", "41ec83527689de534587bfaeb08dcd8fc9006051e9bd829bc7d8b19b1fbc39de"),
      "nets_stub_S0": ("/workspace/port_w10/pod_backup_2026-08-21/nets_histv2_0_0_0.npy", "41ec83527689de534587bfaeb08dcd8fc9006051e9bd829bc7d8b19b1fbc39de"),
      "NW_s42_archive": (R18 + "/arms/NW_s42.npz", "afbcd92ea41d7e4cd75159e64e8640dedf7727219dd852df3a1f0ef3e7f4692d"),
      "NW_s2027_archive": (R18 + "/arms/NW_s2027.npz", "89d28a319f2bd61f755cf973d1697f30b6fe0f3dfeb9aad20d2bb553575c11a5")}
for k, (p, s) in IN.items(): assert sha(p) == s, ("input sha", k, p)
PRE = dict(loadavg=open("/proc/loadavg").read().split()[:3], protected_pids=sh("ps -o pid,stat,etime -p 333197,339489"),
           nvidia_smi=sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"), memory_current=sh("cat /sys/fs/cgroup/memory.current"))
assert float(PRE["loadavg"][0]) <= 20.0, ("host busy — queue", PRE["loadavg"])
# dev tree (same link layout as r18_drive.py L38-47, rooted under P2)
D = under(P2 + "/work/r18dev"); BK = D + "/pod_backup_2026-08-21"; OUTD = under(P2 + "/work/r18arms")
for p in (D + "/logs", D + "/probe_artifacts", BK, OUTD): os.makedirs(under(p), exist_ok=True)
LINKS = {BK + "/nets_histv2_-30_2_42.npy": IN["nets_stub_d30"][0], BK + "/nets_histv2_0_0_0.npy": IN["nets_stub_S0"][0],
         BK + "/slow_pred_hist_oos.npy": IN["SLOW_v4"][0], BK + "/wide_fea_hist_meta.npz": IN["meta_newprod_v4"][0],
         BK + "/wide_panel_4h_hist_v2.npz": IN["panel_v2ext"][0], D + "/dlw_2026-08-22": "/workspace/dlw_v4raw", D + "/f8_2026-08-22": HC + "/dev_v4/f8_2026-08-22"}
for t, v in LINKS.items():
    if os.path.islink(t): assert os.readlink(t) == v, (t, os.readlink(t), v)
    else: os.symlink(v, under(t))
BASE = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "HOME": "/root", "OMP_NUM_THREADS": "3", "OPENBLAS_NUM_THREADS": "3", "MKL_NUM_THREADS": "3"}
def A0(seed): return {"LEGS": "101", "PHI": "0.45", "WRULE": "msharpe", "LOOK": "900", "MEMBERS_TOPN": "829", "FTRIM": "zero", "FTRIM_TH": "-0.0010",
                      "UMASK_SCOPE": "m1", "CAL": "log", "FTPOS": "0", "SEATNET": "0", "UMASK_NPZ": IN["umask_UPIT_CRYPTO"][0], "SLOW_NPY": IN["SLOW_v3_on_v4axis"][0],
                      "FSEED": seed, "FPRED": "f10_A0_s%s.npy" % seed, "COSTB_JSON": IN["costb_PWR_G230k"][0]}
NW = {"R18_ELIG": "1", "R18_WARM": "1", "R18_INSTR": "1"}
def env_nw(seed):
    e = dict(BASE); e.update(A0(seed)); e.update(NW); e["OUT_TAG"] = "s" + seed; return e
def env_a1nw(seed):
    e = env_nw(seed); e["SLOW_NPY"] = IN["SLOW_v4"][0]; e["FPRED"] = "f10_v4RAW_s%s.npy" % seed; return e
for s in ("42", "2027"):
    a, b = env_nw(s), env_a1nw(s)
    assert sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k)) == ["FPRED", "SLOW_NPY"], "A6.8: A1-NW env must differ from NW in exactly SLOW_NPY and FPRED"
def run(tag, seed, env):
    src = D + "/probe_artifacts/w10_ablation_series_s%s.npz" % seed; summ = D + "/probe_artifacts/w10_ablation_summary_s%s.json" % seed
    for p in (src, summ):
        if os.path.exists(p): os.remove(under(p))
    t = time.time(); logp = under(D + "/logs/%s.log" % tag)
    with open(logp, "w") as lf:
        p = subprocess.Popen(["nice", "-n", "10", PY, DER], cwd=D, stdout=lf, stderr=subprocess.STDOUT, env=env)
    return dict(tag=tag, seed=seed, proc=p, t0=t, log=logp, src=src, summ=summ, env=env)
def finish(job):
    rc = job["proc"].wait(); job["rc"] = rc; job["secs"] = round(time.time() - job["t0"], 1)
    tail = open(job["log"], errors="replace").read().strip().splitlines()[-2:]
    out = under(OUTD + "/%s.npz" % job["tag"])
    if rc == 0 and os.path.exists(job["src"]):
        shutil.move(job["src"], out); shutil.move(job["summ"], under(OUTD + "/%s_summary.json" % job["tag"]))
        Z = np.load(out, allow_pickle=True); cfg = json.loads(str(Z["config_json"]))
        return dict(tag=job["tag"], rc=rc, secs=job["secs"], log_tail=tail, out=out, out_sha256=sha(out), self_sha256_reported=cfg["UPLIFT"]["self_sha256"],
                    cfg_knobs={k: cfg.get(k) for k in ("SLOW_NPY", "FPRED", "FSEED", "CAL", "PHI", "LEGS", "WRULE", "LOOK", "MEMBERS_TOPN", "FTRIM", "FTRIM_TH", "UMASK_SCOPE", "COSTB_JSON")},
                    cfg_R18=cfg.get("R18"), env=job["env"], log=job["log"], log_sha256=sha(job["log"]))
    return dict(tag=job["tag"], rc=rc, secs=job["secs"], log_tail=tail, FAIL=True, env=job["env"], log=job["log"])
def bitwise(a, b):
    a = np.asarray(a); b = np.asarray(b)
    if a.shape != b.shape or a.dtype != b.dtype:
        return dict(bitwise=False, shape_a=list(a.shape), shape_b=list(b.shape), dtype_a=str(a.dtype), dtype_b=str(b.dtype))
    if a.dtype.kind in "fc":
        na, nb = np.isnan(a), np.isnan(b); ok = bool(np.array_equal(na, nb) and np.array_equal(a[~na], b[~nb]))
        return dict(bitwise=ok, shape=list(a.shape), maxabs=0.0 if ok else float(np.nanmax(np.abs(a.astype(float) - b.astype(float)))))
    return dict(bitwise=bool(np.array_equal(a, b)), shape=list(a.shape))
OUT = dict(device="p2_r18_runner.py", self_sha256=SELF_SHA, prereg_sha256=PREREG_SHA, argv=sys.argv, env=dict(os.environ), python=sys.version.split()[0], numpy=np.__version__,
           inputs={k: dict(path=p, sha256=s) for k, (p, s) in IN.items()}, links=LINKS, preflight=PRE, base_env=BASE)
# phase 1: NW reproduction, both seeds concurrently (3 threads each)
jobs = [run("NWrepro_s%s" % s, s, env_nw(s)) for s in ("42", "2027")]
R1 = {j["tag"]: finish(j) for j in jobs}
GATE = {}
GATED = ("S0_rec", "S0_W", "d30_n2_c42_rec", "d30_n2_c42_W", "cols", "symbols")
for s in ("42", "2027"):
    r = R1["NWrepro_s%s" % s]
    if r.get("FAIL"): GATE["s" + s] = dict(PASS=False, why="run failed", rc=r["rc"]); continue
    A = np.load(r["out"], allow_pickle=True); B = np.load(IN["NW_s%s_archive" % s][0], allow_pickle=True)
    keys = sorted(set(A.files) | set(B.files)); cmp_ = {}
    for k in keys:
        if k not in A.files or k not in B.files: cmp_[k] = dict(bitwise=False, missing_in=("new" if k not in A.files else "archive")); continue
        if k == "config_json": cmp_[k] = dict(equal=str(A[k]) == str(B[k])); continue
        cmp_[k] = bitwise(A[k], B[k])
    GATE["s" + s] = dict(compare=cmp_, self_sha_ok=r["self_sha256_reported"] == DER_SHA, PASS=bool(all(cmp_.get(k, {}).get("bitwise") for k in GATED) and r["self_sha256_reported"] == DER_SHA))
GATE_PASS = bool(GATE["s42"]["PASS"] and GATE["s2027"]["PASS"])
OUT.update(phase1_runs=R1, GATE_S2_P_NW=dict(gated_keys=list(GATED), per_seed=GATE, PASS=GATE_PASS))
R2 = {}
if GATE_PASS:
    jobs = [run("A1NW_s%s" % s, s, env_a1nw(s)) for s in ("42", "2027")]
    R2 = {j["tag"]: finish(j) for j in jobs}
    for s in ("42", "2027"):
        r = R2["A1NW_s%s" % s]
        if not r.get("FAIL"):
            assert r["self_sha256_reported"] == DER_SHA
            assert r["cfg_knobs"]["SLOW_NPY"] == IN["SLOW_v4"][0] and r["cfg_knobs"]["FPRED"] == "f10_v4RAW_s%s.npy" % s, r["cfg_knobs"]
OUT.update(phase2_runs=R2, A1NW_all_rc0=bool(GATE_PASS and all(not r.get("FAIL") and r["rc"] == 0 for r in R2.values()) and len(R2) == 2),
           postflight=dict(loadavg=open("/proc/loadavg").read().split()[:3], protected_pids=sh("ps -o pid,stat,etime -p 333197,339489"),
                           nvidia_smi=sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader")),
           wall_s=round(time.time() - T0, 1), utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
rp = under(P2 + "/receipts/S2_R18_runner.json"); json.dump(OUT, open(rp + ".tmp", "w"), indent=1, default=str); os.replace(rp + ".tmp", rp)
print("S2_R18_RUNNER GATE_S2_P_NW=%s NWrepro_rc=%s A1NW_rc=%s A1NW_all_rc0=%s wall_s=%s receipt_sha256=%s" % (
    "PASS" if GATE_PASS else "RED", [R1[t]["rc"] for t in sorted(R1)], [R2[t]["rc"] for t in sorted(R2)], OUT["A1NW_all_rc0"], OUT["wall_s"], sha(rp)), flush=True)
sys.exit(0 if (GATE_PASS and OUT["A1NW_all_rc0"]) else 3)

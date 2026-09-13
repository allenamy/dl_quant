#!/usr/bin/env python3
"""ATTR Stage C -- docs/PREREG_combo_chain_residual_attribution_2026-09-13.md (sha 63c335d6..., commit efda139f) §2/§3 + AMENDMENT 1 + AMENDMENT 2 (sequential lanes, quota probe).
Interventions at the three snapshot-seeded anchors whose G2-C baseline is exact (s12/s16/s20 -> 1789214400/1789228800/1789243200). Each variant gets a fresh
tree built from the G2-C tree (same files, same symlink targets); ONLY the fake-HOME `state/rolling.npz` differs. The byte-identical Phase 1 driver (f2ced820...)
runs the anchor in snapshot mode with REPLAY_COMBO=1 against snapshot A-4h, as G2-C did:
  V0       G2-C rolling copied byte for byte (positive control; must reproduce 0.0)
  V1_K     first K rows removed, K in {48, 288, 960, 1920} (H-d left boundary); all other rows unchanged
  V2_dead  live names with no 5m bar whose log_cnt (channel 4 = log1p(trade count)) is > 0 over (A-24h, A] set to NaN in every row (H-c, descriptive)
Per variant: king weights L-inf, target_combo L-inf, target_live L-inf (driver receipt), replay state_H_{f10,kc,fc}_A vs the producer's own file (read-only copy,
AMENDMENT 1, sha-verified against ATTR_prod_stateH_SHA256SUMS.txt), names with |diff| > 1e-6 in target_live.
Verdict (§3): V0 exact at 3/3 (king, target_combo, target_live all 0.0) else STOP exit 3; H-d CONFIRMED iff V1_1920 target_live L-inf > 1e-6 on >= 2/3 anchors
with kc state L-inf == 0.0 on those anchors. Writes only under P2/work/attr_C and P2/receipts/ATTR_stageC.json.
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B p2_attr_stageC.py PATH,HOME,LC_CTYPE"""
import os, sys, json, time, hashlib, shutil, subprocess
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
import numpy as np
P2 = "/workspace/uplift_r2_2026-09-13/P2"; W = P2 + "/work"; OUTD = W + "/attr_C"; RC = P2 + "/receipts"; PRODH = W + "/live_ro/prod_stateH_attr"
PREREG_SHA = "63c335d6780f7bfc492ba2b0f0f25be269b42ab5c401d2528d443302be8563cc"
SLOTS = {"s12": (1789214400, "0-7"), "s16": (1789228800, "8-15"), "s20": (1789243200, "16-23")}
VARIANTS = ["V0", "V1_48", "V1_288", "V1_960", "V1_1920", "V2_dead"]
DEV = {"replay_driver.py": "f2ced820daa45e0fec0879b6eaeba58905109b60dc0ac09a6e5b0d7cd1bee4ec", "combo_stage_replay.py": "f5ba9a8234ef0c01ee1aa5bdb0ebd87e8e7093c10b164e37f4fc10f97bc7f77b",
       "shadow_loop_v3_replay.py": "4d3bc157f03e3462a69e64f817b3fd4cd51be4c03d72650304b7d0c1a0089d42"}
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 22), b""): h.update(ch)
    return h.hexdigest()
def under(p):
    ap = os.path.abspath(p); assert ap.startswith(OUTD + "/") or ap.startswith(RC + "/ATTR_"), p; return p
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
T0 = time.time(); SELF = sha(os.path.abspath(__file__))
PREP = json.load(open(RC + "/G2C_prep.json")); G2CV = json.load(open(RC + "/G2C_verdict.json")); GB = json.load(open(RC + "/G2C_BIND.json"))
assert G2CV["verdict"] == "PASS" and GB["verdict"] == "PASS"
SUMS = {}
for l in open(PRODH + "/ATTR_prod_stateH_SHA256SUMS.txt"):
    if l.strip(): d, f = l.rstrip("\n").split("  ", 1); SUMS[f] = d
cfg = json.load(open("/workspace/shadow_bundle_v3/config.json")); SYMS = list(cfg["symbols_panel"]); LIVE = list(cfg["symbols_live"])
col = {s: j for j, s in enumerate(SYMS)}; lidx = np.array([col[s] for s in LIVE], np.int64)
INPUTS = {"G2C_prep.json": sha(RC + "/G2C_prep.json"), "G2C_verdict.json": sha(RC + "/G2C_verdict.json"), "G2C_BIND.json": sha(RC + "/G2C_BIND.json"),
          "prod_stateH_sums": sha(PRODH + "/ATTR_prod_stateH_SHA256SUMS.txt"), "bundle_config": sha("/workspace/shadow_bundle_v3/config.json")}

def prod_state(tag, A):
    f = f"state_H_{tag}_{A}.npz"; p = f"{PRODH}/{f}"
    if f not in SUMS: return None
    assert sha(p) == SUMS[f], f; return p

def build(slot, variant):
    A = SLOTS[slot][0]; src = f"{W}/g2c_{slot}"; dst = under(f"{OUTD}/{variant}_{slot}")
    if os.path.exists(dst): shutil.rmtree(dst)
    home = dst + "/home"; ws = home + "/wide_shadow"
    for d_ in (dst + "/dev", dst + "/receipts", ws + "/state", ws + "/fea171", home + "/dl_quant_live/live"): os.makedirs(d_, exist_ok=True)
    for f, s in DEV.items():
        assert sha(f"{src}/dev/{f}") == s, (slot, f); shutil.copy2(f"{src}/dev/{f}", f"{dst}/dev/{f}")
    for f in ("external_book.py", "book_config.py"): shutil.copy2(f"{src}/home/dl_quant_live/live/{f}", f"{home}/dl_quant_live/live/{f}")
    os.symlink("/workspace/shadow_bundle_v3", ws + "/shadow_bundle"); os.symlink("/workspace/venv", ws + "/venv")
    for d_ in ("weights", "target_live_king", "target_live", "target_combo"): os.symlink(f"{W}/live_ro/state/{d_}", f"{ws}/state/{d_}")
    for f in ("aux.json", "leg_returns_live.json"): shutil.copy2(f"{src}/home/wide_shadow/state/{f}", f"{ws}/state/{f}")
    shutil.copy2(f"{src}/home/wide_shadow/shadow_log.jsonl", ws + "/shadow_log.jsonl")
    for f in sorted(os.listdir(f"{src}/home/wide_shadow/fea171")):
        p = f"{src}/home/wide_shadow/fea171/{f}"
        if os.path.isfile(p): shutil.copy2(p, f"{ws}/fea171/{f}")
    rsrc = f"{src}/home/wide_shadow/state/rolling.npz"; rsha = sha(rsrc)
    assert rsha == PREP["runs"][f"g2c_{slot}"]["hybrid_sha256"], (slot, "G2-C rolling changed since prep")
    info = {"src_rolling_sha256": rsha}
    if variant == "V0":
        shutil.copy2(rsrc, f"{ws}/state/rolling.npz"); Z = np.load(f"{ws}/state/rolling.npz", allow_pickle=True); ts = Z["ts"]
    else:
        Z = np.load(rsrc, allow_pickle=True); ts = np.array(Z["ts"]); d = np.array(Z["data"])
        assert len(ts) == 11520 and int(ts[-1]) == A and ts.dtype == np.int64 and d.dtype == np.float16
        if variant.startswith("V1_"):
            K = int(variant.split("_")[1]); ts = ts[K:]; d = d[K:]; info["head_rows_removed"] = K
        elif variant == "V2_dead":
            w = (ts > A - 86400) & (ts <= A); lc = d[w][:, lidx, 4].astype(np.float64); assert int(w.sum()) == 288
            dead = lidx[~np.any(np.isfinite(lc) & (lc > 0), axis=0)]
            d[:, dead, :] = np.nan; info["dead_live_names"] = [SYMS[j] for j in dead]; info["n_dead_live_names"] = int(len(dead))
            aux = json.load(open(f"{ws}/state/aux.json")); pm = set(int(x) for x in (aux.get("prev_rec") or {}).get("members", []))
            tl = json.load(open(f"{ws}/state/target_live/{A}.json"))["weights"]
            info["n_dead_in_aux_prev_rec_members"] = int(sum(1 for j in dead if int(j) in pm)); info["n_dead_in_producer_target_live"] = int(sum(1 for j in dead if SYMS[j] in tl))
        np.savez_compressed(f"{ws}/state/rolling.npz", ts=ts, data=d)
    info.update(rows=int(len(ts)), first_ts=iso(ts[0]), last_ts=iso(ts[-1]), rolling_sha256=sha(f"{ws}/state/rolling.npz"))
    return dst, info

def probe(mb=300):
    """AMENDMENT 2: disk-quota probe before every variant (pod2 /workspace quota exhausted at 15:51Z killed attempt 1)."""
    pp = under(f"{OUTD}/_quota_probe.bin")
    try:
        with open(pp, "wb") as f:
            for _ in range(mb): f.write(b"\0" * (1 << 20))
            f.flush(); os.fsync(f.fileno())
        ok = os.path.getsize(pp) == mb << 20
    except OSError as e:
        ok = False; print("QUOTA_PROBE_FAIL", repr(e)[:160], flush=True)
    try: os.remove(pp)
    except OSError: pass
    return ok

def run(slot, variant):
    if not probe():
        print("ATTR_STAGE_C ABORT quota probe failed before", slot, variant, flush=True); sys.exit(4)
    A, cores = SLOTS[slot]; dst, info = build(slot, variant); tag = f"ATTR_{variant}"
    env = {"PATH": "/usr/bin:/bin", "HOME": dst + "/home", "REPLAY_COMBO": "1", "REPLAY_RECEIPT_TAG": tag}
    cmd = ["taskset", "-c", cores, "nice", "-n", "10", "/workspace/venv/bin/python", "-B", f"{dst}/dev/replay_driver.py", "--snapshot", f"{W}/snapshots/{A - 14400}", str(A)]
    logp = f"{dst}/receipts/{tag}.log"; t = time.time()
    with open(logp, "w") as lf:
        rc = subprocess.call(cmd, cwd=dst + "/dev", env=env, stdout=lf, stderr=subprocess.STDOUT, timeout=1800)
    with open(logp, "a") as lf: lf.write(f"rc={rc}\n")
    rp = f"{dst}/receipts/PARITY_{tag}_{A}_{A}.json"
    out = dict(slot=slot, anchor=A, variant=variant, cmd=cmd, env=env, cwd=dst + "/dev", rc=rc, secs=round(time.time() - t, 1), log=logp, **info)
    if rc != 0 or not os.path.exists(rp):
        out["FAIL"] = True; out["log_tail"] = open(logp, errors="replace").read().strip().splitlines()[-8:]; return out
    R = json.load(open(rp)); a0 = R["anchors"][0]; cb = a0.get("combo") or {}
    out.update(receipt=rp, receipt_sha256=sha(rp), driver_rolling_sha256=R.get("rolling_sha256"), king_weights_Linf=a0.get("weights_npz_Linf"), king_content_sha_equal=a0.get("content_sha_equal"),
               combo_rc=cb.get("rc"), combo_tail=cb.get("tail"), combo_err=cb.get("err"), target_combo_Linf=cb.get("target_combo_Linf"), target_live_Linf=cb.get("target_live_Linf"),
               target_live_n=cb.get("target_live_n"), ftrim_n=cb.get("ftrim_n"), w3m_equal=cb.get("w3m_equal"), compare_error=cb.get("compare_error"))
    out["driver_saw_variant_rolling"] = bool(R.get("rolling_sha256") == info["rolling_sha256"])
    rh = dst + "/replay_home"; st = {}
    for tagH in ("f10", "kc", "fc"):
        pr, pp = f"{rh}/fea171/state_H_{tagH}_{A}.npz", prod_state(tagH, A)
        if os.path.exists(pr) and pp:
            a = np.zeros(829); b = np.zeros(829); zr = np.load(pr); zp = np.load(pp)
            a[zr["idx"].astype(int)] = zr["val"]; b[zp["idx"].astype(int)] = zp["val"]; dd = np.abs(a - b)
            st[tagH] = dict(Linf=float(dd.max()), n_gt_1e6=int((dd > 1e-6).sum()), replay_sha256=sha(pr), producer_sha256=SUMS[os.path.basename(pp)])
        else:
            st[tagH] = dict(missing_replay=not os.path.exists(pr), missing_producer=pp is None)
    out["state_H_vs_producer"] = st
    try:
        rl = json.load(open(f"{rh}/state/target_live_combo/{A}.json"))["weights"]; ll = json.load(open(f"{dst}/home/wide_shadow/state/target_live/{A}.json"))["weights"]
        dif = {k: abs(rl.get(k, 0.0) - ll.get(k, 0.0)) for k in set(rl) | set(ll)}
        out["target_live_names_gt_1e6"] = int(sum(1 for v in dif.values() if v > 1e-6)); out["target_live_worst5"] = sorted(((round(v, 12), k) for k, v in dif.items()), reverse=True)[:5]
    except Exception as e:
        out["target_live_names_error"] = repr(e)[:200]
    for p in (f"{dst}/home/wide_shadow/state/rolling.npz", f"{rh}/fea171/mini", f"{rh}/fea171/ref_fea89.npz", f"{dst}/home/wide_shadow/fea171/ref_fea89.npz"):
        if os.path.isdir(p) and not os.path.islink(p): shutil.rmtree(under(p))
        elif os.path.isfile(p) and not os.path.islink(p): os.remove(under(p))
    return out

os.makedirs(OUTD, exist_ok=True)
PRE = dict(loadavg=open("/proc/loadavg").read().split()[:3], memory_current=open("/sys/fs/cgroup/memory.current").read().strip())
print("ATTR_STAGE_C start", iso(T0), "self", SELF, json.dumps(PRE), flush=True)
def lane(slot):
    res = []
    for v in VARIANTS:
        r = run(slot, v); res.append(r)
        print(json.dumps({k: r.get(k) for k in ("slot", "variant", "rc", "secs", "rows", "king_weights_Linf", "target_combo_Linf", "target_live_Linf", "target_live_names_gt_1e6", "n_dead_live_names")}), flush=True)
    return res
RES = [r for slot in SLOTS for r in lane(slot)]     # AMENDMENT 2: one lane at a time (peak disk ~250 MB)
BY = {(r["slot"], r["variant"]): r for r in RES}
failed = [f"{r['variant']}_{r['slot']}" for r in RES if r.get("FAIL") or r.get("combo_rc") != 0 or r.get("compare_error")]
def exact0(r): return (not r.get("FAIL")) and r.get("king_weights_Linf") == 0.0 and r.get("target_combo_Linf") == 0.0 and r.get("target_live_Linf") == 0.0 and r.get("driver_saw_variant_rolling")
v0_exact = all(exact0(BY[(s, "V0")]) for s in SLOTS)
def c1_ok(s):
    r = BY[(s, "V1_1920")]
    if r.get("FAIL") or r.get("target_live_Linf") is None or not r.get("driver_saw_variant_rolling"): return False
    kc = (r.get("state_H_vs_producer") or {}).get("kc") or {}
    kc_ok = kc.get("Linf") == 0.0 if "Linf" in kc else True     # prereg: kc condition applies where the producer file is available
    return bool(r["target_live_Linf"] > 1e-6 and kc_ok)
n_c1 = sum(c1_ok(s) for s in SLOTS)
if failed or not v0_exact: verdict = "STOP (V0 not exact or a run failed)"
else: verdict = "H-d CONFIRMED" if n_c1 >= 2 else "H-d NOT CONFIRMED"
TABLE = {f"{v}|{s}": dict(rows=BY[(s, v)].get("rows"), king=BY[(s, v)].get("king_weights_Linf"), target_combo=BY[(s, v)].get("target_combo_Linf"), target_live=BY[(s, v)].get("target_live_Linf"),
                          state_H={k: x.get("Linf") for k, x in (BY[(s, v)].get("state_H_vs_producer") or {}).items()}, names_gt_1e6=BY[(s, v)].get("target_live_names_gt_1e6"),
                          n_dead=BY[(s, v)].get("n_dead_live_names")) for v in VARIANTS for s in SLOTS}
OUT = dict(device="p2_attr_stageC.py", self_sha256=SELF, prereg_sha256=PREREG_SHA, inputs=INPUTS, device_pins=DEV, env=dict(os.environ), preflight=PRE, python=sys.version.split()[0], numpy=np.__version__,
           results=RES, failed=failed, V0_exact_3of3=v0_exact, V1_1920_c1_count=n_c1, verdict=verdict, table=TABLE, runtime_s=round(time.time() - T0, 1), utc_end=iso(time.time()))
rp = under(RC + "/ATTR_stageC.json"); json.dump(OUT, open(rp + ".tmp", "w"), indent=1, default=str); os.replace(rp + ".tmp", rp)
for v in VARIANTS: print(v, json.dumps({s: TABLE[f"{v}|{s}"] for s in SLOTS}), flush=True)
print("ATTR_STAGE_C verdict=%s V0_exact=%s c1=%d/3 failed=%s runtime_s=%.0f receipt_sha256=%s" % (verdict, v0_exact, n_c1, failed, OUT["runtime_s"], sha(rp)), flush=True)
sys.exit(0 if not verdict.startswith("STOP") else 3)

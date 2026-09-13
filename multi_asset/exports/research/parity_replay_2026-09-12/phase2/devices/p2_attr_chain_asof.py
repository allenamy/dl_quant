#!/usr/bin/env python3
"""ATTR Stage D -- G2-C-ASOF certification gate. docs/PREREG_combo_chain_residual_attribution_2026-09-13.md §2 Stage D / §3 + AMENDMENT 1/2/3.
Long source cache: 13,440 5m rows 2026-07-27T16:05Z .. 2026-09-12T08:00Z; rows <= 2026-09-01T00:00Z from holefix2 (non-live names NaN, the G2-C rule),
later rows from producer snapshot 1789200000 rolling (c2ab7134...). Two trees built like the G2-C chain tree (same pinned devices, reader modules, fea171
pipeline + producer state_H copies, aux/leg_returns = snapshot 1789200000, truncated shadow_log, same state symlinks); the fake-HOME state/rolling.npz is a
symlink to the long source cache (the king stage keeps its last 11,520 rows itself: shadow_loop_v3 CACHE_ROWS).
A wrapper process imports the BYTE-IDENTICAL Phase 1 driver (f2ced820...) as a module and replaces only the module-global name `run_combo_stage` with a
function that, before calling the original, points replay_home/state/rolling.npz (symlink) at a window file:
  D-id   : the 11,520 rows ending 2026-09-12T08:00Z (Phase 1 geometry; the combo stage truncates to <= A itself) -> must reproduce the G2-C chain receipt
           per anchor bit for bit (weights_npz_Linf, target_combo_Linf, target_live_Linf); otherwise STOP (exit 3), D-asof is not run.
  D-asof : the 11,520 rows ending at A (production geometry), rewritten per anchor (single file).
Gate D-asof PASS <=> 41/41 target_live L-inf <= 1e-6 AND 41/41 target_combo L-inf <= 1e-6 AND 41/41 king weights L-inf <= 1e-6 (combo rc 0, no compare error).
Also reported: per-anchor replay vs producer state_H_{f10,kc,fc}_A (AMENDMENT 1 copies, sha-verified), window provenance per anchor.
Writes only under P2/work/attr_D and P2/receipts/ATTR_stageD*.
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B p2_attr_chain_asof.py PATH,HOME,LC_CTYPE
       (internal) ... p2_attr_chain_asof.py --wrap <tree> <mode> <long_cache>"""
import os, sys, json, time, hashlib, shutil, subprocess
P2 = "/workspace/uplift_r2_2026-09-13/P2"; W = P2 + "/work"; OUTD = W + "/attr_D"; RC = P2 + "/receipts"; PRODH = W + "/live_ro/prod_stateH_attr"
A_END = 1789200000; CUT = 1788220800; NROW = 11520; ANCH = [1788624000 + 14400 * k for k in range(41)]
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 22), b""): h.update(ch)
    return h.hexdigest()
def under(p):
    ap = os.path.abspath(p); assert ap.startswith(OUTD + "/") or ap.startswith(RC + "/ATTR_stageD"), p; return p
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))

if len(sys.argv) > 1 and sys.argv[1] == "--wrap":
    tree, mode, longp = sys.argv[2], sys.argv[3], sys.argv[4]
    assert set(os.environ) - {"LC_CTYPE"} == {"PATH", "HOME", "REPLAY_COMBO", "REPLAY_RECEIPT_TAG"}, sorted(os.environ)   # LC_CTYPE: PEP 538 coercion only
    assert mode in ("id", "asof") and os.path.abspath(tree).startswith(OUTD + "/")
    import numpy as np
    sys.path.insert(0, tree + "/dev"); sys.argv = [tree + "/dev/replay_driver.py", "--chain"] + [str(a) for a in ANCH]
    import replay_driver as RDm
    assert os.path.abspath(RDm.__file__) == os.path.abspath(tree + "/dev/replay_driver.py") and RDm.RH == tree + "/replay_home"
    Z = np.load(longp, allow_pickle=True); LTS = np.array(Z["ts"]); LD = np.array(Z["data"]); assert len(LTS) == 13440 and int(LTS[-1]) == A_END
    WINP = RDm.RH + "/state/rolling_window.npz"; LINK = RDm.RH + "/state/rolling.npz"; PROV = []
    def write_window(end):
        m = (LTS > end - NROW * 300) & (LTS <= end); ts = LTS[m]; d = LD[m]; assert len(ts) == NROW and int(ts[-1]) == end
        np.savez(WINP + ".tmp.npz", ts=ts, data=d); os.replace(WINP + ".tmp.npz", WINP)
        return {"window_end": int(end), "rows": int(len(ts)), "first_utc": iso(ts[0]), "last_utc": iso(ts[-1]), "window_sha256": sha(WINP)}
    if os.path.lexists(LINK): os.remove(LINK)
    os.symlink(WINP, LINK)
    ORIG = RDm.run_combo_stage; FIXED = write_window(A_END) if mode == "id" else None
    def run_combo_stage_asof(A, st, first):
        assert os.path.islink(LINK) and os.readlink(LINK) == WINP
        pv = dict(FIXED) if mode == "id" else write_window(A)
        pv["anchor"] = int(A); pv["window_sha256_at_call"] = sha(WINP); PROV.append(pv)
        return ORIG(A, st, first)
    RDm.run_combo_stage = run_combo_stage_asof
    RDm.main()
    json.dump({"mode": mode, "tree": tree, "long_cache": longp, "long_cache_sha256": sha(longp), "window_provenance": PROV}, open(tree + "/receipts/ATTR_D_window_provenance.json", "w"), indent=1)
    print("WRAP_DONE", mode, len(PROV), flush=True); sys.exit(0)

WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
import numpy as np
T0 = time.time(); SELF = sha(os.path.abspath(__file__))
PIN = {"cache": ("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz", "1d7f459dee434ec49e7714a2a612807f2e38e97f35c6c39471a8a4aaa7452488"),
       "bundle_config": ("/workspace/shadow_bundle_v3/config.json", "3a8422f377519cac77b0c42305d2ba40a4b7a42a830f0542bda844f66647c94e"),
       "snap_1789200000_rolling": (W + "/snapshots/1789200000/rolling.npz", "c2ab71344d965d08b7ea0dac82acace7b030716047d732a4296756704f82f93d"),
       "prod_stateH_sums": (PRODH + "/ATTR_prod_stateH_SHA256SUMS.txt", "243a78d78a87ac24d480fc322643ee943706afe33e856dc15a7175f3947f50fc")}
DEV = {"replay_driver.py": "f2ced820daa45e0fec0879b6eaeba58905109b60dc0ac09a6e5b0d7cd1bee4ec", "combo_stage_replay.py": "f5ba9a8234ef0c01ee1aa5bdb0ebd87e8e7093c10b164e37f4fc10f97bc7f77b",
       "shadow_loop_v3_replay.py": "4d3bc157f03e3462a69e64f817b3fd4cd51be4c03d72650304b7d0c1a0089d42"}
SH = {k: sha(p) for k, (p, _) in PIN.items()}
for k, (p, s) in PIN.items(): assert SH[k] == s, (k, SH[k])
PREP = json.load(open(RC + "/G2C_prep.json")); G2CV = json.load(open(RC + "/G2C_verdict.json")); assert G2CV["verdict"] == "PASS"
GCP = W + "/g2c_chain/receipts/PARITY_G2C_chain_1788624000_1789200000.json"; assert sha(GCP) == G2CV["chain_receipt_sha256"]; GC = json.load(open(GCP))
HYB = W + "/g2c_chain/home/wide_shadow/state/rolling.npz"; assert sha(HYB) == PREP["runs"]["g2c_chain"]["hybrid_sha256"]
SUMS = {}
for l in open(PIN["prod_stateH_sums"][0]):
    if l.strip(): d_, f_ = l.rstrip("\n").split("  ", 1); SUMS[f_] = d_
os.makedirs(OUTD, exist_ok=True)
R = {"device": os.path.abspath(__file__), "self_sha256": SELF, "env": dict(os.environ), "inputs": {k: {"path": PIN[k][0], "sha256": SH[k]} for k in PIN}, "device_pins": DEV,
     "g2c_chain_receipt_sha256": G2CV["chain_receipt_sha256"], "g2c_chain_hybrid_sha256": PREP["runs"]["g2c_chain"]["hybrid_sha256"], "python": sys.version.split()[0], "numpy": np.__version__, "utc_start": iso(T0)}
def save():
    rp = under(RC + "/ATTR_stageD.json"); json.dump(R, open(rp + ".tmp", "w"), indent=1, default=str); os.replace(rp + ".tmp", rp); return rp
def probe(mb=500):
    pp = under(OUTD + "/_quota_probe.bin")
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
if not probe():
    R["verdict"] = "ABORT quota probe"; save(); print("ATTR_STAGE_D ABORT quota probe", flush=True); sys.exit(4)

# ---- long source cache ----
cfg = json.load(open(PIN["bundle_config"][0])); SYMS = cfg["symbols_panel"]; LIVE = cfg["symbols_live"]
col = {s: j for j, s in enumerate(SYMS)}; lmask = np.zeros(829, bool); lmask[[col[s] for s in LIVE]] = True
HZ = np.load(PIN["cache"][0], allow_pickle=True); assert [str(s) for s in HZ["symbols"]] == SYMS
PTS = HZ["ts"].astype(np.int64); PROW = {int(t): i for i, t in enumerate(PTS)}; PD = HZ["data"]; assert int(PTS[-1]) == CUT
S0 = np.load(PIN["snap_1789200000_rolling"][0], allow_pickle=True); S0ts = S0["ts"].astype(np.int64); S0d = S0["data"]; S0ROW = {int(t): i for i, t in enumerate(S0ts)}
LTS = np.arange(A_END - 13439 * 300, A_END + 300, 300, dtype=np.int64); assert iso(LTS[0]) == "2026-07-27T16:05:00Z" and len(LTS) == 13440
LD = np.full((len(LTS), 829, 7), np.nan, np.float16); src = np.zeros(len(LTS), np.int8)
for i, t in enumerate(LTS):
    t = int(t)
    if t <= CUT:
        row = np.array(PD[PROW[t]]); row[~lmask] = np.nan; LD[i] = row; src[i] = 1
    else:
        LD[i] = S0d[S0ROW[t]]; src[i] = 2
del HZ, PD
LONG = under(OUTD + "/long_source_cache.npz"); np.savez_compressed(LONG, ts=LTS, data=LD)
Hh = np.load(HYB, allow_pickle=True); hts = Hh["ts"].astype(np.int64); hd = np.array(Hh["data"])
tail_equal = bool(np.array_equal(LTS[-NROW:], hts) and LD[-NROW:].tobytes() == hd.tobytes())
R["long_cache"] = {"path": LONG, "sha256": sha(LONG), "rows": int(len(LTS)), "first_utc": iso(LTS[0]), "last_utc": iso(LTS[-1]), "rows_holefix2": int((src == 1).sum()), "rows_snapshot_1789200000": int((src == 2).sum()),
                   "rows_before_2026-08-03T08:05Z_unverified_vs_producer": int((LTS < A_END - (NROW - 1) * 300).sum()), "last_11520_bytes_equal_g2c_chain_hybrid": tail_equal}
del hd, Hh
print("LONG_CACHE", json.dumps(R["long_cache"]), flush=True); save()

def build(mode):
    src_t = W + "/g2c_chain"; dst = under(f"{OUTD}/D_{mode}")
    if os.path.exists(dst): shutil.rmtree(dst)
    home = dst + "/home"; ws = home + "/wide_shadow"
    for d_ in (dst + "/dev", dst + "/receipts", ws + "/state", ws + "/fea171", home + "/dl_quant_live/live"): os.makedirs(d_, exist_ok=True)
    for f, s in DEV.items():
        assert sha(f"{src_t}/dev/{f}") == s, f; shutil.copy2(f"{src_t}/dev/{f}", f"{dst}/dev/{f}")
    for f in ("external_book.py", "book_config.py"): shutil.copy2(f"{src_t}/home/dl_quant_live/live/{f}", f"{home}/dl_quant_live/live/{f}")
    os.symlink("/workspace/shadow_bundle_v3", ws + "/shadow_bundle"); os.symlink("/workspace/venv", ws + "/venv")
    for d_ in ("weights", "target_live_king", "target_live", "target_combo"): os.symlink(f"{W}/live_ro/state/{d_}", f"{ws}/state/{d_}")
    for f in ("aux.json", "leg_returns_live.json"): shutil.copy2(f"{src_t}/home/wide_shadow/state/{f}", f"{ws}/state/{f}")
    shutil.copy2(f"{src_t}/home/wide_shadow/shadow_log.jsonl", ws + "/shadow_log.jsonl")
    for f in sorted(os.listdir(f"{src_t}/home/wide_shadow/fea171")):
        p = f"{src_t}/home/wide_shadow/fea171/{f}"
        if os.path.isfile(p): shutil.copy2(p, f"{ws}/fea171/{f}")
    for tag in ("f10", "kc", "fc"):
        f = f"state_H_{tag}_1788609600.npz"; assert sha(f"{ws}/fea171/{f}") == SUMS[f], f
    os.symlink(LONG, ws + "/state/rolling.npz")
    return dst

def dense(p):
    z = np.load(p); v = np.zeros(829); v[z["idx"].astype(int)] = z["val"]; return v
def run_mode(mode):
    if not probe():
        return {"mode": mode, "FAIL": "quota probe"}
    dst = build(mode); tag = f"ATTR_D_{mode}"
    env = {"PATH": "/usr/bin:/bin", "HOME": dst + "/home", "REPLAY_COMBO": "1", "REPLAY_RECEIPT_TAG": tag}
    cmd = ["taskset", "-c", "0-7", "nice", "-n", "10", "/workspace/venv/bin/python", "-B", os.path.abspath(__file__), "--wrap", dst, mode, LONG]
    logp = dst + "/receipts/" + tag + ".log"; t = time.time()
    with open(logp, "w") as lf:
        rc = subprocess.call(cmd, cwd=dst + "/dev", env=env, stdout=lf, stderr=subprocess.STDOUT, timeout=4 * 3600)
    with open(logp, "a") as lf: lf.write(f"rc={rc}\n")
    out = {"mode": mode, "cmd": cmd, "env": env, "rc": rc, "secs": round(time.time() - t, 1), "log": logp, "log_tail": open(logp, errors="replace").read().strip().splitlines()[-4:]}
    rp = f"{dst}/receipts/PARITY_{tag}_{ANCH[0]}_{ANCH[-1]}.json"; pv = dst + "/receipts/ATTR_D_window_provenance.json"
    if rc != 0 or not os.path.exists(rp) or not os.path.exists(pv):
        out["FAIL"] = "run"; return out
    Rr = json.load(open(rp)); P = json.load(open(pv)); out.update(receipt=rp, receipt_sha256=sha(rp), provenance=pv, provenance_sha256=sha(pv), chain_start_diag=Rr.get("chain_start_diag"), driver_rolling_sha256=Rr.get("rolling_sha256"))
    prov = {int(x["anchor"]): x for x in P["window_provenance"]}
    rows = []
    for a in Rr["anchors"]:
        A = int(a["anchor"]); cb = a.get("combo") or {}; r = {"anchor": A, "king": a.get("weights_npz_Linf"), "target_combo": cb.get("target_combo_Linf"), "target_live": cb.get("target_live_Linf"),
                                                            "combo_rc": cb.get("rc"), "compare_error": cb.get("compare_error"), "lr_diff": a.get("lr_entry_max_abs_diff"),
                                                            "window": {k: prov.get(A, {}).get(k) for k in ("first_utc", "last_utc", "rows", "window_sha256_at_call")}}
        for tagH in ("f10", "kc", "fc"):
            f = f"state_H_{tagH}_{A}.npz"; rpH = f"{dst}/replay_home/fea171/{f}"
            if f in SUMS and os.path.exists(rpH):
                assert sha(f"{PRODH}/{f}") == SUMS[f]; d = np.abs(dense(rpH) - dense(f"{PRODH}/{f}")); r["state_H_" + tagH] = float(d.max())
            else: r["state_H_" + tagH] = None
        rows.append(r)
    out["per_anchor"] = rows; out["anchors_ok"] = [r["anchor"] for r in rows] == ANCH
    for p in (f"{dst}/replay_home/state/rolling_window.npz", f"{dst}/replay_home/fea171/mini", f"{dst}/replay_home/fea171/ref_fea89.npz", f"{dst}/home/wide_shadow/fea171/ref_fea89.npz"):
        if os.path.isdir(p) and not os.path.islink(p): shutil.rmtree(under(p))
        elif os.path.isfile(p) and not os.path.islink(p): os.remove(under(p))
    return out

GCA = {int(a["anchor"]): a for a in GC["anchors"]}
Did = run_mode("id"); R["D_id"] = Did
def id_match(r):
    g = GCA[r["anchor"]]; gc = g.get("combo") or {}
    return r["king"] == g["weights_npz_Linf"] and r["target_combo"] == gc.get("target_combo_Linf") and r["target_live"] == gc.get("target_live_Linf")
if Did.get("FAIL") or not Did.get("anchors_ok"):
    R["D_id_bitwise_41"] = False; n_id = 0
else:
    n_id = sum(1 for r in Did["per_anchor"] if id_match(r)); R["D_id_bitwise_41"] = (n_id == 41)
R["D_id_n_match"] = n_id; R["D_id_mismatch"] = [r["anchor"] for r in Did.get("per_anchor", []) if not id_match(r)]
save(); print("D_ID bitwise %d/41 rc=%s secs=%s" % (n_id, Did.get("rc"), Did.get("secs")), flush=True)
if not R["D_id_bitwise_41"]:
    R["verdict"] = "STOP (D-id did not reproduce the G2-C chain receipt bit for bit; wrapper not trusted; D-asof not run)"; R["runtime_s"] = round(time.time() - T0, 1); rp = save()
    print("ATTR_STAGE_D verdict=%s receipt_sha256=%s" % (R["verdict"], sha(rp)), flush=True); sys.exit(3)
Das = run_mode("asof"); R["D_asof"] = Das
if Das.get("FAIL") or not Das.get("anchors_ok"):
    R["verdict"] = "RED (D-asof run failed)"; ok = False
else:
    pa = Das["per_anchor"]
    def le(x): return x is not None and x <= 1e-6
    n_tl = sum(1 for r in pa if le(r["target_live"])); n_tc = sum(1 for r in pa if le(r["target_combo"])); n_k = sum(1 for r in pa if le(r["king"])); n_rc = sum(1 for r in pa if r["combo_rc"] == 0 and not r["compare_error"])
    R["D_asof_counts"] = {"target_live_le_1e-6": n_tl, "target_combo_le_1e-6": n_tc, "king_le_1e-6": n_k, "combo_rc0_no_error": n_rc,
                          "max_target_live": max((r["target_live"] for r in pa if r["target_live"] is not None), default=None), "max_target_combo": max((r["target_combo"] for r in pa if r["target_combo"] is not None), default=None),
                          "n_target_live_exact0": sum(1 for r in pa if r["target_live"] == 0.0),
                          "state_H_max": {t: max((r["state_H_" + t] for r in pa if r["state_H_" + t] is not None), default=None) for t in ("f10", "kc", "fc")},
                          "state_H_n_exact0": {t: sum(1 for r in pa if r["state_H_" + t] == 0.0) for t in ("f10", "kc", "fc")}}
    ok = n_tl == 41 and n_tc == 41 and n_k == 41 and n_rc == 41
    R["verdict"] = "G2-C-ASOF PASS" if ok else "G2-C-ASOF RED"
R["runtime_s"] = round(time.time() - T0, 1); R["utc_end"] = iso(time.time()); rp = save()
print("ATTR_STAGE_D verdict=%s D_id=%d/41 D_asof=%s runtime_s=%.0f receipt_sha256=%s" % (R["verdict"], n_id, json.dumps(R.get("D_asof_counts")), R["runtime_s"], sha(rp)), flush=True)
sys.exit(0 if ok else 1)

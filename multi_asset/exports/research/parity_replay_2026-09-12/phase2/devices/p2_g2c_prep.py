#!/usr/bin/env python3
"""G2-C preparation (AMENDMENT 2 §A2.5 G2-C, frozen). READ-ONLY on every source; writes only under /workspace/uplift_r2_2026-09-13/P2/work/g2c_*.
G2-C runs the BYTE-IDENTICAL Phase 1 driver (replay_driver.py f2ced820…) with its devices (4d3bc157… / f5ba9a82…) on pod2, with `~/wide_shadow` resolved to a
fake HOME whose state/rolling.npz is a HYBRID cache: holefix2 rows (ts <= 2026-09-01 00:00Z, names outside the live 450 set to NaN, as the producer never
fetches them) + producer rows from snapshot 1789243200 rolling.npz (ts > 2026-09-01 00:00Z). Every other file the driver reads is a read-only copy of the file
Phase 1 read. One isolated tree per run (the Phase 1 driver derives replay_home/receipts from its own directory):
  g2c_chain : 41-anchor chain 1788624000..1789200000; aux/leg_returns = snapshot 1789200000 (= Phase 1 aux 5e825c2f…); rolling rows = the 11520 5m rows ending
              1789200000 (= the ts grid of the Phase 1 rolling c2ab7134…); shadow_log truncated to rows logged <= 2026-09-12T09:43:53Z (Phase 1 run start).
  g2c_sNN   : snapshot-seeded anchor A in {1789214400, 1789228800, 1789243200}; aux/leg_returns = snapshot A (the live state at the Phase 1 G-P3 run);
              rolling rows = the 11520 rows ending at A; snapdir = snapshot A-4h.
For each hybrid the receipt records a cell-level comparison against the producer rolling.npz of the same anchor (NaN-aware), so the size of the "swap" is known.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B p2_g2c_prep.py PATH,HOME,LC_CTYPE"""
import os, sys, json, time, hashlib, shutil, subprocess
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
import numpy as np
P2 = "/workspace/uplift_r2_2026-09-13/P2"; W = f"{P2}/work"; OUT = f"{P2}/receipts/G2C_prep.json"
def under(p): assert os.path.realpath(p).startswith(P2 + "/") or os.path.realpath(os.path.dirname(p)).startswith(P2 + "/"), p; return p
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
T0 = time.time()
PIN = {"cache": ("/workspace/data/dlnative_5m_wide829_f16_holefix2.npz", "1d7f459dee434ec49e7714a2a612807f2e38e97f35c6c39471a8a4aaa7452488"),
       "bundle_config": ("/workspace/shadow_bundle_v3/config.json", "3a8422f377519cac77b0c42305d2ba40a4b7a42a830f0542bda844f66647c94e"),
       "replay_driver": (f"{W}/phase1_ro/replay_driver.py", "f2ced820daa45e0fec0879b6eaeba58905109b60dc0ac09a6e5b0d7cd1bee4ec"),
       "shadow_loop_v3_replay": (f"{P2}/devices/shadow_loop_v3_replay.py", "4d3bc157f03e3462a69e64f817b3fd4cd51be4c03d72650304b7d0c1a0089d42"),
       "combo_stage_replay": (f"{P2}/devices/combo_stage_replay.py", "f5ba9a8234ef0c01ee1aa5bdb0ebd87e8e7093c10b164e37f4fc10f97bc7f77b"),
       "external_book": (f"{W}/reader_ro/external_book.py", "f875fe5411119e9ad852a30d452d2393b28564eca874d71026d9620a251a2c5f"),
       "book_config": (f"{W}/reader_ro/book_config.py", "a724406e831ec21828ff9475704559fede5693d5606ca99894b850a9e8c50bc5"),
       "snap_1789200000_aux": (f"{W}/snapshots/1789200000/aux.json", "5e825c2f791bb860e9a1d6fb50817719de4acbe54594c9940392bb0640a0260e"),
       "snap_1789200000_rolling": (f"{W}/snapshots/1789200000/rolling.npz", "c2ab71344d965d08b7ea0dac82acace7b030716047d732a4296756704f82f93d"),
       "snap_1789214400_aux": (f"{W}/snapshots/1789214400/aux.json", "4a3572efa33f1a393048107b28b9a794d50ee37193aa09ba2153d235d6b4242a"),
       "snap_1789214400_rolling": (f"{W}/snapshots/1789214400/rolling.npz", "2582fd7519e2d846df72916279ce6fedec4b7a29f3787ed476ecc15c69beee4f"),
       "snap_1789228800_aux": (f"{W}/snapshots/1789228800/aux.json", "d653bca08bccc087dd076b72d31d5be25a991f92cf676c36d7e4fab10fb7ba0c"),
       "snap_1789228800_rolling": (f"{W}/snapshots/1789228800/rolling.npz", "3448aa217b00961a9523e743a37166b1eb3f2e86b609bd36ec129d6f5a9fb35c"),
       "snap_1789243200_aux": (f"{W}/snapshots/1789243200/aux.json", "69d8af7c9b3b7ac3957dfc52fc77c8ba97b53cdeec4b450e31f47b2526065360"),
       "snap_1789243200_rolling": (f"{W}/snapshots/1789243200/rolling.npz", "8d19b76feab424cb45c2e8d7362ebce091552f060ce6533d45910cb7da6fd4c9")}
SH = {}
for k, (p, s) in PIN.items():
    got = sha(p); SH[k] = got
    assert got == s, (k, got, s)
R = {"device": os.path.abspath(__file__), "self_sha256": sha(os.path.abspath(__file__)), "env": dict(os.environ), "inputs": {k: {"path": PIN[k][0], "sha256": SH[k]} for k in PIN},
     "python": sys.version.split()[0], "numpy": np.__version__, "utc_start": iso(T0)}
cfg = json.load(open(PIN["bundle_config"][0])); SYMS = cfg["symbols_panel"]; LIVE = cfg["symbols_live"]
col = {s: j for j, s in enumerate(SYMS)}; lmask = np.zeros(829, bool); lmask[[col[s] for s in LIVE]] = True
Z = np.load(PIN["cache"][0], allow_pickle=True); assert [str(s) for s in Z["symbols"]] == SYMS
PTS = Z["ts"].astype(np.int64); PROW = {int(t): i for i, t in enumerate(PTS)}; PD = Z["data"]
S20 = np.load(PIN["snap_1789243200_rolling"][0], allow_pickle=True); S20ts = S20["ts"].astype(np.int64); S20d = S20["data"]; S20ROW = {int(t): i for i, t in enumerate(S20ts)}
CUT = 1788220800   # 2026-09-01 00:00Z, last holefix2 row
assert int(PTS[-1]) == CUT
def hybrid(A):
    ts = np.arange(A - 11519 * 300, A + 300, 300, dtype=np.int64); d = np.full((len(ts), 829, 7), np.nan, np.float16); src = np.zeros(len(ts), np.int8)
    for i, t in enumerate(ts):
        t = int(t)
        if t <= CUT:
            r = PROW[t]; row = np.array(PD[r]); row[~lmask] = np.nan; d[i] = row; src[i] = 1
        else:
            r = S20ROW[t]; d[i] = S20d[r]; src[i] = 2
    return ts, d, src
def compare(ts, d, prod_path):
    Pz = np.load(prod_path, allow_pickle=True); pts = Pz["ts"].astype(np.int64); pdd = Pz["data"]
    same_ts = bool(np.array_equal(ts, pts)); out = {"producer_rolling": prod_path, "ts_equal": same_ts, "producer_rows": int(len(pts))}
    if not same_ts:
        com = np.intersect1d(ts, pts); ia = np.searchsorted(ts, com); ib = np.searchsorted(pts, com); a = d[ia]; b = pdd[ib]; out["common_rows"] = int(len(com))
    else:
        a = d; b = pdd
    fa = np.isfinite(a); fb = np.isfinite(b)
    out["nan_support_diff_cells"] = int((fa != fb).sum()); both = fa & fb
    out["finite_value_diff_cells"] = int((a[both] != b[both]).sum()); out["bitwise_equal_nan_aware"] = bool(out["nan_support_diff_cells"] == 0 and out["finite_value_diff_cells"] == 0)
    out["pod_rows_used"] = None
    return out
RUNS = {"g2c_chain": {"A_end": 1789200000, "aux": "1789200000", "anchors": [1788624000 + 14400 * k for k in range(41)], "mode": "chain"},
        "g2c_s12": {"A_end": 1789214400, "aux": "1789214400", "snapdir": "1789200000", "anchors": [1789214400], "mode": "snapshot"},
        "g2c_s16": {"A_end": 1789228800, "aux": "1789228800", "snapdir": "1789214400", "anchors": [1789228800], "mode": "snapshot"},
        "g2c_s20": {"A_end": 1789243200, "aux": "1789243200", "snapdir": "1789228800", "anchors": [1789243200], "mode": "snapshot"}}
R["runs"] = {}
for name, spec in RUNS.items():
    root = under(f"{W}/{name}"); home = f"{root}/home"; ws = f"{home}/wide_shadow"
    if os.path.exists(root): shutil.rmtree(root)
    for d_ in (f"{root}/dev", f"{root}/receipts", f"{ws}/state", f"{ws}/fea171", f"{home}/dl_quant_live/live"): os.makedirs(d_, exist_ok=True)
    for f in ("replay_driver",): shutil.copy2(PIN[f][0], f"{root}/dev/replay_driver.py")
    shutil.copy2(PIN["shadow_loop_v3_replay"][0], f"{root}/dev/shadow_loop_v3_replay.py"); shutil.copy2(PIN["combo_stage_replay"][0], f"{root}/dev/combo_stage_replay.py")
    for f in ("external_book", "book_config"): shutil.copy2(PIN[f][0], f"{home}/dl_quant_live/live/{f}.py")
    os.symlink("/workspace/shadow_bundle_v3", f"{ws}/shadow_bundle"); os.symlink("/workspace/venv", f"{ws}/venv")
    for d_ in ("weights", "target_live_king", "target_live", "target_combo"): os.symlink(f"{W}/live_ro/state/{d_}", f"{ws}/state/{d_}")
    shutil.copy2(f"{W}/snapshots/{spec['aux']}/aux.json", f"{ws}/state/aux.json"); shutil.copy2(f"{W}/snapshots/{spec['aux']}/leg_returns_live.json", f"{ws}/state/leg_returns_live.json")
    for f in os.listdir(f"{W}/live_ro/fea171_pipeline"): shutil.copy2(f"{W}/live_ro/fea171_pipeline/{f}", f"{ws}/fea171/{f}")
    for f in os.listdir(f"{W}/live_ro/live_fea171"): shutil.copy2(f"{W}/live_ro/live_fea171/{f}", f"{ws}/fea171/{f}")
    # shadow_log as of the Phase 1 run (chain: rows logged <= 2026-09-12T09:43:53Z; snapshot runs: rows logged <= end of anchor A's run window)
    cutoff = "2026-09-12T09:43:53Z" if spec["mode"] == "chain" else iso(spec["A_end"] + 3600)
    kept = 0
    with open(f"{W}/live_ro/state/shadow_log.jsonl") as fi, open(f"{ws}/shadow_log.jsonl", "w") as fo:
        for l in fi:
            try: r = json.loads(l)
            except Exception: continue
            if str(r.get("logged_utc", "9999")) <= cutoff: fo.write(l); kept += 1
    ts, d, src = hybrid(spec["A_end"])
    np.savez_compressed(f"{ws}/state/rolling.npz", ts=ts, data=d)
    prod = f"{W}/snapshots/{spec['aux']}/rolling.npz"
    cmpr = compare(ts, d, prod); cmpr["pod_rows_used"] = int((src == 1).sum()); cmpr["producer_rows_used"] = int((src == 2).sum())
    R["runs"][name] = {**spec, "root": root, "fake_home": home, "hybrid_rolling": f"{ws}/state/rolling.npz", "hybrid_sha256": sha(f"{ws}/state/rolling.npz"),
                       "hybrid_ts_first": iso(ts[0]), "hybrid_ts_last": iso(ts[-1]), "vs_producer_rolling_same_anchor": cmpr, "shadow_log_rows_kept": kept, "shadow_log_cutoff": cutoff}
    print(name, json.dumps(cmpr), "kept log rows", kept, flush=True)
R["runtime_s"] = round(time.time() - T0, 1)
json.dump(R, open(OUT, "w"), indent=1)
print("G2C_PREP_DONE", OUT, flush=True)

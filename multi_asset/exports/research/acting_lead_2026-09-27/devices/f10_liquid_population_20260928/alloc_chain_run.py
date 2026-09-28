#!/usr/bin/env python3
"""alloc_chain_run.py — run ONE combination-layer arm through the certified combo -> adapter -> engine chain.

Derived from dlarch_chain_run.py (6345132f): same root layout, same read-only share symlinks, same UNMODIFIED adapter (ovn_adapter.py
17555e56) and engine (bt_launch.py 393a8dc8), same X-axis base config (RUN_CONFIG_NEWS2_s42X_2026-09-23.json, only targets / arm /
pod_root changed), same team engine gate (<= 2 foreign bt_launch groups, cgroup headroom >= config min + 2 GiB, /dev/shm >= 4 GiB).
The ONLY functional difference: step 1 runs alloc_combo.py (--rule, --mix) instead of news2_combo.py.

Built-in gates, all BEFORE the engine:
  COMBO IDENTITY  --rule inservice --mix shared at a seed with an archived NC combo (42 = the deployed book, 2027) must reproduce
                  /dev/shm/news2_2026-09-23/work/combo_s<seed>/{scaled_diagnostic,literal}.npz BIT FOR BIT (container sha AND arrays).
                  Any other arm at those seeds must NOT be bitwise (a switch that is not wired would otherwise pass as an arm).
  ENGINE IDENTITY --engine-identity: after the engine, every PATH_*.npz of the in-service arm must equal the NC reference cell's PATH npz
                  of the same path seed bit for bit (the reference cell DLARCH_REF_NC_s<seed>X, whose own combo was asserted bitwise to the
                  production archive by dlarch_chain_run).
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B alloc_chain_run.py PATH,HOME,LC_CTYPE <outdir> \
         --seed N --rule R --mix M [--engine] [--engine-identity]
"""
import os, sys, json, time, shutil, hashlib, subprocess, glob
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import dlarch_safe_io as sio          # vendored byte-identical copy (sha asserted below); E-0925-A: artifact sha from a verified write
SAFE_IO_SHA = "36deb92fdd5e8c3506198d82bab8a53312f5c03a1b866e9318f8489d51e0cd4e"
sio.install_guards()

NS = "/dev/shm/news2_2026-09-23"
BASE = json.load(open(os.path.join(HERE,"CONTRACT.json")))["root"]
CELLS = f"{BASE}/cells"
DEV = HERE
PV = "/workspace/venv/bin/python"
BASE_CFG = f"{NS}/configs/RUN_CONFIG_NEWS2_s42X_2026-09-23.json"
BASE_CELL_SUFFIX = "|scaled|rule|raw|UAFE"
DLARCH_CHAIN = "/workspace/dlarch_2026-09-24/chain"
F10_SRC = {42: f"{NS}/work/f10_s42", 2027: f"{NS}/work/f10_s2027",
           7: "/workspace/dlarch_2026-09-24/T3/G1_T0_nomask/f10_s7"}      # the SAME F10 each NC reference cell used (CHAIN_ref_nc_s*X.json f10_source)
REF_CELL = {s: f"{DLARCH_CHAIN}/ref_nc_s{s}X/runs/DLARCH_REF_NC_s{s}X_scaled_rule_raw_UAFE" for s in (42, 2027, 7)}
SHARE = {
    "work/NEWS_FEATURES.npz": f"{NS}/work/NEWS_FEATURES.npz",
    "work/legs.npz": f"{NS}/work/legs.npz",
    "work/king/KING_OOF.npz": f"{NS}/work/king/KING_OOF.npz",
    "inputs/bundle_config.json": f"{NS}/inputs/bundle_config.json",
    "receipts/P2B_FEATURES.json": f"{NS}/receipts/P2B_FEATURES.json",
    "receipts/P3_LEGS.json": f"{NS}/receipts/P3_LEGS.json",
    "receipts/P1_members_2025H2on.npz": f"{NS}/receipts/P1_members_2025H2on.npz",
    "vendor_live/fea171/combo_stage.py": f"{NS}/vendor_live/fea171/combo_stage.py",
}
MAX_FOREIGN_ENGINES = 1      # lead 2026-09-26 17:5xZ: at most TWO engine cells in parallel team-wide (mine + 1); was 2 (three-cell rule)
ENGINE_GATE_MARGIN_GIB = 2.0
SHM_FREE_MIN_GIB = 4.0
PRIORITY_CLAIMS = "/workspace/dlarch_2026-09-24/CHAIN/.claim_NESTEP_s*"   # dlarch 18:2xZ: a claim = its cell is due; do not start a new cell
HOLD_FILE = f"{BASE}/HOLD_CANDIDATE_CELLS"   # lead-placed priority slot for candidate cells


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def log(*a): print(time.strftime("%H:%M:%S", time.gmtime()), *a, flush=True)


def mem_gate():
    def rd(p):
        try: return open(p).read()
        except OSError: return ""
    mx = rd("/sys/fs/cgroup/memory.max").strip()
    st = {l.split()[0]: int(l.split()[1]) for l in rd("/sys/fs/cgroup/memory.stat").splitlines() if " " in l}
    out = {"memory_max_bytes": mx, "anon_bytes": st.get("anon"), "shmem_bytes": st.get("shmem")}
    if mx.isdigit() and st.get("anon") is not None and st.get("shmem") is not None:
        out["available_gib_v2"] = round((int(mx) - st["anon"] - st["shmem"]) / 2 ** 30, 2)
    return out


def shm_free_gib():
    try:
        st = os.statvfs("/dev/shm"); return (st.f_bavail * st.f_frsize) / 2 ** 30
    except OSError:
        return None


def foreign_engines():
    """every bt_launch process group that is NOT mine, by argv; reads the process table only, never signals."""
    mine = os.getpgid(0); out = {}
    try:
        ps = subprocess.run(["ps", "-eo", "pid,pgid,args"], capture_output=True, text=True, timeout=30).stdout
    except Exception as e:
        return {"UNREADABLE": f"{type(e).__name__}: {e}"}
    for line in ps.splitlines()[1:]:
        f = line.split(None, 2)
        if len(f) < 3 or "bt_launch.py" not in f[2]: continue
        pgid = int(f[1])
        if pgid == mine: continue
        out.setdefault(pgid, next((t for t in f[2].split() if t.endswith(".json")), "<config not in argv>"))
    return out


def engine_gate(cpath, poll=60, max_wait=6 * 3600):
    base = float(json.load(open(cpath))["launch"]["min_available_gib"]); need = base + ENGINE_GATE_MARGIN_GIB
    obs = []; t0 = time.monotonic()
    while True:
        g = foreign_engines(); m = mem_gate(); avail = m.get("available_gib_v2"); shm = shm_free_gib()
        claims = sorted(glob.glob(PRIORITY_CLAIMS))     # dlarch R1.4 priority-1 claims (lead's team order): yield while any exists
        ok = (not claims and len(g) <= MAX_FOREIGN_ENGINES and "UNREADABLE" not in g and avail is not None and avail >= need
              and shm is not None and shm >= SHM_FREE_MIN_GIB)
        obs.append({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "foreign_engine_pgids": {str(k): v for k, v in g.items()},
                    "avail_gib": avail, "need_gib": need, "need_gib_source": f"{cpath}:launch.min_available_gib ({base}) + {ENGINE_GATE_MARGIN_GIB}",
                    "shm_free_gib": None if shm is None else round(shm, 2), "priority_claims": claims, "PASS": bool(ok), "waited_s": int(time.monotonic() - t0)})
        if ok:
            log(f"engine gate PASS foreign={len(g)} avail={avail}>={need} shm={obs[-1]['shm_free_gib']}"); return obs
        log(f"engine gate WAIT claims={claims} foreign={list(g)} avail={avail}/{need} shm={obs[-1]['shm_free_gib']}")
        assert time.monotonic() - t0 < max_wait, f"engine gate: still blocked after {max_wait}s"
        time.sleep(poll)


def run(cmd, logp, env=None, cwd=None):
    e = {"PATH": "/usr/bin:/bin", "HOME": "/root"}
    if env: e.update(env)
    with open(logp, "w") as f:
        r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, env=e, cwd=cwd)
    if r.returncode != 0: print(open(logp).read()[-2000:], flush=True)
    return r.returncode


def arrays_equal(p1, p2):
    import numpy as np
    with np.load(p1, allow_pickle=False) as a, np.load(p2, allow_pickle=False) as b:
        if sorted(a.files) != sorted(b.files): return False, "key sets differ"
        for k in a.files:
            x, y = a[k], b[k]
            if x.dtype != y.dtype or x.shape != y.shape: return False, f"{k}: dtype/shape"
            if x.tobytes() != y.tobytes(): return False, f"{k}: bytes"
    return True, "all arrays bitwise"


def main():
    WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL)
    assert not extra, f"env outside whitelist: {extra}"
    assert sha(os.path.join(HERE, "dlarch_safe_io.py")) == SAFE_IO_SHA, "vendored dlarch_safe_io drifted"
    outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True); args = sys.argv[3:]
    seed = int(args[args.index("--seed") + 1]); rule = args[args.index("--rule") + 1]; mix = args[args.index("--mix") + 1]
    do_engine = "--engine" in args; eng_ident = "--engine-identity" in args
    assert seed in F10_SRC, f"seed {seed}: no NC reference cell to pair with"
    kind = args[args.index("--kind") + 1]
    assert kind in ("LQ",)
    F10_SRC[seed] = f"{BASE}/models/{kind}_s{seed}"
    identity_arm = False  # Entire score component replaced; seats remain inservice.
    assert not eng_ident or (identity_arm and do_engine), "--engine-identity is the in-service arm's end-to-end check"
    arm = f"ADAPT_{kind}_s{seed}X"; label = f"{kind}_s{seed}"
    if "--label" in args:     # a separate root (e.g. a re-identity combo that must not rmtree the kept identity cell's PATH files)
        assert not do_engine, "--label is for combo-only runs"; label = args[args.index("--label") + 1]
    root = f"{CELLS}/{label}"
    rec = {"device": "alloc_chain_run.py", "self_sha256": sha(os.path.abspath(__file__)), "arm": arm, "rule": rule, "mix": mix, "seed": seed,
           "root": root, "f10_source": F10_SRC[seed], "reference_cell": REF_CELL[seed],
           "devices": {n: sha(os.path.join(DEV, n)) for n in sorted(os.listdir(DEV)) if n.endswith(".py")},
           "devices_realpath": {n: os.path.realpath(os.path.join(DEV, n)) for n in sorted(os.listdir(DEV)) if n.endswith(".py")},
           "utc_start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "mem_gate_at_start": mem_gate(), "steps": {}}
    # ---- root ----
    if os.path.lexists(root): raise RuntimeError("private output already exists: " + root)
    for d in ("work/king", "inputs", "receipts", "vendor_live/fea171", "configs", "targets", "runs", "logs"):
        os.makedirs(f"{root}/{d}", exist_ok=True)
    for rel, src in SHARE.items():
        assert os.path.exists(src), f"missing share {src}"; os.symlink(src, f"{root}/{rel}")
    os.symlink(F10_SRC[seed], f"{root}/work/f10_s{seed}"); os.symlink(DEV, f"{root}/devices")
    L = f"{root}/logs"
    # ---- 1. combo ----
    t0 = time.monotonic()
    rc = run([PV, "-u", "-B", "alloc_combo.py", "--seed", str(seed), "--rule", rule, "--mix", mix], f"{L}/combo.log",
             env={"PNOISE_W": root, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
                  "NPY_DISABLE_CPU_FEATURES": "X86_V4 AVX512_ICL AVX512_SPR"}, cwd=f"{root}/devices")
    rec["steps"]["combo"] = {"rc": rc, "seconds": round(time.monotonic() - t0, 1)}
    assert rc == 0, "combo failed"
    cdir = f"{root}/work/combo_s{seed}"
    rec["steps"]["combo"]["outputs"] = {n: sha(f"{cdir}/{n}") for n in ("scaled_diagnostic.npz", "literal.npz", "TARGET_RECEIPT.json")}
    rec["steps"]["combo"]["arm_receipt"] = json.load(open(f"{cdir}/TARGET_RECEIPT.json"))["arm"]
    # ---- COMBO IDENTITY / WIRING gate ----
    arch = f"{NS}/work/combo_s{seed}"
    if os.path.isdir(arch):
        cmp_ = {}
        for n in ("scaled_diagnostic.npz", "literal.npz"):
            eq, why = arrays_equal(f"{arch}/{n}", f"{cdir}/{n}")
            cmp_[n] = {"archive_sha256": sha(f"{arch}/{n}"), "arm_sha256": sha(f"{cdir}/{n}"),
                       "container_IDENTICAL": sha(f"{arch}/{n}") == sha(f"{cdir}/{n}"), "arrays_IDENTICAL": eq, "why": why}
        allid = all(v["container_IDENTICAL"] and v["arrays_IDENTICAL"] for v in cmp_.values())
        rec["COMBO_VS_ARCHIVE"] = {"archive": arch, "files": cmp_, "ALL_IDENTICAL": allid, "expected_identical": identity_arm}
        log(f"COMBO_VS_ARCHIVE ALL_IDENTICAL={allid} expected={identity_arm}")
        if identity_arm:
            assert allid, "IDENTITY FAILED: the in-service arm does not reproduce the production-parity combo"
        else:
            assert not any(v["arrays_IDENTICAL"] for v in cmp_.values()), "WIRING FAILED: a non-identity arm reproduced the archive -- switch not wired"
    else:
        rec["COMBO_VS_ARCHIVE"] = {"archive": arch, "ARCHIVE_ABSENT": True,
                                   "note": "no archived combo at this seed; identity is inherited from the same code at s42/s2027, not proven here"}
    # ---- 2. adapter spec (dlarch's derived device, arm passed in) ----
    rc = run([PV, "-B", f"{DEV}/news2_adapter_specs.py", "PATH,HOME,LC_CTYPE", root, str(seed), arm], f"{L}/spec.log")
    assert rc == 0, "adapter spec failed"
    spec = f"{root}/configs/ADAPTER_SPEC_{arm}.json"; rec["steps"]["adapter_spec"] = {"rc": rc, "spec_sha256": sha(spec)}
    # ---- 3. adapter (UNMODIFIED) ----
    tnpz = f"{root}/targets/TARGETS_{arm}.npz"; tjson = tnpz.replace(".npz", ".json")
    rc = run([PV, "-B", "ovn_adapter.py", "PATH,HOME,LC_CTYPE", spec, tnpz, tjson], f"{L}/adapter.log", cwd=f"{NS}/engine")
    assert rc == 0, "adapter failed"
    import numpy as _np
    _R = json.load(open(tjson))
    with _np.load(tnpz, allow_pickle=False) as _z:
        for _k in _z.files: _ = _z[_k].tobytes()[:1]
    assert _R.get("targets_npz_sha256") == sha(tnpz), "targets receipt/npz disagree"
    rec["steps"]["adapter"] = {"rc": rc, "targets_npz_sha256": sha(tnpz), "targets_json_sha256": sha(tjson), "readback_verified": True}
    # ---- 4. RUN_CONFIG (only targets / arm / pod_root changed) ----
    cfg = json.load(open(BASE_CFG))
    base_run = [r for r in cfg["runs"] if r["tag"].endswith(BASE_CELL_SUFFIX)]
    assert len(base_run) == 1, f"expected one base cell in {BASE_CFG}"
    r0 = json.loads(json.dumps(base_run[0]))
    r0["arm"] = arm; r0["tag"] = f"{arm}|scaled|rule|raw|UAFE"; r0["targets"]["arm"] = arm
    for x in r0["targets"]["sources"]:
        x["npz"] = tnpz; x["npz_sha256"] = sha(tnpz); x["receipt"] = tjson; x["receipt_sha256"] = sha(tjson)
    r0["role"] = f"alloc combination-layer arm rule={rule} mix={mix} seed={seed} (DESIGN_combination_layer_2026-09-26)"
    cfg["runs"] = [r0]; cfg["paths"]["pod_root"] = root; cfg["config"] = f"RUN_CONFIG_{arm}"
    cpath = f"{root}/configs/RUN_CONFIG_{arm}.json"; sio.write_json(cpath, cfg)
    rec["steps"]["run_config"] = {"path": cpath, "sha256": sha(cpath), "base_config": BASE_CFG, "base_config_sha256": sha(BASE_CFG), "base_tag_used": base_run[0]["tag"]}
    # ---- 5. engine (UNMODIFIED) ----
    if do_engine:
        # lead 2026-09-26 18:1xZ team engine-slot priority: candidate cells run only when the lead places them. While the hold file
        # exists, a CANDIDATE arm waits here (controls -- the in-service identity, the fundflip red control, the oracle ceiling -- are
        # exempt). Scheduling only: nothing about the cell changes. Every poll is recorded in the receipt.
        control_arm = (rule in ("inservice", "oracle") and mix in ("shared", "fundflip", "negbook", "conc20"))
        rec["candidate_hold"] = []
        while (not control_arm) and os.path.exists(HOLD_FILE):
            rec["candidate_hold"].append(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
            if len(rec["candidate_hold"]) % 10 == 1: log(f"candidate hold: {HOLD_FILE} exists, waiting")
            time.sleep(60)
        rec["engine_gate"] = engine_gate(cpath)
        t0 = time.monotonic()
        rc = run([PV, "-B", "bt_launch.py", "PATH,HOME,LC_CTYPE", cpath, "--resume", arm], f"{L}/engine.log", cwd=f"{NS}/engine")
        rd = f"{root}/runs/{r0['tag'].replace('|', '_')}"
        paths = sorted(glob.glob(f"{rd}/PATH_*.npz"))
        rec["steps"]["engine"] = {"rc": rc, "seconds": round(time.monotonic() - t0, 1), "path_npz_found": len(paths), "expected": 32, "run_dir": rd}
        assert rc == 0 and len(paths) == 32, f"engine rc={rc} paths={len(paths)}"
        if eng_ident:
            ref = REF_CELL[seed]; per = []
            for k in range(32):
                a_ = f"{rd}/PATH_{arm}_scaled_rule_raw_UAFE_seed_{k:02d}.npz"
                b_ = f"{ref}/PATH_DLARCH_REF_NC_s{seed}X_scaled_rule_raw_UAFE_seed_{k:02d}.npz"
                eq, why = arrays_equal(a_, b_); per.append({"seed": k, "arrays_IDENTICAL": eq, "why": why})
            n_eq = sum(p["arrays_IDENTICAL"] for p in per)
            rec["ENGINE_IDENTITY"] = {"reference": ref, "n_paths_identical": n_eq, "n_paths": 32, "ALL_IDENTICAL": n_eq == 32, "per_path": per,
                                      "note": "arrays compared, not containers: the PATH npz embeds the arm name, which differs by construction"}
            log(f"ENGINE_IDENTITY {n_eq}/32")
            assert n_eq == 32, "ENGINE IDENTITY FAILED"
    else:
        rec["steps"]["engine"] = {"SKIPPED": "run again with --engine"}
    rec["utc_end"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    jsha = sio.write_json(os.path.join(outdir, f"ALLOC_CHAIN_{label}.json"), rec)
    print(f"ALLOC_CHAIN arm={arm} combo_vs_archive={rec['COMBO_VS_ARCHIVE'].get('ALL_IDENTICAL')} engine={rec['steps']['engine'].get('rc', 'skipped')} "
          f"engine_identity={rec.get('ENGINE_IDENTITY', {}).get('ALL_IDENTICAL')} json={jsha[:16]}", flush=True)


if __name__ == "__main__":
    main()

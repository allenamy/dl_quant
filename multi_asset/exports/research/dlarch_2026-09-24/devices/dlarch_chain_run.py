#!/usr/bin/env python3
"""dlarch_chain_run.py — run the DERIVED combo->engine chain for one family member (or the parity gate).

PREREG docs/PREREG_dlarch_T3_leg_gate_2026-09-25.md revision 9 + lead 2026-09-25 (build it so fresh's
combo-layer arms can reuse the same family members; README + parity receipt sha to fresh).

Layout it builds, per seed, under CHAIN/s<seed>/ :
    work/NEWS_FEATURES.npz            -> symlink  (read-only share)
    work/legs.npz                     -> symlink
    work/king/KING_OOF.npz            -> symlink
    work/f10_s<seed>                  -> symlink to the FAMILY MEMBER's training output
    inputs/bundle_config.json         -> symlink
    receipts/{P2B_FEATURES,P3_LEGS}.json, receipts/P1_members_2025H2on.npz -> symlinks
    vendor_live/fea171/combo_stage.py -> symlink
    devices/                          -> symlink to the DERIVED devices
    configs/ targets/ runs/ logs/     -> real, writable
Nothing is ever written under /dev/shm. runs/ lives under /workspace via paths.pod_root.

--parity: point work/f10_s42 at the IN-SERVICE F10 OOF and require the combo output to reproduce the
archived work/combo_s42/{scaled_diagnostic,literal}.npz BIT-FOR-BIT. That is the gate on the chain
itself; only after it passes is the chain used on family members.

usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B dlarch_chain_run.py \
         PATH,HOME,LC_CTYPE <outdir> (--parity | --seed N) [--engine]
"""
import os, sys, json, time, shutil, hashlib, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dlarch_safe_io as sio          # E-0925-A: artifact sha must come from a verified write
sio.install_guards()

NS = "/dev/shm/news2_2026-09-23"
BASE = "/workspace/dlarch_2026-09-24"
CHAIN = f"{BASE}/chain"
DEV = f"{CHAIN}/devices"
T0ROOT = f"{BASE}/T3/T0"
PV = "/workspace/venv/bin/python"
P314 = PV                                      # same interpreter as the NEW_S pin for combo
# Book-layer gate revision 2 (lead `8d2cc5546`): the T0 x 8 engine cells use the X extended axis
# (last anchor 2026-09-18T20Z, 9,252 anchors), not the short 08-31 axis. BASE_CFG is used ONLY by
# the engine step (L168/L181); the parity gate returns before it, so parity is NOT affected.
BASE_CFG = f"{NS}/configs/RUN_CONFIG_NEWS2_s42X_2026-09-23.json"
# BASE_TAG is DERIVED from BASE_CFG, never written next to it: two constants that must agree will
# drift, and they did -- switching BASE_CFG to the X config left the hardcoded BASE_TAG naming the
# short-axis run, and `len(base_run) == 1` caught it with "found 0" instead of silently taking a
# wrong run. The base cell is the one tagged "...|scaled|rule|raw|UAFE" with no cost-cell suffix:
# true for the short config (5 runs, of which 1 matches) and the X config (1 run).
BASE_CELL_SUFFIX = "|scaled|rule|raw|UAFE"
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


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def log(*a): print(time.strftime("%H:%M:%S", time.gmtime()), *a, flush=True)


def mem_gate():
    """The three numbers bt_launch's gate is computed from (lead: into every engine cell's receipt)."""
    def rd(p):
        try: return open(p).read()
        except OSError: return ""
    mx = rd("/sys/fs/cgroup/memory.max").strip()
    st = {l.split()[0]: int(l.split()[1]) for l in rd("/sys/fs/cgroup/memory.stat").splitlines() if " " in l}
    g = 1 << 30
    out = {"memory_max_bytes": mx, "anon_bytes": st.get("anon"), "shmem_bytes": st.get("shmem")}
    if mx.isdigit() and st.get("anon") is not None and st.get("shmem") is not None:
        out["available_gib_v2"] = round((int(mx) - st["anon"] - st["shmem"]) / g, 2)
        out["gate_threshold_gib"] = 22
        out["gate_passes_now"] = out["available_gib_v2"] >= 22
    return out


def build_root(root, seed, f10_src):
    if os.path.islink(root) or os.path.exists(root): shutil.rmtree(root, ignore_errors=True)
    for d in ("work/king", "inputs", "receipts", "vendor_live/fea171", "configs", "targets", "runs", "logs"):
        os.makedirs(f"{root}/{d}", exist_ok=True)
    for rel, src in SHARE.items():
        assert os.path.exists(src), f"missing share {src}"
        dst = f"{root}/{rel}"; os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not os.path.lexists(dst): os.symlink(src, dst)
    assert os.path.isdir(f10_src), f"missing F10 source {f10_src}"
    os.symlink(f10_src, f"{root}/work/f10_s{seed}")
    if not os.path.lexists(f"{root}/devices"): os.symlink(DEV, f"{root}/devices")
    return root


def run(cmd, logp, env=None, cwd=None):
    e = {"PATH": "/usr/bin:/bin", "HOME": "/root"}
    if env: e.update(env)
    with open(logp, "w") as f:
        r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, env=e, cwd=cwd)
    if r.returncode != 0:
        print(open(logp).read()[-1500:], flush=True)
    return r.returncode


def main():
    WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL)
    assert not extra, f"env outside whitelist: {extra}"
    outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
    args = sys.argv[3:]
    parity = "--parity" in args
    # --reference: the in-service NC s42 book on the X axis, needed as the dbar control for every
    # T0_k. The original NEWS2_s42X cell no longer exists (verified: zero PATH_NEWS2_s42X* files in
    # any tree; fanom ext/NEWS2_s42X keeps only its RUN_CONFIG). So it is re-made by THIS chain from
    # the in-service F10 -- and the run asserts the combo-layer parity inline, so the reference cell
    # carries its own proof that its book is the production book, not merely a rebuild of it.
    reference = "--reference" in args
    assert not (parity and reference), "--parity and --reference are different modes"
    inservice_f10 = parity or reference
    do_engine = "--engine" in args
    seed = 42 if inservice_f10 else int(args[args.index("--seed") + 1])
    label = "parity" if parity else ("ref_nc_s42X" if reference else f"s{seed}")
    f10_src = f"{NS}/work/f10_s42" if inservice_f10 else f"{T0ROOT}/f10_s{seed}"
    root = f"{CHAIN}/{label}"
    rec = {"device": "dlarch_chain_run.py", "self_sha256": sha(os.path.abspath(__file__)),
           "mode": "PARITY_GATE" if parity else ("REFERENCE_NC_s42X" if reference else "FAMILY_MEMBER"), "seed": seed, "root": root,
           "f10_source": f10_src, "derived_devices": DEV,
           "derive_receipt_sha256": sha(f"{DEV}/DERIVE_CHAIN.json"),
           "utc_start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "mem_gate_at_start": mem_gate(), "steps": {}}
    log(f"build root {root}  f10<-{f10_src}")
    build_root(root, seed, f10_src)
    L = f"{root}/logs"

    # ---- 1. combo (derived device; PNOISE_W redirects its root) ----
    t0 = time.monotonic()
    rc = run([P314, "-u", "news2_combo.py", "--seed", str(seed)], f"{L}/combo.log",
             env={"PNOISE_W": root, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
                  "NPY_DISABLE_CPU_FEATURES": "X86_V4 AVX512_ICL AVX512_SPR"}, cwd=f"{root}/devices")
    rec["steps"]["combo"] = {"rc": rc, "seconds": round(time.monotonic() - t0, 1)}
    assert rc == 0, "combo failed"
    cdir = f"{root}/work/combo_s{seed}"
    rec["steps"]["combo"]["outputs"] = {n: sha(f"{cdir}/{n}") for n in
                                       ("scaled_diagnostic.npz", "literal.npz", "TARGET_RECEIPT.json")}
    log("combo done", json.dumps(rec["steps"]["combo"]["outputs"]))

    # ---- PARITY GATE: must reproduce the archive BIT-FOR-BIT ----
    if parity or reference:
        arch = f"{NS}/work/combo_s42"
        cmp_ = {}
        for n in ("scaled_diagnostic.npz", "literal.npz"):
            a, b = sha(f"{arch}/{n}"), sha(f"{cdir}/{n}")
            cmp_[n] = {"archive_sha256": a, "chain_sha256": b, "IDENTICAL": a == b}
        rec["PARITY"] = {"archive": arch, "files": cmp_, "ALL_IDENTICAL": all(v["IDENTICAL"] for v in cmp_.values())}
        rec["utc_end"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        op = os.path.join(outdir, "CHAIN_PARITY.json")
        jsha = sio.write_json(op, rec)      # sha comes from the verified write, not a later re-read
        print(f"DLARCH_CHAIN_PARITY ALL_IDENTICAL={rec['PARITY']['ALL_IDENTICAL']} "
              + " ".join(f"{n}={v['IDENTICAL']}" for n, v in cmp_.items()) + f" json={jsha[:16]}", flush=True)
        assert rec["PARITY"]["ALL_IDENTICAL"], "CHAIN PARITY FAILED -- the derived chain is not the production chain"
        if parity:
            return                      # the gate stops here; --reference goes on to build the cell

    # ---- 2. adapter spec (derived device takes the seed on argv) ----
    t0 = time.monotonic()
    rc = run([PV, "-B", f"{DEV}/news2_adapter_specs.py", "PATH,HOME,LC_CTYPE", root, str(seed)], f"{L}/spec.log")
    rec["steps"]["adapter_spec"] = {"rc": rc, "seconds": round(time.monotonic() - t0, 1)}
    assert rc == 0, "adapter spec failed"
    spec = f"{root}/configs/ADAPTER_SPEC_DLARCH_T0_s{seed}.json"
    rec["steps"]["adapter_spec"]["spec_sha256"] = sha(spec)

    # ---- 3. adapter -> TARGETS (upstream device, UNMODIFIED) ----
    tnpz = f"{root}/targets/TARGETS_DLARCH_T0_s{seed}.npz"; tjson = tnpz.replace(".npz", ".json")
    t0 = time.monotonic()
    rc = run([PV, "-B", "ovn_adapter.py", "PATH,HOME,LC_CTYPE", spec, tnpz, tjson], f"{L}/adapter.log",
             cwd=f"{NS}/engine")
    rec["steps"]["adapter"] = {"rc": rc, "seconds": round(time.monotonic() - t0, 1)}
    assert rc == 0, "adapter failed"
    rec["steps"]["adapter"]["targets_npz_sha256"] = sha(tnpz)
    rec["steps"]["adapter"]["targets_json_sha256"] = sha(tjson)
    log("adapter done", sha(tnpz)[:16])

    # ---- 4. RUN_CONFIG: same settings, only targets / arm / pod_root changed ----
    cfg = json.load(open(BASE_CFG))
    base_run = [r for r in cfg["runs"] if r["tag"].endswith(BASE_CELL_SUFFIX)]
    assert len(base_run) == 1, (
        f"expected exactly one base cell (tag ending {BASE_CELL_SUFFIX}) in {BASE_CFG}, "
        f"found {[r['tag'] for r in base_run]}")
    BASE_TAG = base_run[0]["tag"]
    r0 = json.loads(json.dumps(base_run[0]))
    arm = "DLARCH_REF_NC_s42X" if reference else f"DLARCH_T0_s{seed}"
    r0["arm"] = arm; r0["tag"] = f"{arm}|scaled|rule|raw|UAFE"; r0["targets"]["arm"] = arm
    for x in r0["targets"]["sources"]:
        x["npz"] = tnpz; x["npz_sha256"] = sha(tnpz); x["receipt"] = tjson; x["receipt_sha256"] = sha(tjson)
    r0["role"] = ("dlarch dbar CONTROL: in-service NC s42 book on the X axis, rebuilt by this chain "
                  "because the original NEWS2_s42X PATH files no longer exist; combo layer asserted "
                  "bitwise identical to the production archive in this same run"
                  if reference else
                  f"dlarch T0 family member seed {seed} (sigma_F10 + fresh's fusion-layer family)")
    cfg["runs"] = [r0]; cfg["paths"]["pod_root"] = root; cfg["config"] = f"RUN_CONFIG_{arm}"
    cpath = f"{root}/configs/RUN_CONFIG_{arm}.json"
    sio.write_json(cpath, cfg)             # the engine reads this; read back before it is used
    rec["steps"]["run_config"] = {"path": cpath, "sha256": sha(cpath), "arm": arm, "tag": r0["tag"],
                                  "base_tag_used": BASE_TAG,
                                  "pod_root": root, "base_config": BASE_CFG, "base_config_sha256": sha(BASE_CFG)}
    log("config done", arm)

    # ---- 5. engine (upstream bt_launch, UNMODIFIED) ----
    if do_engine:
        rec["mem_gate_before_engine"] = mem_gate()
        t0 = time.monotonic()
        rc = run([PV, "-B", "bt_launch.py", "PATH,HOME,LC_CTYPE", cpath, "--resume", arm], f"{L}/engine.log",
                 cwd=f"{NS}/engine")
        npaths = len([f for f in os.listdir(f"{root}/runs/{r0['tag'].replace('|', '_')}")
                      if f.endswith(".npz")]) if os.path.isdir(f"{root}/runs/{r0['tag'].replace('|', '_')}") else 0
        rec["steps"]["engine"] = {"rc": rc, "seconds": round(time.monotonic() - t0, 1),
                                  "path_npz_found": npaths, "expected": 32}
        rec["mem_gate_after_engine"] = mem_gate()
        log("engine rc", rc, "paths", npaths)
    else:
        rec["steps"]["engine"] = {"SKIPPED": "run again with --engine"}
    rec["utc_end"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    op = os.path.join(outdir, f"CHAIN_{label}.json")
    jsha = sio.write_json(op, rec)         # sha comes from the verified write
    print(f"DLARCH_CHAIN seed={seed} combo_ok=1 targets={sha(tnpz)[:16]} "
          f"engine={rec['steps']['engine'].get('rc', 'skipped')} json={jsha[:16]}", flush=True)


if __name__ == "__main__":
    main()

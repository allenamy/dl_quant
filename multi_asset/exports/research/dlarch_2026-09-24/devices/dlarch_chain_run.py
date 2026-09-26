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
T0ROOT = f"{BASE}/T3/T0"          # kept for reference; the live value is TRAIN_ROOT, derived from --train-arm
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


# Team engine rule (lead 2026-09-25, updated twice): at most THREE cells in parallel.
# MAX_FOREIGN_ENGINES is the count of OTHER bt_launch process groups tolerated -- 2, so that mine plus
# two others makes three. (It was 1 for the two-cell rule; lead raised it.) The memory floor is the config's own launch.min_available_gib (single source,
# read from the very file bt_launch is handed) PLUS a named margin, so the two numbers never drift:
# the margin is explicit and the base is never copied.
MAX_FOREIGN_ENGINES = 2
ENGINE_GATE_MARGIN_GIB = 2.0      # named margin ON TOP OF the config's min_available_gib
SHM_FREE_MIN_GIB = 4.0            # /dev/shm is shared with every other agent's caches


def shm_free_gib():
    try:
        st = os.statvfs("/dev/shm")
        return (st.f_bavail * st.f_frsize) / 2 ** 30
    except OSError:
        return None                # unreadable => caller must not proceed


def foreign_engines():
    """Every bt_launch process group that is NOT mine, identified by the CONFIG PATH in its argv.

    Team rule (lead 2026-09-25): one engine cell at a time; the 04:33Z oom_kill came from several heavy
    runs stacking. Identification is by argv, NOT by pgid resemblance: at 06:56Z I mistook another
    group's bt_launch (fanom's KZWL ladder) for my own purely because its pgid looked familiar and I
    never read its argv. Reads the process table ONLY -- this function never signals anything.
    """
    mine = os.getpgid(0)
    out = {}
    try:
        ps = subprocess.run(["ps", "-eo", "pid,pgid,args"], capture_output=True, text=True, timeout=30).stdout
    except Exception as e:
        return {"UNREADABLE": f"{type(e).__name__}: {e}"}     # cannot verify => caller must not proceed
    for line in ps.splitlines()[1:]:
        f = line.split(None, 2)
        if len(f) < 3 or "bt_launch.py" not in f[2]:
            continue
        pgid = int(f[1])
        if pgid == mine:
            continue
        cfg = next((t for t in f[2].split() if t.endswith(".json")), "<config not in argv>")
        out.setdefault(pgid, cfg)
    return out


def engine_gate(cpath, poll=60, max_wait=14400):
    """Block until the team engine rule is satisfied, then return the observation log for the receipt
    (every poll recorded, so a long wait is auditable).

    THREE conditions, all measured, none inferred:
      1 foreign bt_launch process groups <= MAX_FOREIGN_ENGINES (at most two cells in parallel),
        identified by the CONFIG PATH in argv -- never by a familiar-looking pgid;
      2 cgroup available (memory.max - anon - shmem) >= config's launch.min_available_gib + a named margin;
      3 /dev/shm free >= SHM_FREE_MIN_GIB (it is shared with every other agent's caches).
    An UNREADABLE process table, headroom or shm reading is NOT a pass: if I cannot verify a condition
    I must not start.

    The threshold is read from THE CONFIG bt_launch will read -- `launch.min_available_gib` in cpath,
    the same file, so there is exactly ONE number and it cannot drift. bt_launch does
    `MINFREE = float(CFG["launch"]["min_available_gib"])` (bt_launch.py L151) and blocks with
    "memory: available 20.1 GiB < 22.0 ... polling every 60 s" (L210).

    Two earlier versions of this docstring were wrong in the same way twice over: first I invented a
    separate `min_avail_gib=8.0` default (looser than the engine's, so my gate would "pass" and then
    the work would sit blocked INSIDE bt_launch while holding the one engine slot), then I pointed it
    at my own `mem_gate()["gate_threshold_gib"] = 22`, which is still a COPY of the config's value.
    Reading the config is the single source. I wrote the 8.0 version one hour after building the
    coupled-constant census -- the census only checks couplings I declared, so new code can add a new
    one; that is the census's real limitation and it is why this note is here."""
    # single source: the very config bt_launch will be handed
    base = float(json.load(open(cpath))["launch"]["min_available_gib"])
    need = base + ENGINE_GATE_MARGIN_GIB
    obs = []
    t0 = time.monotonic()
    while True:
        g = foreign_engines()
        m = mem_gate()
        avail = m.get("available_gib_v2")        # computed by mem_gate; absent if memory.max is "max"
        rec = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "foreign_engine_pgids": {str(k): v for k, v in g.items()},
               "avail_gib": avail, "mem_gate": m, "waited_s": int(time.monotonic() - t0)}
        # An unreadable process table or an unavailable headroom reading is NOT a pass: if I cannot
        # verify the condition, I must not start. (Absent evidence is not evidence of absence.)
        shm = shm_free_gib()
        rec["need_gib"] = need
        rec["need_gib_source"] = f"{cpath}:launch.min_available_gib ({base}) + named margin {ENGINE_GATE_MARGIN_GIB}"
        rec["shm_free_gib"] = None if shm is None else round(shm, 2)
        rec["shm_free_min_gib"] = SHM_FREE_MIN_GIB
        rec["max_foreign_engines"] = MAX_FOREIGN_ENGINES
        # Three conditions, all measured; an UNREADABLE reading is never a pass.
        ok = (len(g) <= MAX_FOREIGN_ENGINES and "UNREADABLE" not in g
              and avail is not None and avail >= need
              and shm is not None and shm >= SHM_FREE_MIN_GIB)
        rec["PASS"] = bool(ok)
        obs.append(rec)
        if ok:
            log(f"engine gate PASS: foreign={len(g)}<={MAX_FOREIGN_ENGINES} avail={avail}>={need} "
                f"shm={rec['shm_free_gib']}>={SHM_FREE_MIN_GIB} GiB, waited {rec['waited_s']}s")
            return obs
        log(f"engine gate WAIT: foreign={list(g)}(max {MAX_FOREIGN_ENGINES}) avail={avail}/{need} "
                f"shm={rec['shm_free_gib']}/{SHM_FREE_MIN_GIB} GiB waited={rec['waited_s']}s")
        assert time.monotonic() - t0 < max_wait, f"engine gate: still blocked after {max_wait}s, giving up"
        time.sleep(poll)


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
    # --reference may now name a seed (lead revision 5: rebuild NC references at s2027 and s7 so the
    # pairing is same-seed). Default stays 42, so every existing command line and the already-built
    # DLARCH_REF_NC_s42X cell keep their exact identity. --parity stays pinned to 42 because the object
    # it reproduces is the DEPLOYED book, which exists at one seed only.
    if parity:
        seed = 42
    elif reference:
        seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 42
    else:
        seed = int(args[args.index("--seed") + 1])
    # --train-arm: which TRAINING arm's family member this cell is built from. Default T0, so every
    # existing command line keeps its exact meaning and the T0 cells already produced stay comparable.
    # lead 2026-09-25 asked for T3 to be PIPELINED -- each T3 seed's book cell run as soon as that seed
    # finishes training, rather than waiting for 3/3 -- which needs the source root and the cell's arm
    # name to follow the training arm instead of being hardcoded to T0.
    train_arm = "T0"
    if "--train-arm" in args:
        train_arm = args[args.index("--train-arm") + 1]
    assert train_arm in ("T0", "T3_clamp"), f"unknown train arm {train_arm}"
    assert not (inservice_f10 and train_arm != "T0"), "--parity/--reference use the in-service F10, so a train arm is meaningless there"
    TRAIN_ROOT = f"{BASE}/T3/{train_arm}"
    label = "parity" if parity else (f"ref_nc_s{seed}X" if reference else f"{'s' if train_arm == 'T0' else train_arm + '_s'}{seed}")
    # --ref-f10 names the reference cell's F10 EXPLICITLY. Needed because seed 7 has no NC-recipe F10 in
    # news2's tree (only 42 and 2027 exist), so its reference must be built from dlarch's own --no-mask
    # product -- which G1 proved is BITWISE identical to the in-service F10 at s42. Passing the path
    # rather than inferring it keeps the receipt honest about which array was used.
    if "--ref-f10" in args:
        assert reference, "--ref-f10 only means something with --reference"
        f10_src = args[args.index("--ref-f10") + 1]
    elif inservice_f10:
        f10_src = f"{NS}/work/f10_s{seed}"
    else:
        f10_src = f"{TRAIN_ROOT}/f10_s{seed}"
    # ONE source of truth for the arm name. It used to be rebuilt in four places (here, the adapter
    # spec device, the spec path, the targets path); the copies drifted as soon as --reference added a
    # second arm, and the engine's bt_objb_targets caught it: arm_mismatch {receipt: DLARCH_T0_s42,
    # want: DLARCH_REF_NC_s42X}. Computed once, passed down, recorded in the receipt.
    arm = f"DLARCH_REF_NC_s{seed}X" if reference else f"DLARCH_{train_arm}_s{seed}"
    root = f"{CHAIN}/{label}"
    rec = {"device": "dlarch_chain_run.py", "self_sha256": sha(os.path.abspath(__file__)),
           "mode": "PARITY_GATE" if parity else (f"REFERENCE_NC_s{seed}X" if reference else "FAMILY_MEMBER"), "seed": seed, "root": root,
           "f10_source": f10_src, "train_arm": train_arm, "derived_devices": DEV,
           "reference_is_the_deployed_book": bool(inservice_f10 and seed == 42),
           "reference_note": (None if not reference else
                              ("s42: the archived combo reproduced here IS the deployed production book"
                               if seed == 42 else
                               f"s{seed}: NC RECIPE at a seed production never ran; the parity assertion "
                               "still validates this chain, but this cell is not 'the production book'")),
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
        # the archived combo to reproduce, at THIS seed. For s42 that archive IS the deployed production
        # book; for any other seed it is an archived research combo at a seed production never ran. The
        # parity assertion validates MY CHAIN equally in both cases, but only the s42 reference cell may
        # be called "the production book" -- recorded in the receipt so the two are not conflated.
        arch = f"{NS}/work/combo_s{seed}"
        if not os.path.isdir(arch):
            # No archived combo exists at this seed, so this cell CANNOT carry a bitwise self-proof.
            # s42 and s2027 have archives and do prove themselves; s7 does not exist upstream at all.
            # Recording the absence explicitly, because a missing proof must not read as a passed one.
            rec["PARITY"] = {"archive": arch, "ARCHIVE_ABSENT": True, "ALL_IDENTICAL": None,
                             "why_no_self_proof": (
                                 "no archived combo at this seed, so there is nothing to reproduce. This "
                                 "cell's standing rests on two OTHER things, both named: (a) the chain is "
                                 "the same code that reproduced the s42 and s2027 archives bit-for-bit, "
                                 "and (b) its F10 is dlarch's --no-mask product, which G1 proved bitwise "
                                 "identical to the in-service F10 AT s42 -- inherited, never verified at "
                                 "this seed, and unverifiable here because no NC F10 exists at this seed.")}
            assert reference, "only a --reference cell may proceed without an archive"
        else:
            cmp_ = {}
            for n in ("scaled_diagnostic.npz", "literal.npz"):
                a, b = sha(f"{arch}/{n}"), sha(f"{cdir}/{n}")
                cmp_[n] = {"archive_sha256": a, "chain_sha256": b, "IDENTICAL": a == b}
            rec["PARITY"] = {"archive": arch, "files": cmp_,
                             "ALL_IDENTICAL": all(v["IDENTICAL"] for v in cmp_.values())}
        rec["utc_end"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        op = os.path.join(outdir, "CHAIN_PARITY.json")
        jsha = sio.write_json(op, rec)      # sha comes from the verified write, not a later re-read
        # `cmp_` exists ONLY when an archive was present. My first archive-absent patch added the new
        # branch but did not follow this consumer, so the s7 run died here with UnboundLocalError AFTER
        # completing its combo -- a branch changed without checking who reads its variables.
        _files = rec["PARITY"].get("files") or {}
        print(f"DLARCH_CHAIN_PARITY ALL_IDENTICAL={rec['PARITY']['ALL_IDENTICAL']} "
              + " ".join(f"{n}={v['IDENTICAL']}" for n, v in _files.items()) + f" json={jsha[:16]}", flush=True)
        # Distinguish ABSENT from FAILED. A missing archive is a named limitation recorded above; a
        # present archive that does not match is a hard stop. Collapsing the two would let "no proof"
        # pass as "proof".
        if rec["PARITY"].get("ARCHIVE_ABSENT"):
            print("DLARCH_CHAIN_PARITY SKIPPED: no archive at this seed; this cell carries NO self-proof "
                  "(see PARITY.why_no_self_proof)", flush=True)
        else:
            assert rec["PARITY"]["ALL_IDENTICAL"], "CHAIN PARITY FAILED -- the derived chain is not the production chain"
        if parity:
            return                      # the gate stops here; --reference goes on to build the cell

    # ---- 2. adapter spec (derived device takes the seed on argv) ----
    t0 = time.monotonic()
    rc = run([PV, "-B", f"{DEV}/news2_adapter_specs.py", "PATH,HOME,LC_CTYPE", root, str(seed), arm], f"{L}/spec.log")
    rec["steps"]["adapter_spec"] = {"rc": rc, "seconds": round(time.monotonic() - t0, 1)}
    assert rc == 0, "adapter spec failed"
    spec = f"{root}/configs/ADAPTER_SPEC_{arm}.json"
    rec["steps"]["adapter_spec"]["spec_sha256"] = sha(spec)

    # ---- 3. adapter -> TARGETS (upstream device, UNMODIFIED) ----
    tnpz = f"{root}/targets/TARGETS_{arm}.npz"; tjson = tnpz.replace(".npz", ".json")
    t0 = time.monotonic()
    rc = run([PV, "-B", "ovn_adapter.py", "PATH,HOME,LC_CTYPE", spec, tnpz, tjson], f"{L}/adapter.log",
             cwd=f"{NS}/engine")
    rec["steps"]["adapter"] = {"rc": rc, "seconds": round(time.monotonic() - t0, 1)}
    assert rc == 0, "adapter failed"
    # ---- read back the adapter's outputs BEFORE hashing them (E-0925-A, applied to a file that
    # upstream code wrote). fresh spotted the hole at ovn_adapter.py:196: the adapter verifies the NPZ
    # (verify_roundtrip + `assert sha(out_npz) == s_npz == R["targets_npz_sha256"]`) but then REWRITES
    # the receipt with the round-trip result and prints `sha(out_receipt)` by re-reading the file, with
    # no assertion that the rewritten receipt reads back. I then hash that same file and put the value
    # into the engine's RUN_CONFIG as `receipt_sha256` -- so a truncated receipt would be compared
    # against the sha OF THE TRUNCATED FILE, agree, and the engine would proceed. These three checks
    # close that: the json must parse, the npz must decompress, and the receipt's own recorded
    # npz sha must equal the npz's actual sha (which ties receipt CONTENT to the artifact).
    try:
        _R = json.load(open(tjson))
    except Exception as e:
        raise AssertionError(f"targets receipt does not parse after the adapter rewrote it: {tjson}: {e}")
    import numpy as _np
    with _np.load(tnpz, allow_pickle=False) as _z:
        for _k in _z.files:
            _a = _z[_k]
            _ = _a.tobytes()[:1] if _a.size else b""
    _npz_sha = sha(tnpz)
    assert _R.get("targets_npz_sha256") == _npz_sha, (
        f"targets receipt records npz sha {str(_R.get('targets_npz_sha256'))[:16]} but the npz is "
        f"{_npz_sha[:16]} -- receipt and artifact disagree, refusing to hand this to the engine")
    rec["steps"]["adapter"]["readback_verified"] = {
        "receipt_parses": True, "npz_arrays_read_back": True,
        "receipt_npz_sha_matches_artifact": True,
        "why": "ovn_adapter rewrites the receipt then hashes it by re-reading; nothing asserted the "
               "rewrite is readable (E-0925-A family, flagged by fresh)"}
    rec["steps"]["adapter"]["targets_npz_sha256"] = _npz_sha
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
        # Team rule: one engine cell at a time. Gate BEFORE the engine step, never around it.
        rec["engine_gate"] = engine_gate(cpath)
        rec["mem_gate_before_engine"] = mem_gate()
        t0 = time.monotonic()
        rc = run([PV, "-B", "bt_launch.py", "PATH,HOME,LC_CTYPE", cpath, "--resume", arm], f"{L}/engine.log",
                 cwd=f"{NS}/engine")
        # Count ONLY the PATH npz. Counting every .npz also swept in the aggregate AGG_<tag>.npz, so the
        # field named `path_npz_found` reported 33 against `expected: 32` -- a check that could never
        # pass, and whose failure mode is that someone "fixes" it by changing 32 to 33 and loses the
        # check entirely. Same family as `anchors_outside_universe` counting only one side: the name and
        # the number have to mean the same thing. s42's cell was produced before this fix and its receipt
        # says 33; its true PATH count was verified to be 32 (64 files = 32 npz + 32 json).
        _rd = f"{root}/runs/{r0['tag'].replace('|', '_')}"
        _all_npz = [f for f in os.listdir(_rd) if f.endswith(".npz")] if os.path.isdir(_rd) else []
        npaths = len([f for f in _all_npz if f.startswith("PATH")])
        nagg = len([f for f in _all_npz if f.startswith("AGG")])
        rec["steps"]["engine"] = {"rc": rc, "seconds": round(time.monotonic() - t0, 1),
                                  "path_npz_found": npaths, "expected": 32,
                                  "agg_npz_found": nagg, "all_npz": len(_all_npz),
                                  "count_note": "path_npz_found counts PATH*.npz only; the aggregate is "
                                                "counted separately so the field matches its name"}
        assert rc != 0 or npaths == 32, (f"engine rc=0 but {npaths} PATH npz, expected 32 "
                                         f"(aggregates: {nagg}, all npz: {len(_all_npz)})")
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

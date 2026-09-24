"""Startup gate: refuse to run a chain step unless its environment matches the NEW_S pin for THAT step.

lead 2026-09-24: the class-shaped fix for "I read the device names instead of the chain script". Getting it
right once by following the script by hand is not a fix; the pin has to be enforced at every entry point.

The pins are transcribed from /dev/shm/news_2026-09-23/devices/news_chain_resume.sh, per step, with the
line each one comes from. Gates B1/B2 compare this book against NEW_S, so "same conditions" means the
same interpreter and the same numerical environment at every step, not merely a working one.

★ WHY THE PIN IS sys.prefix AND NOT THE PATH OR THE REALPATH.
  /workspace/venv/bin/python is a symlink. Measured on pod2:

      /workspace/venv/bin/python   realpath /usr/bin/python3.11   sys.prefix /workspace/venv   numpy 2.4.6
      /usr/bin/python3             realpath /usr/bin/python3.11   sys.prefix /usr              numpy 2.4.6

  Same realpath. Same numpy VERSION. They differ only in which site-packages numpy is imported from
  (/workspace/venv/lib/python3.11/site-packages vs /usr/local/lib/python3.11/dist-packages). So a gate
  that asserted the realpath, or the version string, would pass the exact mutation lead asked to be
  refused -- it would be a gate that cannot fail. sys.prefix is the thing that actually differs, and
  numpy's load directory is recorded next to it as the consequence that matters.

Each pin says, for its step:
  prefix        required sys.prefix (the environment, not the path typed on the command line)
  npy_disable   the required value of NPY_DISABLE_CPU_FEATURES, or None meaning it MUST BE UNSET
  threads       required OMP_NUM_THREADS / OPENBLAS_NUM_THREADS, or None meaning unconstrained

"Unconstrained" is written as None and PRINTED as unconstrained; it is never silently skipped, because a
check that quietly does nothing is the failure mode this whole gate exists to prevent.

usage:
  python news2_env_gate.py --check <step>       exit 0 if the environment matches, 9 with a named refusal
  python news2_env_gate.py --selftest <out.json>    baseline-green + the wrong-interpreter mutation
  python -c "import news2_env_gate as g; g.require('combo')"    in-process, from a device
"""
import json, os, subprocess, sys, time

PV = "/workspace/venv"
P314 = "/root/news_2026-09-23_env/venv314"
NPY = "X86_V4 AVX512_ICL AVX512_SPR"

# step -> (required sys.prefix, required NPY_DISABLE_CPU_FEATURES or None=unset, OMP, OPENBLAS, source line)
PINS = {
    "king":     (PV,   NPY,  None, None, "news_chain_resume.sh L14: nice -n 5 $PV -u news_train_king.py, "
                                         "under the script-level `export NPY_DISABLE_CPU_FEATURES=...`; "
                                         "AMENDMENT 2 lead ruling (a) moved King from $P314 to $PV"),
    "legs":     (P314, NPY,  "1", "1",   "news_chain_resume.sh L15: OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 "
                                         "nice -n 5 $P314 -u news_legs.py"),
    "f10":      (PV,   None, "2", "2",   "news_chain_resume.sh: `unset NPY_DISABLE_CPU_FEATURES` then "
                                         "OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 setsid $PV -u news_train_f10.py"),
    "combo":    (P314, NPY,  "1", "1",   "news_chain_resume.sh: export restored, then OMP_NUM_THREADS=1 "
                                         "OPENBLAS_NUM_THREADS=1 nice -n 5 $P314 -u news_combo.py"),
    "adapter":  (PV,   None, None, None, "news_chain_resume.sh: env -i PATH=/usr/bin:/bin HOME=/root $PV -B "
                                         "news_adapter_specs.py / ovn_adapter*.py (env -i leaves NPY unset)"),
    "configs":  (PV,   None, None, None, "news_chain_resume.sh: env -i ... $PV -B news_make_configs.py"),
    "engine":   (PV,   None, None, None, "news_chain_resume.sh: setsid env -i ... $PV -B bt_launch.py"),
    "readings": (PV,   None, None, None, "news_chain_resume.sh: env -i ... $PV -B bt_p*_reading.py"),
    "stats":    (PV,   None, None, None, "news_chain_resume.sh: env -i ... $PV -B news_stats.py"),
    "ext":      (PV,   None, None, None, "news_chain_resume.sh: env -i ... $PV -B news_ext.py"),
    # my own step; NEW_S has no counterpart, so there is nothing to match and nothing is claimed
    "staging":  (None, None, None, None, "news2 only (no NEW_S counterpart): pure file staging, no arithmetic"),
    # P5 export. The pin source is WEAKER than the others and that is stated rather than smoothed over:
    # NEW_S's P5 manifest records only torch 2.11.0+cu128 / numpy 2.4.6 (which identifies PV), and the
    # device docstring documents the usage as "/workspace/venv/bin/python news_export_models.py" with no
    # env prefix -- so NPY_DISABLE unset is read off the DOCUMENTED USAGE, not off a recorded environment.
    "export":   (PV,   None, None, None, "news_export_models.py docstring usage line + the NEW_S P5 manifest "
                                         "(torch 2.11.0+cu128 / numpy 2.4.6 => PV). NOTE: NEW_S recorded no "
                                         "env for this step, so the unset requirement is inferred from the "
                                         "documented usage, not measured from NEW_S."),
}


def measured():
    import importlib
    m = {"sys_executable": sys.executable, "realpath": os.path.realpath(sys.executable),
         "sys_prefix": sys.prefix, "sys_base_prefix": sys.base_prefix,
         "python_version": sys.version.split()[0],
         "NPY_DISABLE_CPU_FEATURES": os.environ.get("NPY_DISABLE_CPU_FEATURES"),
         "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS"),
         "OPENBLAS_NUM_THREADS": os.environ.get("OPENBLAS_NUM_THREADS")}
    for mod in ("numpy", "lightgbm", "torch"):
        try:
            x = importlib.import_module(mod)
            m[mod] = getattr(x, "__version__", None)
            m[mod + "_path"] = os.path.dirname(getattr(x, "__file__", "") or "")
        except Exception as e:
            m[mod] = None
            m[mod + "_import_error"] = f"{type(e).__name__}: {e}"
    if m.get("torch"):
        try:
            import torch
            m["torch_cuda"] = torch.version.cuda
            m["gpu_name"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
            m["gpu_capability"] = list(torch.cuda.get_device_capability(0)) if torch.cuda.is_available() else None
            m["torch_arch_list"] = torch.cuda.get_arch_list()
        except Exception as e:
            m["torch_probe_error"] = f"{type(e).__name__}: {e}"
    return m


def evaluate(step):
    """Returns (ok, measured, expected, failures). Pure: makes no decision about exiting."""
    if step not in PINS:
        return False, measured(), None, [f"unknown step {step!r}; known: {sorted(PINS)}"]
    prefix, npy, omp, blas, src = PINS[step]
    m = measured()
    exp = {"sys_prefix": prefix, "NPY_DISABLE_CPU_FEATURES": npy,
           "OMP_NUM_THREADS": omp, "OPENBLAS_NUM_THREADS": blas, "pin_source": src}
    fail = []
    if prefix is not None and m["sys_prefix"] != prefix:
        fail.append(f"sys_prefix is {m['sys_prefix']!r}, the pin for {step!r} is {prefix!r} "
                    f"(note: the realpath and the numpy VERSION do not distinguish these interpreters)")
    # None means MUST BE UNSET -- an explicit requirement, not an absence of one
    if npy is None:
        if m["NPY_DISABLE_CPU_FEATURES"] is not None:
            fail.append(f"NPY_DISABLE_CPU_FEATURES is set to {m['NPY_DISABLE_CPU_FEATURES']!r}; "
                        f"the pin for {step!r} requires it UNSET")
    elif m["NPY_DISABLE_CPU_FEATURES"] != npy:
        fail.append(f"NPY_DISABLE_CPU_FEATURES is {m['NPY_DISABLE_CPU_FEATURES']!r}, the pin is {npy!r}")
    for name, want in (("OMP_NUM_THREADS", omp), ("OPENBLAS_NUM_THREADS", blas)):
        if want is not None and m[name] != want:
            fail.append(f"{name} is {m[name]!r}, the pin is {want!r}")
    return not fail, m, exp, fail


def require(step, receipt_path=None):
    """Call this FIRST in a chain step. Raises SystemExit(9) with a named reason if the env is wrong."""
    ok, m, exp, fail = evaluate(step)
    rec = {"device": "news2_env_gate.py", "step": step,
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "measured": m, "expected": exp, "failures": fail, "VERDICT": "PASS" if ok else "REFUSED"}
    if receipt_path:
        json.dump(rec, open(receipt_path, "w"), indent=1)
    unc = [k for k, v in (("OMP_NUM_THREADS", exp and exp.get("OMP_NUM_THREADS")),
                          ("OPENBLAS_NUM_THREADS", exp and exp.get("OPENBLAS_NUM_THREADS"))) if v is None]
    print(f"NEWS2_ENV_GATE step={step} VERDICT={rec['VERDICT']} "
          f"sys_prefix={m['sys_prefix']} npy_disable={m['NPY_DISABLE_CPU_FEATURES']!r} "
          f"omp={m['OMP_NUM_THREADS']!r} openblas={m['OPENBLAS_NUM_THREADS']!r} "
          f"unconstrained={unc or 'none'}", flush=True)
    if not ok:
        for f in fail:
            print(f"  REFUSED: {f}", flush=True)
        sys.exit(9)
    return rec


def selftest(out_path):
    """Both experiments lead asked for, measured, in one receipt.

    BASELINE GREEN first: the gate must PASS under the correct environment. A mutation check whose
    baseline is already red is vacuous -- it would "catch" the mutation for the wrong reason.
    Then the MUTATION: relaunch this same file under /usr/bin/python3 and require refusal with rc 9.
    """
    cells, t0 = [], time.time()

    def cell(tag, ok, want, got):
        cells.append({"cell": tag, "verdict": "PASS" if ok else "FAIL", "expected": want, "observed": got})
        print(f"  {tag:34s} {'PASS' if ok else 'FAIL':5s} expected={want}  observed={got}", flush=True)

    me = os.path.abspath(__file__)

    def run(interp, step, env):
        e = dict(os.environ)
        for k, v in env.items():
            if v is None:
                e.pop(k, None)
            else:
                e[k] = v
        r = subprocess.run([interp, me, "--check", step], capture_output=True, text=True, env=e)
        line = (r.stdout + r.stderr).strip().splitlines()
        return r.returncode, (line[0] if line else ""), "\n".join(line)

    # --- baseline green: every step under its own pinned environment
    base_env = {
        "king":     ("/workspace/venv/bin/python", {"NPY_DISABLE_CPU_FEATURES": NPY, "OMP_NUM_THREADS": None, "OPENBLAS_NUM_THREADS": None}),
        "legs":     (f"{P314}/bin/python", {"NPY_DISABLE_CPU_FEATURES": NPY, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"}),
        "f10":      ("/workspace/venv/bin/python", {"NPY_DISABLE_CPU_FEATURES": None, "OMP_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "2"}),
        "combo":    (f"{P314}/bin/python", {"NPY_DISABLE_CPU_FEATURES": NPY, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"}),
        "engine":   ("/workspace/venv/bin/python", {"NPY_DISABLE_CPU_FEATURES": None, "OMP_NUM_THREADS": None, "OPENBLAS_NUM_THREADS": None}),
    }
    for step, (interp, env) in base_env.items():
        rc, first, _ = run(interp, step, env)
        cell(f"GREEN.baseline.{step}", rc == 0 and "VERDICT=PASS" in first,
             "rc 0, VERDICT=PASS under the pinned environment", f"rc={rc} {first[:110]}")

    # --- the mutation lead named: the wrong interpreter must be refused
    rc, first, full = run("/usr/bin/python3", "king",
                          {"NPY_DISABLE_CPU_FEATURES": NPY, "OMP_NUM_THREADS": None, "OPENBLAS_NUM_THREADS": None})
    cell("RED.mutation.system_python", rc == 9 and "VERDICT=REFUSED" in first and "sys_prefix" in full,
         "rc 9, REFUSED, and the reason names sys_prefix",
         f"rc={rc} {first[:110]}")

    # the same interpreter, right prefix, wrong numerical env -> also refused
    rc, first, _ = run("/workspace/venv/bin/python", "f10", {"NPY_DISABLE_CPU_FEATURES": NPY, "OMP_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "2"})
    cell("RED.mutation.npy_set_when_unset_required", rc == 9 and "VERDICT=REFUSED" in first,
         "rc 9, REFUSED (f10 requires the variable UNSET)", f"rc={rc} {first[:110]}")
    rc, first, _ = run(f"{P314}/bin/python", "legs", {"NPY_DISABLE_CPU_FEATURES": NPY, "OMP_NUM_THREADS": "8", "OPENBLAS_NUM_THREADS": "1"})
    cell("RED.mutation.wrong_thread_count", rc == 9 and "VERDICT=REFUSED" in first,
         "rc 9, REFUSED (legs pins OMP=1)", f"rc={rc} {first[:110]}")

    bad = [c for c in cells if c["verdict"] != "PASS"]
    rec = {"device": "news2_env_gate.py", "mode": "selftest",
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "why_sys_prefix_and_not_realpath":
               "/workspace/venv/bin/python and /usr/bin/python3 have the SAME realpath "
               "(/usr/bin/python3.11) and the SAME numpy version (2.4.6); they differ in sys.prefix and "
               "therefore in which site-packages numpy is loaded from. A gate on the realpath or on the "
               "version string could not refuse the mutation lead asked to be refused.",
           "pins": {k: {"sys_prefix": v[0], "NPY_DISABLE_CPU_FEATURES": v[1], "OMP_NUM_THREADS": v[2],
                        "OPENBLAS_NUM_THREADS": v[3], "pin_source": v[4]} for k, v in PINS.items()},
           "cells": cells, "n_cells": len(cells), "n_not_pass": len(bad),
           "VERDICT": "PASS" if not bad else "FAIL", "seconds": round(time.time() - t0, 1)}
    json.dump(rec, open(out_path, "w"), indent=1)
    print(f"NEWS2_ENV_GATE VERDICT={rec['VERDICT']} mode=selftest cells={len(cells)} not_pass={len(bad)}", flush=True)
    sys.exit(0 if not bad else 1)


if __name__ == "__main__":
    if sys.argv[1] == "--selftest":
        selftest(os.path.abspath(sys.argv[2]))
    elif sys.argv[1] == "--check":
        require(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    else:
        print(__doc__)
        sys.exit(2)

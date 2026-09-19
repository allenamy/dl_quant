#!/usr/bin/env python3
"""Warm scorer executor (lead request 14:4xZ: zero-behaviour-change speed-up of pass P2). The scorer device text is NOT changed: this process
runs the byte-identical device f10_scorer_3520d363.py in-process (runpy, fresh namespace per anchor) instead of `python -B device`, and serves
the device's two pipeline children in-process instead of as new interpreters:
  [PY, HERE/dlw_features.py]                                    -> runpy.run_path(HERE/dlw_features.py, run_name="__main__")
  [PY, "-c", "import os,sys; sys.path.insert(0,HERE); os.chdir(HERE); import f8_higher_order_features as m; m.build()"]
                                                                -> runpy.run_path(HERE/f8_higher_order_features.py)["build"]()  (module text re-executed)
with os.environ replaced by exactly the env the device passed and the cwd the device asked for; any other subprocess call is refused.
What is saved: interpreter start-up and the numpy / scipy / pandas imports (3 per anchor). Feature and model code, dtypes and order of
operations are the same text. Started with OMP / OPENBLAS / MKL = 1 BEFORE numpy is imported (the device's children inherit those).
Protocol (stdin/stdout lines): the caller writes the anchor's sandbox inputs (as b_scorer.worker does), then sends one JSON line
{"cwd": ..., "env": {...}} and reads one JSON line {"rc": int, "dt": seconds, "log": [...]}.
usage: started by fast_worker / fast_gate with env -i PATH HOME LC_CTYPE OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1"""
import os, sys, json, time, runpy, subprocess, io, contextlib, traceback
assert os.environ.get("OMP_NUM_THREADS") == "1" and os.environ.get("OPENBLAS_NUM_THREADS") == "1" and os.environ.get("MKL_NUM_THREADS") == "1"
import numpy, scipy.stats, scipy.special, pandas   # warm imports (the device and its children import these)

HERE_DEV = os.path.dirname(os.path.abspath(__file__)); DEVICE = f"{HERE_DEV}/f10_scorer_3520d363.py"
_real_run = subprocess.run
BASE_ENV = dict(os.environ)


class _Refused(Exception): pass


def _inproc_run(args, env=None, capture_output=False, text=False, cwd=None, **kw):
    """the two child calls of the device, in-process; returns a CompletedProcess like subprocess.run (stdout/stderr captured as text)."""
    args = list(args); old_env = dict(os.environ); old_cwd = os.getcwd(); old_path = list(sys.path); buf = io.StringIO(); rc = 0
    try:
        os.environ.clear(); os.environ.update(env if env is not None else old_env)
        if len(args) == 2 and args[1].endswith("/dlw_features.py"):
            if cwd: os.chdir(cwd)
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                try: runpy.run_path(args[1], run_name="__main__")
                except SystemExit as e: rc = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        elif len(args) == 3 and args[1] == "-c" and "import f8_higher_order_features as m; m.build()" in args[2]:
            here = args[2].split("sys.path.insert(0,'")[1].split("'")[0]
            sys.path.insert(0, here); os.chdir(here)
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                ns = runpy.run_path(f"{here}/f8_higher_order_features.py", run_name="f8_higher_order_features"); ns["build"]()
        else:
            raise _Refused(f"subprocess call not served in-process: {args[:3]}")
    except _Refused:
        raise
    except BaseException:
        buf.write(traceback.format_exc()); rc = 1
    finally:
        os.environ.clear(); os.environ.update(old_env); os.chdir(old_cwd); sys.path[:] = old_path
    out = buf.getvalue()
    return subprocess.CompletedProcess(args, rc, stdout=out if (capture_output and text) else (out.encode() if capture_output else None),
                                       stderr="" if (capture_output and text) else (b"" if capture_output else None))


def run_one(req):
    t0 = time.time(); buf = io.StringIO(); rc = 0; old_cwd = os.getcwd(); old_argv = list(sys.argv); old_path = list(sys.path)
    try:
        os.environ.clear(); os.environ.update({k: v for k, v in req["env"].items() if not k.startswith("_")}); os.chdir(req["cwd"])
        sys.argv = [DEVICE]; sys.path.insert(0, HERE_DEV)   # as `python -B DEVICE`: the script's directory first on sys.path
        subprocess.run = _inproc_run
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            try: runpy.run_path(DEVICE, run_name="__main__")
            except SystemExit as e: rc = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except BaseException:
        buf.write(traceback.format_exc()); rc = 1
    finally:
        subprocess.run = _real_run; os.environ.clear(); os.environ.update(BASE_ENV); os.chdir(old_cwd); sys.argv = old_argv; sys.path[:] = old_path
    return {"rc": rc, "dt": round(time.time() - t0, 3), "log": buf.getvalue().strip().splitlines()[-8:]}


def main():
    sys.stdout.write(json.dumps({"ready": True, "pid": os.getpid()}) + "\n"); sys.stdout.flush()
    for line in sys.stdin:
        if not line.strip(): continue
        res = run_one(json.loads(line))
        sys.stdout.write(json.dumps(res) + "\n"); sys.stdout.flush()


if __name__ == "__main__":
    main()

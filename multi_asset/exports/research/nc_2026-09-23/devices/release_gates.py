#!/usr/bin/env python3
"""Fail-closed runner for the gates of a release window (E-0926-A, lead ruling 2026-09-26 ~01:2xZ).

The defect this replaces (fix-pkg-d window, 2026-09-26 01:18Z): the W3 switch was a shell sequence
`$PAIR $XC ...; echo rc=$?; ... ff_running_tree.py ...`. zsh did not split `$PAIR`, the pair-check gate
never launched (rc 127, "no such file or directory"), and the sequence went on to the fast-forward: a
gate that stops only when it SPEAKS red is silent when it cannot start, and silence passed.

Contract, per gate, in order; the first failure stops the whole run (later gates never start):
  * the gate is an argv LIST (no shell, no word splitting: the launch cannot be mis-split);
  * a launch failure (missing program, not executable, OSError) is a failure;
  * ANY non-zero exit code is a failure (not only an explicit red verdict);
  * the gate's output (stdout+stderr) must contain a line matching its `verdict` regex — a gate that
    exits 0 without printing its verdict line did not judge, and that is a failure;
  * optional `timeout_s`: exceeding it is a failure.
Every gate's argv, rc, elapsed, verdict line (or the reason it has none) and full output go to the log.
Exit code: 0 only if every gate passed; 3 on the first failed gate; 2 on a malformed gate file.

usage: /usr/bin/python3 release_gates.py <gates.json> <log file>
gates.json: [{"name": "...", "argv": ["/usr/bin/python3", "x.py", "..."], "verdict": "^UPSTREAM_PAIR_CHECK PASS ", "timeout_s": 600}, ...]
Paths in argv are used literally; `~` is expanded only when an element starts with "~/"."""
import json, os, re, subprocess, sys, time


def load(p):
    gates = json.load(open(p))
    if not isinstance(gates, list) or not gates:
        raise ValueError("gate file must be a NON-EMPTY list")          # an empty list would pass vacuously
    for i, g in enumerate(gates):
        if not isinstance(g, dict) or set(g) - {"name", "argv", "verdict", "timeout_s"}:
            raise ValueError(f"gate {i}: unknown or missing keys {sorted(g) if isinstance(g, dict) else type(g)}")
        if not (isinstance(g.get("name"), str) and g["name"]):
            raise ValueError(f"gate {i}: name missing")
        if not (isinstance(g.get("argv"), list) and g["argv"] and all(isinstance(a, str) and a for a in g["argv"])):
            raise ValueError(f"gate {g['name']}: argv must be a non-empty list of non-empty strings")
        if not (isinstance(g.get("verdict"), str) and g["verdict"]):
            raise ValueError(f"gate {g['name']}: a verdict regex is REQUIRED (a gate without one cannot be told from a silent pass)")
        re.compile(g["verdict"], re.M)
    return gates


def run(gates, log):
    ts = lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    log.write(f"RELEASE_GATES start {ts()} n_gates={len(gates)}\n"); log.flush()
    for i, g in enumerate(gates, 1):
        argv = [os.path.expanduser(a) if a.startswith("~/") else a for a in g["argv"]]
        log.write(f"--- gate {i}/{len(gates)} {g['name']} start {ts()}\n    argv={json.dumps(argv)}\n"); log.flush()
        t0 = time.time()
        try:
            p = subprocess.run(argv, capture_output=True, text=True, timeout=g.get("timeout_s"))
            rc, out = p.returncode, (p.stdout or "") + (p.stderr or "")
            why = None if rc == 0 else f"exit code {rc} (non-zero)"
        except subprocess.TimeoutExpired as e:
            rc, out, why = None, str(e), f"timeout after {g.get('timeout_s')} s"
        except OSError as e:                                             # FileNotFoundError / PermissionError / ...
            rc, out, why = None, repr(e), f"LAUNCH FAILED: {e!r}"
        m = re.search(g["verdict"], out, re.M)
        if why is None and not m:
            why = f"exit 0 but NO verdict line matching {g['verdict']!r} (the gate did not judge)"
        log.write(out if out.endswith("\n") or not out else out + "\n")
        vline = m.group(0) if m else None
        log.write(f"    rc={rc} elapsed_s={time.time() - t0:.1f} verdict_line={vline!r}\n")
        if why:
            log.write(f"RELEASE_GATES STOP at gate {i} {g['name']}: {why} — later gates NOT started {ts()}\n"); log.flush()
            print(f"RELEASE_GATES STOP gate={g['name']} reason={why}")
            return 3
        log.write(f"    PASS {g['name']}\n"); log.flush()
        print(f"PASS {g['name']}: {m.group(0)}")
    log.write(f"RELEASE_GATES ALL_PASS n={len(gates)} {ts()}\n")
    print(f"RELEASE_GATES ALL_PASS n={len(gates)}")
    return 0


def main():
    if len(sys.argv) != 3:
        print(__doc__); return 2
    try:
        gates = load(sys.argv[1])
    except (ValueError, OSError, re.error, json.JSONDecodeError) as e:
        print(f"RELEASE_GATES MALFORMED {e!r}"); return 2
    with open(sys.argv[2], "a") as log:
        return run(gates, log)


if __name__ == "__main__":
    sys.exit(main())

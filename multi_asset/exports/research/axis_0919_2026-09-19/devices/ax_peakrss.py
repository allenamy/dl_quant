"""ax_peakrss.py (axis_0919): run a child command unchanged (same env, same argv, stdout/stderr inherited) and write its wall time, return code and
peak resident set size (getrusage(RUSAGE_CHILDREN).ru_maxrss, KiB on Linux) to a JSON file. Exit code = the child's exit code.
usage: python ax_peakrss.py <out.json> -- <cmd> [args...]"""
import json, os, resource, subprocess, sys, time
out = sys.argv[1]; assert sys.argv[2] == "--"; cmd = sys.argv[3:]
t0 = time.time(); rc = subprocess.call(cmd)
ru = resource.getrusage(resource.RUSAGE_CHILDREN)
json.dump({"cmd": cmd, "rc": rc, "wall_s": round(time.time() - t0, 1), "peak_rss_GiB": round(ru.ru_maxrss / 1024 ** 2, 2),
           "start_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)), "end_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, open(out, "w"), indent=1)
sys.exit(rc)

"""E10: the [B] check of tests_env_loading, reproduced in a temp copy of live/ + ops/ WITH A FAKE .env (fake values, never the real
file) — the clone has no .env, which is why that suite is red there for every member. Controls: ic_monitor (an existing member), the
same tree without .env, and the read-only `verify` invocation (must NOT load)."""
import os, shutil, subprocess, sys, tempfile
SRC = sys.argv[1]
def tree(with_env):
    d = tempfile.mkdtemp(prefix="e10env_")
    for sub in ("live", "ops", "config"):
        os.makedirs(os.path.join(d, sub))
        for fn in os.listdir(os.path.join(SRC, sub)):
            if fn.endswith((".py", ".json")): shutil.copy(os.path.join(SRC, sub, fn), os.path.join(d, sub, fn))
    if with_env: open(os.path.join(d, ".env"), "w").write("TELEGRAM_BOT_TOKEN=fake_probe_token\nTELEGRAM_CHAT_ID=fake_probe_chat\n")
    return d
def probe(d, mod, argv):
    code = ("import os, sys\n" f"sys.argv = {argv!r}\n" f"for x in ('live','ops'): sys.path.insert(0, os.path.join({d!r}, x))\n"
            f"import {mod}\n" "print(int(bool(os.environ.get('TELEGRAM_BOT_TOKEN'))))\n")
    env = {k: v for k, v in os.environ.items() if k not in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")}
    r = subprocess.run(["/usr/bin/python3", "-c", code], capture_output=True, text=True, env=env, timeout=120)
    return (r.stdout.strip().splitlines() or ["ERR " + r.stderr[-200:]])[-1]
a, b = tree(True), tree(False)
try:
    rows = [("fake .env", "ic_monitor", ["-c"]), ("fake .env", "notarize_ledgers", ["-c"]), ("fake .env", "notarize_ledgers", ["notarize_ledgers.py"]),
            ("fake .env", "notarize_ledgers", ["notarize_ledgers.py", "verify"]), ("no .env", "notarize_ledgers", ["-c"]), ("no .env", "ic_monitor", ["-c"])]
    for lab, mod, argv in rows:
        print(f"{lab:10s} {mod:18s} argv={argv!r:40s} TELEGRAM_BOT_TOKEN populated = {probe(a if lab == 'fake .env' else b, mod, argv)}")
finally:
    shutil.rmtree(a, ignore_errors=True); shutil.rmtree(b, ignore_errors=True)

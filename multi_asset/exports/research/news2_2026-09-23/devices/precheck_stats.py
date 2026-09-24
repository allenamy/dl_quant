"""Read-only: do the preconditions news2_stats.py checks at L88-103 hold under the FIXED invocation?

Replicates the whitelist assertion and the sha pins WITHOUT running the verdict, so the chain step itself
is not re-run. Produces no verdict artefact.
"""
import hashlib, os, sys

WL = set(sys.argv[1].split(","))
extra = sorted(set(os.environ) - WL)
print("  whitelist arg :", sorted(WL))
print("  env present   :", sorted(os.environ))
print("  outside list  :", extra, "->", "PASS" if not extra else "WOULD ASSERT")

nsd = os.path.abspath(os.environ.get("NEWS2_NEWS_DEVICES", "(unset)"))
print("  NEWS2_NEWS_DEVICES ->", nsd)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


PIN = "7141ba42ab227b9f35b48acce62d5e2a2494f364fdf6a83189974cb2af67e03c"
ok = sha(os.path.join(nsd, "news_stats.py")) == PIN
print("  news_stats.py pin:", "PASS" if ok else "FAIL")
sys.path.insert(0, nsd)
import news_stats as NS
import bt_tables as _BT
import bt_driver_lib as _DL
print("  imports        : news_stats, bt_tables, bt_driver_lib all OK")
bad = []
for f, s in NS.DEV.items():
    p = os.path.join(nsd, f)
    if not os.path.exists(p):
        bad.append((f, "ABSENT"))
    elif sha(p) != s:
        bad.append((f, "SHA MISMATCH"))
print("  NS.DEV pins    :", len(NS.DEV), "files ->", "all PASS" if not bad else f"FAIL {bad}")
print("PRECHECK", "PASS" if (not extra and ok and not bad) else "FAIL")

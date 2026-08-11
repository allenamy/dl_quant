import gzip, os
BD = "/workspace/data/raw/bookDepth"
def bands(sym, day):
    p = "%s/%s-%s.csv.gz" % (BD, sym, day)
    if not os.path.exists(p): return None
    s = set()
    with gzip.open(p, "rt") as f:
        f.readline()
        for i, l in enumerate(f):
            if i > 200: break
            s.add(l.split(",")[1])
    return sorted(s, key=float)
print("带集随时间 (BTCUSDT):")
for d in ("2023-01-01","2023-07-01","2024-01-01","2024-07-01","2025-01-01","2025-04-01",
          "2025-07-01","2025-10-01","2026-01-01","2026-02-01","2026-03-01","2026-08-05"):
    b = bands("BTCUSDT", d)
    n = len(b) if b else 0
    has = "有" if (b and any(abs(float(x)) < 0.5 for x in b)) else "无"
    print("  %s: %2d 带  pm0.2=%s   %s" % (d, n, has, b if b else ""))
print("\n其他币抽查 2026-01-01:")
for s in ("ETHUSDT","SOLUSDT","OPUSDT"):
    b = bands(s, "2026-01-01")
    print("  %-9s %s" % (s, b))

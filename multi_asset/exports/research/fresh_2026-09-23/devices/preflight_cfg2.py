import json, re
N = "/dev/shm/news_2026-09-23/configs"
for seed in ("42", "2027"):
    for suf in ("", "X"):
        p = f"{N}/RUN_CONFIG_NEWS_s{seed}{suf}_2026-09-23.json"
        C = json.load(open(p)); arm = f"FRESH_s{seed}"
        print(f"--- NEWS_s{seed}{suf}: {len(C['runs'])} runs")
        for r in C["runs"]:
            old = r["role"]; new = re.sub(r"NEW_S arm NEWS_s\d+", f"FRESH arm {arm}", old)
            ok = ("NEWS_s" not in new) and (("NEWS_s" not in old) or (f"FRESH arm {arm}" in new))
            print(f"    {'OK ' if ok else 'BAD'} tag={r['tag']:<42s} role={new[:64]}")

import json
N = "/dev/shm/news_2026-09-23/configs"; S1 = "/workspace/old_vs_new_2026-09-23/devices"
for seed in ("42", "2027"):
    base = json.load(open(f"{S1}/ADAPTER_SPEC_NEW_s{seed}.json"))
    nb = json.load(open(f"{N}/ADAPTER_SPEC_NEWS_s{seed}.json"))
    agree = {k: (nb.get(k) == base[k]) for k in ("price_meta", "universe", "window_first_anchor")}
    print(f"s{seed}: NEW_S spec keys == Stage1 base:", agree, "| key sets equal:", set(nb) == set(base))

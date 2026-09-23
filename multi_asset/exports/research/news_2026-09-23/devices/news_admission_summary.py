"""E.2-1: per fold ADMISSION.json dropped-window ratio for both F10 seeds (read-only)."""
import json, glob, os, time
W = "/dev/shm/news_2026-09-23"; out = {}
for seed in (42, 2027):
    rows = []
    for p in sorted(glob.glob(f"{W}/work/f10_s{seed}/*/ADMISSION.json")):
        a = json.load(open(p)); rej = sum(a["rejected"].values()); tot = a["accepted_windows"] + rej
        rows.append({"fold": a["fold"], "accepted": a["accepted_windows"], "rejected": rej, "rejected_by_reason": a["rejected"], "drop_ratio": (rej / tot) if tot else None,
                     "train_anchors": a["train_anchors"], "max_train_label_end_utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(a["max_train_label_end"])),
                     "cutoff_utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(a["cutoff"]))})
    out[f"s{seed}"] = rows
json.dump(out, open(f"{W}/receipts/P3_F10_ADMISSION_SUMMARY.json", "w"), indent=1)
for s, rows in out.items():
    print(s, " ".join(f"{r['fold']}:{r['rejected']}/{r['accepted']+r['rejected']}" for r in rows))

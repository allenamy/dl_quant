"""Receipt-only sampling diagnosis; never reads scores or economic outcomes."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--inventory", type=Path, required=True)
    ap.add_argument("--old", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    inputs = {}

    def read(path):
        raw = path.read_bytes()
        inputs[str(path)] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    inv = read(args.inventory)
    declared = {r["fold"]: r for r in inv["rows"] if r["refit"]}
    if set(declared) != set(inv["affected"]):
        raise ValueError("inventory population")
    rows = []
    for seed in (42, 2027):
        for tag, item in declared.items():
            new = read(args.root / f"models/REPAIR_s{seed}/{tag}/FOLD_RECEIPT.json")
            old = read(args.old / f"models/U_s{seed}/{tag}/FOLD_RECEIPT.json")
            if any(r["seed"] != seed or r["fold"] != tag for r in (old, new)):
                raise ValueError("fold identity")
            a, b = old["admission"], new["admission"]
            oe, ne = a["label_end_times"], b["label_end_times"]
            if len(set(oe)) != len(oe) or len(set(ne)) != len(ne):
                raise ValueError("ambiguous window identity")
            gained = set(ne) - set(oe)
            if not set(oe) <= set(ne) or gained != set(item["gained_window_label_end"]):
                raise ValueError("unexpected population change")
            if len(oe) != item["old"] or len(ne) != item["new"]:
                raise ValueError("inventory count")
            for r, ends in ((a, oe), (b, ne)):
                if len(r["sampled_windows"]) != 96 or any(type(i) is not int or i < 0 or i >= len(ends) for i in r["sampled_windows"]):
                    raise ValueError("sample index population")
            os = [oe[i] for i in a["sampled_windows"]]
            ns = [ne[i] for i in b["sampled_windows"]]
            new_count = sum(t in gained for t in ns)
            same = sum(x == y for x, y in zip(os, ns))
            replaced = sum(x != y and y not in gained for x, y in zip(os, ns))
            if new_count + same + replaced != 96:
                raise ValueError("partition identity")
            rows.append({"seed": seed, "fold": tag, "accepted_old": len(oe), "accepted_new": len(ne),
                         "updates": 96, "newly_admitted_updates": new_count,
                         "newly_admitted_unique_windows_sampled": len(set(ns) & gained),
                         "same_window_identity_as_old_U_updates": same,
                         "substituted_existing_window_updates": replaced,
                         "gained_window_update_counts": {str(t): ns.count(t) for t in sorted(gained)}})
    out = {"status": "TRAINING_POPULATION_EXPOSURE_ONLY_NO_OUTCOME_SELECTION",
           "utc": datetime.now(timezone.utc).isoformat(), "rows": rows, "inputs": inputs,
           "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "limits": "Post-training receipt diagnosis. Fixed uniforms with a changed population replace old windows too; economic differences cannot isolate the information benefit of the repaired labels."}
    with args.output.open("x") as f:
        json.dump(out, f, indent=2, allow_nan=False)
    print(json.dumps({"status": out["status"], "rows": rows, "source_sha256": out["source_sha256"]}))


if __name__ == "__main__":
    main()

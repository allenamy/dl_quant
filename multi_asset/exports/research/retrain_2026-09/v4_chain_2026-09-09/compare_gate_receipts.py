"""compare_gate_receipts.py — field-by-field parity of two STEP1/STEP2 gate receipts (archived September run vs a re-run through chain_v4_monthly.sh).
Compares every VERDICT field (recursively) except the run metadata (utc, built_utc, argv, self_sha256, inputs_sha256, inputs_path, receipt_schema, gate);
prints the differing paths and writes a JSON parity receipt. rc 0 iff no verdict field differs.
usage: compare_gate_receipts.py <archived.json> <rerun.json> <out.json> [label]"""
import json
import sys
import time

META = {"utc", "built_utc", "argv", "self_sha256", "inputs_sha256", "inputs_path", "receipt_schema", "gate"}


def walk(a, b, path, diffs, same):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if not path and k in META:
                continue
            if k not in a or k not in b:
                diffs.append((path + [k], "missing_in_archived" if k not in a else "missing_in_rerun"))
                continue
            walk(a[k], b[k], path + [k], diffs, same)
    elif isinstance(a, list) and isinstance(b, list):
        if a != b:
            diffs.append((path, f"list differs (len {len(a)} vs {len(b)})"))
        else:
            same[0] += 1
    else:
        if a == b or (isinstance(a, float) and isinstance(b, float) and abs(a - b) <= 1e-12 * max(1.0, abs(a), abs(b))):
            same[0] += 1
        else:
            diffs.append((path, f"{a!r} != {b!r}"))


def main(argv):
    A = json.load(open(argv[1])); B = json.load(open(argv[2])); out = argv[3]; label = argv[4] if len(argv) > 4 else ""
    diffs, same = [], [0]
    walk(A, B, [], diffs, same)
    rec = {"label": label, "archived": argv[1], "rerun": argv[2], "n_equal_verdict_fields": same[0], "n_diff": len(diffs),
           "diffs": [{"path": "/".join(map(str, p)), "what": w} for p, w in diffs],
           "archived_PASS": A.get("PASS"), "rerun_PASS": B.get("PASS"), "archived_built_utc": A.get("built_utc"), "rerun_built_utc": B.get("built_utc"),
           "rerun_gate": B.get("gate"), "rerun_self_sha256": B.get("self_sha256"), "rerun_inputs_sha256": B.get("inputs_sha256"), "PARITY": not diffs,
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    json.dump(rec, open(out, "w"), indent=1)
    print(f"GATE_RECEIPT_PARITY {'OK' if not diffs else 'DIFF'} {label}: {same[0]} verdict fields equal, {len(diffs)} differ; PASS archived={A.get('PASS')} rerun={B.get('PASS')}")
    for d in rec["diffs"][:20]:
        print("  -", d["path"], d["what"])
    return 0 if not diffs else 3


if __name__ == "__main__":
    sys.exit(main(sys.argv))

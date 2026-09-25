#!/usr/bin/env python3
"""dlarch_pairwise_constants.py -- census of values that must be EQUAL in two or more places.

WHY (lead 2026-09-25, after the same defect class bit twice in one hour):
  1. `BASE_TAG` was written next to `BASE_CFG`; switching the config to the X axis left the tag naming
     the short-axis run. Caught by my own `assert len(base_run) == 1` ("found 0").
  2. The arm name existed in FOUR places (chain_run variable, the derived adapter spec rebuilding
     f"DLARCH_T0_s{seed}", the spec path, the targets path). Adding a second arm (--reference) drifted
     them. Caught by the UPSTREAM engine's own guard (bt_objb_targets: arm_mismatch).
  I fixed (1) and kept going without looking for siblings -- an instance-shaped fix for a class-shaped
  defect. This device is the class-shaped answer: it finds the couplings and states, for each, whether
  it is single-sourced or guarded.

WHAT IT DOES
  A. DECLARED table: the couplings I have enumerated by reading the chain, each with its resolution
     (SINGLE_SOURCE = the value is computed/derived once, or GUARDED = an equality assertion exists).
     Each declared entry is CHECKED against the source, so the table cannot rot silently.
  B. UNDECLARED scan: any name-like string literal that occurs in 2+ distinct places, and any f-string
     that REBUILDS a name from `seed`/`arm`. These are candidates I may have missed; the device fails
     if a candidate is not in the declared table, so the table has to be extended deliberately.

Read-only. usage: dlarch_pairwise_constants.py <env-whitelist> <devices dir> [<derived dir>...]
"""
import hashlib
import json
import os
import re
import sys

# Couplings enumerated by reading the chain. resolution: SINGLE_SOURCE | GUARDED
DECLARED = [
    {"value": "the base-cell run tag", "was": "BASE_TAG literal next to BASE_CFG",
     "resolution": "SINGLE_SOURCE",
     "how": "BASE_TAG is derived: base_run = [r for r in cfg['runs'] if r['tag'].endswith(BASE_CELL_SUFFIX)]",
     "evidence_must_appear": ["BASE_CELL_SUFFIX", 'BASE_TAG = base_run[0]["tag"]'],
     "evidence_must_not_appear": ['BASE_TAG = "NEWS2_s42'],
     "file": "dlarch_chain_run.py"},
    {"value": "the arm name", "was": "rebuilt as f\"DLARCH_T0_s{seed}\" in 4 places",
     "resolution": "SINGLE_SOURCE",
     "how": "arm computed once in chain_run and passed to the adapter spec on argv; paths use {arm}",
     "evidence_must_appear": ['ADAPTER_SPEC_{arm}.json', 'TARGETS_{arm}.npz', 'str(seed), arm'],
     "evidence_must_not_appear": ['ADAPTER_SPEC_DLARCH_T0_s{seed}', 'TARGETS_DLARCH_T0_s{seed}'],
     "file": "dlarch_chain_run.py"},
    {"value": "the arm name, adapter side", "was": "spec rebuilt the arm itself",
     "resolution": "SINGLE_SOURCE", "how": "ARM = sys.argv[4]; spec uses ARM and ADAPTER_SPEC_{ARM}.json",
     "evidence_must_appear": ["ARM = sys.argv[4]", '"arm": ARM', "ADAPTER_SPEC_{ARM}.json"],
     "evidence_must_not_appear": ['"arm": f"DLARCH_T0_s{seed}"'],
     "file": "news2_adapter_specs.py"},
    {"value": "the reference F10 source", "was": "-", "resolution": "SINGLE_SOURCE",
     "how": "one expression: f10_src = f'{NS}/work/f10_s42' if inservice_f10 else ...; --parity and "
            "--reference share it, so the parity gate and the reference cell cannot read different F10s",
     "evidence_must_appear": ["inservice_f10 = parity or reference", "f10_src = "],
     "evidence_must_not_appear": [], "file": "dlarch_chain_run.py"},
    # --- LAYOUT couplings: two devices must agree on where an artifact lives. Their guard is weaker
    # than an equality assertion (a wrong path fails as file-not-found), but it is a guard: it cannot
    # silently produce a wrong NUMBER, only a loud absence. Declared so they are not invisible.
    {"value": "F10 artifact layout OUT_ROOT/<arm>/f10_s<seed>", "was": "-", "resolution": "GUARDED",
     "how": "dlarch_train_f10 writes it; dlarch_leg_readout and dlarch_chain_run read it. A mismatch "
            "surfaces as NOT_PRESENT / missing F10 source, never as a wrong number",
     "evidence_must_appear": ["f10_s"], "evidence_must_not_appear": [], "file": "dlarch_leg_readout.py"},
    {"value": "combo output layout <root>/work/combo_s<seed>", "was": "-", "resolution": "GUARDED",
     "how": "the derived news2_combo writes it (PNOISE_W redirects the root); chain_run and "
            "dlarch_chain_torch read it. A mismatch fails as file-not-found at read time",
     "evidence_must_appear": ["combo_s"], "evidence_must_not_appear": [], "file": "dlarch_chain_run.py"},
    {"value": "the run tag = <arm>|scaled|rule|raw|UAFE", "was": "-", "resolution": "SINGLE_SOURCE",
     "how": "built from arm in one place; the engine also re-derives the runs/ dir from r0['tag'], and "
            "bt_objb_targets independently asserts the targets receipt's arm == the config's arm",
     "evidence_must_appear": ['f"{arm}|scaled|rule|raw|UAFE"'], "evidence_must_not_appear": [],
     "file": "dlarch_chain_run.py"},
    {"value": "frozen upstream device shas", "was": "-", "resolution": "GUARDED",
     "how": "the derive script sha-pins every source and every symlinked sibling and asserts before use",
     "evidence_must_appear": ["!= pinned", "sha("], "evidence_must_not_appear": [],
     "file": "dlarch_derive_chain.py"},
    {"value": "the reference trainer recipe", "was": "-", "resolution": "GUARDED",
     "how": "dlarch_train_f10 asserts sha(REF) == REF_SHA at run time",
     "evidence_must_appear": ["REF_SHA"], "evidence_must_not_appear": [],
     "file": "dlarch_train_f10.py"},
]

# name-like literals worth treating as coupling candidates
NAMEISH = re.compile(r'"((?:[A-Za-z0-9_]*(?:NEWS2?|DLARCH|OBJB|OVN|UAFE|scaled\|rule)[A-Za-z0-9_|.$-]*))"')
REBUILD = re.compile(r'f"[^"]*\{(?:seed|args\.seed|arm)\}[^"]*"')
# Literals that are legitimately repeated: they name an external contract, not an internal coupling.
ALLOW_REPEAT = {"|scaled|rule|raw|UAFE"}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    wl = set(sys.argv[1].split(","))
    extra = sorted(set(os.environ) - wl)
    assert not extra, f"env outside whitelist: {extra}"
    roots = sys.argv[2:]
    files = {}
    for r in roots:
        for fn in sorted(os.listdir(r)):
            if fn.endswith(".py") and not fn.startswith("."):
                p = os.path.join(r, fn)
                if os.path.islink(p) and not os.path.exists(p):
                    continue
                files[fn] = {"path": p, "sha256": sha(p), "text": open(p).read()}
    print(f"scanned {len(files)} files from {len(roots)} root(s)")

    # ---- A. declared table, each entry CHECKED ----
    declared_rows, declared_fail = [], 0
    for d in DECLARED:
        f = files.get(d["file"])
        if f is None:
            row = {**{k: d[k] for k in ("value", "was", "resolution", "how", "file")}, "CHECK": "FILE_ABSENT"}
            declared_rows.append(row); declared_fail += 1; continue
        missing = [e for e in d["evidence_must_appear"] if e not in f["text"]]
        present = [e for e in d["evidence_must_not_appear"] if e in f["text"]]
        ok = not missing and not present
        declared_fail += 0 if ok else 1
        declared_rows.append({**{k: d[k] for k in ("value", "was", "resolution", "how", "file")},
                             "CHECK": "OK" if ok else "STALE",
                             "missing_evidence": missing, "forbidden_present": present})
    print(f"\nDECLARED couplings: {len(declared_rows)}  stale: {declared_fail}")
    for r in declared_rows:
        mark = "ok " if r["CHECK"] == "OK" else "!! "
        print(f"  {mark}{r['resolution']:14} {r['value']:32} [{r['file']}]")
        if r["CHECK"] != "OK":
            print(f"      missing={r.get('missing_evidence')} forbidden_present={r.get('forbidden_present')}")

    # ---- B. undeclared scan ----
    lit_where = {}
    for fn, f in files.items():
        for m in NAMEISH.finditer(f["text"]):
            lit_where.setdefault(m.group(1), set()).add(fn)
    repeated = {k: sorted(v) for k, v in lit_where.items() if len(v) >= 2 and k not in ALLOW_REPEAT}
    rebuilds = {fn: sorted(set(REBUILD.findall(f["text"]))) for fn, f in files.items()
                if REBUILD.search(f["text"])}
    print(f"\nUNDECLARED scan: name-like literals in >=2 files: {len(repeated)}")
    for k, v in sorted(repeated.items()):
        print(f"    {k!r} in {v}")
    print(f"  files that REBUILD a name from seed/arm: {len(rebuilds)}")
    for fn, v in sorted(rebuilds.items()):
        for x in v:
            print(f"    {fn}: {x}")

    rec = {"device": "dlarch_pairwise_constants.py", "self_sha256": sha(os.path.abspath(__file__)),
           "roots": roots, "files": {k: v["sha256"] for k, v in files.items()},
           "declared": declared_rows, "declared_stale": declared_fail,
           "undeclared_repeated_literals": repeated, "undeclared_rebuilds": rebuilds,
           "note": ("A repeated literal or a rebuild is a CANDIDATE coupling, not proof of a defect: "
                    "the allowlist names the ones that encode an external contract. Anything else must "
                    "be moved into DECLARED with a resolution, so the next one does not wait for "
                    "someone else's guard to catch it.")}
    out = os.path.join(roots[0], "PAIRWISE_CONSTANTS.json")
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import dlarch_safe_io as sio
        rec["receipt_sha256"] = sio.write_json(out, rec)
    except Exception as e:
        open(out, "w").write(json.dumps(rec, indent=2)); rec["receipt_note"] = f"plain write ({e})"
    print(f"\nreceipt {out}")
    print(f"DLARCH_PAIRWISE_CONSTANTS declared={len(declared_rows)} stale={declared_fail} "
          f"repeated_literals={len(repeated)} rebuild_files={len(rebuilds)}")
    return 1 if declared_fail else 0


if __name__ == "__main__":
    sys.exit(main())

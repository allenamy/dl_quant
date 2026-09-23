"""Stage the integrator's build products into the NEW_S2 chain root, under the names the derived
chain devices expect, and bind every one of them by sha.

The chain devices are derived from NEW_S's (news2_derive_chain.py) and therefore still look for
`work/NEWS_FEATURES.npz`, `receipts/P2B_FEATURES.json`, `work/legs.npz`, `receipts/P3_LEGS.json`.
The integrator's build (DESIGN A9) produces `NC_FEATURES.npz` / `NC_FEATURES.json` / `legs.npz` /
`NC_LEGS.json` in the nc root. Renaming inside the trainers would have meant editing the recipe; a
staging step keeps the recipe untouched and puts the mapping in ONE auditable place.

Two things this does NOT do, on purpose:
  * it does not copy the feature npz (they are gigabytes) - it hard-links, and then re-hashes the
    LINKED path, so the receipt records the sha of the bytes the trainers will actually open;
  * it does not rewrite the integrator's receipts - it copies them, so their internal `output` path
    still points at the nc root and the provenance stays visible.

The chain must not start before this has run: a missing input here is a loud refusal, whereas a
half-staged root is how a trainer ends up reading last run's features.

usage: python news2_stage_inputs.py <nc_root> <news2_root> <out_receipt.json>
"""
import hashlib, json, os, shutil, sys, time

MAP = [
    # (source in the nc root, destination in the news2 root, required)
    ("work/NC_FEATURES.npz", "work/NEWS_FEATURES.npz", True),
    ("receipts/NC_FEATURES.json", "receipts/P2B_FEATURES.json", True),
    ("work/legs.npz", "work/legs.npz", True),
    ("receipts/NC_LEGS.json", "receipts/P3_LEGS.json", True),
    ("work/members_hist_all.npz", "work/members_hist_all.npz", False),
    ("inputs/bundle_config.json", "inputs/bundle_config.json", True),
]
# the derived chain devices assert sha(features) == receipt['sha256'] and sha(legs) == receipt['sha256'];
# these pairs say which receipt field must match which staged file, and are checked here too, so a
# mismatch is caught before a multi-hour training run rather than inside it.
BINDINGS = [("receipts/P2B_FEATURES.json", "sha256", "work/NEWS_FEATURES.npz"),
            ("receipts/P3_LEGS.json", "sha256", "work/legs.npz")]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def main():
    nc, w2, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    staged, missing = {}, []
    for src, dst, required in MAP:
        s = os.path.join(nc, src)
        d = os.path.join(w2, dst)
        if not os.path.exists(s):
            (missing.append({"source": s, "dest": dst}) if required else staged.setdefault("_optional_absent", []).append(src))
            continue
        os.makedirs(os.path.dirname(d), exist_ok=True)
        if os.path.lexists(d):
            os.remove(d)
        try:
            os.link(s, d)                      # same filesystem (both under /dev/shm): no copy
            how = "hardlink"
        except OSError:
            shutil.copyfile(s, d)
            how = "copy"
        staged[dst] = {"source": s, "source_sha256": sha(s), "staged_sha256": sha(d), "how": how}
        assert staged[dst]["source_sha256"] == staged[dst]["staged_sha256"], (dst, "staged bytes differ from source")
    if missing:
        rec = {"device": "news2_stage_inputs.py", "VERDICT": "REFUSED: required inputs missing",
               "missing": missing, "staged": staged}
        json.dump(rec, open(out_path, "w"), indent=1)
        print(f"NEWS2_STAGE VERDICT=REFUSED missing={[m['source'] for m in missing]}", flush=True)
        sys.exit(2)

    bound = {}
    for rcpt, field, target in BINDINGS:
        R = json.load(open(os.path.join(w2, rcpt)))
        want = R.get(field)
        got = staged[target]["staged_sha256"]
        bound[target] = {"receipt": rcpt, "field": field, "receipt_value": want, "file_sha256": got,
                         "MATCH": want == got}
    bad = [k for k, v in bound.items() if not v["MATCH"]]
    rec = {"device": "news2_stage_inputs.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "nc_root": nc, "news2_root": w2, "staged": staged, "bindings": bound,
           "VERDICT": "STAGED" if not bad else "REFUSED: receipt does not bind the staged file",
           "note": "the chain devices re-check these same bindings; this is the early, cheap check"}
    json.dump(rec, open(out_path, "w"), indent=1)
    print(f"NEWS2_STAGE VERDICT={rec['VERDICT']} staged={len(staged)} bindings_ok={len(bound) - len(bad)}/{len(bound)} "
          f"receipt_sha256={sha(out_path)}", flush=True)
    sys.exit(0 if not bad else 3)


if __name__ == "__main__":
    main()

"""Stage the integrator's build products into the NEW_S2 chain root, under the names the derived
chain devices expect, and bind every one of them by sha.

The chain devices are derived from NEW_S's (news2_derive_chain.py) and therefore still look for
`work/NEWS_FEATURES.npz`, `receipts/P2B_FEATURES.json`, `work/legs.npz`, `receipts/P3_LEGS.json`.
The integrator's build (DESIGN A9) produces `NC_FEATURES.npz` / `NC_FEATURES.json` in the nc root and,
LATER, `legs.npz` / `NC_LEGS.json`. A staging step keeps the recipes untouched and puts the mapping in
ONE auditable place.

★ TWO PHASES, and the split is not cosmetic (defect found by the integrator 2026-09-23, after the
  first version of this file listed legs as a pre-chain input):

      pre_king   features + its receipt + bundle_config + members_hist
      post_king  legs + its receipt

  nc_legs.py consumes the King OOF, so legs cannot exist until King training has run -- which is a
  step of THIS chain. Requiring legs up front made the chain unstartable. `post_king` additionally
  refuses to run unless `pre_king` has already been staged, so the order cannot be lost again.

Two things this does NOT do, on purpose:
  * it does not copy the feature npz (gigabytes) - it hard-links, then re-hashes the LINKED path, so
    the receipt records the sha of the bytes the trainers will actually open;
  * it does not rewrite the integrator's receipts - it copies them, so their internal `output` path
    still points at the nc root and the provenance stays visible.

usage: python news2_stage_inputs.py <nc_root> <news2_root> <out_receipt.json> --phase pre_king|post_king
"""
import argparse, hashlib, json, os, shutil, sys, time

PHASES = {
    # phase -> [(source in nc root, destination in news2 root, required)]
    "pre_king": [
        ("work/NC_FEATURES.npz", "work/NEWS_FEATURES.npz", True),
        ("receipts/NC_FEATURES.json", "receipts/P2B_FEATURES.json", True),
        ("work/members_hist_all.npz", "work/members_hist_all.npz", True),
        ("inputs/bundle_config.json", "inputs/bundle_config.json", True),
    ],
    "post_king": [
        ("work/legs.npz", "work/legs.npz", True),
        ("receipts/NC_LEGS.json", "receipts/P3_LEGS.json", True),
    ],
}
# receipt field -> staged file it must bind. The chain devices re-check these; this is the early check.
BINDINGS = {
    "pre_king": [("receipts/P2B_FEATURES.json", "sha256", "work/NEWS_FEATURES.npz")],
    "post_king": [("receipts/P3_LEGS.json", "sha256", "work/legs.npz")],
}
# post_king may not run before pre_king: these must already be staged
PREREQ = {"post_king": ["work/NEWS_FEATURES.npz", "receipts/P2B_FEATURES.json"]}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def fail(out_path, rec, msg, code):
    json.dump(rec, open(out_path, "w"), indent=1)
    print(f"NEWS2_STAGE VERDICT={rec['VERDICT']} {msg}", flush=True)
    sys.exit(code)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("nc_root"); ap.add_argument("news2_root"); ap.add_argument("out")
    ap.add_argument("--phase", required=True, choices=sorted(PHASES))
    a = ap.parse_args()
    nc, w2, out_path, phase = a.nc_root, a.news2_root, a.out, a.phase
    rec = {"device": "news2_stage_inputs.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "phase": phase, "nc_root": nc, "news2_root": w2,
           "phase_note": ("legs depend on the King OOF, so they are staged AFTER King training, not before; "
                          "post_king refuses to run unless pre_king already staged the features")}

    missing_prereq = [p for p in PREREQ.get(phase, []) if not os.path.exists(os.path.join(w2, p))]
    if missing_prereq:
        rec["VERDICT"] = "REFUSED: pre_king has not been staged"
        rec["missing_prerequisites"] = missing_prereq
        fail(out_path, rec, f"missing={missing_prereq}", 4)

    staged, missing = {}, []
    for src, dst, required in PHASES[phase]:
        s = os.path.join(nc, src); d = os.path.join(w2, dst)
        if not os.path.exists(s):
            if required:
                missing.append({"source": s, "dest": dst})
            else:
                staged.setdefault("_optional_absent", []).append(src)
            continue
        os.makedirs(os.path.dirname(d), exist_ok=True)
        if os.path.lexists(d):
            os.remove(d)
        try:
            os.link(s, d); how = "hardlink"
        except OSError:
            shutil.copyfile(s, d); how = "copy"
        staged[dst] = {"source": s, "source_sha256": sha(s), "staged_sha256": sha(d), "how": how}
        assert staged[dst]["source_sha256"] == staged[dst]["staged_sha256"], (dst, "staged bytes differ from source")
    rec["staged"] = staged
    if missing:
        rec["VERDICT"] = "REFUSED: required inputs missing"
        rec["missing"] = missing
        fail(out_path, rec, f"missing={[m['source'] for m in missing]}", 2)

    bound = {}
    for rcpt, field, target in BINDINGS[phase]:
        R = json.load(open(os.path.join(w2, rcpt)))
        want, got = R.get(field), staged[target]["staged_sha256"]
        bound[target] = {"receipt": rcpt, "field": field, "receipt_value": want, "file_sha256": got,
                         "MATCH": want == got}
    rec["bindings"] = bound
    bad = [k for k, v in bound.items() if not v["MATCH"]]
    rec["VERDICT"] = "STAGED" if not bad else "REFUSED: receipt does not bind the staged file"
    json.dump(rec, open(out_path, "w"), indent=1)
    print(f"NEWS2_STAGE VERDICT={rec['VERDICT']} phase={phase} staged={len(staged)} "
          f"bindings_ok={len(bound) - len(bad)}/{len(bound)} receipt_sha256={sha(out_path)}", flush=True)
    sys.exit(0 if not bad else 3)


if __name__ == "__main__":
    main()

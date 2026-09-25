#!/usr/bin/env python3
"""d10_gate_old_vs_new.py [out.json] -- how much of R25-11 was really open?

The independent review (7cbe907ba, R25-11) found that the D10 consumers rejected only manifest entries
whose `checksum_match` was explicitly False. "I fixed it" is not a receipt; the receipt is the measured
before-state. This device builds a month that is green by construction, applies one defect at a time, and
asks BOTH gates. It lives next to the conclusion it signs, per 判决装置与结论同寿命.

OLD = the predicate every consumer used before the fix:
        skip the month iff any(v.get("checksum_match") is False); otherwise read it as verified.
NEW = d10_manifest_gate.verify_month: checksum_match must be True, set equality, per-file re-hash.

Limitation, stated rather than hidden: the fixture is hashed by the same function the gate uses, so this
control tests the DECISION, not the hash algorithm. A wrong algorithm would pass here. The real-month
`d10_manifest_gate.py --selftest` covers that direction, and the venue's own .CHECKSUM covers pull time.
"""
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import d10_manifest_gate as G


def old_gate(zipdir, month):
    """Returns (reads_as_verified, what_it_said)."""
    mp = os.path.join(zipdir, f"MANIFEST_{month}.json")
    if not os.path.exists(mp):
        return False, "ABSENT_MANIFEST"
    man = json.load(open(mp))["files"]
    if any(v.get("checksum_match") is False for v in man.values()):
        return False, "MISMATCH (skipped)"
    return True, "read as VERIFIED"


def main(out=None):
    root = tempfile.mkdtemp(prefix="d10gate_cmp_")
    pristine = tempfile.mkdtemp(prefix="d10gate_pri_")
    try:
        month = G._make_synthetic(root)
        for n in os.listdir(root):
            shutil.copy(os.path.join(root, n), os.path.join(pristine, n))
        victim = "SYN0USDT"
        sfx = f"-fundingRate-{month}.zip"
        vzip = os.path.join(root, f"{victim}{sfx}")
        mp = os.path.join(root, f"MANIFEST_{month}.json")

        def restore():
            for n in os.listdir(root):
                if n.endswith(sfx) and not os.path.exists(os.path.join(pristine, n)):
                    os.remove(os.path.join(root, n))
            for n in os.listdir(pristine):
                shutil.copy(os.path.join(pristine, n), os.path.join(root, n))

        def edit(fn):
            d = json.load(open(mp)); fn(d["files"][victim]); json.dump(d, open(mp, "w"))

        cases = [
            ("(no mutation) baseline", lambda: None, True),
            ("byte flipped inside a pulled zip", lambda: _flip(vzip), False),
            ("a pulled zip deleted after the pull", lambda: os.remove(vzip), False),
            ("stray zip on disk with no manifest entry", lambda: shutil.copy(vzip, os.path.join(root, f"ZZSTRAY{sfx}")), False),
            ("checksum_match = None (venue served no .CHECKSUM)", lambda: edit(lambda e: e.__setitem__("checksum_match", None)), False),
            ("checksum_match key absent (older manifest)", lambda: edit(lambda e: e.pop("checksum_match", None)), False),
            ("recorded sha256 absent (nothing to re-hash against)", lambda: edit(lambda e: e.pop("sha256", None)), False),
            ("checksum_match = False (the one class OLD was written for)", lambda: edit(lambda e: e.__setitem__("checksum_match", False)), False),
        ]
        rows, missed = [], 0
        for name, fn, want_green in cases:
            restore(); fn()
            ov, osaid = old_gate(root, month)
            nv = G.verify_month(root, month)
            old_wrong = (ov != want_green)
            new_wrong = (nv["ok"] != want_green)
            if old_wrong and not want_green:
                missed += 1
            rows.append({"mutation": name, "should_be_green": want_green,
                         "old_reads_as_verified": ov, "old_said": osaid,
                         "new_ok": nv["ok"], "new_verdict": nv["verdict"],
                         "old_wrong": old_wrong, "new_wrong": new_wrong})
        restore()
        rec = {"device": os.path.basename(__file__),
               "self_sha256": G._sha256(os.path.realpath(__file__)),
               "gate_sha256": G._sha256(os.path.realpath(G.__file__)),
               "what": "R25-11 before/after: which archive-corruption classes each gate detects",
               "fixture": "synthetic month, green by construction",
               "limitation": "fixture hashed by the gate's own hash function: tests the decision, not the algorithm",
               "n_defect_classes": sum(1 for r in rows if not r["should_be_green"]),
               "old_missed": missed,
               "new_missed": sum(1 for r in rows if r["new_wrong"]),
               "baseline_green_under_both": rows[0]["old_reads_as_verified"] and rows[0]["new_ok"],
               "rows": rows}
        w = max(len(r["mutation"]) for r in rows)
        print(f"{'mutation':{w}s}  {'OLD':26s}  NEW")
        print("-" * (w + 46))
        for r in rows:
            old = ("reads as VERIFIED" if r["old_reads_as_verified"] else r["old_said"])
            flag = "  <-- MISSED" if r["old_wrong"] and not r["should_be_green"] else ""
            print(f"{r['mutation']:{w}s}  {old:26s}  {'green' if r['new_ok'] else 'RED'} {r['new_verdict']}{flag}")
        print("-" * (w + 46))
        print(f"defect classes: {rec['n_defect_classes']}   OLD read as verified data: {missed}   "
              f"NEW missed: {rec['new_missed']}   baseline green under both: {rec['baseline_green_under_both']}")
        if out:
            json.dump(rec, open(out, "w"), indent=1)
            print(f"receipt -> {out}  sha256={G._sha256(out)}")
        # the control is only meaningful if the baseline is green under BOTH gates
        assert rec["baseline_green_under_both"], "baseline not green under both gates: the fixture is wrong, not the gates"
        assert rec["new_missed"] == 0, ("the new gate missed a class", rows)
        return 0
    finally:
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(pristine, ignore_errors=True)


def _flip(p):
    b = bytearray(open(p, "rb").read())
    b[len(b) // 2] ^= 0x01
    open(p, "wb").write(bytes(b))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))

#!/usr/bin/env python3
"""fcf_control_F0.py — THE END-TO-END CONTROL. F0's targets reproduce the archived production target bitwise (fcf_targets.py check A1),
so F0's 32 simulated paths must reproduce the CERTIFIED baseline-tables run OBJB_A0|scaled|rule|raw|UAFE bitwise, array by array.

What this certifies, and what it does not:
  IT CERTIFIES  that the judge as run in this tree (device copies, run config, target adapter, universe rows, prices, calibration,
                executor tree, seeds) is the same judge that produced the certified A0 tables — end to end, not by sha bookkeeping.
                It also certifies that the run TAG has no numerical effect (the certified run's tag is OBJB_A0|…, this one's is
                OBJB_F0|…, and the tag travels into the target document's booster_sha / producer fields).
  IT DOES NOT   certify any arm's return, and it is not a judgement about any arm.

A DIFFERENCE IS A REFUSAL, not a tolerance: every array of every seed must be bitwise equal. The comparison is over the FULL key set of
both files (asserted equal first), so a key present in one and missing in the other is a failure, not an unexamined pass.

usage: fcf_control_F0.py <mine_run_dir> <mine_tag> <certified_run_dir> <certified_tag> <n_seeds> <out.json>
"""
import hashlib, json, os, sys, time

import numpy as np


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def main():
    MD, MT, CD, CT, NS, OUTP = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]), sys.argv[6]
    doc = {"device": "fcf_control_F0.py", "self_sha256": sha(os.path.abspath(__file__)),
           "mine": {"dir": MD, "tag": MT}, "certified": {"dir": CD, "tag": CT}, "n_seeds": NS,
           "rule": "every array of every seed must be BITWISE equal; any difference is a REFUSAL",
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "seeds": {}}
    bad = []
    for s in range(NS):
        a = os.path.join(MD, f"PATH_{MT}_seed_{s:02d}.npz"); b = os.path.join(CD, f"PATH_{CT}_seed_{s:02d}.npz")
        if not (os.path.exists(a) and os.path.exists(b)):
            bad.append(f"seed{s:02d}:missing"); doc["seeds"][s] = {"ok": False, "why": "missing", "mine": os.path.exists(a), "certified": os.path.exists(b)}
            continue
        Za = np.load(a); Zb = np.load(b)
        ka, kb = sorted(Za.files), sorted(Zb.files)
        if ka != kb:
            bad.append(f"seed{s:02d}:keyset"); doc["seeds"][s] = {"ok": False, "why": "key sets differ", "only_mine": sorted(set(ka) - set(kb)),
                                                                 "only_certified": sorted(set(kb) - set(ka))}
            continue
        diff = [k for k in ka if (Za[k].dtype != Zb[k].dtype or Za[k].shape != Zb[k].shape or Za[k].tobytes() != Zb[k].tobytes())]
        ok = not diff
        if not ok: bad.append(f"seed{s:02d}:" + ",".join(diff[:4]))
        doc["seeds"][s] = {"ok": ok, "n_keys": len(ka), "keys_differing": diff[:8],
                           "npz_sha256_mine": sha(a), "npz_sha256_certified": sha(b),
                           "nav_last_mine": float(Za["nav1"][-1]), "nav_last_certified": float(Zb["nav1"][-1])}
    doc["n_seeds_bitwise_equal"] = sum(1 for v in doc["seeds"].values() if v.get("ok"))
    doc["VERDICT"] = "PASS" if (not bad and doc["n_seeds_bitwise_equal"] == NS) else "REFUSED"
    doc["failures"] = bad
    json.dump(doc, open(OUTP + ".tmp", "w"), indent=1); os.replace(OUTP + ".tmp", OUTP)
    print(f"FCF_CONTROL_F0 VERDICT={doc['VERDICT']} bitwise_equal_seeds={doc['n_seeds_bitwise_equal']}/{NS} "
          f"failures={len(bad)} receipt_sha256={sha(OUTP)}", flush=True)
    sys.exit(0 if doc["VERDICT"] == "PASS" else 3)


if __name__ == "__main__":
    main()

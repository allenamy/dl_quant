#!/usr/bin/env python3
"""m3c_sha_compare.py — bitwise equality of FULL path files by sha256 when the reference run directory no longer exists.
Why: news2 removed its NEWS2_s{42,2027}X run directories from /dev/shm after M3c's s42 readout had read them; their launch receipts
(BT_LAUNCH_full_news2_s{42,2027}x.json, sha-pinned in M3C_OPERATIONALISATION.json) keep every seed's full-npz sha256. M3c's zero-hedge control
full files were compacted after the launch; m3c_compact.py recorded each full file's sha256 (asserted equal to its path json's npz_sha256)
before removing it. Equal sha256 of the full npz = the files are byte-identical = every array bitwise equal.
Red-capability control: our seed 0 against the reference's seed 1 must differ. Output schema = m2_path_compare.py's (VERDICT BITWISE_EQUAL,
per_seed{…}), so m3_readout.py's control check reads it unchanged.
usage: python m3c_sha_compare.py <compact_receipt.json> <reference_launch_receipt.json> <reference_receipt_sha256> <out.json>
"""
import sys, json, hashlib, time, os


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


cr_p, ref_p, ref_sha, outp = sys.argv[1:5]
if sha(ref_p) != ref_sha: raise SystemExit("reference launch receipt sha mismatch — refused")
CR = json.load(open(cr_p)); REF = json.load(open(ref_p))
runs = REF["runs"]
if len(runs) != 1: raise SystemExit(f"reference receipt has {len(runs)} runs")
ref_seeds = {int(s): v["npz_sha256"] for s, v in list(runs.values())[0]["seeds"].items()}
ours = {}
for f, v in CR["files"].items():
    s = int(f.split("_seed_")[1][:2]); ours[s] = v["full_sha256"]
if sorted(ours) != list(range(32)) or sorted(ref_seeds) != list(range(32)): raise SystemExit("seed sets are not 0..31 on both sides")
per = {s: {"ours_full_sha256": ours[s], "reference_full_sha256": ref_seeds[s], "equal": ours[s] == ref_seeds[s]} for s in range(32)}
ctrl = {"a_seed": 0, "b_seed": 1, "must_differ": True, "differs": ours[0] != ref_seeds[1]}
ok = all(v["equal"] for v in per.values()) and ctrl["differs"]
out = {"device": "m3c_sha_compare.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "compact_receipt": {"path": cr_p, "sha256": sha(cr_p)}, "reference_launch_receipt": {"path": ref_p, "sha256": ref_sha,
       "run": list(runs)[0]}, "per_seed": per, "red_capability_control": ctrl, "method": "sha256 of the FULL path npz on both sides",
       "VERDICT": "BITWISE_EQUAL" if ok else "NOT_EQUAL_OR_CONTROL_FAILED"}
json.dump(out, open(outp, "w"), indent=1)
print("M3C_SHA_COMPARE", out["VERDICT"], "equal", sum(v["equal"] for v in per.values()), "/ 32 control_differs", ctrl["differs"], "out_sha256", sha(outp), flush=True)
sys.exit(0 if ok else 1)

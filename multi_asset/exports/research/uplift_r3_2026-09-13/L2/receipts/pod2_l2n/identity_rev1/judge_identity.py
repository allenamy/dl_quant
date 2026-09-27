#!/usr/bin/env python3
"""judge_identity.py — identity control for l2n_judge_rev1.py vs l2n_judge.py (MAIN stage), lead conditions 1 (2026-09-27 06:4xZ).
Both device sources are exec'd with the SAME harness substitutions (applied identically, asserted to hit exactly once each):
  SEEDS/MODELS restricted to s42 / R (and the verdict loop's eligible list to the same models, rev b: rev a crashed with KeyError s42|L); 200 nulls -> 2 nulls (r = 0, 1); each permuted y2 captured; receipt path -> /dev/shm.
Compared bitwise: y2 for r = 0 and r = 1 (np.array_equal, equal_nan), null ICs (float.hex), and the whole non-permutation cell
(spectrum, SF IC, A / B / by_year / Pneg summaries, sd_ratio, decile descriptives) via json with float.hex encoding.
usage (pod2, env whitelist as the executor): python -B judge_identity.py <whitelist> <out_json>"""
import sys, json, time, hashlib, numpy as np
DEV = "/workspace/uplift_r3_2026-09-13/L2/devices"; W = sys.argv[1]; OUTJ = sys.argv[2]
SUBS = [('SEEDS = ("42", "2027"); MODELS = ("R", "L")', 'SEEDS = ("42",); MODELS = ("R",)'),
        ("for r in range(200):", "for r in range(2):"),
        ("v, _, _ = anchor_ic(p, y2, i, day); nulls.append(float(v.mean()))", "v, _, _ = anchor_ic(p, y2, i, day); nulls.append(float(v.mean())); _Y2.append(y2.copy())"),
        ('p = f"{REC}/RECEIPT_L2N_judge_{STAGE}.json"', 'p = _RECP'),
        ('elig = RJ["eligible_models"]; void = []', 'elig = [m for m in RJ["eligible_models"] if m in MODELS]; void = []')]
def hexify(o):
    if isinstance(o, float): return o.hex()
    if isinstance(o, dict): return {k: hexify(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [hexify(v) for v in o]
    return o
res = {}
for name in ("l2n_judge.py", "l2n_judge_rev1.py"):
    src = open(f"{DEV}/{name}").read()
    for a, b in SUBS:
        assert src.count(a) == 1, (name, a, src.count(a)); src = src.replace(a, b)
    g = {"__name__": "__main__", "__file__": f"{DEV}/{name}", "_Y2": [], "_RECP": f"/dev/shm/alloc_2026-09-26/eta/IDENT_{name}.json"}
    sys.argv = [f"{DEV}/{name}", W, "MAIN"]; t = time.time()
    exec(compile(src, f"{DEV}/{name}", "exec"), g)
    res[name] = {"cell": g["rec"]["cells"]["s42|R"], "nulls": g["nulls"], "Y2": g["_Y2"], "wall_s": time.time() - t, "self_sha256": g["rec"]["self_sha256"]}
    print(name, "wall_s", round(res[name]["wall_s"], 1), flush=True)
A, B = res["l2n_judge.py"], res["l2n_judge_rev1.py"]
chk = {"y2_r0_equal": bool(np.array_equal(A["Y2"][0], B["Y2"][0], equal_nan=True)),
       "y2_r1_equal": bool(np.array_equal(A["Y2"][1], B["Y2"][1], equal_nan=True)),
       "y2_sha": [[hashlib.sha256(x.tobytes()).hexdigest()[:16] for x in r["Y2"]] for r in (A, B)],
       "nulls_hex_old": [x.hex() for x in A["nulls"]], "nulls_hex_new": [x.hex() for x in B["nulls"]],
       "nulls_equal": [x.hex() for x in A["nulls"]] == [x.hex() for x in B["nulls"]],
       "cell_hex_equal": json.dumps(hexify(A["cell"]), sort_keys=True) == json.dumps(hexify(B["cell"]), sort_keys=True),
       "cell_sha_old": hashlib.sha256(json.dumps(hexify(A["cell"]), sort_keys=True).encode()).hexdigest(),
       "cell_sha_new": hashlib.sha256(json.dumps(hexify(B["cell"]), sort_keys=True).encode()).hexdigest(),
       "wall_s": {"old": A["wall_s"], "new": B["wall_s"]}, "self_sha256": {"old": A["self_sha256"], "new": B["self_sha256"]},
       "harness_subs": SUBS, "harness_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest()}
chk["ALL_EQUAL"] = chk["y2_r0_equal"] and chk["y2_r1_equal"] and chk["nulls_equal"] and chk["cell_hex_equal"]
with open(OUTJ, "w") as f: json.dump(chk, f, indent=1)
assert json.load(open(OUTJ))["ALL_EQUAL"] == chk["ALL_EQUAL"]
print("IDENTITY", "ALL_EQUAL" if chk["ALL_EQUAL"] else "NOT_EQUAL", json.dumps({k: chk[k] for k in ("y2_r0_equal", "y2_r1_equal", "nulls_equal", "cell_hex_equal")}), flush=True)

#!/usr/bin/env python3
"""ovn_adapter_test.py — red/green test of ovn_adapter.py on the REAL NEW inputs (no fixture): the baseline must be GREEN first (asserted and
printed with its measured values), then every mutation must go RED with its NAMED reason. A mutation that goes red for a different reason
counts as a test failure (it would not show that the intended check works).
  M1 one CSR column index +1 (a column not already in that row, so the certified loader accepts the file) -> RoundTripError 'dense rows differ'
  M2 one published row turned into a hold (kind 2 -> 0, row emptied, CSR still valid)            -> RoundTripError 'fresh != trade_mask'
  M3 one weight +1 ulp                                                                            -> RoundTripError 'dense rows differ'
  M4 two symbols swapped on the NEW symbol axis (input copy, its own sha pinned)                  -> AdapterError 'symbols_vs_certified_price_axis'
  M5 a HOLD row given a nonzero weight (input copy, its own sha pinned)                           -> AdapterError 'hold_row_with_weight'
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B ovn_adapter_test.py PATH,HOME,LC_CTYPE <spec.json> <scratch_dir> <out.json>
"""
import os, sys, json, time, shutil

import numpy as np

WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import ovn_adapter as AD
import bt_objb_targets as OT

spec_p, SCR, OUT = sys.argv[2:5]
spec = json.load(open(spec_p)); os.makedirs(SCR, exist_ok=True)
FIRST = AD.ts(spec["window_first_anchor"])
rec = {"device": "ovn_adapter_test.py", "self_sha256": AD.sha(os.path.abspath(__file__)), "adapter_sha256": AD.sha(os.path.join(HERE, "ovn_adapter.py")),
       "loader_sha256": AD.sha(os.path.join(HERE, "bt_objb_targets.py")), "spec": spec, "utc_start": AD.iso(time.time()), "cases": []}


def run_case(name, spec_c, mutate_targets=None, expect=None):
    npz = os.path.join(SCR, f"T_{name}.npz"); rj = os.path.join(SCR, f"T_{name}.json")
    try:
        out, info, D = AD.build(spec_c)
        if mutate_targets: out, note = mutate_targets(out)
        else: note = None
        AD.write(out, info, spec_c, npz, rj, rec["adapter_sha256"])
        rt = AD.verify_roundtrip(npz, rj, spec_c["arm"], D, FIRST, OT)
        res = {"case": name, "outcome": "GREEN", "detail": {k: {kk: v[kk] for kk in ("anchors_compared", "published_equal", "bitwise_equal", "padded_checked")} for k, v in rt.items()}, "mutation": note}
    except (AD.AdapterError, AD.RoundTripError, OT.TargetFormatError) as e:
        res = {"case": name, "outcome": "RED", "error_type": type(e).__name__, "error": str(e)[:400]}
        if mutate_targets is None and name != "baseline": res["mutation"] = spec_c.get("_mutation")
    for p in (npz, rj):
        if os.path.exists(p): os.remove(p)
    if expect is None:
        res["as_expected"] = res["outcome"] == "GREEN"
    else:
        res["expected"] = expect; res["as_expected"] = res["outcome"] == "RED" and res.get("error_type") == expect[0] and expect[1] in res.get("error", "")
    rec["cases"].append(res); print(json.dumps(res)[:600], flush=True)
    return res


# ---- baseline first: must be green, with measured values printed ----
base = run_case("baseline", spec)
if not base["as_expected"]:
    rec["VERDICT"] = "RED_BASELINE"; json.dump(rec, open(OUT, "w"), indent=1); print("OVN_ADAPTER_TEST VERDICT=RED_BASELINE"); sys.exit(3)


def pick_row(out, R_="scaled"):
    k = np.nonzero(out[f"{R_}_kind"] == 2)[0]; return int(k[len(k) // 2])       # a published row in the middle of the axis


def m1(out):
    o = {k: v.copy() for k, v in out.items()}; i = pick_row(o); a, b = o["scaled_off"][i], o["scaled_off"][i + 1]
    row = set(o["scaled_idx"][a:b].tolist())
    for p in range(a, b):
        c = int(o["scaled_idx"][p])
        if c + 1 < AD.N_SYM and (c + 1) not in row:
            o["scaled_idx"][p] = c + 1; return o, {"anchor": AD.iso(o["anchor"][i]), "position": int(p), "from": c, "to": c + 1}
    raise RuntimeError("no movable column")


def m2(out):
    o = {k: v.copy() for k, v in out.items()}; i = pick_row(o); a, b = int(o["scaled_off"][i]), int(o["scaled_off"][i + 1]); L = b - a
    o["scaled_kind"][i] = 0; o["scaled_idx"] = np.concatenate([o["scaled_idx"][:a], o["scaled_idx"][b:]])
    o["scaled_val"] = np.concatenate([o["scaled_val"][:a], o["scaled_val"][b:]]); o["scaled_off"][i + 1:] -= L
    return o, {"anchor": AD.iso(o["anchor"][i]), "removed_entries": L}


def m3(out):
    o = {k: v.copy() for k, v in out.items()}; i = pick_row(o); a = int(o["scaled_off"][i]); v = o["scaled_val"][a]
    o["scaled_val"][a] = np.nextafter(v, np.inf); return o, {"anchor": AD.iso(o["anchor"][i]), "position": a, "from": float(v), "to": float(o["scaled_val"][a])}


run_case("M1_index_plus_one", spec, m1, ("RoundTripError", "dense rows differ"))
run_case("M2_published_row_to_hold", spec, m2, ("RoundTripError", "fresh != trade_mask"))
run_case("M3_value_plus_one_ulp", spec, m3, ("RoundTripError", "dense rows differ"))


def mutated_input(name, fn):
    Z = np.load(spec["scaled"]["npz"], allow_pickle=False); D = {k: Z[k] for k in Z.files}; note = fn(D)
    p = os.path.join(SCR, f"IN_{name}.npz"); np.savez(p, **D)
    s = json.loads(json.dumps(spec)); s["scaled"] = {"npz": p, "sha256": AD.sha(p)}; s["_mutation"] = note
    # the NEW receipt pins the scaled file's sha; a mutated copy needs a receipt copy that pins it, or the case would go red on the receipt instead
    NR = json.load(open(spec["new_receipt"]["path"])); NR["policies"]["scaled_diagnostic"]["sha"] = s["scaled"]["sha256"]
    rp = os.path.join(SCR, f"RC_{name}.json"); json.dump(NR, open(rp, "w")); s["new_receipt"] = {"path": rp, "sha256": AD.sha(rp)}
    return s, [p, rp]


def m4(D):
    s = D["symbols"].copy(); s[[10, 11]] = s[[11, 10]]; D["symbols"] = s; return {"swapped_positions": [10, 11]}


def m5(D):
    tm = D["trade_mask"]; i = int(np.nonzero(~tm)[0][-1]); W = D["weights"].copy(); W[i, 0] = 1e-3; D["weights"] = W; return {"hold_anchor": AD.iso(D["E_ts"][i]), "col": 0}


for name, fn, exp in (("M4_symbols_swapped", m4, ("AdapterError", "symbols_vs_certified_price_axis")), ("M5_hold_row_weight", m5, ("AdapterError", "hold_row_with_weight"))):
    s, files = mutated_input(name, fn)
    run_case(name, s, None, exp)
    for p in files: os.remove(p)

ok = all(c["as_expected"] for c in rec["cases"])
rec["VERDICT"] = "PASS" if ok else "FAIL"; rec["utc_end"] = AD.iso(time.time())
json.dump(rec, open(OUT, "w"), indent=1)
line = "OVN_ADAPTER_TEST VERDICT=%s baseline=%s mutations_red_as_named=%d/%d" % (rec["VERDICT"], base["outcome"], sum(c["as_expected"] for c in rec["cases"][1:]), len(rec["cases"]) - 1)
print(line, flush=True); sys.exit(0 if ok else 3)

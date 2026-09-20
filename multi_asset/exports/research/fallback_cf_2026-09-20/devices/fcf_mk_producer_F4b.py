#!/usr/bin/env python3
"""fcf_mk_producer_F4b.py — make the F4b producer: a copy of the pinned production producer with EXACTLY ONE line changed, and prove it.

PREREG_fallback_counterfactual_2026-09-20 §2 F4: "预检失败 ⇒ 写 king 组件但去掉 rev24 腿", under §2's standing constraint
"不改预检本身, 不改席位, 不改 gross 归一化".

THE ONE LINE (object_b_2026-09-19/devices/shadow_loop_v3_replay.py, run_anchor step 8 — E-0920-B: the production definition line,
file:line + code, copied verbatim):
L449:     z = w3[0] * np.nan_to_num(legz["king"]) + w3[1] * np.nan_to_num(legz["rev24"]) + w3[2] * np.nan_to_num(legz["fund"])
becomes
L449:     z = w3[0] * np.nan_to_num(legz["king"]) + 0.0 * np.nan_to_num(legz["rev24"]) + w3[2] * np.nan_to_num(legz["fund"])

Why `0.0 *` and not deleting the term: `np.nan_to_num` leaves no NaN or inf, so `0.0 * x` is exactly +0.0 for every element and
`y + 0.0` is exactly y in IEEE-754 (the one exception, -0.0 + 0.0 = +0.0, cannot change any downstream comparison here because the
next operation is a subtraction of the mean). Keeping the term makes the diff ONE line and keeps every other byte, including every
line number, identical — so the structural proof below is a proof about the whole file, not about a region of it.

WHY THE SEAT IS UNTOUCHED, by construction and not by claim: w3 comes from the leg return ledger, which is built from the LEGS, never
from the book —
L410:             for leg in ("king", "rev24", "fund"):
L411:                 z = np.array(prev["legz"][leg])
L416:                 st.LR[leg].append(float((zz / g * np.nan_to_num(y4v[pm], nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0)
L434:     if len(st.LR["king"]) >= look:
L435:         r = np.stack([np.array(st.LR[leg][-look:]) for leg in ("king", "rev24", "fund")])
L436:         shp = r.mean(1) / (r.std(1) + 1e-9); shp = np.maximum(shp, 0.0)
L437:         w3 = shp / shp.sum() if shp.sum() > 0 else np.array([1/3] * 3)
so w3 is bitwise identical in the F4b world. This is ASSERTED at run time (fcf_rechain_F4b.py), not only argued here.

STRUCTURAL GATE (refuses to write the file unless all four hold):
  G1  the source file's sha256 equals b_driver.PIN_DEV["shadow_loop_v3_replay.py"] (the pinned production device)
  G2  the unified diff between source and output has EXACTLY ONE changed line
  G3  that line is line 449, and its before / after text equals the two strings above, byte for byte
  G4  the output still parses and still carries the same REPLAY_META production_sha256

usage: fcf_mk_producer_F4b.py
"""
import ast, difflib, hashlib, json, os, sys, time

OBJB_DEV = "/workspace/object_b_2026-09-19/devices"
SRC = f"{OBJB_DEV}/shadow_loop_v3_replay.py"
OUT = "/workspace/fallback_cf_2026-09-20"
DST = f"{OUT}/devices/shadow_loop_v3_replay_F4b.py"
LINE_NO = 449
BEFORE = '    z = w3[0] * np.nan_to_num(legz["king"]) + w3[1] * np.nan_to_num(legz["rev24"]) + w3[2] * np.nan_to_num(legz["fund"])\n'
AFTER = '    z = w3[0] * np.nan_to_num(legz["king"]) + 0.0 * np.nan_to_num(legz["rev24"]) + w3[2] * np.nan_to_num(legz["fund"])\n'
PIN_SRC = "4d3bc157f03e3462a69e64f817b3fd4cd51be4c03d72650304b7d0c1a0089d42"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def main():
    rec = {"device": "fcf_mk_producer_F4b.py", "self_sha256": sha(os.path.abspath(__file__)),
           "source": {"path": SRC, "sha256": sha(SRC)}, "pinned_production_sha256": PIN_SRC,
           "intervention": {"line": LINE_NO, "before": BEFORE.rstrip("\n"), "after": AFTER.rstrip("\n"),
                            "meaning": "the rev24 leg is removed from the producer's book signal; the seat w3 is NOT renormalised and NOT changed"},
           "gates": [], "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    FAILS = []

    def g(name, ok, detail=None):
        rec["gates"].append(dict(gate=name, ok=bool(ok), detail=detail))
        print(("PASS " if ok else "FAIL ") + name, json.dumps(detail, default=str)[:260] if detail is not None else "", flush=True)
        if not ok: FAILS.append(name)

    g("G1.source_is_the_pinned_production_producer", sha(SRC) == PIN_SRC, dict(got=sha(SRC)[:16], want=PIN_SRC[:16]))
    src = open(SRC).readlines()
    g("G3a.line_449_is_the_expected_production_line", src[LINE_NO - 1] == BEFORE,
      dict(got=src[LINE_NO - 1].rstrip("\n")[:160], want=BEFORE.rstrip("\n")[:160]))
    if FAILS:
        json.dump(dict(rec, VERDICT="REFUSED", failed=FAILS), open(f"{OUT}/receipts/FCF_PRODUCER_F4b.json", "w"), indent=1)
        print("FCF_PRODUCER_F4b VERDICT=REFUSED failed=" + ",".join(FAILS), flush=True); sys.exit(3)

    dst = list(src); dst[LINE_NO - 1] = AFTER
    changed = [(i + 1, a, b) for i, (a, b) in enumerate(zip(src, dst)) if a != b]
    g("G2.exactly_one_changed_line", len(changed) == 1 and len(src) == len(dst),
      dict(n_changed=len(changed), lines=[c[0] for c in changed], n_lines_src=len(src), n_lines_dst=len(dst)))
    g("G3b.the_changed_line_is_449_with_the_expected_text",
      bool(changed) and changed[0][0] == LINE_NO and changed[0][1] == BEFORE and changed[0][2] == AFTER,
      dict(line=changed[0][0] if changed else None))
    rec["unified_diff"] = "".join(difflib.unified_diff(src, dst, "shadow_loop_v3_replay.py", "shadow_loop_v3_replay_F4b.py", n=1))
    try:
        ast.parse("".join(dst)); parse_ok = True; perr = None
    except SyntaxError as e:
        parse_ok = False; perr = repr(e)
    g("G4a.output_parses", parse_ok, perr)
    meta_src = [l for l in src if "production_sha256" in l]; meta_dst = [l for l in dst if "production_sha256" in l]
    g("G4b.REPLAY_META_production_sha256_unchanged", meta_src == meta_dst and len(meta_src) >= 1, dict(n=len(meta_src)))
    if FAILS:
        json.dump(dict(rec, VERDICT="REFUSED", failed=FAILS), open(f"{OUT}/receipts/FCF_PRODUCER_F4b.json", "w"), indent=1)
        print("FCF_PRODUCER_F4b VERDICT=REFUSED failed=" + ",".join(FAILS), flush=True); sys.exit(3)

    with open(DST + ".tmp", "w") as f: f.writelines(dst)
    os.replace(DST + ".tmp", DST)
    rec["output"] = {"path": DST, "sha256": sha(DST)}
    rec["VERDICT"] = "PASS"; rec["failed"] = []
    json.dump(rec, open(f"{OUT}/receipts/FCF_PRODUCER_F4b.json", "w"), indent=1)
    print("FCF_PRODUCER_F4b VERDICT=PASS out_sha256=" + rec["output"]["sha256"] + " receipt_sha256=" + sha(f"{OUT}/receipts/FCF_PRODUCER_F4b.json"), flush=True)
    print(rec["unified_diff"], flush=True)


if __name__ == "__main__":
    main()

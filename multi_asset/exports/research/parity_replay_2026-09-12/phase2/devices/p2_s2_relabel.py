#!/usr/bin/env python3
"""S2 relabel — PREREG_producer_parity_phase2_oos_2026-09-12 AMENDMENT 8 (file sha 0d8d2cee…, commit 12c0553b). Runs on the Mac repo (no numpy needed here).
1. Guarded reads (APFS dataless flag refused; bytes == st_size) and sha pins of every input: the shared K2 module equivalence_labels.py (ab651754…),
   its test file (0491f9b1…), DELTA_TABLE_K2.json (ad6af207…), p2_s2_lib.py (c53f5c49…, only for the AST extraction of the superseded `verdict`),
   S2_TABLES.json (2f3c67f6…, the committed copy of the pod2 receipt).
2. Module self-test: `python3 tests_equivalence_labels.py --impl module` must exit 0 with its SUMMARY line. (AMENDMENT 8 said the test file must be
   importable; it asserts `--impl` at import, so it is executed instead — a stronger check, recorded as a deviation in the receipt.)
3. Red test R1-R5 of A8 (old predicate AST-extracted verbatim; new = equivalence_labels.v4_label with D1). Any mismatch -> exit 3, no labels issued.
4. Re-issue the verdict words of the 12 two-seed P2-CMB contrasts x 3 windows from the S2_TABLES intervals (no interval is recomputed): k0 label,
   k9 label, sensitivity labels at D1 in {0.02, 0.25}. Writes receipts/s2/S2_TABLES_K2.json and .md; prints one S2_RELABEL line; exit 0 iff all checks pass.
usage: python3 p2_s2_relabel.py"""
import os, sys, json, ast, stat, time, hashlib, subprocess
ROOT = "/Users/haosiyu/Desktop/quant_research"; PH = ROOT + "/multi_asset/exports/research/parity_replay_2026-09-12/phase2"
PIN = {"equivalence_labels": (ROOT + "/multi_asset/exports/research/common/equivalence_labels.py", "ab651754208e62a947bbfcad4a2f6cbbb41dc9cc3b7673869a6e4de77e0b8f04"),
       "tests_equivalence_labels": (ROOT + "/multi_asset/exports/research/common/tests_equivalence_labels.py", "0491f9b131dc66ca31efba28b4aa0331c4ace95b80274ad6b9e47d632625b65f"),
       "delta_table": (ROOT + "/docs/fixprogram_2026-09-13/FX_EVAL/DELTA_TABLE_K2.json", "ad6af2075ca71ed756be26bbe7759761f981add24f02581de41c3f014643dea6"),
       "p2_s2_lib": (PH + "/devices/p2_s2_lib.py", "c53f5c495036727fcd7115bad6838229923c91f6b76bed955ebdb0f25d57c831"),
       "S2_TABLES": (PH + "/receipts/s2/S2_TABLES.json", "2f3c67f6049ab538f4313dedadc6b1336e6727d6b6f69fc098c78a0ccd475bc1")}
PREREG_SHA = "0d8d2ceeabc6e991951d466a02a8a06c5e3416a7ef0f86f5a36dca6fcbd54a90"
SF_DATALESS = getattr(stat, "SF_DATALESS", 0x40000000)
def guarded(p):
    st = os.stat(p)
    if st.st_flags & SF_DATALESS: raise SystemExit("REFUSE %s: dataless" % p)
    b = open(p, "rb").read()
    if len(b) != st.st_size: raise SystemExit("REFUSE %s: read %d of %d bytes" % (p, len(b), st.st_size))
    return b
RAW = {}
for k, (p, s) in PIN.items():
    b = guarded(p); h = hashlib.sha256(b).hexdigest(); assert h == s, ("pin", k, h); RAW[k] = b
SELF = hashlib.sha256(guarded(os.path.abspath(__file__))).hexdigest()
sys.path.insert(0, os.path.dirname(PIN["equivalence_labels"][0]))
import equivalence_labels as EL
assert hashlib.sha256(guarded(EL.__file__)).hexdigest() == PIN["equivalence_labels"][1]
# δ = D1 from the frozen table
DT = json.loads(RAW["delta_table"]); D1 = [e for e in DT["deltas"] if e["key"] == "D1"][0]
assert D1["delta"] == 0.05 and D1["sensitivity"] == [0.02, 0.25]
def margin(delta, sens=False):
    return EL.Margin(delta=delta, unit=D1["unit"], justification=" | ".join(D1["justification"]) + (" [SENSITIVITY COLUMN, never sets a label]" if sens else ""),
                     source="docs/fixprogram_2026-09-13/FX_EVAL/DELTA_TABLE_K2.json sha256 ad6af207… key D1")
M = margin(0.05); MS = {0.02: margin(0.02, True), 0.25: margin(0.25, True)}
OUT = dict(device="p2_s2_relabel.py", self_sha256=SELF, prereg_sha256=PREREG_SHA, inputs={k: dict(path=p, sha256=s) for k, (p, s) in PIN.items()},
           python=sys.version.split()[0], utc_start=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), delta=dict(key="D1", delta=0.05, unit=D1["unit"], sensitivity=[0.02, 0.25]))
# 2. module self-test
t = subprocess.run([sys.executable, PIN["tests_equivalence_labels"][0], "--impl", "module"], capture_output=True, text=True, timeout=600, cwd=os.path.dirname(PIN["tests_equivalence_labels"][0]))
summ = [l for l in t.stdout.splitlines() if l.startswith("SUMMARY")]
OUT["module_selftest"] = dict(rc=t.returncode, summary=summ[-1] if summ else None, stderr_tail=t.stderr.strip().splitlines()[-3:],
                              deviation="A8 text said 'importable'; the file asserts --impl at import, so it is executed with --impl module and must exit 0")
SELFTEST_OK = t.returncode == 0 and bool(summ)
# 3. red test
tree = ast.parse(RAW["p2_s2_lib"].decode()); seg = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "verdict"][0]
src = ast.get_source_segment(RAW["p2_s2_lib"].decode(), seg); ns = {"RES_BPS": 0.23}; exec(compile(src, "p2_s2_lib.py:verdict", "exec"), ns); OLD = ns["verdict"]
assert [n for n in tree.body if isinstance(n, ast.Assign) and any(getattr(t_, "id", None) == "RES_BPS" for t_ in n.targets)], "RES_BPS in lib"
def old_cells(c42, c27): return {"42": dict(dg=c42[0], ci95_k0=[c42[1], c42[2]]), "2027": dict(dg=c27[0], ci95_k0=[c27[1], c27[2]])}
def new_label(c42, c27, m=M):
    return EL.v4_label([EL.Interval(point=c[0], lo=c[1], hi=c[2], level=0.95) for c in (c42, c27)], margin=m)
RED = {}
cases = {"R1": ((0.20, 0.10, 0.30), (0.20, 0.10, 0.30), "(C) indistinguishable (|Δg| < 0.23)", "(A)", None),
         "R2": ((0.02, -0.40, 0.44), (0.02, -0.40, 0.44), "(C) indistinguishable (|Δg| < 0.23)", "(C) INCONCLUSIVE", None),
         "R3": ((0.01, -0.03, 0.04), (0.01, -0.03, 0.04), None, "(C) EQUIVALENT", None),
         "R4": ((-0.30, -0.50, -0.10), (-0.30, -0.50, -0.10), "(B)", "(B)", None),
         "R5": ((0.01, -0.03, 0.04), (0.30, 0.10, 0.50), None, "(C) INCONCLUSIVE", True)}
for k, (a, b, want_old, want_new, want_conflict) in cases.items():
    o = OLD(old_cells(a, b), 0); n = new_label(a, b)
    ok = (want_old is None or o == want_old) and n["label"] == want_new and (want_conflict is None or n["seed_conflict"] == want_conflict)
    RED[k] = dict(cells=[a, b], old=o, old_expected=want_old, new=n["label"], new_expected=want_new, seed_conflict=n["seed_conflict"], PASS=bool(ok))
OUT["red_test"] = RED; RED_OK = all(v["PASS"] for v in RED.values())
if not (SELFTEST_OK and RED_OK):
    OUT["ALL_PASS"] = False; rp = PH + "/receipts/s2/S2_TABLES_K2.json"; json.dump(OUT, open(rp, "w"), indent=1, ensure_ascii=False)
    print("S2_RELABEL selftest=%s red=%s -> STOP (no labels)" % (SELFTEST_OK, {k: v["PASS"] for k, v in RED.items()})); sys.exit(3)
# 4. re-issue
TB = json.loads(RAW["S2_TABLES"]); C = TB["contrasts"]; WN = ("W_ALPHA", "W_FULL", "FROZEN")
IDS = ("K1", "K2", "K3", "K4", "K5", "K6", "K7", "K8", "K9", "M1", "M2", "M3")
LAB = {}; contradictions = []
for cid in IDS:
    LAB[cid] = {"arm": C[f"{cid}|s42"]["arm"], "ref": C[f"{cid}|s42"]["ref"]}
    for w in WN:
        c42 = C[f"{cid}|s42"][w]; c27 = C[f"{cid}|s2027"][w]
        row = dict(dg=[c42["dg"], c27["dg"]], ci95_k0=[c42["ci95_k0"], c27["ci95_k0"]], ci95_k9=[c42["ci95_k9"], c27["ci95_k9"]])
        k0 = new_label((c42["dg"], *c42["ci95_k0"]), (c27["dg"], *c27["ci95_k0"])); k9 = new_label((c42["dg"], *c42["ci95_k9"]), (c27["dg"], *c27["ci95_k9"]))
        row.update(label_k0=k0["label"], direction_k0=k0["direction"], equivalence_k0=k0["equivalence"], seed_conflict_k0=k0["seed_conflict"], label_k9=k9["label"],
                   k9_disagrees=bool(k0["label"] != k9["label"]),
                   sensitivity_labels={str(d): new_label((c42["dg"], *c42["ci95_k0"]), (c27["dg"], *c27["ci95_k0"]), MS[d])["label"] for d in (0.02, 0.25)},
                   superseded_old_rule=TB["verdicts"][cid][w]["verdict_k0"])
        if row["k9_disagrees"]: contradictions.append(f"{cid} {w}: k0 {row['label_k0']} vs k9 {row['label_k9']}")
        LAB[cid][w] = row
OUT.update(labels=LAB, k9_contradictions=contradictions, label_uncertified=TB.get("label"), S2_TABLES_md_sha256=TB.get("md_sha256"), ALL_PASS=True,
           counts={w: {lab: sum(1 for cid in IDS if LAB[cid][w]["label_k0"] == lab) for lab in sorted({LAB[c][w]["label_k0"] for c in IDS})} for w in WN},
           utc_end=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
rp = PH + "/receipts/s2/S2_TABLES_K2.json"; json.dump(OUT, open(rp, "w"), indent=1, ensure_ascii=False)
md = ["# S2 verdict words under K2 (AMENDMENT 8; δ = D1 0.05 bps/anchor/gross; module equivalence_labels.py ab651754…)", "",
      "**LABEL: " + str(TB.get("label")) + "**", "",
      "Numbers are S2_TABLES.json (2f3c67f6…) intervals, not recomputed. Labels: (A)/(B) direction (judge_v4 rule, evaluated first); otherwise (C) EQUIVALENT / INCONCLUSIVE / NOT EQUIVALENT by TOST at ±δ over both seeds. The old A6.7 words are superseded and not shown.", "",
      "| id | arm − ref | window | Δg s42 [CI95 k0] | Δg s2027 [CI95 k0] | label k0 | label k9 | sens δ=0.02 | sens δ=0.25 |", "|---|---|---|---|---|---|---|---|---|"]
for cid in IDS:
    for w in WN:
        r = LAB[cid][w]
        md.append("| %s | %s − %s | %s | %+.4f [%+.4f, %+.4f] | %+.4f [%+.4f, %+.4f] | %s | %s | %s | %s |" % (cid, LAB[cid]["arm"], LAB[cid]["ref"], w, r["dg"][0], r["ci95_k0"][0][0], r["ci95_k0"][0][1],
                  r["dg"][1], r["ci95_k0"][1][0], r["ci95_k0"][1][1], r["label_k0"], r["label_k9"] + (" ⚠" if r["k9_disagrees"] else ""), r["sensitivity_labels"]["0.02"], r["sensitivity_labels"]["0.25"]))
open(PH + "/receipts/s2/S2_TABLES_K2.md", "w").write("\n".join(md) + "\n")
print("S2_RELABEL selftest=%s red=%s labels=%s k9_contradictions=%d receipt_sha256=%s" % (OUT["module_selftest"]["summary"], "5/5", json.dumps(OUT["counts"], ensure_ascii=False), len(contradictions),
      hashlib.sha256(open(rp, "rb").read()).hexdigest()))

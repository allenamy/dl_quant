#!/usr/bin/env python3
"""bt_objb_prerun.py — the lead's pre-run checks for the object-B A0 part of the baseline tables, then (only if every check passes) the FROZEN
A0 run configuration filled from RUN_CONFIG_main_TEMPLATE_2026-09-19.json. It reads object-B receipts and input files and hashes the TARGETS
files; it never opens a target's contents beyond what bt_objb_targets.load_targets validates (no simulation, no returns).

Modes:  universe   U only (object B's universe_ext.npz vs P2 universe.npz) — can run before the targets exist
        full       U + G + T + D, then writes the frozen config
Checks (each named; any failure ⇒ no config, exit 1):
  U  universe_ext.npz (object-B EXT_INPUTS, sha pinned in the template) first 10,039 rows vs P2 universe.npz (6322b573): ts, symbols, pit and
     trading24 bitwise; the rows after them are the extension (count and span reported). Differences are listed, not tolerated.
  G  gate F lineage, per TARGETS source: TARGETS_<tag>.json → its p3_json_sha256 == sha(work/<tag>/P3.json); RUN_CONFIG_<tag>.json has
     gate_f_verdict == PASS and gate_f_sha256 == sha(receipts/GATE_F.json) == the GATE_F.json blob committed at d3596aced (916b109f…, passed
     on the command line from `git show d3596aced:…/GATE_F.json | sha256sum`); GATE_F.json VERDICT == PASS; arm == A0 in both receipts.
  T  targets: the npz sha == TARGETS json targets_npz_sha256; bt_objb_targets.load_targets validates every source (all three readings) and their
     concatenation; the axis covers the simulation window; the combo / king / hold counts inside the window are recorded.
  D  full-recipe start = B_CORE_start of the main-axis TARGETS receipt (object-B prereg §4); it must be a 4h anchor inside the window; an
     extension receipt's own B_CORE_start is recorded (not used).
Window: first anchor 2022-06-30T00Z (prereg); last anchor = 2026-09-18T20Z if the extension segment is among the sources, else the last
anchor the main-axis targets cover minus nothing — the config then says which, and the result doc must label it.
v2 (2026-09-20, the extension run): optional <run_tag_suffix> — the run tags become OBJB_A0<suffix>|… so the extended runs write their own
run directories and never touch the ones already published; the config name comes from the output file name. A new check D.ext_B_CORE_start
compares an extension receipt's B_CORE_start with the main receipt's when both are given.
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B bt_objb_prerun.py PATH,HOME,LC_CTYPE universe <out.json>
       env -i … bt_objb_prerun.py PATH,HOME,LC_CTYPE full <out.json> <template.json> <frozen_config_out.json> <gate_f_sha_at_d3596aced> <tag>[,<ext_tag>] [<run_tag_suffix>]
"""
import os, sys, json, time, hashlib, calendar
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt_objb_targets as OT

MODE = sys.argv[2]; OUTP = sys.argv[3]
OB = "/workspace/object_b_2026-09-19"
UNI_EXT = (OB + "/work/ext_inputs/universe_ext.npz", "3ee838cfc4ee4b90cef9202716af8645ff601b69137346d518ea706a5f4d598f")
UNI_P2 = ("/workspace/uplift_r2_2026-09-13/P2/work/universe.npz", "6322b57366078ed0022fd8a8156ee36f527bf309e0d66bfa5f6ec17d7a09efa7")
H4 = 14400
rec = dict(device="bt_objb_prerun.py", self_sha256=OT.sha_file(os.path.abspath(__file__)), adapter_sha256=OT.sha_file(os.path.join(HERE, "bt_objb_targets.py")),
           argv=sys.argv, utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), checks=[])
FAILS = []


def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


def check(name, ok, detail=None):
    rec["checks"].append(dict(check=name, ok=bool(ok), detail=detail)); print(("OK   " if ok else "FAIL ") + name, json.dumps(detail, default=str)[:400] if detail is not None else "", flush=True)
    if not ok: FAILS.append(name)


def done(code):
    rec["failed"] = FAILS; rec["VERDICT"] = "PASS" if not FAILS else "STOP"
    json.dump(rec, open(OUTP, "w"), indent=1, default=str); print("BT_OBJB_PRERUN VERDICT=%s mode=%s failed=%s" % (rec["VERDICT"], MODE, FAILS), flush=True); sys.exit(code)


# ---------------- U ----------------
for nm, (p, s) in (("universe_ext", UNI_EXT), ("universe_p2", UNI_P2)):
    got = OT.sha_file(p); check(f"U.input_sha.{nm}", got == s, {"got": got[:16], "want": s[:16]})
E = np.load(UNI_EXT[0], allow_pickle=True); P = np.load(UNI_P2[0], allow_pickle=True)
n = len(P["ts"])
check("U.symbols_equal", [str(x) for x in E["symbols"]] == [str(x) for x in P["symbols"]])
diffs = {}
for k in ("ts", "pit", "trading24"):
    a = np.asarray(E[k])[:n]; b = np.asarray(P[k])
    eq = a.shape == b.shape and bool(np.array_equal(a, b))
    diffs[k] = {"equal": eq, "cells_differ": (int((a != b).sum()) if a.shape == b.shape else "shape " + str(a.shape) + " vs " + str(b.shape))}
    if not eq and a.shape == b.shape and a.ndim == 2:
        rows = np.nonzero((a != b).any(1))[0]; diffs[k]["rows_differ"] = int(len(rows)); diffs[k]["first_rows"] = [iso(P["ts"][r]) for r in rows[:10]]
check("U.first_10039_rows_bitwise_equal_P2_universe", n == 10039 and all(v["equal"] for v in diffs.values()), dict(n_p2_rows=n, keys=diffs))
ets = np.asarray(E["ts"]).astype(np.int64)
rec["universe_extension"] = dict(rows_total=int(len(ets)), rows_after_p2=int(len(ets) - n), first_ext=(iso(ets[n]) if len(ets) > n else None), last=iso(ets[-1]),
                                 contiguous_4h=bool(np.all(np.diff(ets) == H4)))
check("U.extension_contiguous_to_2026-09-18T20Z", bool(np.all(np.diff(ets) == H4)) and int(ets[-1]) == calendar.timegm((2026, 9, 18, 20, 0, 0)), rec["universe_extension"])
if MODE == "universe": done(0 if not FAILS else 1)

# ---------------- G / T / D ----------------
TEMPLATE = json.load(open(sys.argv[4])); CFG_OUT = sys.argv[5]; GATE_SHA_GIT = sys.argv[6]; TAGS = sys.argv[7].split(",")
SUF = sys.argv[8] if len(sys.argv) > 8 else ""
assert all(ch.isalnum() or ch in "_-" for ch in SUF), "run tag suffix must be alphanumeric"
gate_p = OB + "/receipts/GATE_F.json"; gate_sha = OT.sha_file(gate_p); G = json.load(open(gate_p))
check("G.gate_f_file_equals_the_d3596aced_blob", gate_sha == GATE_SHA_GIT, {"pod": gate_sha[:16], "git_d3596aced": GATE_SHA_GIT[:16]})
check("G.gate_f_verdict_PASS", G.get("VERDICT") == "PASS", G.get("VERDICT"))
sources = []; info = {}
for tag in TAGS:
    tj = f"{OB}/receipts/TARGETS_{tag}.json"; tn = f"{OB}/work/{tag}/TARGETS_{tag}.npz"; p3 = f"{OB}/work/{tag}/P3.json"; rc = f"{OB}/receipts/RUN_CONFIG_{tag}.json"
    have = {k: os.path.exists(v) for k, v in (("targets_json", tj), ("targets_npz", tn), ("p3_json", p3), ("run_config", rc))}
    check(f"G.{tag}.files_present", all(have.values()), have)
    if not all(have.values()): continue
    TJ = json.load(open(tj)); RC = json.load(open(rc))
    check(f"G.{tag}.p3_sha_matches_targets_receipt", OT.sha_file(p3) == TJ.get("p3_json_sha256"))
    check(f"G.{tag}.run_config_gate_f_PASS_same_file", RC.get("gate_f_verdict") == "PASS" and RC.get("gate_f_sha256") == gate_sha, {"verdict": RC.get("gate_f_verdict"), "sha": str(RC.get("gate_f_sha256"))[:16]})
    check(f"G.{tag}.arm_A0", TJ.get("arm") == "A0" and RC.get("arm", "A0") == "A0", {"targets": TJ.get("arm"), "run_config": RC.get("arm", "A0")})
    check(f"T.{tag}.npz_sha_matches_receipt", OT.sha_file(tn) == TJ.get("targets_npz_sha256"))
    sources.append({"npz": tn, "npz_sha256": OT.sha_file(tn), "receipt": tj, "receipt_sha256": OT.sha_file(tj)})
    info[tag] = dict(axis=TJ.get("axis"), data=TJ.get("data"), B_CORE_start=TJ.get("B_CORE_start"), king_first_served=TJ.get("king_first_served"),
                     f10_first_served=TJ.get("f10_first_served"), run_config_sha256=OT.sha_file(rc), gate_f_disclosure=RC.get("gate_f_disclosure"))
rec["sources"] = info
if FAILS: done(1)
T = {}
for reading in OT.READINGS:
    try:
        T[reading] = OT.load_targets(sources, reading=reading, arm="A0")
        check(f"T.load_and_validate.{reading}", True, {"axis": [iso(T[reading]["anchor"][0]), iso(T[reading]["anchor"][-1])], "n": len(T[reading]["anchor"])})
    except OT.TargetFormatError as e:
        check(f"T.load_and_validate.{reading}", False, str(e))
if FAILS: done(1)
first = calendar.timegm((2022, 6, 30, 0, 0, 0)); end_full = calendar.timegm((2026, 9, 18, 20, 0, 0)); ax = T["scaled"]["anchor"]
last = end_full if int(ax[-1]) >= end_full else int(ax[-1])
win = np.arange(first, last + 1, H4, dtype=np.int64)
check("T.window_on_targets_axis", int(ax[0]) <= first and int(ax[-1]) >= last, {"window": [iso(first), iso(last)], "targets_axis": [iso(ax[0]), iso(ax[-1])]})
counts = {}
for reading in OT.READINGS:
    try:
        counts[reading] = OT.book_for_window(T[reading], win)[3]
    except OT.TargetFormatError as e:
        check(f"T.window_book.{reading}", False, str(e))
rec["window_counts"] = counts
bcore = info[TAGS[0]]["B_CORE_start"]
try:
    bts = calendar.timegm(time.strptime(bcore, "%Y-%m-%dT%H:%M:%SZ")) if bcore else None
except (TypeError, ValueError):
    bts = None
check("D.full_recipe_start_from_main_receipt", bts is not None and bts % H4 == 0 and first <= bts <= last, {"B_CORE_start": bcore, "tag": TAGS[0]})
if len(TAGS) > 1 or os.path.exists(f"{OB}/receipts/TARGETS_A0_main.json"):
    MJ = json.load(open(f"{OB}/receipts/TARGETS_A0_main.json")) if os.path.exists(f"{OB}/receipts/TARGETS_A0_main.json") else {}
    others = {t: info[t]["B_CORE_start"] for t in TAGS[1:]}
    check("D.B_CORE_start_agrees_across_receipts", all(v == bcore for v in others.values()) and (MJ.get("B_CORE_start", bcore) == bcore),
          {"used": bcore, "other_sources": others, "A0_main_receipt": MJ.get("B_CORE_start")})
if FAILS: done(1)
# ---------------- the frozen A0 config ----------------
C = json.loads(json.dumps(TEMPLATE))
C["config"] = os.path.basename(CFG_OUT)[:-5] if CFG_OUT.endswith(".json") else os.path.basename(CFG_OUT)
C["status"] = "FROZEN before any object-B number of this device (A0 part; pairing with the v4 refit follows)"
C["created_utc"] = rec["utc"]; C["frozen_by"] = {"device": "bt_objb_prerun.py", "sha256": rec["self_sha256"], "receipt": OUTP}
C["window"]["last_anchor"] = iso(last); C["window"]["n_anchors"] = int(len(win)); C["window"]["full_recipe_start"] = bcore
C["window"]["coverage"] = ("full prereg window" if last == end_full else f"targets end at {iso(last)}: the extension segment to 2026-09-18T20Z follows with the extension targets")
C["runs"] = [r for r in C["runs"] if r["arm"] == "OBJB_A0"]
for r in C["runs"]:
    r["targets"]["sources"] = sources
    if SUF: r["tag"] = r["tag"].replace("OBJB_A0|", "OBJB_A0" + SUF + "|", 1)     # its own run directories; the published runs are never touched
C["run_tag_suffix"] = SUF or None
C["launch"]["max_parallel"] = 4
C["pending"] = {"(a) object-B A0 targets": "filled: " + ", ".join(TAGS) + " (gate F lineage checked)", "(b) object-B v4 targets": "not in this config: the v4 runs and the pairing table follow on the lead's go",
                "(c) restored prices to 09-18T20Z": "DONE (pinned)", "(d) full-recipe window start": f"filled from TARGETS_{TAGS[0]}.json B_CORE_start"}
C["objb_lineage"] = {"gate_f_sha256": gate_sha, "gate_f_commit": "d3596aced", "sources": info}
json.dump(C, open(CFG_OUT, "w"), indent=1, ensure_ascii=False)
rec["frozen_config"] = {"path": CFG_OUT, "sha256": OT.sha_file(CFG_OUT), "runs": [r["tag"] for r in C["runs"]], "window": [iso(first), iso(last)], "full_recipe_start": bcore}
done(0)

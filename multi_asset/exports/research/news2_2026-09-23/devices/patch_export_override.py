"""Apply the user-override gate on top of the DERIVED exporter.

The derivation regenerates news2_export_models.py from the NEW_S source, so the override gate cannot live
in the derive table (it is new behaviour, not a substitution). It is applied here as a patch on the
derived base, the same shape as the B-part patcher: every (old, new) pair must occur EXACTLY ONCE, or the
base has moved and the patch refuses rather than half-applying.

usage: python patch_export_override.py <derived_base.py> <out.py> <diff_out.diff>
"""
import difflib, sys

base_p, out_p, diff_p = sys.argv[1:4]
t0 = open(base_p).read()
t = t0

EDITS = [
("""def main():
    man = {"device": os.path.abspath(__file__), "device_sha256": sha(os.path.abspath(__file__)), "utc": iso(time.time()), "links": {}}
    L = man["links"]""",
'''# ---------------------------------------------------------------------------------------------------
# USER OVERRIDE GATE (lead relaying the user ruling, 2026-09-24; RULING_user_NC_s42_override_2026-09-24.md)
#
# The frozen verdict is NO_DEPLOY. The user chose to release s42 ON TOP OF that verdict. This exporter
# therefore refuses to write anything under a non-DEPLOY verdict UNLESS the override is named, its file
# hash is verified, and the seed is exactly s42. When the verdict is DEPLOY the behaviour is unchanged.
#
# The override is a PERMISSION, not a re-judgement: nothing here rewrites the verdict, and the manifest
# carries VERDICT=NO_DEPLOY verbatim plus the ruling sha. Wording that would read as admission
# ("PASS", "admitted", "certified") is kept out of the export status on purpose -- a deploy artefact that
# describes itself as passing would outlive the conversation in which it was an exception.
OVERRIDE_SEED = "s42"


def override_gate(stats_verdict, args):
    """Returns the override record, or raises ExportError. Writes nothing either way."""
    rec = {"stats_VERDICT": stats_verdict, "seed_requested": args.seed,
           "override_path": args.user_override, "override_sha_declared": args.user_override_sha}
    if stats_verdict == "DEPLOY":
        rec["override_required"] = False
        rec["note"] = "verdict is DEPLOY; the override path is not consulted"
        return rec
    rec["override_required"] = True
    if not args.user_override or not args.user_override_sha:
        raise ExportError(f"stats VERDICT={stats_verdict}: --user-override AND --user-override-sha are "
                          f"both required; nothing written")
    if not os.path.exists(args.user_override):
        raise ExportError(f"override file not found: {args.user_override}; nothing written")
    measured = sha(args.user_override)
    rec["override_sha_measured"] = measured
    if measured != args.user_override_sha:
        raise ExportError(f"override sha mismatch: measured {measured} != declared "
                          f"{args.user_override_sha}; nothing written")
    if args.seed != OVERRIDE_SEED:
        raise ExportError(f"the override releases {OVERRIDE_SEED} only; refused seed={args.seed}; "
                          f"nothing written")
    rec["override_verified"] = True
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", default="s42", help="which F10 seed to export; the user override covers s42 only")
    ap.add_argument("--user-override", default=None, help="path to the user ruling that releases export under a non-DEPLOY verdict")
    ap.add_argument("--user-override-sha", default=None, help="the expected sha256 of that file; measured and compared")
    ap.add_argument("--out-dir", default=None, help="deploy output dir (default <W>/deploy); the selftest uses a temp dir")
    ap.add_argument("--manifest", default=None, help="manifest path (default <W>/receipts/P5_DEPLOY_MANIFEST.json)")
    args = ap.parse_args()
    man = {"device": os.path.abspath(__file__), "device_sha256": sha(os.path.abspath(__file__)), "utc": iso(time.time()),
           "argv": list(sys.argv), "links": {}}
    L = man["links"]'''),

('''    L["stats"] = {"path": st_p, "sha256": sha(st_p), "VERDICT": st["VERDICT"], "failing_by_seed": st["failing_by_seed"]}
    # ---- deploy files ----
    out = f"{W}/deploy"; os.makedirs(out, exist_ok=True)''',
'''    L["stats"] = {"path": st_p, "sha256": sha(st_p), "VERDICT": st["VERDICT"], "failing_by_seed": st["failing_by_seed"]}
    # * the gate runs HERE: after the lineage is verified, before anything is written.
    man["user_override"] = override_gate(st["VERDICT"], args)
    man["VERDICT"] = st["VERDICT"]                       # the frozen verdict, verbatim, never rewritten
    man["seed"] = args.seed
    if st["VERDICT"] != "DEPLOY":
        man["USER_OVERRIDE"] = args.user_override_sha
        man["export_status"] = ("FILES_WRITTEN_UNDER_USER_OVERRIDE. This is a permission recorded against "
                                "a NO_DEPLOY verdict, not an admission: no gate was passed and no criterion "
                                "was relaxed. FREEZE section 2 is unamended.")
    # ---- deploy files ----
    out = args.out_dir or f"{W}/deploy"; os.makedirs(out, exist_ok=True)'''),

('''    man["torch"] = torch.__version__; man["numpy"] = np.__version__; man["VERDICT"] = "BOUND"
    json.dump(man, open(f"{W}/receipts/P5_DEPLOY_MANIFEST.json", "w"), indent=1)''',
'''    man["torch"] = torch.__version__; man["numpy"] = np.__version__
    man["lineage_bound"] = True          # was man["VERDICT"]="BOUND"; that key now holds the FROZEN verdict
    # lead: list every exported model file with its path and FULL sha; the install rehearsal takes its
    # shas from here, so this list is the handoff surface, not the log line.
    man["exported_files"] = [{"name": os.path.basename(pth), "path": pth, "sha256": sha(pth),
                              "bytes": os.path.getsize(pth)}
                             for pth in (f"{out}/slow2026.txt", npz)]
    mpath = args.manifest or f"{W}/receipts/P5_DEPLOY_MANIFEST.json"
    json.dump(man, open(mpath, "w"), indent=1)
    print("EXPORT_FILES " + json.dumps(man["exported_files"]), flush=True)'''),

("import os, sys, json, time, hashlib, shutil",
 "import argparse, os, sys, json, time, hashlib, shutil"),
]

for old, new in EDITS:
    n = t.count(old)
    assert n == 1, f"anchor occurs {n} times, expected exactly 1: {old[:70]!r}"
    t = t.replace(old, new)

open(out_p, "w").write(t)
open(diff_p, "w").write("".join(difflib.unified_diff(t0.splitlines(True), t.splitlines(True),
                                                     fromfile="derived_base", tofile="with_override_gate")))
print(f"  {len(EDITS)} edits applied, each anchored exactly once")

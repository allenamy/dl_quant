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
import argparse, hashlib, json, os, re, shutil, subprocess, sys, time

# The producing build must have FINISHED. Found the hard way on 2026-09-23: merge2 OOM'd, was
# restarted, and meanwhile a 2.96 GB NC_FEATURES.npz and a self-consistent NC_FEATURES.json from the
# DEAD attempt sat on disk. Both existed, and the receipt's sha matched that stale file -- so the
# existence check and the sha binding both passed while the real build was still running. Neither
# guard can see this; only the producer's own completion marker can.
BUILD_DONE_MARKER = "BUILD_DONE"

COMPLETION = {
    "pre_king":  {"kind": "log_marker", "marker": BUILD_DONE_MARKER, "producer": "nc merge build"},
    # ★ Match the SCRIPT PATH, not the interpreter. `python3?\s+.*nc_legs\.py` looked right and
    # matched nothing on macOS, where the framework build's argv[0] is ".../MacOS/Python" -- capital
    # P, no "3". A guard that silently matches nothing is a guard that always says "quiesced".
    # Shell wrappers whose command line mentions the script match too; that is deliberate. A live
    # wrapper means the run has not exited, and every match is printed in full so the reader can
    # see what it is instead of inferring from a count (the 2026-09-23 "4 alive" misread).
    "post_king": {"kind": "producer_quiesced", "producer": "nc_legs.py",
                  "pattern": r"nc_legs\.py"},
}

# Each source is a LIST of candidate paths inside the nc root; the first that exists wins and the
# chosen one is recorded. Reason (2026-09-23): the integrator's nc_legs.py is invoked with explicit
# output paths, so where it writes is decided by the CALLER, not by the nc layout -- when it was run
# for this chain it wrote `work/legs.npz` and `work/NC_LEGS_RECEIPT.json` into the NEWS2 root, not
# the nc root. Guessing one path made the step unrunnable; enumerating the candidates in the device
# text keeps the resolution auditable instead of moving files by hand to fit the table.
PHASES = {
    # phase -> [([candidate sources in nc root], destination in news2 root, required)]
    "pre_king": [
        (["work/NC_FEATURES.npz"], "work/NEWS_FEATURES.npz", True),
        (["receipts/NC_FEATURES.json"], "receipts/P2B_FEATURES.json", True),
        (["work/members_hist_all.npz"], "work/members_hist_all.npz", True),
        (["inputs/bundle_config.json"], "inputs/bundle_config.json", True),
    ],
    "post_king": [
        (["work/legs.npz"], "work/legs.npz", True),
        (["receipts/NC_LEGS.json", "work/NC_LEGS_RECEIPT.json"], "receipts/P3_LEGS.json", True),
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
    ap.add_argument("--build-log", default=None,
                    help="the producing build's log; it must contain BUILD_DONE. Default: <nc_root>/logs/nc_build.log")
    ap.add_argument("--allow-incomplete-build", action="store_true",
                    help="stage even though the build log has no BUILD_DONE. Recorded in the receipt as a named "
                         "override; never use it to work around a build that is still running.")
    a = ap.parse_args()
    nc, w2, out_path, phase = a.nc_root, a.news2_root, a.out, a.phase
    rec = {"device": "news2_stage_inputs.py", "self_sha256": sha(os.path.abspath(__file__)),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "phase": phase, "nc_root": nc, "news2_root": w2,
           # 复跑命令逐字进收据 (E-0826 family). The pre_king receipt was written without this and
           # the invocation had to be reconstructed from the source; recording it is not optional.
           "argv": list(sys.argv), "cwd": os.getcwd(),
           "rerun_command": " ".join([sys.executable, os.path.abspath(__file__)] + sys.argv[1:]),
           "phase_note": ("legs depend on the King OOF, so they are staged AFTER King training, not before; "
                          "post_king refuses to run unless pre_king already staged the features")}

    # ★ The completion evidence is PER PHASE, because the two phases have different producers and the
    # producers do not signal completion the same way. Waiving the guard for the phase whose producer
    # happens not to write a build log would be the "零测量也算通过" false green; so each phase gets a
    # check that is actually measurable for ITS producer, and the check that does not apply is printed
    # as NOT_APPLICABLE with a reason rather than silently skipped.
    #   pre_king   producer = the nc merge build, which writes BUILD_DONE into its log  -> log marker
    #   post_king  producer = nc_legs.py, which writes NO log (its output path is chosen by the caller)
    #              -> require that no nc_legs process is still running. A stale artifact from a killed
    #                 attempt is exactly the case where a producer IS still running over it.
    comp = COMPLETION[phase]
    rec["completion_check"] = {"kind": comp["kind"]}
    if comp["kind"] == "log_marker":
        blog = a.build_log or os.path.join(nc, "logs/nc_build.log")
        done = os.path.exists(blog) and comp["marker"] in open(blog, errors="replace").read()
        rec["build_log"] = {"path": blog, "exists": os.path.exists(blog), "has_BUILD_DONE": done}
        rec["completion_check"].update({"path": blog, "marker": comp["marker"], "satisfied": done})
        why = (f"{blog} does not contain {comp['marker']}. Files may exist and their receipt may even "
               f"bind them and still be from a dead attempt (merge2 OOM, 2026-09-23).")
        msg = f"no {comp['marker']} in {blog}"
    else:  # producer_quiesced
        # `pgrep -af` is NOT portable: BSD/macOS pgrep has no -a, so it exits non-zero with EMPTY
        # stdout -- and an empty process list reads as "the producer is quiesced". The guard would
        # then pass on this Mac precisely because it could not measure anything (caught by
        # RED.producer_running, 2026-09-23). `ps -Ao pid=,args=` exists on both, and the match is
        # done here instead of being delegated to a flag that may not exist.
        err = None
        try:
            r = subprocess.run(["ps", "-Ao", "pid=,ppid=,args="], capture_output=True, text=True)
            out = r.stdout if r.returncode == 0 else None
            if out is None:
                err = f"ps exited {r.returncode}: {r.stderr.strip()[:200]}"
        except (FileNotFoundError, OSError) as e:
            out, err = None, f"{type(e).__name__}: {e}"
        rx = re.compile(comp["pattern"])
        alive = excluded = None
        if out is not None:
            rows = []
            for ln in out.splitlines():
                f = ln.split(None, 2)
                if len(f) == 3 and f[0].isdigit() and f[1].isdigit():
                    rows.append((int(f[0]), int(f[1]), f[2]))
            # ★ Exclude THIS process and its ancestors. The command line that launched this device
            # necessarily mentions the pattern (it is written in the invocation, in a wrapper shell,
            # in an ssh command), so a self-match is guaranteed and would refuse every run forever.
            # Walking the ancestor chain excludes exactly those and nothing else -- in particular a
            # sibling wrapper from ANOTHER session still counts as alive, which is the safe direction.
            ppid = {pid: pp for pid, pp, _ in rows}
            anc, cur = {os.getpid()}, os.getpid()
            while cur in ppid and ppid[cur] not in anc and ppid[cur] > 0:
                cur = ppid[cur]; anc.add(cur)
            hits = [(pid, cmd) for pid, _, cmd in rows if rx.search(cmd)]
            alive = [f"{pid} {cmd}".strip() for pid, cmd in hits if pid not in anc]
            excluded = [f"{pid} {cmd}".strip() for pid, cmd in hits if pid in anc]
        # ★ Could-not-measure is NOT quiesced. If ps is unavailable the guard must refuse, not pass.
        done = alive == []
        if alive is None:
            rec["completion_check"]["measurement_error"] = err
        rec["build_log"] = {"path": None, "exists": False, "has_BUILD_DONE": None,
                            "NOT_APPLICABLE": f"{comp['producer']} writes no build log"}
        rec["completion_check"].update({"pattern": comp["pattern"], "producer": comp["producer"],
                                        "matches": alive, "n_matches": (None if alive is None else len(alive)),
                                        "excluded_self_and_ancestors": excluded,
                                        "satisfied": done,
                                        "could_not_measure": out is None})
        why = (f"a {comp['producer']} process is still running ({alive}); its outputs may be mid-write, and a "
               f"receipt binding the current bytes would bind a partial file.")
        msg = f"{comp['producer']} still running: {alive}"
    if not done and not a.allow_incomplete_build:
        rec["VERDICT"] = "REFUSED: the producing build has not finished"
        rec["why"] = why
        rec["staged"] = {}; rec["nothing_was_staged"] = True
        fail(out_path, rec, msg, 5)
    rec["build_completion_override"] = bool(a.allow_incomplete_build and not done)

    missing_prereq = [p for p in PREREQ.get(phase, []) if not os.path.exists(os.path.join(w2, p))]
    if missing_prereq:
        rec["VERDICT"] = "REFUSED: pre_king has not been staged"
        rec["missing_prerequisites"] = missing_prereq
        fail(out_path, rec, f"missing={missing_prereq}", 4)

    # ★ CHECK EVERYTHING FIRST, THEN STAGE. The first version linked what it found and only then
    # refused on what it did not, which leaves a half-staged root behind -- and on 2026-09-23 the live
    # case was worse than untidy: NC_FEATURES.npz existed while merge2 was still writing it (restarted
    # after an OOM) and its receipt did not exist yet, so the old order would have hard-linked a
    # PARTIALLY WRITTEN 3 GB file and hashed it. A refusal whose side effects already happened is not
    # a refusal.
    def resolve(cands):
        """First existing candidate, or None. Returns (chosen, [all candidates tried])."""
        for c in cands:
            if os.path.exists(os.path.join(nc, c)):
                return c, list(cands)
        return None, list(cands)

    resolved = {dst: resolve(cands) for cands, dst, _ in PHASES[phase]}
    missing = [{"candidates": [os.path.join(nc, c) for c in resolved[dst][1]], "dest": dst}
               for cands, dst, required in PHASES[phase] if required and resolved[dst][0] is None]
    if missing:
        rec["VERDICT"] = "REFUSED: required inputs missing"
        rec["missing"] = missing
        rec["staged"] = {}
        rec["nothing_was_staged"] = True
        fail(out_path, rec, f"missing={[m['candidates'] for m in missing]}", 2)

    staged = {}
    for cands, dst, required in PHASES[phase]:
        src = resolved[dst][0]
        if src is None:
            staged.setdefault("_optional_absent", []).append(cands)
            continue
        s = os.path.join(nc, src); d = os.path.join(w2, dst)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        # ★ The source may already BE the destination (same root, same relative path). The original
        # code unlinked the destination and then linked the source onto it -- with one inode that is
        # `os.remove(legs.npz)` followed by `os.link` on a path that no longer exists: it DESTROYS the
        # artifact it was asked to stage. A staging step must never be able to lose its own input.
        # Detected 2026-09-23 before running, because nc_legs.py had written into the news2 root.
        in_place = os.path.exists(d) and os.path.samefile(s, d)
        if in_place:
            how = "in_place"
        else:
            if os.path.lexists(d):
                os.remove(d)
            try:
                os.link(s, d); how = "hardlink"
            except OSError:
                shutil.copyfile(s, d); how = "copy"
        staged[dst] = {"source": s, "candidates": resolved[dst][1], "source_sha256": sha(s),
                       "staged_sha256": sha(d), "how": how}
        assert staged[dst]["source_sha256"] == staged[dst]["staged_sha256"], (dst, "staged bytes differ from source")
    rec["staged"] = staged

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

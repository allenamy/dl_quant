"""DOC_APPROVAL_IDENTITY gate (FX-TRAIN TRN-27, 2026-09-13/16; AUDIT_TRAIN 7e1ecf9a TRN-27; FACT_TABLE_TRN §TRN-27).

WHY: the document a user rules from named `0fe5ec55…` (修订 4) and `b2f9cfd4…` (修订 5) as the STEP2_m approval object while the
file on disk was `d99a9109…`, which is not a typo but two earlier real versions; and its frozen device-sha table was 6/6 stale.
Approving `b2f9cfd4` would have approved a gate that PASSes a member index the exporter crashes on (FACT_TABLE 27.4). A prose
document cannot be kept current by discipline alone, so the objects it names are stated in a machine-checkable DECLARATION BLOCK
and this gate verifies them against the files that are actually on disk.

DECLARATION BLOCK — anywhere in the doc, one statement per line (leading list markers and backticks are ignored):
    APPROVAL_OBJECT   <file-in-device-dir> <sha256 (full 64 hex)>      the object a ruling would approve; must equal the measured file
    SUPERSEDED_OBJECT <file-in-device-dir> <sha256 (full 64 hex)>      an earlier version of that file, named in the doc as history
A truncated sha is refused: a 8-hex prefix is a label, not an identity.

PASS iff all four checks hold (none is skipped because something is absent — an absent declaration is a FAIL, not a skip):
  A1 approval_objects_match_measured   every APPROVAL_OBJECT names a file in DEVICE_DIR whose MEASURED sha equals the stated one
  A2 pending_gates_declared            every month-generic gate source in DEVICE_DIR (v4_gate_*_m.py) whose measured sha is NOT in
                                       the contract's approved list for any gate is declared by exactly one APPROVAL_OBJECT with
                                       that measured sha — i.e. the doc names the object a ruling is actually needed for
  A3 superseded_tokens_declared        every hex token (>= 8) anywhere in the doc that matches an ARCHIVED snapshot
                                       (`<stem>.r<N>_<sha8>.<ext>` whose live sibling `<stem>.<ext>` differs) is covered by a
                                       SUPERSEDED_OBJECT line for that live sibling carrying the snapshot's full sha
  A4 stated_device_shas_are_current    outside the declaration block, a hex token separated from a DEVICE_DIR filename by nothing
                                       but separators (the `file` sha table shape) is a CLAIM about that file and must prefix its
                                       measured sha, unless that exact token is declared SUPERSEDED for it. A sha further along the
                                       same line is reported (nonadjacent_pairs_reported) and never decides the verdict
Hex tokens that match no file in DEVICE_DIR (commit shas, receipt shas, shas of files elsewhere) are REPORTED as
tokens_unresolved and never decide the verdict — the receipt states that boundary rather than hiding it.

Receipt through v4_gate_common.finalize (gate DOC_APPROVAL_IDENTITY; inputs doc / contract): rc 0 iff PASS, else 3.
env (all REQUIRED, no defaults): DOC, DEVICE_DIR, CONTRACT, DOCGATE_PROFILE, DOCGATE_OUT. A missing key or file is a PASS=false
receipt naming it. DOCGATE_PROFILE says what KIND of document this is and there is no default, because the caller must say it:
  ruling     the document a user rules from — all four checks, A2 included
  reference  a config template or design note that merely mentions the objects — A1/A3/A4 apply (what it names must be current),
             A2 is recorded NOT_APPLICABLE with its reason rather than passing silently
"""
import json, os, re, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v4_gate_common import finalize, sha256_file

_OUT = os.environ.get("DOCGATE_OUT")
if not _OUT:
    print("DOCGATE_REFUSED missing DOCGATE_OUT (no receipt path: nothing written)", flush=True)
    sys.exit(3)
_KEYS = ("DOC", "DEVICE_DIR", "CONTRACT", "DOCGATE_PROFILE")
E = {k: os.environ.get(k, "") for k in _KEYS}
INPUTS = {"doc": E["DOC"] or None, "contract": E["CONTRACT"] or None}
_ref = {}
if [k for k in _KEYS if not E[k]]:
    _ref["missing_env"] = [k for k in _KEYS if not E[k]]
_missing = {k: v for k, v in (("doc", E["DOC"]), ("contract", E["CONTRACT"])) if not v or not os.path.isfile(v)}
if not E["DEVICE_DIR"] or not os.path.isdir(E["DEVICE_DIR"]):
    _missing["device_dir"] = E["DEVICE_DIR"] or None
if _missing:
    _ref["missing_files"] = _missing
_PROFILES = ("ruling", "reference")
if E["DOCGATE_PROFILE"] and E["DOCGATE_PROFILE"] not in _PROFILES:
    _ref["bad_profile"] = {"given": E["DOCGATE_PROFILE"], "allowed": list(_PROFILES)}
if _ref:
    print("DOCGATE_REFUSED", json.dumps(_ref), flush=True)
    finalize("DOC_APPROVAL_IDENTITY", {"PASS": False, "REFUSED": _ref}, _OUT, INPUTS)
PROFILE = E["DOCGATE_PROFILE"]

t0 = time.time()
DOC, DEV, CONTRACT = E["DOC"], os.path.abspath(E["DEVICE_DIR"]), E["CONTRACT"]
SNAP = re.compile(r"^(?P<stem>.+?)\.r(?P<n>\d+)_(?P<sha8>[0-9a-f]{8})\.(?P<ext>[^.]+)$")
HEX = re.compile(r"(?<![0-9a-zA-Z])([0-9a-f]{8,64})(?![0-9a-zA-Z])")
DECL = re.compile(r"^[\s>*\-–|`]*(APPROVAL_OBJECT|SUPERSEDED_OBJECT)\s+`?([^\s`]+)`?\s+`?([0-9a-fA-F]+)`?")
MONTH_GATE = re.compile(r"^v4_gate_.*_m\.py$")
# only separators may stand between a filename and the sha that CLAIMS to be its identity (the `file` sha table shape)
ADJACENT = re.compile(r"^[\s`'\"():,;·|=\-]*([0-9a-f]{8,64})(?![0-9a-zA-Z])")

# ---- measured state of the device directory (nothing here is taken from a document or a name) ----
files = sorted(f for f in os.listdir(DEV) if os.path.isfile(os.path.join(DEV, f)))
measured = {f: sha256_file(os.path.join(DEV, f)) for f in files}
snapshots = {}                       # live sibling -> {full_sha: snapshot filename}
for f in files:
    m = SNAP.match(f)
    if not m:
        continue
    live = f"{m.group('stem')}.{m.group('ext')}"
    if live in measured and measured[live] != measured[f]:
        snapshots.setdefault(live, {})[measured[f]] = f
approved = set()
try:
    _c = json.load(open(CONTRACT))
    for _g, _v in (_c.get("gates") or {}).items():
        _a = _v.get("approved_source_sha256")
        approved.update(_a if isinstance(_a, list) else ([_a] if _a else []))
except Exception as _e:                                   # a contract that cannot be read is a FAIL, never a skip
    approved = None
    contract_error = f"{type(_e).__name__}: {_e}"

# ---- the document ----
lines = open(DOC, encoding="utf-8").read().splitlines()
decl_app, decl_sup, decl_lines, decl_bad = {}, {}, set(), []
for i, ln in enumerate(lines, 1):
    m = DECL.match(ln)
    if not m:
        continue
    kind, fname, sha = m.group(1), m.group(2), m.group(3).lower()
    decl_lines.add(i)
    if len(sha) != 64:
        decl_bad.append({"line": i, "kind": kind, "file": fname, "sha": sha,
                         "why": "a truncated sha is a label, not an identity: 64 hex required"})
        continue
    (decl_app if kind == "APPROVAL_OBJECT" else decl_sup).setdefault(fname, []).append({"line": i, "sha": sha})

checks, fails = {}, []


def chk(name, ok, detail):
    checks[name] = dict(detail, ok=bool(ok))
    if not ok:
        fails.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + " " + json.dumps(detail, default=str)[:400], flush=True)


# A1 — every declared approval object equals the measured file
a1 = []
for fname, entries in sorted(decl_app.items()):
    for e in entries:
        if fname not in measured:
            a1.append({"line": e["line"], "file": fname, "why": "not a file in DEVICE_DIR"})
        elif measured[fname] != e["sha"]:
            a1.append({"line": e["line"], "file": fname, "declared": e["sha"][:16], "measured": measured[fname][:16],
                       "why": "declared approval object is not the file on disk"})
chk("A1_approval_objects_match_measured", not a1 and not decl_bad,
    {"n_declared": sum(len(v) for v in decl_app.values()), "violations": a1, "malformed_declarations": decl_bad})

# A2 — every month-generic gate that still needs a ruling is named, exactly once, with its measured sha
a2 = []
pending = [f for f in files if MONTH_GATE.match(f) and not SNAP.match(f)]
if PROFILE == "reference":
    chk("A2_pending_gates_declared", True,
        {"NOT_APPLICABLE": "profile=reference: this document is not the one a ruling is taken from, so it is not required to "
                           "carry the pending approval objects. A1/A3/A4 still apply: what it DOES name must be current.",
         "month_generic_gates": pending})
elif approved is None:
    a2.append({"why": "contract unreadable", "error": contract_error})
else:
    for f in pending:
        if measured[f] in approved:
            continue
        got = decl_app.get(f, [])
        if len(got) != 1:
            a2.append({"file": f, "measured": measured[f][:16], "n_approval_object_lines": len(got),
                       "why": "a gate source awaiting approval must be declared by exactly one APPROVAL_OBJECT line"})
        elif got[0]["sha"] != measured[f]:
            a2.append({"file": f, "measured": measured[f][:16], "declared": got[0]["sha"][:16], "line": got[0]["line"],
                       "why": "the declared object is not the source that would run"})
if PROFILE != "reference":
        chk("A2_pending_gates_declared", not a2,
        {"month_generic_gates": pending, "n_awaiting_approval": None if approved is None else
     len([f for f in pending if measured[f] not in approved]), "violations": a2})

# SUPERSEDED_OBJECT is an exemption, so its own standing is classified and counted: a sha that matches an archived snapshot in
# DEVICE_DIR is VERIFIED history; one that matches nothing is an UNVERIFIABLE claim (older than the archives, or from elsewhere).
# It is never silently accepted as proof — the receipt carries both lists.
sup_by_file = {f: {e["sha"] for e in v} for f, v in decl_sup.items()}
sup_verified, sup_unverifiable = [], []
_all_sha = set(measured.values())
for _f, _v in sorted(decl_sup.items()):
    for _e in _v:
        (sup_verified if _e["sha"] in _all_sha else sup_unverifiable).append(
            {"line": _e["line"], "file": _f, "sha": _e["sha"][:16],
             "archive": next((n for n, h in measured.items() if h == _e["sha"]), None)})
a3, unresolved, token_sites = [], {}, []
snap_sha_to_live = {sha: live for live, d in snapshots.items() for sha in d}
live_prefixes = {f: measured[f] for f in files}
for i, ln in enumerate(lines, 1):
    if i in decl_lines:
        continue
    for tok in HEX.findall(ln):
        hit_snap = [(sha, live) for sha, live in snap_sha_to_live.items() if sha.startswith(tok)]
        if hit_snap:
            for sha, live in hit_snap:
                snap_name = snapshots[live][sha]
                named_as_file = snap_name in ln            # "前身 judge_v4.r4_7f1aa5d6.py" names the ARCHIVE, which is unambiguous
                token_sites.append({"line": i, "token": tok, "file": live, "snapshot": snap_name,
                                    "named_as_archive_file": named_as_file})
                if not named_as_file and sha not in sup_by_file.get(live, set()):
                    a3.append({"line": i, "token": tok, "file": live, "snapshot_sha": sha[:16],
                               "why": "an earlier version of a device file is named without a SUPERSEDED_OBJECT declaration",
                               "text": ln.strip()[:200]})
            continue
        if not any(s.startswith(tok) for s in live_prefixes.values()):
            unresolved.setdefault(tok, []).append(i)
chk("A3_superseded_tokens_declared", not a3,
    {"n_snapshot_mentions": len(token_sites), "violations": a3[:40], "n_violations": len(a3),
     "superseded_declarations_verified_against_an_archive": sup_verified,
     "superseded_declarations_unverifiable": sup_unverifiable,
     "note": "an UNVERIFIABLE superseded declaration still exempts the token; it is counted here so the exemption is visible"})

# A4 — a sha stated next to a device filename is a claim about that file
a4, a4_far = [], []
name_re = re.compile("|".join(sorted((re.escape(f) for f in files), key=len, reverse=True))) if files else None
for i, ln in enumerate(lines, 1):
    if i in decl_lines or name_re is None:
        continue
    for m in name_re.finditer(ln):
        fname = m.group(0)
        window = ln[m.end(): m.end() + 80]
        adj = ADJACENT.match(window)
        if not adj:
            far = HEX.search(window)
            if far and not measured[fname].startswith(far.group(1)):
                a4_far.append({"line": i, "file": fname, "token": far.group(1), "measured": measured[fname][:16],
                               "note": "same line but not adjacent: reported, not a claim about this file"})
            continue
        tok = adj.group(1)
        if measured[fname].startswith(tok):
            continue
        if any(s.startswith(tok) for s in sup_by_file.get(fname, set())):
            continue
        if any(s.startswith(tok) for s in snapshots.get(fname, {})):
            continue                       # reported by A3 instead, with the declaration it is missing
        a4.append({"line": i, "file": fname, "claimed": tok, "measured": measured[fname][:16],
                   "text": ln.strip()[:200]})
chk("A4_stated_device_shas_are_current", not a4,
    {"violations": a4[:40], "n_violations": len(a4), "n_nonadjacent_pairs_reported": len(a4_far),
     "nonadjacent_pairs_reported": a4_far[:20]})

res = {"PASS": not fails, "failed_checks": fails, "checks": checks,
       "doc": DOC, "device_dir": DEV, "contract": CONTRACT, "profile": PROFILE,
       "summary": {"n_device_files": len(files), "n_snapshot_files": sum(len(v) for v in snapshots.values()),
                   "n_declarations": len(decl_lines), "n_tokens_unresolved": len(unresolved)},
       "tokens_unresolved": {k: v[:10] for k, v in sorted(unresolved.items())},
       "tokens_unresolved_note": "hex tokens in the doc that match no file in DEVICE_DIR (commit shas, receipt shas, files "
                                 "elsewhere). They are data, not a verdict: this gate can only speak about files it measured.",
       "wall_s": round(time.time() - t0, 1), "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
print("DOC_APPROVAL_IDENTITY", "PASS" if res["PASS"] else "FAIL", json.dumps(res["summary"]), flush=True)
finalize("DOC_APPROVAL_IDENTITY", res, _OUT, INPUTS)

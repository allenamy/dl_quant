"""FX-TRAIN device (TRN-02, lead ruling FIXPROGRAM §7.2 condition (a)), READ-ONLY: enumerate every file that references a
target directory and decide, per file, whether anything in it binds the DIRECTORY'S IDENTITY (its listing / file set) rather
than individual files. Adding a new file to that directory is a pure append ONLY IF no such binding exists anywhere.

Hazard classes (a hit is a CANDIDATE for manual adjudication, never an automatic verdict):
  H1 dir_level_hash      a hash/digest whose SUBJECT is the directory itself (key like dir_sha256 / tree_hash, a sha keyed by
                         the bare directory path, or a shell hash over the directory or a glob in it)
  H2 dir_enumeration     code that lists the directory (listdir / glob / scandir / iterdir / os.walk / find / ls / tar / du)
  H3 file_set_assertion  a recorded or asserted FILE SET of the directory (a listing array, a path->sha manifest, an
                         "unlisted_files" / n_files / set-equality check) — the v4e_gate_export_v2 E1_manifest shape
Structural JSON walk (for every .json that parses) finds H1/H3 without relying on regex spelling.

The detectors are POSITIVE-CONTROLLED before the scan: the device writes five synthetic files into a temp directory it creates
itself (H1, H2 on the target's own line, H2 through a variable defined elsewhere in the file, H3, and one benign per-file sha
reference) and exits 4 DETECTOR_BROKEN unless the four hazards are flagged in the expected class/how and the benign file is
not flagged at all. "Zero hazards found" is meaningless without this, so the scan does not run if the control fails.

iCloud guard (T6): a file whose size > 0 that reads back as 0 bytes is reported ICLOUD_EVICTED and makes the run exit 5; it is
never counted as "does not reference the target".

Reproduction: no environment variable is read (the whitelist is empty and the receipt asserts it); every input is an argument.
usage: python fx_trn02_enumerate_dir_identity.py <out.json> <target_dir>[,<target_dir>...] <root> [<root> ...]
"""
import hashlib, json, os, re, sys, tempfile, time

MAX_BYTES = 64 << 20          # per-file read cap; anything larger is reported in files_skipped_too_large, never silently
CAP_LINES = 40                # matching lines listed per file (counts are always complete)
ENV_WHITELIST = ()            # E-0826: enumerated env whitelist — this device reads NOTHING from the environment
# Read policy: only artifacts that can ASSERT something (receipts, logs, code, docs, tabular text) are read. A binary array
# cannot make an identity claim about a directory. Everything not read is counted and listed BY EXTENSION in the receipt
# (not_read_by_policy) so the boundary is quantified rather than silent.
READ_EXT = {".json", ".jsonl", ".log", ".txt", ".md", ".py", ".sh", ".bash", ".zsh", ".csv", ".tsv", ".yaml", ".yml",
            ".env", ".template", ".diff", ".patch", ".cfg", ".ini", ".toml", ".html", ".sha256", ".sums", ".manifest",
            ".out", ".err", ".rst", ".sql", ".r", ".ipynb", ".lock", ".gitignore"}
NOEXT_MAX = 4 << 20           # extensionless files are read up to this size (scripts, SHA256SUMS, receipts without suffix)

_HEX = re.compile(r"^[0-9a-f]{32,64}$")
_RE_H1_KEY = re.compile(r"(?i)[\"']?[a-z0-9_]*(?:dir|directory|folder|tree|listing)[a-z0-9_]*_?(?:sha256|sha1|sha|hash|digest|md5)[\"']?\s*[:=]")
_RE_H1_KEY2 = re.compile(r"(?i)[\"']?(?:sha256|sha1|sha|hash|digest|md5)_?(?:of_)?(?:dir|directory|folder|tree|listing)[a-z0-9_]*[\"']?\s*[:=]")
# Programmatic enumerators can act on a variable defined elsewhere in the file, so they count at FILE level.
_RE_H2_PROG = re.compile(r"(?i)\b(?:os\.listdir|listdir|scandir|iterdir|os\.walk|glob\.glob|iglob|glob\(|shasum|sha256sum|du\s+-s)")
# Shell words that are also ordinary English ('find', 'ls', 'tar') mean nothing unless the target is on the SAME line.
_RE_H2_SHELL = re.compile(r"(?i)(?:^|[\s;|(`$])(?:find|ls|tar)(?:\s|$)")
_RE_H3 = re.compile(r"(?i)unlisted|\bn_files\b|file_count|num_files|set\(\s*os\.listdir|sorted\(\s*os\.listdir|len\(\s*os\.listdir")


def sha256_and_bytes(path, size):
    """(sha256, data, note). Reads at most MAX_BYTES. Guards the iCloud-evicted short read (T6)."""
    if size > MAX_BYTES:
        return None, None, "too_large"
    with open(path, "rb") as f:
        data = f.read()
    if size > 0 and len(data) == 0:
        return None, None, "ICLOUD_EVICTED"
    if len(data) != size:
        return None, None, f"SHORT_READ {len(data)} != {size}"
    return hashlib.sha256(data).hexdigest(), data, None


def _walk_json(obj, targets, path="$", out=None):
    """Structural hazards in a parsed JSON document: H1 (a sha whose subject is the directory) and H3 (a recorded file set)."""
    if out is None:
        out = []
    if isinstance(obj, dict):
        dir_exact = [(k, v) for k, v in obj.items()
                     if isinstance(v, str) and any(v.rstrip("/") == t.rstrip("/") for t in targets)]
        shas = [(k, v) for k, v in obj.items() if isinstance(v, str) and _HEX.match(v) and re.search(r"(?i)sha|hash|digest", k)]
        if dir_exact and shas:
            out.append({"class": "H1", "how": "structural_json", "at": path,
                        "dir_keys": [k for k, _ in dir_exact], "sha_keys": [k for k, _ in shas]})
        # a key whose value is a path->hex mapping (a manifest of some directory's files)
        for k, v in obj.items():
            if isinstance(v, dict) and len(v) >= 2 and all(isinstance(x, str) and _HEX.match(x) for x in v.values()):
                if dir_exact or any(any(t in str(kk) for t in targets) for kk in v):
                    out.append({"class": "H3", "how": "structural_json_manifest", "at": f"{path}.{k}", "n_entries": len(v)})
        for k, v in obj.items():
            _walk_json(v, targets, f"{path}.{k}", out)
    elif isinstance(obj, list):
        strs = [x for x in obj if isinstance(x, str)]
        if len(strs) >= 2 and len(strs) == len(obj):
            under = [x for x in strs if any(x.startswith(t.rstrip("/") + "/") for t in targets)]
            if len(under) >= 2:
                out.append({"class": "H3", "how": "structural_json_listing", "at": path, "n_entries": len(under),
                            "sample": under[:5]})
        for i, v in enumerate(obj):
            _walk_json(v, targets, f"{path}[{i}]", out)
    return out


def scan_text(text, targets):
    """Per-line hits and regex hazards. A hazard token counts when it shares a LINE with a target reference (line_level),
    and is additionally reported when it merely shares the FILE (file_level, weaker, still adjudicated by hand)."""
    lines = text.splitlines()
    hits, hz = [], []
    ref_lines = [i for i, ln in enumerate(lines, 1) if any(t in ln for t in targets)]
    for i in ref_lines[:CAP_LINES]:
        hits.append({"line": i, "text": lines[i - 1].strip()[:400]})
    refset = set(ref_lines)
    file_h2, file_h3 = [], []
    for i, ln in enumerate(lines, 1):
        m2 = _RE_H2_PROG.search(ln) or (_RE_H2_SHELL.search(ln) and i in refset)
        m3 = _RE_H3.search(ln)
        h1 = _RE_H1_KEY.search(ln) or _RE_H1_KEY2.search(ln)
        if h1:
            hz.append({"class": "H1", "how": "regex_key", "line": i, "text": ln.strip()[:300]})
        if m2:
            if i in refset:
                hz.append({"class": "H2", "how": "line_level", "line": i, "text": ln.strip()[:300]})
            else:
                file_h2.append({"line": i, "text": ln.strip()[:300]})
        if m3:
            if i in refset:
                hz.append({"class": "H3", "how": "line_level", "line": i, "text": ln.strip()[:300]})
            else:
                file_h3.append({"line": i, "text": ln.strip()[:300]})
    for t in targets:
        for i, ln in enumerate(lines, 1):
            if re.search(r"(?:shasum|sha256sum|tar|du\s+-s)[^\n]*" + re.escape(t.rstrip("/")) + r"(?:/\*|/?\s|$)", ln):
                hz.append({"class": "H1", "how": "regex_shell_over_dir", "line": i, "text": ln.strip()[:300]})
    # File-level co-occurrence: the enumerator's ARGUMENT is carried into the receipt so the candidate can be adjudicated
    # from the receipt alone (does it act on the target directory, or on some other path?).
    if ref_lines and file_h2 and not any(h["class"] == "H2" for h in hz):
        hz.append({"class": "H2", "how": "file_level_cooccurrence", "line": None,
                   "text": "enumerator in a file that references the target; its call sites are listed",
                   "n_call_sites": len(file_h2), "call_sites": file_h2[:12]})
    if ref_lines and file_h3 and not any(h["class"] == "H3" for h in hz):
        hz.append({"class": "H3", "how": "file_level_cooccurrence", "line": None,
                   "text": "file-set token in a file that references the target; its sites are listed",
                   "n_call_sites": len(file_h3), "call_sites": file_h3[:12]})
    return hits, hz, len(ref_lines)


def analyse(path, data, targets):
    try:
        text = data.decode("utf-8")
        binary = False
    except UnicodeDecodeError:
        text = data.decode("latin-1")
        binary = True
    hits, hz, n = scan_text(text, targets)
    if path.endswith(".json") and not binary:
        try:
            hz += _walk_json(json.loads(text), targets)
        except Exception as e:
            hz.append({"class": "NOTE", "how": "json_parse_failed", "line": None, "text": str(e)[:200]})
    return hits, hz, n, binary


def positive_control(targets):
    """Three synthetic hazards must be flagged and one benign per-file reference must not. Returns (ok, detail)."""
    t = targets[0].rstrip("/")
    d = tempfile.mkdtemp(prefix="fx_trn02_ctl_")
    files = {
        "ctl_h1.json": json.dumps({"root": t, "dir_sha256": "a" * 64, "built_utc": "2026-09-13T00:00:00Z"}, indent=1),
        "ctl_h2.py": f'import os\nfor f in sorted(os.listdir("{t}")):\n    print(f)\n',
        "ctl_h2_file.py": f'import os\nPATCH = "{t}/raw_patch.npz"\nD = os.environ["SOMEWHERE"]\nfor f in os.listdir(D):\n    print(f)\n',
        "ctl_h3.json": json.dumps({"root": t, "files": [f"{t}/a.npz", f"{t}/b.npz", f"{t}/c.npz"]}, indent=1),
        "ctl_neg.json": json.dumps({"raw_patch": f"{t}/raw_patch.npz", "raw_patch_sha256": "b" * 64}, indent=1),
    }
    got = {}
    for name, body in files.items():
        p = os.path.join(d, name)
        with open(p, "w") as f:
            f.write(body)
        _, hz, _, _ = analyse(p, body.encode(), targets)
        got[name] = sorted({(h["class"], h["how"]) for h in hz})
    def has(name, cls, how=None):
        return any(c == cls and (how is None or h == how) for c, h in got[name])
    ok = (has("ctl_h1.json", "H1") and has("ctl_h2.py", "H2", "line_level")
          and has("ctl_h2_file.py", "H2", "file_level_cooccurrence") and has("ctl_h3.json", "H3")
          and not [c for c, _ in got["ctl_neg.json"] if c in ("H1", "H2", "H3")])
    for name in files:
        os.remove(os.path.join(d, name))
    os.rmdir(d)
    return ok, {"tmpdir": d, "flagged": {k: [f"{c}/{h}" for c, h in v] for k, v in got.items()},
                "expected": {"ctl_h1.json": "H1", "ctl_h2.py": "H2/line_level",
                             "ctl_h2_file.py": "H2/file_level_cooccurrence", "ctl_h3.json": "H3", "ctl_neg.json": "none"}}


def main(argv):
    if len(argv) < 4:
        print(__doc__.strip().splitlines()[-1], flush=True)
        return 2
    out, targets, roots = argv[1], [t for t in argv[2].split(",") if t], argv[3:]
    self_sha = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
    res = {"device": os.path.abspath(__file__), "self_sha256": self_sha,
           "config": {"targets": targets, "roots": [os.path.abspath(r) for r in roots], "max_bytes": MAX_BYTES,
                      "cap_lines": CAP_LINES, "read_ext": sorted(READ_EXT), "noext_max": NOEXT_MAX, "hostname": os.uname().nodename, "python": sys.version.split()[0]},
           "env_whitelist": list(ENV_WHITELIST),
           "env_whitelist_assertion": "this device reads no environment variable; every input is a command-line argument",
           "env_names_present": sorted(os.environ.keys()),
           "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    ok, detail = positive_control(targets)
    res["positive_control"] = dict(detail, passed=bool(ok))
    print("POSITIVE_CONTROL", "PASS" if ok else "FAIL", json.dumps(detail["flagged"]), flush=True)
    if not ok:
        json.dump(res, open(out, "w"), indent=1)
        print("DETECTOR_BROKEN — scan not run", flush=True)
        return 4
    refs, hazards, skipped_large, evicted, unreadable = [], [], [], [], []
    not_read = {}
    n_files = n_scanned = 0
    t0 = time.time()
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(os.path.abspath(root)):
            dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", ".ipynb_checkpoints")]
            for fn in sorted(filenames):
                p = os.path.join(dirpath, fn)
                if os.path.islink(p) or not os.path.isfile(p):
                    continue
                n_files += 1
                try:
                    size = os.path.getsize(p)
                except OSError as e:
                    unreadable.append({"path": p, "why": str(e)[:200]})
                    continue
                ext = os.path.splitext(fn)[1].lower()
                if not (ext in READ_EXT or (ext == "" and size <= NOEXT_MAX)):
                    e_ = not_read.setdefault(ext or "<no extension>", {"n": 0, "bytes": 0})
                    e_["n"] += 1
                    e_["bytes"] += size
                    continue
                try:
                    sha, data, note = sha256_and_bytes(p, size)
                except OSError as e:
                    unreadable.append({"path": p, "why": str(e)[:200]})
                    continue
                if note == "too_large":
                    skipped_large.append({"path": p, "bytes": size})
                    continue
                if note == "ICLOUD_EVICTED" or (note or "").startswith("SHORT_READ"):
                    evicted.append({"path": p, "bytes": size, "why": note})
                    continue
                n_scanned += 1
                if not any(t.encode() in data for t in targets):
                    continue
                hits, hz, n_ref, binary = analyse(p, data, targets)
                rec = {"path": p, "bytes": size, "sha256": sha, "binary": binary, "n_reference_lines": n_ref,
                       "reference_lines": hits}
                refs.append(rec)
                for h in hz:
                    hazards.append(dict(h, path=p, sha256=sha))
    by_class = {}
    for h in hazards:
        by_class.setdefault(h["class"], []).append(h)
    res.update({
        "counts": {"files_walked": n_files, "files_scanned": n_scanned, "files_referencing_target": len(refs),
                   "files_skipped_too_large": len(skipped_large), "files_icloud_evicted_or_short": len(evicted),
                   "files_unreadable": len(unreadable),
                   "files_not_read_by_policy": sum(v["n"] for v in not_read.values()),
                   "bytes_not_read_by_policy": sum(v["bytes"] for v in not_read.values()),
                   "hazard_candidates": len(hazards),
                   "hazard_candidates_by_class": {k: len(v) for k, v in sorted(by_class.items())},
                   "files_with_hazard_candidates": len({h["path"] for h in hazards})},
        "files_skipped_too_large": skipped_large, "files_icloud_evicted_or_short": evicted, "files_unreadable": unreadable,
        "not_read_by_policy": dict(sorted(not_read.items(), key=lambda kv: -kv[1]["n"])),
        "hazard_candidates": hazards, "references": refs,
        "verdict_rule": "NO directory-level binding may be claimed until every hazard candidate below is adjudicated by reading "
                        "the file; this device reports candidates, it does not issue the verdict",
        "wall_s": round(time.time() - t0, 1),
        "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(res, open(out, "w"), indent=1)
    print("FX_TRN02_DIRID_DONE " + json.dumps(res["counts"]) + f" -> {out}", flush=True)
    if evicted:
        print(f"ICLOUD_EVICTED_OR_SHORT {len(evicted)} files — enumeration is INCOMPLETE", flush=True)
        return 5
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

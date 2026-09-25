#!/usr/bin/env python3
"""write_point_census.py — READ-ONLY survey for E-0925-A (a write truncated silently by a full disk / quota, followed by "sha of the file on
disk into the receipt", certifies a damaged artefact). For every non-test .py under the given roots, every WRITE SITE is listed with:
  kind      open-w / open-a (append) / open-x / json.dump / np.save / np.savez / np.savez_compressed / torch.save / pickle.dump /
            write_text / write_bytes / to_csv / to_parquet / shutil.copy* / np.ndarray.tofile
  atomic    the enclosing function (or module body) calls os.replace / os.rename / Path.replace / Path.rename   (tmp + rename pattern)
  fsync     the enclosing function calls os.fsync
  readback  the enclosing function, AFTER the write line, reads a file back (np.load / json.load / open(.., 'r'/'rb') / pd.read_* /
            a sha helper over a path) — a HEURISTIC for "verify after write"; each hit is listed for a human to confirm
  sha_src   sha256 computations in the function: FILE (hashlib over open(..).read() or a helper named sha*/sha_file*/file_sha* called on a
            path-like argument) vs MEMORY (hashlib over a bytes expression that is not a file read)
Category per site: A = atomic + readback, B = atomic without readback, C = direct (no rename) — APPEND sites are reported as D (append; a
partial last line on a full disk is the failure mode). Heuristic, syntactic; the table is for triage, every production-relevant row is to be
confirmed by reading the line. Nothing is written except the output files.
usage: python3 write_point_census.py <out_prefix> <root> [<root> ...]
"""
import ast, csv, json, os, sys

WRITE_FUNCS = {("np", "save"): "np.save", ("numpy", "save"): "np.save", ("np", "savez"): "np.savez", ("np", "savez_compressed"): "np.savez_compressed",
               ("torch", "save"): "torch.save", ("pickle", "dump"): "pickle.dump", ("json", "dump"): "json.dump", ("shutil", "copy"): "shutil.copy",
               ("shutil", "copy2"): "shutil.copy2", ("shutil", "copyfile"): "shutil.copyfile"}
WRITE_METHODS = {"write_text", "write_bytes", "to_csv", "to_parquet", "tofile"}
READ_FUNCS = {("np", "load"), ("json", "load"), ("pd", "read_csv"), ("pd", "read_parquet"), ("torch", "load"), ("pickle", "load")}


def dotted(n):
    if isinstance(n, ast.Name): return (n.id,)
    if isinstance(n, ast.Attribute): return dotted(n.value) + (n.attr,)
    return ()


def open_mode(call):
    m = None
    if len(call.args) >= 2 and isinstance(call.args[1], ast.Constant): m = call.args[1].value
    for k in call.keywords:
        if k.arg == "mode" and isinstance(k.value, ast.Constant): m = k.value.value
    return m if isinstance(m, str) else ("r" if (len(call.args) < 2 and not any(k.arg == "mode" for k in call.keywords)) else "?")


def scan_scope(body_nodes, src_lines, rel, scope):
    sites, renames, fsyncs, reads, shas = [], [], [], [], []
    for n in body_nodes:
        for c in ast.walk(n):
            if not isinstance(c, ast.Call): continue
            d = dotted(c.func); name = d[-1] if d else ""
            if d in (("open",), ("io", "open")) or (name == "open" and len(d) >= 2 and d[0] not in ("os",)):
                m = open_mode(c)
                if any(x in m for x in "wax"): sites.append((c.lineno, "open-a" if "a" in m else ("open-x" if "x" in m else "open-w"), m))
                elif m in ("r", "rb", "rt"): reads.append(c.lineno)
            elif len(d) >= 2 and (d[-2], d[-1]) in WRITE_FUNCS: sites.append((c.lineno, WRITE_FUNCS[(d[-2], d[-1])], ""))
            elif isinstance(c.func, ast.Attribute) and c.func.attr in WRITE_METHODS: sites.append((c.lineno, c.func.attr, ""))
            if (len(d) >= 2 and d[-2:] in (("os", "replace"), ("os", "rename"))) or (isinstance(c.func, ast.Attribute) and c.func.attr in ("replace", "rename")
                                                                                     and not (d and d[0] in ("str",)) and len(c.args) == 1): renames.append(c.lineno)
            if d[-2:] == ("os", "fsync"): fsyncs.append(c.lineno)
            if len(d) >= 2 and (d[-2], d[-1]) in READ_FUNCS: reads.append(c.lineno)
            if d[-2:] in (("hashlib", "sha256"), ("hashlib", "md5")):
                a = c.args[0] if c.args else None
                src = ast.get_source_segment("\n".join(src_lines), a) if a is not None else ""
                shas.append((c.lineno, "FILE" if (src and ".read()" in src and "open(" in src) else ("MEMORY" if src else "EMPTY(update)")))
            elif name and (name.startswith("sha") or name.startswith("file_sha") or name == "sha_file") and c.args:
                shas.append((c.lineno, "FILE(helper)"))
    # the unclosed-handle idiom: a write whose file object is an open(...) call expression (json.dump(x, open(p, "w")),
    # open(p, "w").write(...), pickle.dump(x, open(..))): the final buffer is flushed by the implicit close at garbage collection,
    # where a write error (ENOSPC) is NOT raised to the caller (measured: gc_close_probe.py)
    idiom = set()
    for n in body_nodes:
        for c in ast.walk(n):
            if not isinstance(c, ast.Call): continue
            d = dotted(c.func)
            if len(d) >= 2 and (d[-2], d[-1]) in (("json", "dump"), ("pickle", "dump")) and len(c.args) >= 2 and isinstance(c.args[1], ast.Call) \
                    and dotted(c.args[1].func)[-1:] == ("open",) and any(x in open_mode(c.args[1]) for x in "wax"):
                idiom.add(c.lineno); idiom.add(c.args[1].lineno)
            if isinstance(c.func, ast.Attribute) and c.func.attr == "write" and isinstance(c.func.value, ast.Call) \
                    and dotted(c.func.value.func)[-1:] == ("open",) and any(x in open_mode(c.func.value) for x in "wax"):
                idiom.add(c.lineno); idiom.add(c.func.value.lineno)
    out = []
    for ln, kind, mode in sites:
        rb = [r for r in reads if r > ln]
        cat = "D" if kind == "open-a" else ("A" if (renames and rb) else ("B" if renames else "C"))
        out.append({"file": rel, "line": ln, "scope": scope, "kind": kind, "mode": mode, "atomic_rename_in_scope": bool(renames),
                    "fsync_in_scope": bool(fsyncs), "readback_after_in_scope": rb[:5], "sha_in_scope": shas[:6], "category": cat,
                    "unclosed_handle_idiom": ln in idiom,
                    "text": src_lines[ln - 1].strip()[:180]})
    return out


def scan_file(path, rel):
    src = open(path).read(); lines = src.splitlines()
    try: tree = ast.parse(src)
    except SyntaxError as e: return [{"file": rel, "line": 0, "scope": "", "kind": "PARSE_ERROR", "category": "?", "text": str(e)[:120]}]
    rows = []
    funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    inner = set()
    for f in funcs:
        for c in ast.walk(f):
            if c is not f and isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef)): inner.add(id(c))
    for f in funcs:
        if id(f) in inner: continue                                # nested functions are scanned inside their parent
        rows += scan_scope([f], lines, rel, f.name)
    mod = [n for n in tree.body if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
        for f in cls.body:
            if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)): rows += scan_scope([f], lines, rel, f"{cls.name}.{f.name}")
    rows += scan_scope(mod, lines, rel, "<module>")
    seen, uniq = set(), []
    for r in rows:
        k = (r["file"], r["line"], r["kind"])
        if k not in seen: seen.add(k); uniq.append(r)
    return uniq


def main():
    outp, roots = sys.argv[1], sys.argv[2:]
    rows = []
    for root in roots:
        root = os.path.abspath(os.path.expanduser(root))
        files = [root] if os.path.isfile(root) else sorted(os.path.join(dp, f) for dp, dn, fs in os.walk(root)
                                                            for f in fs if f.endswith(".py") and not f.startswith("tests_") and not f.startswith("test_")
                                                            and "/venv" not in dp and "__pycache__" not in dp and "/.git" not in dp and "/state/" not in dp + "/")
        for p in files: rows += scan_file(p, p)
    with open(outp + ".csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["category", "unclosed_handle_idiom", "file", "line", "scope", "kind", "mode", "atomic_rename_in_scope", "fsync_in_scope", "readback_after_in_scope", "sha_in_scope", "text"])
        for r in rows: w.writerow([r.get(k) for k in ("category", "unclosed_handle_idiom", "file", "line", "scope", "kind", "mode", "atomic_rename_in_scope", "fsync_in_scope", "readback_after_in_scope", "sha_in_scope", "text")])
    cnt = {}
    for r in rows: cnt[r["category"]] = cnt.get(r["category"], 0) + 1
    cnt["unclosed_handle_idiom_sites"] = len({(r["file"], r["line"]) for r in rows if r.get("unclosed_handle_idiom")})
    json.dump({"roots": roots, "n_sites": len(rows), "by_category": cnt}, open(outp + ".summary.json", "w"), indent=1)
    print("WRITE_POINT_CENSUS", json.dumps({"n_sites": len(rows), "by_category": cnt}))


if __name__ == "__main__":
    main()

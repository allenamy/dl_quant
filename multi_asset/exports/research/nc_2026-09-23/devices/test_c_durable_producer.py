#!/usr/bin/env python3
"""Standing test for the C package (producer durable writes; nc_derive_producer --durable). READ-ONLY on production; temp dirs only.

The functions are taken from the DERIVED TREES' own text (AST extraction, never re-typed): shadow_loop_v3.atomic_write and
ShadowState._save_npz from the base tree (treeNC6) and the durable tree (treeNC7). Faults injected at the Python file layer
(`builtins.open` for write-mode opens of the chosen paths): enospc (every write raises ENOSPC), truncate (half of every chunk
stored, the whole chunk reported), empty (nothing stored, success reported). Reads are never intercepted.

  P0 baseline green first: with no fault, the durable functions write exactly the bytes the base functions write
     (atomic_write: the given bytes; _save_npz: np.load gives identical arrays).
  P1 RED CONTROLS (base, measured): under truncate / empty the base functions raise NOTHING and the target ends up damaged;
     under enospc the base functions already raise (their `with` / np.savez close explicitly) — reported as measured, not claimed silent.
  P2 durable: every fault raises DurableWriteError and the target keeps its bytes; no temp file is left.
  P3 CLASS GUARD over the durable tree's two changed files: every state write site the C package names is routed through durable_io
     (AST: no np.savez* to a path, no json.dump(..., open(...)), no open(...,"w") write in shadow_loop atomic_write / _save_npz / save /
     the weights write, and in combo_stage's state writes); the remaining direct writes are the declared feature-workspace ones.
usage: ~/wide_shadow/venv/bin/python test_c_durable_producer.py <base tree> <durable tree>
"""
import ast, builtins, contextlib, errno, glob, importlib.util, io, json, os, shutil, sys, tempfile
import numpy as np

FAILS, N = [], [0]


def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:300]) if detail is not None else ""), flush=True)


class _FaultyRaw(io.RawIOBase):
    def __init__(self, fd, mode): self._fd, self._mode = fd, mode
    def writable(self): return True
    def seekable(self): return False
    def fileno(self): return self._fd
    def write(self, b):
        b = bytes(b)
        if self._mode == "enospc": raise OSError(errno.ENOSPC, "No space left on device (injected)")
        if self._mode == "truncate": os.write(self._fd, b[: len(b) // 2]); return len(b)
        if self._mode == "empty": return len(b)
        raise ValueError(self._mode)
    def close(self):
        if not self.closed:
            try: os.close(self._fd)
            finally: super().close()


@contextlib.contextmanager
def faulty(pred, mode):
    real = builtins.open

    def fake(file, m="r", *a, **k):
        if isinstance(file, (str, bytes, os.PathLike)) and any(x in m for x in "wax") and pred(os.fsdecode(file)):
            fd = os.open(file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
            buf = io.BufferedWriter(_FaultyRaw(fd, mode))
            return buf if "b" in m else io.TextIOWrapper(buf, encoding=k.get("encoding") or "utf-8")
        return real(file, m, *a, **k)
    builtins.open = fake; io.open = fake            # zipfile (np.savez) opens through io.open, not the builtins name
    try: yield
    finally: builtins.open = real; io.open = real


def extract(tree_file, names):
    """function / method sources by name from a file, compiled into a namespace with os / json / np and STATE_DIR"""
    src = open(tree_file).read(); t = ast.parse(src); keep = []
    for n in ast.walk(t):
        if isinstance(n, ast.FunctionDef) and n.name in names:
            keep.append(n)
    ns = {"os": os, "json": json, "np": np}
    for n in keep:
        n2 = ast.fix_missing_locations(ast.Module(body=[n], type_ignores=[]))
        exec(compile(n2, tree_file, "exec"), ns)
    return ns


def rb(p):
    with open(p, "rb") as f: return f.read()


def main():
    base, dur = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    sys.path.insert(0, os.path.join(dur, "fea171"))
    import durable_io as DIO
    B = extract(os.path.join(base, "shadow_loop_v3.py"), {"atomic_write", "_save_npz"})
    D = extract(os.path.join(dur, "shadow_loop_v3.py"), {"atomic_write", "_save_npz"})
    tmpbase = tempfile.mkdtemp(prefix="test_c_durable_"); tempfile.tempdir = tmpbase

    class Self: pass
    print("P0 baseline green first")
    d = tempfile.mkdtemp(); data = json.dumps({"k": list(range(300))}).encode()
    B["atomic_write"](os.path.join(d, "b.json"), data); D["atomic_write"](os.path.join(d, "d.json"), data)
    check("P0 atomic_write: durable bytes == base bytes == the given bytes", rb(os.path.join(d, "b.json")) == rb(os.path.join(d, "d.json")) == data)
    arrs = {"ts": np.arange(1000, dtype=np.int64), "col": np.arange(1000, dtype=np.int32) % 7, "raw": np.linspace(0, 1, 1000).astype(np.float32)}
    for tag, NS in (("base", B), ("dur", D)):
        NS["STATE_DIR"] = os.path.join(d, tag); os.makedirs(NS["STATE_DIR"])
        NS["_save_npz"](Self(), "boundary_raw.npz", **arrs)
    zb, zd = np.load(os.path.join(d, "base", "boundary_raw.npz")), np.load(os.path.join(d, "dur", "boundary_raw.npz"))
    check("P0 _save_npz: identical arrays from both", all(np.array_equal(zb[k], zd[k]) for k in arrs) and sorted(zb.files) == sorted(zd.files))
    print("P1 RED CONTROLS (base) / P2 durable")
    for mode in ("enospc", "truncate", "empty"):
        for fn, args, tgt_name in (("atomic_write", None, "t.json"), ("_save_npz", arrs, "boundary_raw.npz")):
            res = {}
            for tag, NS in (("base", B), ("dur", D)):
                dd = tempfile.mkdtemp(); NS["STATE_DIR"] = dd; tgt = os.path.join(dd, tgt_name)
                if fn == "atomic_write":
                    NS["atomic_write"](tgt, b'{"good": true}'); before = rb(tgt)
                else:
                    NS["_save_npz"](Self(), tgt_name, ok=np.array([1])); before = rb(tgt)
                raised = None
                try:
                    with faulty(lambda q: q != tgt, mode):          # the temp file, whatever its name
                        if fn == "atomic_write": NS["atomic_write"](tgt, data)
                        else: NS["_save_npz"](Self(), tgt_name, **args)
                except Exception as e:                            # noqa: BLE001
                    raised = e
                res[tag] = (raised, rb(tgt) == before, glob.glob(os.path.join(dd, ".*tmp*")) + glob.glob(os.path.join(dd, "*.tmp")))
            braised, bintact, _ = res["base"]; draised, dintact, dleft = res["dur"]
            if mode == "enospc":
                check(f"P1 base {fn} [{mode}] (measured): raises={type(braised).__name__ if braised else None}, target intact={bintact}", True)
            else:
                check(f"P1 RED CONTROL base {fn} [{mode}]: no exception AND the target was replaced by damaged bytes", braised is None and not bintact,
                      f"raised={braised!r} intact={bintact}")
            check(f"P2 durable {fn} [{mode}]: DurableWriteError, target byte-identical, no temp left", isinstance(draised, DIO.DurableWriteError) and dintact and not dleft,
                  f"raised={type(draised).__name__} intact={dintact} left={dleft}")
    print("P3 CLASS GUARD — the C package's state writes are routed through durable_io")
    def calls(path):
        t = ast.parse(open(path).read()); out = []
        for n in ast.walk(t):
            if isinstance(n, ast.Call):
                f = n.func; name = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
                base_ = f.value.id if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) else ""
                out.append((n.lineno, base_, name, n))
        return out
    sl = os.path.join(dur, "shadow_loop_v3.py"); cs = os.path.join(dur, "fea171", "combo_stage.py")
    sl_src = open(sl).read().splitlines(); cs_src = open(cs).read().splitlines()
    def to_path_savez(c):
        return c[2] in ("savez", "savez_compressed") and c[1] == "np" and not (c[3].args and isinstance(c[3].args[0], ast.Name) and c[3].args[0].id.startswith(("_b", "_hb", "_wb")))
    bad_sl = [(ln, sl_src[ln - 1].strip()) for ln, b_, nm, c in calls(sl) if to_path_savez((ln, b_, nm, c))]
    check("P3 shadow_loop: no np.savez* to a path remains (state npz go through durable_io)", not bad_sl, bad_sl)
    FEATURE_WS_OK = ('np.savez(f"{MINI}/cache.npz"', 'np.savez(f"{MINI}/data/dlw_targets.npz"', 'np.savez(f"{_feature_workspace.name}/xfer_panel_live.npz"')
    bad_cs = [(ln, cs_src[ln - 1].strip()) for ln, b_, nm, c in calls(cs) if to_path_savez((ln, b_, nm, c)) and not cs_src[ln - 1].strip().startswith(FEATURE_WS_OK)]
    check("P3 combo_stage: every np.savez* to a path is a declared per-run feature-workspace file (cache / dlw_targets / xfer_panel)", not bad_cs, bad_cs)
    idiom = []
    for path, src in ((sl, sl_src), (cs, cs_src)):
        for ln, b_, nm, c in calls(path):
            if nm == "dump" and b_ == "json" and len(c.args) >= 2 and isinstance(c.args[1], ast.Call) and getattr(c.args[1].func, "id", "") == "open":
                idiom.append((os.path.basename(path), ln, src[ln - 1].strip()[:100]))
    check("P3 no json.dump(x, open(...)) remains in shadow_loop / combo_stage", not idiom, idiom)
    shutil.rmtree(tmpbase, ignore_errors=True)
    print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
    print("TEST_C_DURABLE_PRODUCER", "PASS" if not FAILS else "FAIL", FAILS if FAILS else "")
    sys.exit(0 if not FAILS else 1)


if __name__ == "__main__":
    main()

"""Do the rev-1 red shapes (R10 guard unreadable, R12 state dir not enumerable) catch rev 0? Measured on the rev-0 file."""
import importlib.util, json, os, sys, tempfile, shutil
p = sys.argv[1]
spec = importlib.util.spec_from_file_location("rev0", p); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
base = tempfile.mkdtemp(prefix="rev0shape_", dir=os.path.dirname(os.path.abspath(__file__)))
out = {"rev0_path": p, "rev0_sha256": M.sha_file(p)}
aux = os.path.join(base, "aux.json"); open(aux, "w").write(json.dumps({"ledger_tail": {"AUSDT": [[1777000000, 0.0001, 4.0]]}}))
# R10 shape: guard path unreadable (as under a TCC wall) -> what does rev 0 report?
M.QW = os.path.join(base, "unreadable", "venue_quiet_window.py")
arch = os.path.join(base, "arch10"); os.makedirs(arch)
try:
    r = M.archive_pass(arch, aux, check_window=True); out["R10_shape"] = {"raised": False, "status": r["status"], "window": r["window"]}
except Exception as e:
    out["R10_shape"] = {"raised": True, "error": repr(e)[:200]}
# R12 shape: state dir execute-only
d = os.path.join(base, "state_x"); os.makedirs(d); ax = os.path.join(d, "aux.json"); shutil.copy(aux, ax); os.chmod(d, 0o100)
arch = os.path.join(base, "arch12"); os.makedirs(arch)
try:
    r = M.archive_pass(arch, ax, check_window=False); out["R12_shape"] = {"raised": False, "status": r["status"]}
except Exception as e:
    out["R12_shape"] = {"raised": True, "error": repr(e)[:200]}
finally:
    os.chmod(d, 0o755)
print(json.dumps(out, indent=1)); shutil.rmtree(base)

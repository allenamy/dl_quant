"""controls for pa_panel_identity v2.2: a 0.5 s axis offset and a non-5m grid must be DIFFERS; identical axes IDENTICAL; an Inf cell is reported."""
import numpy as np, subprocess, sys, json, tempfile, os
DEV = sys.argv[1]; d = tempfile.mkdtemp(); T, N, K = 50, 4, 7; rng = np.random.default_rng(0)
ts = 1700000000 + 300 * np.arange(T, dtype=np.float64); data = rng.normal(size=(T, N, K)).astype(np.float16)
def run(name, rts, rdata):
    np.savez(f"{d}/r_{name}.npz", ts=rts, data=rdata); np.savez(f"{d}/c_{name}.npz", ts=ts, data=data, ch=np.array([f"c{k}" for k in range(K)]), symbols=np.array([f"S{n}" for n in range(N)]))
    r = subprocess.run([sys.executable, DEV, f"{d}/r_{name}.npz", f"{d}/c_{name}.npz", f"{d}/o_{name}.json"], capture_output=True, text=True); assert r.returncode == 0, r.stderr[-500:]
    return json.load(open(f"{d}/o_{name}.json"))
o = run("same", ts.copy(), data.copy()); print("identical axes:", o["VERDICT"], o["axis_checks"]["ok"])
o = run("half", ts + 0.5, data.copy()); print("0.5 s offset:", o["VERDICT"], o["axis_checks"]["producer"])
o = run("grid", ts * 1.0 + np.r_[np.zeros(T - 1), 60.0], data.copy()); print("off-grid last step:", o["VERDICT"], o["axis_checks"]["producer"])
dinf = data.copy(); dinf[3, 1, 0] = np.inf; o = run("inf", ts.copy(), dinf); print("inf cell:", o["VERDICT"], o["per_channel"]["c0"]["inf_cells"])
ok = json.load(open(f"{d}/o_same.json"))["VERDICT"].startswith("IDENTICAL") and json.load(open(f"{d}/o_half.json"))["VERDICT"].startswith("DIFFERS") and json.load(open(f"{d}/o_grid.json"))["VERDICT"].startswith("DIFFERS") and json.load(open(f"{d}/o_inf.json"))["VERDICT"].startswith("DIFFERS")
print("RESULT", "4/4 pass" if ok else "FAIL"); sys.exit(0 if ok else 1)

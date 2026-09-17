#!/usr/bin/env python3
"""tests_fp2_builders_v2.py — FP2-8 (2026-09-17): the two derived builders on a SYNTHETIC 5m cache, through their REAL entry (subprocess, real env contract).

Cells (three-state exit: 0 all pass / 1 fail / 3 unavailable):
  D1  derivation is idempotent: re-running derive_fp2_builders_v2.py leaves both v2 files byte-identical (v2 == v1 + named hunks, nothing else)
  K1  king v2 (no mask) ⊇ v1: every v1 anchor is in v2 with FEA row / members / y4 / qvk BITWISE equal; v2 adds anchors with 576<=E<2016 whose features are finite
  K2  (RED CAPABILITY, on the real v1 code) v1's first anchor has E >= 2016 although the grid starts at 576 — the 30-anchor silent drop, reproduced;
      v2's first anchor has E == 576
  K3  king v2 all-True mask == no-mask bitwise (FEA, members)
  K4  king v2 targeted mask (symbol j* False at anchor E*) removes exactly j* from members[E*]; every OTHER anchor's FEA row bitwise unchanged
  K5  king v2 refusals: mask missing an anchor row / symbols reordered / non-bool mask ⇒ exit 3 with MEMBER_MASK_REFUSED, nothing written
  K6  king v2 META self-report carries builder name + member_mask_json with the mask sha256
  T1  DL v2 (no mask) == v1 BITWISE on every array of dlw_targets.npz (v1 already clamps; v2 adds only the mask hook)
  T2  DL v2 all-True mask == no-mask bitwise
  T3  DL v2 targeted mask removes j* from members[E*]; y4s unchanged everywhere (targets do not depend on membership); YR4s changes only at E*
  T4  DL v2 refusals as K5
  T5  DL v2 report carries member_mask.sha256 == sha256(mask file); meta_json carries builder + member_mask
"""
import hashlib, json, os, shutil, subprocess, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); PY = sys.executable
FAILS, N = [], [0]
def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:240]) if detail is not None else ""), flush=True)
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()

# ── D1 derivation idempotence ──────────────────────────────────────────────────────────────────────────────────────
before = {f: sha(os.path.join(HERE, f)) for f in ("pod_fea_ext_clamp_v2.py", "pod_dlw_targets_raw_v2.py")}
r = subprocess.run([PY, os.path.join(HERE, "derive_fp2_builders_v2.py")], capture_output=True, text=True)
after = {f: sha(os.path.join(HERE, f)) for f in before}
if r.returncode != 0:
    print("UNAVAILABLE: derivation refused —", r.stdout, r.stderr); sys.exit(3)
check("D1 derive_fp2_builders_v2.py re-run leaves both v2 files byte-identical (unchanged ×2 in its output)", before == after and r.stdout.count("(unchanged)") == 2, r.stdout.strip())

# ── synthetic cache / panels ───────────────────────────────────────────────────────────────────────────────────────
TMP = tempfile.mkdtemp(prefix="fp2b_"); rng = np.random.default_rng(20260917)
TT, NW = 8000, 80; TS0 = 1640995200; CTS = TS0 + 300 * np.arange(TT, dtype=np.int64)
syms = ["BTCUSDT"] + ["S%02dUSDT" % i for i in range(1, NW)]
ret = rng.normal(0, 0.005, (TT, NW)).astype(np.float32); ret[:1000, NW - 1] = np.nan     # one late-listing name
D = np.empty((TT, NW, 7), np.float16)
D[:, :, 0] = ret; D[:, :, 1] = rng.uniform(0, 0.02, (TT, NW)); D[:, :, 2] = rng.uniform(0, 1, (TT, NW)); D[:, :, 3] = rng.normal(10, 1, (TT, NW))
D[:, :, 4] = rng.normal(5, 0.5, (TT, NW)); D[:, :, 5] = rng.normal(5, 1, (TT, NW)); D[:, :, 6] = rng.uniform(0, 1, (TT, NW)); D[:1000, NW - 1, :] = np.nan
CH = np.array(["ret5", "range", "cpos", "log_qv", "log_cnt", "log_avgsz", "tbf"])
CACHE = f"{TMP}/cache.npz"; np.savez(CACHE, ts=CTS, symbols=np.array(syms), ch=CH, data=D)
grid = CTS[CTS % 14400 == 0]; nP = len(grid); gi = np.where(CTS % 14400 == 0)[0]
r64 = np.where(np.isfinite(D[:, :, 0].astype(np.float64)), D[:, :, 0].astype(np.float64), 0.0)
Y4 = np.full((nP, NW), np.nan, np.float32)
for k, e in enumerate(gi):
    if e + 48 <= TT: Y4[k] = r64[e:e + 48].sum(0)                     # old panel window [E, E+47]: 47 of 48 bars shared with y4s ⇒ alignment self-check passes @0
KPANEL = f"{TMP}/panel_king.npz"; np.savez(KPANEL, ts=grid, f_fund_ema=rng.normal(0, 1e-4, (nP, NW)).astype(np.float32), f_fund_now=rng.normal(0, 1e-4, (nP, NW)).astype(np.float32))
DPANEL = f"{TMP}/panel_dl.npz"
np.savez(DPANEL, ts=grid, symbols=np.array(syms), Y4=Y4, **{k: rng.normal(0, 1, (nP, NW)).astype(np.float32) for k in ("f_rev_4h", "f_rev_24h", "f_vol_7d", "f_range_24h", "f_mom_7d", "f_fund_ema")})
os.makedirs(f"{TMP}/shim", exist_ok=True)
open(f"{TMP}/shim/zload.py", "w").write(
    "import zipfile, io\nimport numpy as np\nclass _Z(dict):\n    @property\n    def files(self): return list(self.keys())\n"
    "def zload(path, **kw):\n    z = zipfile.ZipFile(path); out = _Z()\n    for n in z.namelist():\n        key = n[:-4] if n.endswith('.npy') else n\n"
    "        with z.open(n) as f: out[key] = np.lib.format.read_array(io.BytesIO(f.read()), allow_pickle=True)\n    return out\n")   # = pod2 /workspace/zload.py

def mask_file(name, mask, ts=grid, symbols=syms):
    p = f"{TMP}/{name}.npz"; np.savez(p, ts=np.asarray(ts), symbols=np.array(symbols), mask=mask, definition=np.array("synthetic " + name)); return p

def run(script, env, tag):
    out = f"{TMP}/{tag}"; os.makedirs(out, exist_ok=True)
    e = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", TMP), "PYTHONPATH": f"{TMP}/shim", "OMP_NUM_THREADS": "1"}; e.update(env)   # real HOME: /usr/bin/python3 numpy is a user-site install
    if script.startswith("pod_fea"): e.update(FEA_OUT=f"{out}/fea.npy", META_OUT=f"{out}/meta.npz", CACHE_IN=CACHE, PANEL_IN=KPANEL)
    else: e.update(DLWT_CACHE=CACHE, DLWT_PANEL=DPANEL, DLWT_OUT=out, DLWT_RET_CH="0", DLWT_RAW_PATCH="")
    r = subprocess.run([PY, os.path.join(HERE, script)], env=e, cwd=TMP, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr, out

def king_load(out):
    M = np.load(f"{out}/meta.npz", allow_pickle=True); F = np.load(f"{out}/fea.npy")
    return {"E_ts": M["E_ts"].astype(np.int64), "members": list(M["members"]), "y4": M["y4"], "qvk": M["qvk"], "FEA": F, "meta": M}
def eq16(a, b): return a.shape == b.shape and np.array_equal(a.view(np.uint16), b.view(np.uint16))
def eqf(a, b): return a.shape == b.shape and np.array_equal(np.asarray(a).view(np.uint8) if a.dtype == object else a.view(np.uint8), b.view(np.uint8)) if a.dtype != object else all(np.array_equal(x, y) for x, y in zip(a, b))

print("[K] king builder v1 vs v2 on the synthetic cache")
rc1, o1, out1 = run("pod_fea_ext_clamp.py", {}, "k_v1"); rc2, o2, out2 = run("pod_fea_ext_clamp_v2.py", {}, "k_v2")
if rc1 or rc2: print("UNAVAILABLE: builder run failed", rc1, rc2, o1[-800:], o2[-800:]); sys.exit(3)
K1, K2 = king_load(out1), king_load(out2)
E1 = (K1["E_ts"] - TS0) // 300; E2 = (K2["E_ts"] - TS0) // 300
row2 = {int(t): i for i, t in enumerate(K2["E_ts"])}
common = [(i, row2[int(t)]) for i, t in enumerate(K1["E_ts"]) if int(t) in row2]
check("K1a every v1 anchor is present in v2", len(common) == len(K1["E_ts"]) and len(K1["E_ts"]) > 100, (len(K1["E_ts"]), len(K2["E_ts"])))
check("K1b on common anchors FEA rows, members, y4, qvk are BITWISE equal",
      all(eq16(K1["FEA"][i], K2["FEA"][j]) and np.array_equal(K1["members"][i], K2["members"][j]) and np.array_equal(K1["y4"][i].view(np.uint32), K2["y4"][j].view(np.uint32))
          and np.array_equal(K1["qvk"][i].view(np.uint32), K2["qvk"][j].view(np.uint32)) for i, j in common))
extra = [j for j in range(len(E2)) if int(K2["E_ts"][j]) not in {int(t) for t in K1["E_ts"]}]
check("K1c v2 adds exactly the anchors with 576 <= E < 2016 (30 on the real grid; here %d) and their member features are finite" % len(extra),
      len(extra) > 0 and all(576 <= E2[j] < 2016 for j in extra) and all(np.isfinite(K2["FEA"][j][K2["members"][j]].astype(np.float32)).all() for j in extra), (len(extra), [int(E2[j]) for j in extra][:6]))
check("★★★ K2 (RED CAPABILITY, real v1 code) v1's first anchor is E >= 2016 while the grid starts at 576 — the silent drop; v2's first anchor is E == 576",
      int(E1.min()) >= 2016 and int(E2.min()) == 576, (int(E1.min()), int(E2.min())))
rc3, o3, out3 = run("pod_fea_ext_clamp_v2.py", {"MEMBER_MASK_NPZ": mask_file("all_true", np.ones((nP, NW), bool))}, "k_all")
K3 = king_load(out3)
check("K3 all-True mask == no-mask BITWISE (FEA + members)", rc3 == 0 and eq16(K3["FEA"], K2["FEA"]) and all(np.array_equal(a, b) for a, b in zip(K3["members"], K2["members"])), rc3)
jstar, istar = 7, 40; Estar = int(K2["E_ts"][istar]); mk = np.ones((nP, NW), bool); mk[int(np.where(grid == Estar)[0][0]), jstar] = False
rc4, o4, out4 = run("pod_fea_ext_clamp_v2.py", {"MEMBER_MASK_NPZ": mask_file("targeted", mk)}, "k_tgt"); K4 = king_load(out4)
others_same = all(eq16(K4["FEA"][i], K2["FEA"][i]) for i in range(len(E2)) if i != istar)
check("K4 targeted mask: j* removed from members[E*] (was present), every OTHER anchor's FEA row bitwise unchanged",
      rc4 == 0 and jstar in K2["members"][istar] and jstar not in K4["members"][istar] and set(K4["members"][istar]) == set(K2["members"][istar]) - {jstar} and others_same, rc4)
_drop = int(np.where(grid == int(K2["E_ts"][20]))[0][0])   # a row that IS an anchor (grid[0] is E=0, never an anchor: anchors start at E=576)
bad = {"missing anchor row": mask_file("miss", np.delete(np.ones((nP, NW), bool), _drop, 0), ts=np.delete(grid, _drop)),
       "symbols reordered": mask_file("reord", np.ones((nP, NW), bool), symbols=syms[1:] + syms[:1]),
       "non-bool mask": mask_file("int8", np.ones((nP, NW), np.int8))}
for why, p in bad.items():
    rc, o, out = run("pod_fea_ext_clamp_v2.py", {"MEMBER_MASK_NPZ": p}, "k_bad_" + why[:4])
    check(f"K5 refusal ({why}) ⇒ exit 3 + MEMBER_MASK_REFUSED, no FEA written", rc == 3 and "MEMBER_MASK_REFUSED" in o and not os.path.exists(f"{out}/fea.npy"), (rc, o.strip().splitlines()[-1][:120] if o.strip() else ""))
mm = json.loads(str(K4["meta"]["member_mask_json"]))
check("K6 META self-report: builder == pod_fea_ext_clamp_v2.py; member_mask_json.sha256 == sha256(mask file); false_cells == 1",
      str(K4["meta"]["builder"]) == "pod_fea_ext_clamp_v2.py" and mm["sha256"] == sha(f"{TMP}/targeted.npz") and mm["false_cells"] == 1, mm)

print("\n[T] DL targets builder v1 vs v2")
rd1, p1, d1 = run("pod_dlw_targets_raw.py", {}, "d_v1"); rd2, p2, d2 = run("pod_dlw_targets_raw_v2.py", {}, "d_v2")
if rd1 or rd2: print("UNAVAILABLE: DL builder run failed", rd1, rd2, p1[-1200:], p2[-1200:]); sys.exit(3)
def dl_load(out): return np.load(f"{out}/data/dlw_targets.npz", allow_pickle=True)
T1a, T1b = dl_load(d1), dl_load(d2)
def arr_eq(a, b):
    if a.dtype == object: return len(a) == len(b) and all(np.array_equal(x, y) for x, y in zip(a, b))
    return a.shape == b.shape and a.dtype == b.dtype and np.array_equal(a.view(np.uint8), b.view(np.uint8))
keys = [k for k in T1a.files if k != "meta_json"]
check("T1 DL v2 (no mask) == v1 BITWISE on every array (%s)" % ",".join(keys), all(arr_eq(T1a[k], T1b[k]) for k in keys), [k for k in keys if not arr_eq(T1a[k], T1b[k])])
rd3, p3, d3 = run("pod_dlw_targets_raw_v2.py", {"MEMBER_MASK_NPZ": f"{TMP}/all_true.npz"}, "d_all"); T2 = dl_load(d3)
check("T2 DL v2 all-True mask == no-mask BITWISE", rd3 == 0 and all(arr_eq(T2[k], T1b[k]) for k in keys), rd3)
Ets = T1b["E_ts"].astype(np.int64); istar_d = 40; Estar_d = int(Ets[istar_d]); mkd = np.ones((nP, NW), bool); mkd[int(np.where(grid == Estar_d)[0][0]), jstar] = False
rd4, p4, d4 = run("pod_dlw_targets_raw_v2.py", {"MEMBER_MASK_NPZ": mask_file("targeted_dl", mkd)}, "d_tgt"); T3 = dl_load(d4)
yr_other = all(np.array_equal(T3["YR4s"][i].view(np.uint32), T1b["YR4s"][i].view(np.uint32)) for i in range(len(Ets)) if i != istar_d)
check("T3 DL targeted mask: j* removed from members[E*]; y4s bitwise unchanged everywhere; YR4s unchanged at every other anchor and changed at E*",
      rd4 == 0 and jstar in T1b["members"][istar_d] and jstar not in T3["members"][istar_d] and arr_eq(T3["y4s"], T1b["y4s"]) and yr_other
      and not np.array_equal(T3["YR4s"][istar_d].view(np.uint32), T1b["YR4s"][istar_d].view(np.uint32)), rd4)
for why, p in bad.items():
    rc, o, out = run("pod_dlw_targets_raw_v2.py", {"MEMBER_MASK_NPZ": p}, "d_bad_" + why[:4])
    check(f"T4 refusal ({why}) ⇒ exit 3 + MEMBER_MASK_REFUSED, no targets written", rc == 3 and "MEMBER_MASK_REFUSED" in o and not os.path.exists(f"{out}/data/dlw_targets.npz"), (rc,))
rep = json.load(open(f"{d4}/results/dlw_targets_report.json")); meta = json.loads(str(T3["meta_json"]))
check("T5 report.member_mask.sha256 == sha256(mask file); meta_json.builder == pod_dlw_targets_raw_v2.py; meta_json.member_mask.false_cells == 1",
      rep["member_mask"]["sha256"] == sha(f"{TMP}/targeted_dl.npz") and meta.get("builder") == "pod_dlw_targets_raw_v2.py" and meta["member_mask"]["false_cells"] == 1, meta.get("member_mask"))
shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
if FAILS: print("FAILED:", *FAILS, sep="\n  "); sys.exit(1)
print("ALL PASS")

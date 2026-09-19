#!/usr/bin/env python3
"""bt_objb_layout_check.py — the adapter (bt_objb_targets.py 05cc5dc2) against the REAL object-B target-file layout, on a fixture cut from the
real file, before any run on it (lead's go for the A0 part, 2026-09-19 ~21:45Z, "before running" item 1). Reads the real file; writes only
into this device's own scratch folder; never into the object-B folder. No simulation.

  L0  the real npz / receipt equal the shas pinned in the frozen A0 run config (every run's targets.sources)
  L1  SCHEMA: the real file's key set, dtype and ndim per key == the adapter test's fixture (TARGETS_FIX_full.npz, which the 30/30 adapter
      test ran on); the CSR relations hold in both; the receipt carries every field the adapter reads
  L2  REAL-LAYOUT FIXTURE: a contiguous slice of the real file (all three readings, real dtypes, rebased offsets) is written as a fixture with
      its own receipt; the adapter (load_targets → book_for_window) on it == an independent dense decode of the SAME rows of the real
      arrays, bitwise (weights, fresh, kind), for all three readings
  L3  the adapter on the FULL real file over the A0 window == the independent decode, bitwise, all three readings; per-kind counts ==
      the pre-run receipt's window counts
  mutations (each must be red): fixture with a key removed / a kind 3 / a pinned sha that differs → refused with the named reason;
      the independent reference with one weight changed → the equality goes red
Baselines are evaluated first; exit 0 only if every baseline is green and every mutation red.
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B bt_objb_layout_check.py PATH,HOME,LC_CTYPE <frozen_A0_config.json>
         <adapter_fixture_npz> <prerun_receipt.json> <scratch_dir> <out.json>
"""
import os, sys, json, time, hashlib, copy
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
import numpy as np

T0 = time.time()
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt_objb_targets as OT
CFG_P, FIX_NPZ, PRERUN_P, SCR, OUTP = sys.argv[2:7]
CFG = json.load(open(CFG_P)); PRERUN = json.load(open(PRERUN_P))
assert "object_b" not in os.path.abspath(SCR), "the scratch fixture never goes into the object-B folder"
os.makedirs(SCR, exist_ok=True)
RES = []
H4 = 14400; NSYM = 829


def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)
def ok(name, cond, detail=None):
    RES.append(dict(check=name, ok=bool(cond), detail=detail)); log(("PASS " if cond else "FAIL ") + name, json.dumps(detail, default=str)[:260] if detail is not None else "")
def mut(name, red, detail=None): ok("[mutation red] " + name, red, detail)
def sha(p): return OT.sha_file(p)
def ts(iso): return int(np.datetime64(iso.replace("Z", ""), "s").astype(np.int64))


def refuses(fn, reason):
    try:
        fn(); return False, "no error"
    except OT.TargetFormatError as e:
        return str(e).startswith(reason), str(e)[:160]


def decode(Z, reading, rows):
    """INDEPENDENT dense decode (does not call the adapter): rows = positions on the file's own axis"""
    off = np.asarray(Z[f"{reading}_off"], np.int64); idx = np.asarray(Z[f"{reading}_idx"]).astype(np.int64); val = np.asarray(Z[f"{reading}_val"], np.float64)
    kind = np.asarray(Z[f"{reading}_kind"]).astype(np.int8)
    W = np.zeros((len(rows), NSYM), np.float64)
    lens = np.diff(off)
    for r, k in enumerate(rows):
        a = off[k]; W[r, idx[a:a + lens[k]]] = val[a:a + lens[k]]
    return W, kind[rows] > 0, kind[rows]


runs = [r for r in CFG["runs"] if (r.get("targets") or {}).get("source") == "objb"]
srcs = {json.dumps(r["targets"]["sources"], sort_keys=True) for r in runs}
ok("L0.one_source_list_across_runs", len(srcs) == 1, len(srcs))
SRC = runs[0]["targets"]["sources"]
ok("L0.single_main_source", len(SRC) == 1, [s["npz"] for s in SRC])
S = SRC[0]
ok("L0.real_npz_sha_equals_pin", sha(S["npz"]) == S["npz_sha256"], S["npz_sha256"][:16])
ok("L0.real_receipt_sha_equals_pin", sha(S["receipt"]) == S["receipt_sha256"], S["receipt_sha256"][:16])
REAL = np.load(S["npz"], allow_pickle=False); FIX = np.load(FIX_NPZ, allow_pickle=False); RR = json.load(open(S["receipt"]))


def schema(Z): return {k: (str(Z[k].dtype), Z[k].ndim) for k in Z.files}


sr, sf = schema(REAL), schema(FIX)
ok("L1.key_set_equal", set(sr) == set(sf), dict(only_real=sorted(set(sr) - set(sf)), only_fixture=sorted(set(sf) - set(sr))))
ok("L1.dtype_and_ndim_equal_per_key", all(sr[k] == sf[k] for k in set(sr) & set(sf)), {k: dict(real=sr[k], fixture=sf.get(k)) for k in sorted(sr)})


def csr_ok(Z):
    n = len(Z["anchor"]); out = {}
    for R in OT.READINGS:
        off = Z[f"{R}_off"]
        out[R] = bool(len(Z[f"{R}_kind"]) == n and len(off) == n + 1 and off[0] == 0 and np.all(np.diff(off) >= 0) and off[-1] == len(Z[f"{R}_idx"]) == len(Z[f"{R}_val"]))
    return out


ok("L1.csr_relations_real", all(csr_ok(REAL).values()), csr_ok(REAL))
ok("L1.csr_relations_fixture", all(csr_ok(FIX).values()), csr_ok(FIX))
need_rc = ["targets_npz_sha256", "arm", "B_CORE_start", "PRE_window", "tag", "data", "axis"]
ok("L1.receipt_fields_the_adapter_reads", all(k in RR for k in need_rc), {k: (k in RR) for k in need_rc})

# ---- L2: real-layout fixture = a contiguous slice of the real file across the full-recipe boundary
A = np.asarray(REAL["anchor"], np.int64); pos = {int(a): i for i, a in enumerate(A)}
b_core = ts(RR["B_CORE_start"]); i0 = pos[b_core] - 150; i1 = pos[b_core] + 150        # 300 anchors: 150 PARTIAL + 150 FULL
sl = np.arange(i0, i1)


def write_slice(name, tamper=None, rc_tamper=None):
    arrs = {"anchor": A[i0:i1].copy()}
    for R in OT.READINGS:
        off = np.asarray(REAL[f"{R}_off"], np.int64); a, b = off[i0], off[i1]
        arrs[f"{R}_kind"] = np.asarray(REAL[f"{R}_kind"])[i0:i1].copy(); arrs[f"{R}_off"] = (off[i0:i1 + 1] - a).astype(REAL[f"{R}_off"].dtype)
        arrs[f"{R}_idx"] = np.asarray(REAL[f"{R}_idx"])[a:b].copy(); arrs[f"{R}_val"] = np.asarray(REAL[f"{R}_val"])[a:b].copy()
    if tamper: tamper(arrs)
    p = os.path.join(SCR, f"TARGETS_RL_{name}.npz"); np.savez(p, **arrs)
    rc = dict(tag=f"RL_{name}", arm="A0", data=RR.get("data"), axis=RR.get("axis"), B_CORE_start=RR["B_CORE_start"], PRE_window=RR.get("PRE_window"),
              targets_npz_sha256=sha(p), fixture_of=dict(npz=S["npz"], npz_sha256=S["npz_sha256"], rows=[int(i0), int(i1)]))
    if rc_tamper: rc_tamper(rc)
    q = os.path.join(SCR, f"TARGETS_RL_{name}.json"); json.dump(rc, open(q, "w"), indent=1)
    return dict(npz=p, npz_sha256=sha(p), receipt=q, receipt_sha256=sha(q))


FXS = write_slice("base")
ok("L2.fixture_schema_equals_real", schema(np.load(FXS["npz"])) == sr, schema(np.load(FXS["npz"])))
WIN = A[i0:i1]
l2 = {}; refW = {}
for R in OT.READINGS:
    T = OT.load_targets([FXS], reading=R, arm="A0")
    W, fresh, kind, cnt = OT.book_for_window(T, WIN)
    W2, fresh2, kind2 = decode(REAL, R, sl); refW[R] = (W2, fresh2, kind2)
    l2[R] = dict(W=bool(np.array_equal(W, W2)), fresh=bool(np.array_equal(fresh, fresh2)), kind=bool(np.array_equal(kind, kind2)), counts=cnt)
    ok(f"L2.adapter_on_real_layout_fixture_equals_independent_decode.{R}", l2[R]["W"] and l2[R]["fresh"] and l2[R]["kind"], l2[R])
kinds_seen = sorted(set(np.concatenate([refW[R][2] for R in OT.READINGS]).tolist()))
ok("L2.fixture_exercises_king_and_combo_rows", {1, 2} <= set(kinds_seen), kinds_seen)

# ---- L3: the full real file over the A0 window
w0, w1 = ts(CFG["window"]["first_anchor"]), ts(CFG["window"]["last_anchor"])
WINF = np.arange(w0, w1 + 1, H4, dtype=np.int64); rowsF = np.array([pos[int(a)] for a in WINF])
l3 = {}
for R in OT.READINGS:
    T = OT.load_targets(SRC, reading=R, arm="A0")
    W, fresh, kind, cnt = OT.book_for_window(T, WINF)
    W2, fresh2, kind2 = decode(REAL, R, rowsF)
    want = PRERUN["window_counts"][R]
    l3[R] = dict(W=bool(np.array_equal(W, W2)), fresh=bool(np.array_equal(fresh, fresh2)), kind=bool(np.array_equal(kind, kind2)), counts=cnt, prerun_counts=want)
    ok(f"L3.adapter_on_full_real_file_equals_independent_decode.{R}", l3[R]["W"] and l3[R]["fresh"] and l3[R]["kind"], {k: v for k, v in l3[R].items() if k != "prerun_counts"})
    ok(f"L3.counts_equal_prerun_receipt.{R}", cnt == want, dict(got=cnt, prerun=want))
    if R == "scaled": W_main_ref = W2

# ---- mutations
def m_miss(a): del a["scaled_off"]
def m_kind3(a): a["scaled_kind"][0] = 3
r_, d_ = refuses(lambda: OT.load_targets([write_slice("m_missing_key", tamper=m_miss)], reading="scaled"), "missing_keys"); mut("fixture without scaled_off refused (missing_keys)", r_, d_)
r_, d_ = refuses(lambda: OT.load_targets([write_slice("m_kind3", tamper=m_kind3)], reading="scaled"), "kind_out_of_range"); mut("fixture with kind 3 refused (kind_out_of_range)", r_, d_)
bad = dict(FXS, npz_sha256="0" * 64)
r_, d_ = refuses(lambda: OT.load_targets([bad], reading="scaled"), "npz_sha_mismatch_vs_pin"); mut("pinned sha differs from the fixture → refused (npz_sha_mismatch_vs_pin)", r_, d_)
T = OT.load_targets([FXS], reading="scaled"); W, *_ = OT.book_for_window(T, WIN)
Wm = refW["scaled"][0].copy(); nz = np.argwhere(Wm != 0)[0]; Wm[tuple(nz)] = Wm[tuple(nz)] * (1 + 1e-12)
mut("independent reference with one weight changed (×(1+1e-12)) → equality red", not np.array_equal(W, Wm), dict(cell=[int(x) for x in nz]))

fails = [r["check"] for r in RES if not r["ok"]]
out = dict(device="bt_objb_layout_check.py", self_sha256=sha(os.path.abspath(__file__)), adapter_sha256=sha(os.path.join(HERE, "bt_objb_targets.py")),
           argv=sys.argv, numpy=np.__version__, config=dict(path=CFG_P, sha256=sha(CFG_P)), real=dict(npz=S["npz"], npz_sha256=S["npz_sha256"], receipt=S["receipt"],
           receipt_sha256=S["receipt_sha256"]), adapter_test_fixture=dict(path=FIX_NPZ, sha256=sha(FIX_NPZ)), prerun_receipt=dict(path=PRERUN_P, sha256=sha(PRERUN_P)),
           real_layout_fixture=dict(FXS, rows=[int(i0), int(i1)], anchors=[str(np.datetime64(int(WIN[0]), "s")) + "Z", str(np.datetime64(int(WIN[-1]), "s")) + "Z"]),
           checks=RES, failed=fails, VERDICT="PASS" if not fails else "RED", runtime_s=round(time.time() - T0, 1))
json.dump(out, open(OUTP, "w"), indent=1, default=str)
n_ok = sum(r["ok"] for r in RES)
print("BT_OBJB_LAYOUT_CHECK VERDICT: " + ("ALL PASS %d/%d checks (real layout == adapter-test fixture layout; adapter == independent decode; every mutation red)" % (n_ok, len(RES))
      if not fails else "FAILURES %d/%d: %s" % (len(fails), len(RES), fails)), flush=True)
sys.exit(0 if not fails else 3)

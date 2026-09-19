#!/usr/bin/env python3
"""bt_objb_adapter_test.py — test of the object-B target adapter (bt_objb_targets.py) and its wiring into the driver (bt_driver_lib v3), on
FIXTURES ONLY. No object-B output is read: the fixture TARGETS files are written here, in the layout of object_b's b_targets.py (da775552b),
from stream R's S2 books (p2_s2_lib.books — the same books the P2-CMB runs use), so the adapter path and the S2 path must give identical paths.
Every baseline must be green and every mutation red; exit 0 only then.

  F0  fixture layout: the three readings, kinds 2 / 0 (scaled) and 1 (lit) present in the tested window, receipt with the npz sha; loads
      (try1 of this test, receipt BT_OBJB_ADAPTER_TEST_try1.json, had three test-code errors: the fixture writer aliased the shared kind array,
      so the kind-3 mutation leaked into the next case; the weight mutation hit a row before the window; F0 / F2 expected hold and combo rows
      in the S2 LIT book, which is king-form at every anchor of this span)
  F1  EQUIVALENCE (reading 'scaled' ← S2 CMB): the driver with run["targets"]["source"] = "objb" (production load_context → make_sim) gives
      bitwise the same path arrays as the S2-sourced run, 2 seeds, a window crossing the 2025-01 HOLD month (hold semantics exercised)
  F2  EQUIVALENCE (reading 'lit' ← S2 LIT, king-form rows = kind 1): the same, and the king rows are written as target files
  F3  two sources (main + extension segment, contiguous) = one source (W, fresh, kind bitwise)
  F4  universe rows from the universe npz = the S2 runs' PIT rows
  mutations (format; each must raise TargetFormatError with its named reason): npz vs receipt sha, npz vs pin, receipt vs pin, offsets,
      idx range, duplicate column, NaN weight, hold row with weights, kind 3, axis gap, overlapping sources, window outside the axis, unknown
      reading, arm mismatch, missing key, universe sha
  mutations (semantics; the equivalence must go red): kind 0 read as a written file; one weight changed in the fixture
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B bt_objb_adapter_test.py PATH,HOME,LC_CTYPE <config.json> <fixture_dir> <out.json>
"""
import os, sys, json, time, copy, shutil
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
import numpy as np

T0 = time.time()
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bt_driver_lib as DL
import bt_objb_targets as OT
CFG = json.load(open(sys.argv[2])); FX = sys.argv[3]; OUTP = sys.argv[4]
os.makedirs(FX, exist_ok=True)
assert "object_b" not in os.path.abspath(FX), "fixtures never go into the object-B folder"
RES = []


def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)
def ok(name, cond, detail=None):
    RES.append(dict(check=name, ok=bool(cond), detail=detail)); log(("PASS " if cond else "FAIL ") + name, json.dumps(detail, default=str)[:240] if detail is not None else "")
def mut(name, red, detail=None): ok("[mutation red] " + name, red, detail)
def quiet(*a, **k): pass


def refuses(fn, reason):
    try:
        fn(); return False, "no error"
    except OT.TargetFormatError as e:
        return str(e).startswith(reason), str(e)[:160]


pins_fail = []
DL.verify_pins(CFG, lambda n, c, d=None: pins_fail.append(n) if not c else None)
ok("F0.pins", not pins_fail, pins_fail)
ES, SL, BH, L2 = DL.import_modules(CFG, HERE)
SL.install_readonly_guard()
R_CMB = next(r for r in CFG["runs"] if r["tag"] == "S2_A0pred_s42|CMB|rule|raw|UAFE")
R_LIT = dict(R_CMB, tag="S2_A0pred_s42|LIT|rule|raw|UAFE", book="LIT")
AX0 = np.arange(DL.ts(CFG["window"]["first_anchor"]), DL.ts(CFG["window"]["last_anchor"]) + 1, 14400, dtype=np.int64)
PM = np.load(CFG["pins"]["price_full_meta"]["path"], allow_pickle=True); G0 = int(PM["grid"][0])
LPM = np.load(CFG["pins"]["price_full_raw"]["path"], mmap_mode="r")
UNI = CFG["pins"]["universe"]


def sel_of(start_iso, n):
    k0 = int(np.searchsorted(AX0, DL.ts(start_iso))); return slice(k0, k0 + n)


def prices(sel):
    a0 = int(AX0[sel][0]); a1 = int(AX0[sel][-1]) + 14400
    r0 = max(0, (a0 - 2 * 14400 - G0) // 300); r1 = min(LPM.shape[0], (a1 + 2 * 14400 - G0) // 300 + 1)
    return {"raw": (np.array(LPM[r0:r1]), G0 + 300 * r0, PM["cref_raw"])}


def ctx(sel, runs):
    fails = []
    c = DL.load_context(CFG, ES, BH, L2, sel, runs, lambda n, cnd, d=None: fails.append((n, d)) if not cnd else None, quiet, prices=prices(sel))
    assert not fails, fails
    return c


# ---------------- fixtures from the S2 books, in b_targets.py's layout ----------------
d, Vz, _, _ = L2.load_run(R_CMB["arm"]); V = {k: Vz[k] for k in Vz.files}
Aax, B, fl = L2.books(d, V)
k_lo = int(np.searchsorted(Aax, DL.ts("2024-12-20T00:00:00Z"))); k_hi = int(np.searchsorted(Aax, DL.ts("2025-01-20T00:00:00Z")))
FA = Aax[k_lo:k_hi].astype(np.int64)
cmb = B["CMB"][k_lo:k_hi]; lit = B["LIT"][k_lo:k_hi]; hs = fl["has_states"][k_lo:k_hi]; sk = fl["skip"][k_lo:k_hi]


def csr(rows, kind):
    off = [0]; idx = []; val = []
    for w, k in zip(rows, kind):
        nz = np.nonzero(np.abs(w) > 0)[0] if k else np.zeros(0, np.int64)
        idx.append(nz.astype(np.int16)); val.append(np.asarray(w)[nz]); off.append(off[-1] + len(nz))
    return np.array(off, np.int64), np.concatenate(idx).astype(np.int16), np.concatenate(val)


kind_s = np.where(hs, 2, 0).astype(np.int8)
kind_l = np.where(sk, 0, np.where(hs & np.all(lit == cmb, axis=1), 2, 1)).astype(np.int8)


def write_fixture(name, A, parts, arm="A0", data="holefix2", tamper=None):
    arrs = {"anchor": np.array(A, np.int64, copy=True)}
    for R_, (kind, rows) in parts.items():
        off, idx, val = csr(rows, kind); arrs[f"{R_}_kind"] = np.array(kind, np.int8, copy=True); arrs[f"{R_}_off"] = off; arrs[f"{R_}_idx"] = idx; arrs[f"{R_}_val"] = val
    if tamper: tamper(arrs)
    npz = f"{FX}/TARGETS_{name}.npz"; np.savez_compressed(npz, **arrs)
    rec = {"tag": name, "fixture": "built from stream R S2 books (p2_s2_lib.books), NOT an object-B output", "arm": arm, "data": data,
           "targets_npz_sha256": DL.sha(npz), "B_CORE_start": "FIXTURE", "axis": [int(A[0]), int(A[-1])]}
    rj = f"{FX}/TARGETS_{name}.json"; json.dump(rec, open(rj, "w"), indent=1)
    return {"npz": npz, "npz_sha256": DL.sha(npz), "receipt": rj, "receipt_sha256": DL.sha(rj)}


PARTS = {"scaled": (kind_s, cmb), "lit": (kind_l, lit), "scaled_l333_only": (kind_s, cmb)}
SRC = write_fixture("FIX_full", FA, PARTS)
T = OT.load_targets([SRC], "scaled")
# in this span the S2 LIT book is king-form at every anchor (S2 D11), so combo and hold are exercised by 'scaled', king by 'lit'
ok("F0.fixture_loads_three_readings_and_all_kinds_across_readings", len(T["anchor"]) == len(FA) and set(np.unique(kind_s).tolist()) == {0, 2} and 1 in set(np.unique(kind_l).tolist()),
   {"n": len(FA), "scaled_kinds": np.bincount(kind_s, minlength=3).tolist(), "lit_kinds": np.bincount(kind_l, minlength=3).tolist()})


def objb_run(base, reading, sources, tag_sfx=""):
    return dict(base, tag=base["tag"] + "|objb_" + reading + tag_sfx, book=reading,
                targets={"source": "objb", "reading": reading, "arm": "A0", "sources": sources, "universe": {"path": UNI["path"], "sha256": UNI["sha256"]}})


def arrays_equal(a, b):
    diff = [k for k in sorted(set(a) | set(b)) if k not in a or k not in b or not np.array_equal(np.asarray(a[k]), np.asarray(b[k]), equal_nan=True)]
    return not diff, diff


SEL = sel_of("2024-12-28T00:00:00Z", 72)                   # 12 days: into the 2025-01 HOLD month
C_s2 = ctx(SEL, [R_CMB, R_LIT])
for reading, R_s2, label in (("scaled", R_CMB, "F1"), ("lit", R_LIT, "F2")):
    R_ob = objb_run(R_s2, reading, [SRC])
    C_ob = ctx(SEL, [R_ob])
    Wk, frk, kk, cnt = OT.book_for_window(OT.load_targets([SRC], reading), C_ob.anchors)
    ok(f"{label}.window_exercises_kinds", (cnt["king"] > 0) if reading == "lit" else (cnt["hold"] > 0 and cnt["combo"] > 0), cnt)
    for sd in (0, 1):
        a_s2, o_s2, S_s2 = DL.run_one(C_s2, R_s2, sd); a_ob, o_ob, S_ob = DL.run_one(C_ob, R_ob, sd)
        eq, diff = arrays_equal(a_s2, a_ob)
        ok(f"{label}.{reading}.seed{sd}.objb_path_equals_S2_path_bitwise", eq and S_s2.tstats == S_ob.tstats, {"diff": diff[:5], "tstats": dict(S_ob.tstats)})
    if reading == "lit":
        ok("F2.king_rows_written_as_target_files", S_ob.tstats["written"] == int(np.sum(kk > 0)) - int(cnt["written_rows_without_weights"]), {"written": S_ob.tstats["written"], "kind>0": int(np.sum(kk > 0))})
    if reading == "scaled":
        # semantic mutations: kind 0 read as a written file; one weight changed
        C_bad = ctx(SEL, [R_ob]); W_, fr_ = C_bad.BOOKS[(R_ob["arm"], R_ob["book"])]
        fr_all = np.ones_like(fr_); W_hold = W_.copy()
        for i in np.nonzero(~fr_)[0]: W_hold[i] = W_[max(j for j in range(i) if fr_[j])] if fr_[:i].any() else W_[i]
        C_bad.BOOKS[(R_ob["arm"], R_ob["book"])] = (W_hold, fr_all)
        a_bad, _, _ = DL.run_one(C_bad, R_ob, 0)
        mut("F1.kind0_read_as_written_file_breaks_equivalence", not arrays_equal(a_s2 if False else DL.run_one(C_s2, R_s2, 0)[0], a_bad)[0])
        k_in = int(np.nonzero(kind_s == 2)[0][np.searchsorted(FA[kind_s == 2], int(C_s2.anchors[0]))])   # the first written row INSIDE the window
        def tw(arrs, k_in=k_in):
            a = arrs["scaled_off"][k_in]; arrs["scaled_val"][a] *= 1.5
        SRC_w = write_fixture("FIX_weight_changed", FA, PARTS, tamper=tw)
        C_w = ctx(SEL, [objb_run(R_s2, "scaled", [SRC_w], "_w")])
        a_w, _, _ = DL.run_one(C_w, objb_run(R_s2, "scaled", [SRC_w], "_w"), 0)
        mut("F1.one_weight_changed_breaks_equivalence", not arrays_equal(DL.run_one(C_s2, R_s2, 0)[0], a_w)[0])

# ---------------- F3 two sources = one ----------------
cut = len(FA) // 2
SRC_a = write_fixture("FIX_part1", FA[:cut], {k: (v[0][:cut], v[1][:cut]) for k, v in PARTS.items()})
SRC_b = write_fixture("FIX_part2", FA[cut:], {k: (v[0][cut:], v[1][cut:]) for k, v in PARTS.items()}, data="x0918r")
for reading in ("scaled", "lit"):
    one = OT.book_for_window(OT.load_targets([SRC], reading), FA); two = OT.book_for_window(OT.load_targets([SRC_a, SRC_b], reading), FA)
    ok(f"F3.{reading}.two_sources_equal_one", all(np.array_equal(x, y) for x, y in zip(one[:3], two[:3])) and one[3] == two[3])
# ---------------- F4 universe rows ----------------
U = OT.universe_rows(UNI["path"], UNI["sha256"], C_s2.anchors, C_s2.SY)
ok("F4.universe_rows_equal_S2_PIT", np.array_equal(U, C_s2.PIT.astype(bool)))

# ---------------- format mutations ----------------
def tampered(name, fn, **kw):
    return write_fixture(name, FA, PARTS, tamper=fn, **kw)


def m_off(a): a["scaled_off"][5] = a["scaled_off"][6] + 3
def m_idx(a): a["scaled_idx"][0] = 829
def m_dup(a):
    k = int(np.nonzero(np.diff(a["scaled_off"]) > 1)[0][0]); s0 = a["scaled_off"][k]; a["scaled_idx"][s0 + 1] = a["scaled_idx"][s0]
def m_nan(a): a["scaled_val"][0] = np.nan
def m_kind3(a): a["scaled_kind"][0] = 3
def m_holdw(a):
    k = int(np.nonzero(a["scaled_kind"] == 2)[0][0]); a["scaled_kind"][k] = 0
def m_gap(a): a["anchor"] = np.concatenate([a["anchor"][:10], a["anchor"][10:] + 14400])
def m_miss(a): del a["scaled_off"]


cases = [("npz_sha_mismatch_vs_pin", lambda: OT.load_targets([dict(SRC, npz_sha256="0" * 64)])),
         ("receipt_sha_mismatch_vs_pin", lambda: OT.load_targets([dict(SRC, receipt_sha256="0" * 64)])),
         ("csr_offsets", lambda: OT.load_targets([tampered("M_off", m_off)])),
         ("idx_out_of_range", lambda: OT.load_targets([tampered("M_idx", m_idx)])),
         ("duplicate_column_in_row", lambda: OT.load_targets([tampered("M_dup", m_dup)])),
         ("non_finite_weight", lambda: OT.load_targets([tampered("M_nan", m_nan)])),
         ("kind_out_of_range", lambda: OT.load_targets([tampered("M_kind3", m_kind3)])),
         ("hold_row_with_weights", lambda: OT.load_targets([tampered("M_holdw", m_holdw)])),
         ("axis_not_contiguous_4h", lambda: OT.load_targets([tampered("M_gap", m_gap)])),
         ("sources_not_contiguous_or_overlapping", lambda: OT.load_targets([SRC, SRC_b])),
         ("window_anchor_not_in_targets_axis", lambda: OT.book_for_window(OT.load_targets([SRC_a]), FA)),
         ("unknown_reading", lambda: OT.load_targets([SRC], "combo")),
         ("arm_mismatch", lambda: OT.load_targets([SRC], "scaled", arm="V4")),
         ("missing_keys", lambda: OT.load_targets([tampered("M_miss", m_miss)])),
         ("universe_sha_mismatch", lambda: OT.universe_rows(UNI["path"], "0" * 64, C_s2.anchors, C_s2.SY))]
M_rec = SRC["receipt"].replace("FIX_full", "M_receipt_wrong_sha")
rj = json.load(open(SRC["receipt"])); rj["targets_npz_sha256"] = "f" * 64; json.dump(rj, open(M_rec, "w"))
cases.append(("npz_sha_mismatch_vs_receipt", lambda: OT.load_targets([dict(SRC, receipt=M_rec, receipt_sha256=DL.sha(M_rec))])))
for reason, fn in cases:
    red, msg = refuses(fn, reason); mut(f"format.{reason}", red, msg)

n_pass = sum(1 for r in RES if r["ok"]); n = len(RES)
line = ("BT_OBJB_ADAPTER_TEST VERDICT: ALL PASS %d/%d checks (baselines green first, every mutation red)" % (n_pass, n)) if n_pass == n else \
       ("BT_OBJB_ADAPTER_TEST VERDICT: FAIL %d/%d checks; failed: %s" % (n_pass, n, [r["check"] for r in RES if not r["ok"]]))
json.dump(dict(device="bt_objb_adapter_test.py", self_sha256=DL.sha(os.path.abspath(__file__)), adapter_sha256=DL.sha(os.path.join(HERE, "bt_objb_targets.py")),
               driver_lib_sha256=DL.sha(os.path.join(HERE, "bt_driver_lib.py")), python=sys.version.split()[0], numpy=np.__version__, argv=sys.argv,
               config_sha256=DL.sha(sys.argv[2]), fixture_dir=FX, fixture_source="stream R S2 books via p2_s2_lib.books; no object-B output read",
               results=RES, verdict=line, runtime_s=round(time.time() - T0, 1)), open(OUTP, "w"), indent=1, default=str)
print(line, flush=True)
sys.exit(0 if n_pass == n else 1)

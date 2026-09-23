#!/usr/bin/env python3
"""m2_tests.py — red/green tests for m2_lib.py (the M2 beta calculator and target transformer). Every test states a BASELINE that must be
green and, where a test could be vacuous, a RED-CAPABILITY control (a deliberately broken input that the same assertion must reject); a
control that does not go red fails the test. Verdict lines are printed with baseline and control values.

  T1  future-perturbation invariance: beta at A is BITWISE unchanged when every price row after A and the UA set after A are changed;
      control: changing the bar ENDING at A must change beta (proves the assertion can see a change)
  T2  known beta = 2 (synthetic 4h returns y = 0.001 + 2x): |b - 2| < 1e-6, with UA-marked bars carrying garbage (jumps and zero-filled
      flats) that must be EXCLUDED; control: the same series with the UA marks removed must miss 2 by > 1e-3
  T3  119 valid pairs ⇒ beta = 1.0 (fallback, EST False); 120 ⇒ estimated (|b - 2| < 1e-6)
  T4  clipping: slope 5 ⇒ 4.0, slope -3 ⇒ -1.0; BTC's own beta = 1.0 exactly
  T5  transformer round trip: hedge = 0 everywhere ⇒ kind / off / idx / val bitwise equal (dtypes too); control: one hedge of 1e-12 ≠
  T6  HOLD rows (kind 0) unchanged whatever the hedge
  T7  BTC present ⇒ only BTC changes (= old + hedge); BTC absent ⇒ inserted at its sorted position, every other entry unchanged
  T8  beta_book = dense dot product (independent computation), |err| <= 1e-12
  T9  empty inputs raise (unknown is not zero)
  T1R (pod2 only, argv[2] = 'real'): T1 on the certified price table (BTC + 80 names incl. every name with a UA cell near A, 4 anchors),
      and the subset result equals the full-table build's beta at A bitwise (argv[3] = the build's BETA npz)
usage: python m2_tests.py <out.json> [real <BETA_npz>]
"""
import json, os, sys, time, hashlib, calendar
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import m2_lib as M

H4, ROW = M.H4, M.ROW
OUT = {"device": "m2_tests.py", "self_sha256": M.sha_file(os.path.abspath(__file__)), "lib_sha256": M.sha_file(os.path.join(HERE, "m2_lib.py")),
       "numpy": np.__version__, "python": sys.version.split()[0], "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "tests": []}
FAILS = []


def rec(name, ok, **kw):
    OUT["tests"].append(dict(test=name, ok=bool(ok), **kw))
    print(("GREEN " if ok else "RED   ") + name + " " + json.dumps(kw, default=str)[:600], flush=True)
    if not ok: FAILS.append(name)


# ───────────────────────── synthetic fixture ─────────────────────────
def fixture(n_bars=400, n_names=6, seed=7, beta=2.0, drift=0.001):
    """5-minute grid; BTC = random walk; name 1 = beta·BTC + drift per 4h bar (exact at 4h boundaries); names 2.. = noise"""
    rng = np.random.default_rng(seed)
    g0 = 1700006400                                  # 2023-11-15T00:00Z (on the 4h grid)
    n5 = n_bars * 48 + 1
    grid = g0 + ROW * np.arange(n5, dtype=np.int64)
    btc = np.concatenate([[0.0], np.cumsum(rng.normal(0, 0.002, n5 - 1))])
    LP = np.zeros((n5, n_names)); LP[:, 0] = btc
    t4 = (grid - g0) / H4
    LP[:, 1] = beta * btc + drift * t4               # y_4h = beta·x_4h + drift at every 4h boundary pair
    for j in range(2, n_names): LP[:, j] = np.concatenate([[0.0], np.cumsum(rng.normal(0, 0.003, n5 - 1))])
    ff = np.full(n_names, g0, np.int64); lf = np.full(n_names, int(grid[-1]), np.int64)
    return grid, LP, ff, lf


def beta_of(grid, LP, ff, lf, ur, uc, A, j, btc_j=0):
    T, R, V = M.bars_4h(LP, grid, ff, lf, ur, uc)
    B, N, E, RAW = M.betas_at(T, R, V, np.array([A]), btc_j)
    return B[0, j], N[0, j], E[0, j], RAW[0, j], (B, N, E)


def t1_synth():
    grid, LP, ff, lf = fixture()
    A = int(grid[0]) + 300 * H4                      # bar 300 ends at A
    ur = np.array([10, 20], np.int64); uc = np.array([3, 4], np.int64)
    T, R, V = M.bars_4h(LP, grid, ff, lf, ur, uc); B0, N0, E0, _ = M.betas_at(T, R, V, np.array([A]), 0)
    rA = int((A - grid[0]) // ROW)
    LP2 = LP.copy(); rng = np.random.default_rng(1); LP2[rA + 1:] += rng.normal(0, 0.5, LP2[rA + 1:].shape); LP2[rA + 5:, 1] += 3.0
    ur2 = np.concatenate([ur, [rA + 1, rA + 48, rA + 49]]); uc2 = np.concatenate([uc, [1, 1, 2]])
    T2, R2, V2 = M.bars_4h(LP2, grid, ff, lf, ur2, uc2); B2, N2, E2, _ = M.betas_at(T2, R2, V2, np.array([A]), 0)
    same = np.array_equal(B0.view(np.uint64), B2.view(np.uint64)) and np.array_equal(N0, N2) and np.array_equal(E0, E2)
    LP3 = LP.copy(); LP3[rA, 1:] += 0.05                     # the bar ENDING at A changes (control)
    T3, R3, V3 = M.bars_4h(LP3, grid, ff, lf, ur, uc); B3, *_ = M.betas_at(T3, R3, V3, np.array([A]), 0)
    changed = not np.array_equal(B0.view(np.uint64), B3.view(np.uint64))
    rec("T1.future_invariance_synthetic.baseline_bitwise_equal", same, n_future_rows_perturbed=int(len(LP) - rA - 1), future_ua_added=3)
    rec("T1.future_invariance_synthetic.control_bar_ending_at_A_changes_beta", changed, max_abs_diff=float(np.max(np.abs(B0 - B3))))


def t2():
    grid, LP, ff, lf = fixture()
    A = int(grid[0]) + 300 * H4
    b, n, e, raw, _ = beta_of(grid, LP, ff, lf, np.zeros(0, np.int64), np.zeros(0, np.int64), A, 1)
    rec("T2.beta2_clean.baseline", e and abs(raw - 2.0) < 1e-6 and n == 180, beta=raw, err=abs(raw - 2.0), nobs=int(n))
    # traps inside bars 200..229 (all inside the 180-bar window ending at bar 300): garbage in the NAME only, those 5-minute bars marked UA
    LPg = LP.copy(); ur, uc = [], []
    for kb in range(200, 230):
        r_mid = kb * 48 - 20                             # a 5-minute bar strictly inside bar kb
        if kb % 2 == 0:
            LPg[r_mid:, 1] += 0.08                       # a jump the regression must not see
        else:
            LPg[(kb - 1) * 48:kb * 48 + 1, 1] = LPg[(kb - 1) * 48, 1]   # a zero-filled flat over the whole bar (BTC keeps moving)
            LPg[kb * 48 + 1:, 1] -= LP[kb * 48, 1] - LP[(kb - 1) * 48, 1]  # level continuity: the flat removed this bar's move
        ur.append(r_mid); uc.append(1)
    ur = np.array(ur, np.int64); uc = np.array(uc, np.int64)
    b1, n1, e1, raw1, _ = beta_of(grid, LPg, ff, lf, ur, uc, A, 1)
    rec("T2.beta2_with_UA_garbage_excluded.baseline", e1 and abs(raw1 - 2.0) < 1e-6 and n1 == 150, beta=raw1, err=abs(raw1 - 2.0), nobs=int(n1))
    b2, n2, e2, raw2, _ = beta_of(grid, LPg, ff, lf, np.zeros(0, np.int64), np.zeros(0, np.int64), A, 1)
    rec("T2.control_same_garbage_unmarked_misses_2", abs(raw2 - 2.0) > 1e-3, beta=raw2, err=abs(raw2 - 2.0), nobs=int(n2))


def t3():
    grid, LP, ff, lf = fixture()
    A = int(grid[0]) + 300 * H4                      # bars 121..300 in the window
    for nv, want_est in ((119, False), (120, True)):
        ff2 = ff.copy(); ff2[1] = A - nv * H4        # bar k valid iff T[k-1] >= ff ⇒ exactly nv bars
        b, n, e, raw, _ = beta_of(grid, LP, ff2, lf, np.zeros(0, np.int64), np.zeros(0, np.int64), A, 1)
        if want_est:
            rec(f"T3.nobs_{nv}_estimated", bool(e) and n == nv and abs(b - 2.0) < 1e-6, beta=b, nobs=int(n), est=bool(e))
        else:
            rec(f"T3.nobs_{nv}_falls_back_to_1.0", (not e) and n == nv and b == 1.0 and np.isnan(raw), beta=b, nobs=int(n), est=bool(e))


def t4():
    for beta, want in ((5.0, 4.0), (-3.0, -1.0)):
        grid, LP, ff, lf = fixture(beta=beta)
        A = int(grid[0]) + 300 * H4
        b, n, e, raw, (B, N, E) = beta_of(grid, LP, ff, lf, np.zeros(0, np.int64), np.zeros(0, np.int64), A, 1)
        rec(f"T4.clip_slope_{beta:+.0f}_to_{want:+.0f}", b == want and abs(raw - beta) < 1e-6, beta=b, raw=raw)
    rec("T4.btc_own_beta_is_exactly_1", B[0, 0] == 1.0 and not E[0, 0], btc=float(B[0, 0]))


def csr_fixture():
    rows = [
        (2, [(3, 0.2), (7, -0.1), (9, 0.05)]),           # BTC (col 7) present
        (1, [(1, -0.3), (4, 0.25), (12, 0.1)]),          # BTC absent ⇒ insert between 4 and 12
        (0, []),                                         # HOLD
        (2, [(0, 0.4), (2, -0.4)]),                      # BTC absent, sorted insert at the end
        (2, [(7, -0.02), (8, 0.3)]),                     # BTC first
    ]
    kind = np.array([k for k, _ in rows], np.int8); off = [0]; idx = []; val = []
    for _, r in rows:
        for c, v in r: idx.append(c); val.append(v)
        off.append(len(idx))
    return kind, np.array(off, np.int64), np.array(idx, np.int16), np.array(val, np.float64)


def t5_t8():
    kind, off, idx, val = csr_fixture(); btc = 7
    k2, o2, i2, v2, st = M.transform(kind, off, idx, val, np.zeros(len(kind)), btc)
    eq = (np.array_equal(k2, kind) and k2.dtype == kind.dtype and np.array_equal(o2, off) and o2.dtype == off.dtype and np.array_equal(i2, idx)
          and i2.dtype == idx.dtype and np.array_equal(v2.view(np.uint64), val.view(np.uint64)) and v2.dtype == val.dtype)
    rec("T5.round_trip_zero_hedge_bitwise.baseline", eq, stats=st)
    h = np.zeros(len(kind)); h[0] = 1e-12
    k3, o3, i3, v3, _ = M.transform(kind, off, idx, val, h, btc)
    rec("T5.control_tiny_hedge_detected", not np.array_equal(v3.view(np.uint64), val.view(np.uint64)))
    hedge = np.array([0.11, -0.07, 0.5, 0.03, 0.02])
    k4, o4, i4, v4, st4 = M.transform(kind, off, idx, val, hedge, btc)
    rec("T6.hold_row_unchanged", o4[3] - o4[2] == 0 and st4["hold_rows_with_nonzero_hedge_ignored"] == 1, stats=st4)
    ok = True; det = []
    for r in range(len(kind)):
        a, b = off[r], off[r + 1]; a2, b2 = o4[r], o4[r + 1]
        old = dict(zip(idx[a:b].tolist(), val[a:b].tolist())); new = dict(zip(i4[a2:b2].tolist(), v4[a2:b2].tolist()))
        if kind[r] == 0:
            ok &= (old == new); continue
        others_same = all(new[c] == v and np.float64(new[c]).view(np.uint64) == np.float64(v).view(np.uint64) for c, v in old.items() if c != btc)
        btc_ok = new.get(btc) == (old.get(btc, 0.0) + hedge[r] if btc in old else hedge[r])
        sorted_ok = bool(np.all(np.diff(i4[a2:b2].astype(int)) > 0))
        n_ok = len(new) == len(old) + (0 if btc in old else 1)
        ok &= others_same and btc_ok and sorted_ok and n_ok; det.append([int(r), others_same, btc_ok, sorted_ok, n_ok])
    rec("T7.only_btc_changes_insert_sorted", ok, per_row=det, stats=st4)
    Bm = np.random.default_rng(3).uniform(-1, 4, (len(kind), 16))
    bb = M.beta_book_rows(kind, off, idx, val, Bm)
    dense = np.zeros((len(kind), 16))
    for r in range(len(kind)): dense[r, idx[off[r]:off[r + 1]]] = val[off[r]:off[r + 1]]
    ref = (dense * Bm).sum(1)
    rec("T8.beta_book_equals_dense_dot", float(np.max(np.abs(bb - ref))) <= 1e-12, max_err=float(np.max(np.abs(bb - ref))))


def t9():
    raised = []
    for nm, f in (("betas_at_empty_anchors", lambda: M.betas_at(np.array([0, H4]), np.zeros((2, 2)), np.zeros((2, 2), bool), np.zeros(0, np.int64), 0)),
                  ("bars_4h_empty_grid", lambda: M.bars_4h(np.zeros((0, 2)), np.zeros(0, np.int64), np.zeros(2), np.zeros(2), [], [])),
                  ("betas_at_anchor_after_last_boundary", lambda: M.betas_at(np.array([0, H4]), np.zeros((2, 2)), np.zeros((2, 2), bool), np.array([2 * H4]), 0))):
        try:
            f(); raised.append((nm, False))
        except M.M2Error:
            raised.append((nm, True))
    rec("T9.empty_or_uncomputable_raises", all(r for _, r in raised), cases=raised)


def t1_real(beta_npz):
    """the certified table; 4 anchors; BTC + every name with a UA cell within 200 bars before A or 10 bars after + random names to 80"""
    W = "/workspace/baseline_tables_2026-09-19/work/"
    PM = np.load(W + "price_full_raw_x0918r_meta.npz", allow_pickle=True); SY = [str(s) for s in PM["symbols"]]; bj = SY.index(M.BTC)
    LPf = np.load(W + "price_full_raw_x0918r.npy", mmap_mode="r"); grid = PM["grid"].astype(np.int64)
    BZ = np.load(beta_npz); BA = BZ["anchor"].astype(np.int64); BB = BZ["beta"]
    rng = np.random.default_rng(20260923)
    for iso in ("2023-09-14T08:00:00Z", "2024-03-12T16:00:00Z", "2025-04-07T00:00:00Z", "2025-10-10T20:00:00Z"):
        A = calendar.timegm(time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ"))
        rA = int((A - grid[0]) // ROW); r0 = rA - (M.N_WIN + 2) * 48; r1 = min(len(grid), rA + 30 * 48)
        ur_all = PM["unavail_grid_row"].astype(np.int64); uc_all = PM["unavail_col"].astype(np.int64)
        near = np.unique(uc_all[(ur_all >= r0) & (ur_all < r1)])
        pool = np.setdiff1d(np.arange(len(SY)), np.concatenate([[bj], near]))
        cols = np.concatenate([[bj], near, rng.choice(pool, max(0, 80 - 1 - len(near)), replace=False)]).astype(np.int64)
        LP = np.array(LPf[r0:r1][:, cols]); g = grid[r0:r1]
        sel = (ur_all >= r0) & (ur_all < r1) & np.isin(uc_all, cols); cmap = {int(c): i for i, c in enumerate(cols)}
        ur = ur_all[sel] - r0; uc = np.array([cmap[int(c)] for c in uc_all[sel]], np.int64)
        ff = PM["first_fin"].astype(np.int64)[cols]; lf = PM["last_fin"].astype(np.int64)[cols]
        T, R, V = M.bars_4h(LP, g, ff, lf, ur, uc); B0, N0, E0, _ = M.betas_at(T, R, V, np.array([A]), 0)
        LP2 = LP.copy(); k = rA - r0
        LP2[k + 1:] += np.random.default_rng(5).normal(0, 0.3, LP2[k + 1:].shape)
        ur2 = np.concatenate([ur, np.arange(k + 1, k + 200)]); uc2 = np.concatenate([uc, np.full(199, 1 + (len(cols) - 1) // 2)])
        T2, R2, V2 = M.bars_4h(LP2, g, ff, lf, ur2, uc2); B2, N2, E2, _ = M.betas_at(T2, R2, V2, np.array([A]), 0)
        same = np.array_equal(B0.view(np.uint64), B2.view(np.uint64)) and np.array_equal(N0, N2)
        LP3 = LP.copy(); LP3[k, 1:] += 0.05
        T3, R3, V3 = M.bars_4h(LP3, g, ff, lf, ur, uc); B3, *_ = M.betas_at(T3, R3, V3, np.array([A]), 0)
        ia = int(np.nonzero(BA == A)[0][0]); full = BB[ia, cols]
        rec(f"T1R.{iso}.future_invariance_real.baseline_bitwise_equal", same, n_cols=len(cols), n_ua_names_near=len(near), n_est=int(E0.sum()))
        rec(f"T1R.{iso}.control_bar_ending_at_A_changes_beta", not np.array_equal(B0.view(np.uint64), B3.view(np.uint64)), max_abs_diff=float(np.max(np.abs(B0 - B3))))
        rec(f"T1R.{iso}.subset_equals_full_build_bitwise", np.array_equal(B0[0].view(np.uint64), np.ascontiguousarray(full).view(np.uint64)),
            max_abs_diff=float(np.max(np.abs(B0[0] - full))))


if __name__ == "__main__":
    outp = sys.argv[1]
    t1_synth(); t2(); t3(); t4(); t5_t8(); t9()
    if len(sys.argv) > 2 and sys.argv[2] == "real":
        OUT["beta_npz"] = {"path": sys.argv[3], "sha256": M.sha_file(sys.argv[3])}
        t1_real(sys.argv[3])
    OUT["n_tests"] = len(OUT["tests"]); OUT["n_red"] = len(FAILS); OUT["red"] = FAILS
    OUT["VERDICT"] = "ALL GREEN" if not FAILS else "RED"
    json.dump(OUT, open(outp + ".tmp", "w"), indent=1, default=str); os.replace(outp + ".tmp", outp)
    print(f"M2_TESTS VERDICT={OUT['VERDICT']} tests={OUT['n_tests']} red={len(FAILS)} out_sha256={M.sha_file(outp)}", flush=True)
    sys.exit(0 if not FAILS else 1)

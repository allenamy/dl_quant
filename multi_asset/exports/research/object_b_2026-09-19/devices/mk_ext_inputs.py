#!/usr/bin/env python3
"""Extension-segment inputs (PREREG AMENDMENT 4 A4.4; lead ruling e3e7a8fc3): the 2026-08-31 04Z -> 2026-09-18 20Z segment of object B / object A.
Targets only; no prices, no returns. READ-ONLY on every source; writes only work/ext_inputs/ and receipts/EXT_INPUTS.json.

  ledger_ext.npz    per-symbol settlement ledger on the 829 axis (same layout as S2 ledger_full: off, ft, rate, src, symbols):
                    rows with ft <= BOUND (= 2026-08-31T00:00Z, the A0 axis end) are ledger_full's rows byte-for-byte; rows with ft > BOUND come
                    from the stream-D funding ledger 74b69e63 (key = ts_ms // 1000, the producer's own key; rate = its `rate`); src = 9 marks them.
                    Every anchor A <= BOUND reads rows ft <= A only (b_driver.ledger_rows), so the A0 chain's inputs are unchanged by construction.
  universe_ext.npz  ts = universe.npz ts (10,039, to BOUND) + the 4h anchors BOUND+4h .. 2026-09-18T20:00Z;
                    pit rows after BOUND = the pinned production bundle config's symbols_live (3a8422f3; its universe_sha 93ad1d25 = the one value
                    carried by all 143 archived target_live files 08-26 00Z -> 09-18 20Z, RESULT §7); trading24 = >= 1 settlement in (E − 24h, E]
                    recomputed on ledger_ext for EVERY row (the S2 rule, p2_prep_inputs.py) and asserted equal to universe.npz on its 10,039 rows.
Descriptive (not gates): the overlap (2026-08-21T00Z, 2026-09-01T02:00Z] of ledger_full and the stream-D ledger (keys and rates), and the
PIT rows 2026-08-26 00Z .. BOUND vs the config symbols_live set.
usage: env -i PATH=/usr/bin:/bin HOME=/root LC_CTYPE=C.UTF-8 nice -n 10 /workspace/venv/bin/python -B mk_ext_inputs.py"""
import os, sys, json, time, hashlib, calendar
import numpy as np

R = "/workspace/object_b_2026-09-19"; OUT = f"{R}/work/ext_inputs"
SRC = {"ledger_full": ("/workspace/uplift_r2_2026-09-13/P2/work/ledger_full.npz", "bea6f5752772d54e659a4da5571ca41945a27d1b2316ec0ae52f387074f795ad"),
       "ledger_streamD": ("/workspace/axis_0919/funding/funding_ledger.npz", "74b69e635efbf3556fe706520fda9d5a1b5cda86dda9d04a844ba5d617a3a09d"),
       "universe": ("/workspace/uplift_r2_2026-09-13/P2/work/universe.npz", "6322b57366078ed0022fd8a8156ee36f527bf309e0d66bfa5f6ec17d7a09efa7"),
       "bundle_config": ("/workspace/shadow_bundle_v3/config.json", "3a8422f377519cac77b0c42305d2ba40a4b7a42a830f0542bda844f66647c94e")}
UNIVERSE_SHA_ARCHIVED = "93ad1d25"
BOUND = calendar.timegm((2026, 8, 31, 0, 0, 0)); LAST = calendar.timegm((2026, 9, 18, 20, 0, 0)); H4 = 14400


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()


def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


def main():
    shas = {}
    for k, (p, s) in SRC.items():
        shas[k] = sha(p); assert shas[k] == s, (k, shas[k])
    L = np.load(SRC["ledger_full"][0], allow_pickle=True); SYMS = [str(s) for s in L["symbols"]]
    D = np.load(SRC["ledger_streamD"][0], allow_pickle=True); assert [str(s) for s in D["symbols"]] == SYMS
    d_sym = D["sym"].astype(np.int64); d_ts = D["ts"].astype(np.int64); d_ms = D["ts_ms"].astype(np.int64); d_rate = D["rate"].astype(np.float64)
    assert np.array_equal(d_ts, d_ms // 1000), "stream-D ts must be ts_ms // 1000 (the producer key)"
    U = np.load(SRC["universe"][0], allow_pickle=True); assert [str(s) for s in U["symbols"]] == SYMS
    UTS = U["ts"].astype(np.int64); assert int(UTS[-1]) == BOUND and np.all(np.diff(UTS) == H4)
    cfg = json.load(open(SRC["bundle_config"][0])); live = list(cfg["symbols_live"])
    usha = hashlib.sha256(json.dumps(live, separators=(",", ":")).encode()).hexdigest(); assert usha.startswith(UNIVERSE_SHA_ARCHIVED), usha
    col = {s: j for j, s in enumerate(SYMS)}; assert all(s in col for s in live)
    off0 = L["off"]; ft0 = L["ft"]; r0 = L["rate"]; s0 = L["src"]
    # ── combined ledger + overlap description ──
    FT, RT, SR, off = [], [], [], [0]
    ov = {"window": [iso(calendar.timegm((2026, 8, 21, 0, 0, 0))), iso(int(ft0.max()))], "n_full": 0, "n_streamD": 0, "keys_only_full": 0,
          "keys_only_streamD": 0, "keys_both": 0, "rate_unequal": 0, "examples_unequal": [], "examples_only_full": [], "examples_only_streamD": []}
    ov_lo = calendar.timegm((2026, 8, 21, 0, 0, 0)); ov_hi = int(ft0.max())
    n_from_D = 0
    for j in range(829):
        a, b = int(off0[j]), int(off0[j + 1]); f = ft0[a:b]; keep = f <= BOUND
        FT.append(f[keep]); RT.append(r0[a:b][keep]); SR.append(s0[a:b][keep])
        m = d_sym == j; fd = d_ts[m]; rd = d_rate[m]; o = np.argsort(fd, kind="stable"); fd = fd[o]; rd = rd[o]
        assert np.all(np.diff(fd) > 0), ("stream-D duplicate key", SYMS[j])
        add = fd > BOUND; FT.append(fd[add]); RT.append(rd[add]); SR.append(np.full(int(add.sum()), 9, np.int8)); n_from_D += int(add.sum())
        off.append(off[-1] + int(keep.sum()) + int(add.sum()))
        fo = f[(f > ov_lo) & (f <= ov_hi)]; ro = r0[a:b][(f > ov_lo) & (f <= ov_hi)]
        md = (fd > ov_lo) & (fd <= ov_hi); fdo = fd[md]; rdo = rd[md]
        ov["n_full"] += len(fo); ov["n_streamD"] += len(fdo)
        both, i1, i2 = np.intersect1d(fo, fdo, return_indices=True)
        ov["keys_both"] += len(both)
        ne = np.where(ro[i1] != rdo[i2])[0]; ov["rate_unequal"] += len(ne)
        for k in ne[:3]:
            if len(ov["examples_unequal"]) < 20: ov["examples_unequal"].append([SYMS[j], iso(both[k]), float(ro[i1[k]]), float(rdo[i2[k]])])
        of = np.setdiff1d(fo, fdo); od = np.setdiff1d(fdo, fo)
        ov["keys_only_full"] += len(of); ov["keys_only_streamD"] += len(od)
        for t in of[:2]:
            if len(ov["examples_only_full"]) < 20: ov["examples_only_full"].append([SYMS[j], iso(t)])
        for t in od[:2]:
            if len(ov["examples_only_streamD"]) < 20: ov["examples_only_streamD"].append([SYMS[j], iso(t)])
    FT = np.concatenate(FT).astype(np.int64); RT = np.concatenate(RT).astype(np.float64); SR = np.concatenate(SR).astype(np.int8); off = np.array(off, np.int64)
    for j in range(829):
        assert np.all(np.diff(FT[off[j]:off[j + 1]]) > 0), SYMS[j]
    # prefix proof: rows <= BOUND are ledger_full's rows byte-for-byte
    for j in range(829):
        a, b = int(off0[j]), int(off0[j + 1]); f = ft0[a:b]; k = int((f <= BOUND).sum())
        assert np.array_equal(FT[off[j]:off[j] + k], f[:k]) and np.array_equal(RT[off[j]:off[j] + k], r0[a:a + k]), SYMS[j]
        assert np.all(FT[off[j] + k:off[j + 1]] > BOUND)
    os.makedirs(OUT, exist_ok=True)
    np.savez(f"{OUT}/ledger_ext.npz", off=off, ft=FT, rate=RT, src=SR, symbols=np.array(SYMS))
    # ── universe_ext ──
    new_ts = np.arange(BOUND + H4, LAST + 1, H4, dtype=np.int64); TS = np.concatenate([UTS, new_ts])
    pin = np.zeros(829, bool); pin[[col[s] for s in live]] = True
    PIT = np.concatenate([np.asarray(U["pit"], bool), np.tile(pin, (len(new_ts), 1))])
    TR24 = np.zeros((len(TS), 829), bool)
    for j in range(829):
        seg = FT[off[j]:off[j + 1]]
        if len(seg) == 0: continue
        hi = np.searchsorted(seg, TS, side="right"); lo = np.searchsorted(seg, TS - 86400, side="right"); TR24[:, j] = hi > lo
    assert np.array_equal(TR24[:len(UTS)], np.asarray(U["trading24"], bool)), "trading24 recomputation must reproduce universe.npz on its rows"
    np.savez(f"{OUT}/universe_ext.npz", ts=TS, pit=PIT, trading24=TR24, symbols=np.array(SYMS))
    # descriptive: PIT rows 08-26 00Z .. BOUND vs the config set; panel-order list sha of the pinned set
    d26 = calendar.timegm((2026, 8, 26, 0, 0, 0)); rows = np.where((UTS >= d26) & (UTS <= BOUND))[0]
    pit_vs = {iso(UTS[r]): {"equal": bool(np.array_equal(np.asarray(U["pit"][r], bool), pin)), "only_pit": int((np.asarray(U["pit"][r], bool) & ~pin).sum()),
                            "only_config": int((~np.asarray(U["pit"][r], bool) & pin).sum())} for r in rows}
    panel_order = [SYMS[j] for j in np.where(pin)[0]]
    doc = {"device": os.path.abspath(__file__), "self_sha256": sha(os.path.abspath(__file__)), "comparison_type": "input construction (no returns)",
           "inputs_sha256": shas, "BOUND": iso(BOUND), "segment": [iso(new_ts[0]), iso(new_ts[-1]), int(len(new_ts))],
           "ledger_ext": {"path": f"{OUT}/ledger_ext.npz", "sha256": sha(f"{OUT}/ledger_ext.npz"), "n_rows": int(len(FT)), "n_rows_from_streamD": n_from_D,
                          "prefix_rows_equal_ledger_full": True, "rule": "ft <= BOUND: ledger_full rows; ft > BOUND: stream-D rows (src 9)"},
           "universe_ext": {"path": f"{OUT}/universe_ext.npz", "sha256": sha(f"{OUT}/universe_ext.npz"), "n_rows": int(len(TS)),
                            "prefix_trading24_equal": True, "new_pit_rows": f"config symbols_live ({len(live)} names), universe_sha {usha}",
                            "new_rows_trading24_mean": round(float(TR24[len(UTS):].sum(1).mean()), 1)},
           "overlap_ledger_full_vs_streamD_descriptive": ov,
           "pit_rows_0826_to_bound_vs_config_symbols_live": pit_vs,
           "panel_order_list_universe_sha": hashlib.sha256(json.dumps(panel_order, separators=(",", ":")).encode()).hexdigest(),
           "config_order_is_panel_order": panel_order == live, "utc": iso(time.time())}
    json.dump(doc, open(f"{R}/receipts/EXT_INPUTS.json", "w"), indent=1)
    print(json.dumps({k: doc[k] for k in ("segment", "ledger_ext", "universe_ext")}), flush=True)
    print("overlap", json.dumps({k: v for k, v in ov.items() if not k.startswith("examples")}), flush=True)
    print("pit_vs_config", sum(v["equal"] for v in pit_vs.values()), "/", len(pit_vs), "config_order_is_panel_order", doc["config_order_is_panel_order"], flush=True)


if __name__ == "__main__":
    main()

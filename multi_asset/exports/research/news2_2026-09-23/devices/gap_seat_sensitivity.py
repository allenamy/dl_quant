#!/usr/bin/env python3
"""gap_seat_sensitivity.py -- how much do the live seats move because the 2026-09-26 outage left a hole in the live leg-return
history? (lead item 5, 2026-09-26; read-only: reads a COPY of the live state, writes only --out.)

Mechanism (shadow_loop_v3.py sha 52baf979 L751-L752): the producer appends one LR entry per leg only when
prev_rec.anchor_ts == last_anchor and anchor - last_anchor == 14400. The outage skipped 12Z and 16Z; at the first anchor after
restart (20Z if restarted before it) the gap is 12 h, so nothing is appended. Missing entries: 08->12Z, 12->16Z, 16->20Z (k = 3;
k = 4 if the first resumed anchor is 00Z). The research NC replay has them. Seats use the frozen msharpe formula on the last
look = 900 entries (IMPORTED from reseed_leg_returns.py, which is shadow_loop_v3.py L784-L790 == nc_legs.py L57-L61).

The real values of the missing entries cannot be computed yet: the producer's 5-min cache (state/rolling.npz) stops at 08Z and
the 12Z/16Z leg z were never produced. So this device measures the seat difference over the EMPIRICAL distribution of what those
entries could be, and the lifetime of the hole, without inventing any value:

  A  first resumed anchor. hole = seats(F[-900:]); counterfactual = seats((F + b)[-900:]) for every consecutive k-block b in
     (A1) the live file's own 950 entries and (A2) the research replay LR over 2026 (label: stand-in distribution). Also b = 0.
  Y  yardstick: the natural change of the same seats from 1 and k ordinary appends, measured on the live file itself.
  B  lifetime: on the research replay series, delete a k-block at many positions p and compare seats with/without the block at
     lags 0..899 after the restart (after 900 anchors the two windows coincide exactly -- asserted).
Masked seat = the combo's own rule (combo_stage.py sha 12a76de8 L285-L286): king / (king + fund) after zeroing rev24.
"""
import argparse, hashlib, importlib.util, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RESEED = os.path.join(HERE, "..", "..", "reseed_2026-09-26", "devices", "reseed_leg_returns.py")
LEGS = ("king", "rev24", "fund")
LOOK = 900


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


spec = importlib.util.spec_from_file_location("reseed_ref", RESEED); R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
assert R.LEGS == LEGS


def seats_arr(M):
    """M: (n>=LOOK, 3) array -> the frozen formula on its last LOOK rows (called through the reseed device, not re-implemented)."""
    return np.asarray(R.seats({l: list(M[-LOOK:, j]) for j, l in enumerate(LEGS)}), float)


def masked_king(w):
    m = np.array([w[0], 0.0, w[2]]); return float(m[0] / m.sum()) if m.sum() > 1e-12 else 0.5


def dist(x):
    a = np.abs(np.asarray(x, float))
    return {"n": int(a.size), "median_abs": float(np.median(a)), "p90_abs": float(np.quantile(a, .9)), "p99_abs": float(np.quantile(a, .99)),
            "max_abs": float(a.max()), "mean_signed": float(np.mean(x))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live-lr", required=True); ap.add_argument("--live-lr-sha", required=True)
    ap.add_argument("--replay", required=True, help="npz with E_ts, LR (reseed receipts legs_9ee5886f_E_ts_LR_slice.npz)")
    ap.add_argument("--k", type=int, nargs="+", default=[3, 4]); ap.add_argument("--step", type=int, default=24); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if sha(a.live_lr) != a.live_lr_sha: sys.exit(f"STOP live LR sha {sha(a.live_lr)[:12]} != pinned {a.live_lr_sha[:12]}")
    d = json.load(open(a.live_lr)); F = np.array([d[l] for l in LEGS], float).T
    Z = np.load(a.replay); E = Z["E_ts"].astype(np.int64); LR = np.asarray(Z["LR"], float)
    ok = np.isfinite(LR).all(1); E, LR = E[ok], LR[ok]
    assert np.all(np.diff(E) == 14400), "replay not contiguous 4h after dropping non-finite rows"  # the lifetime sim needs contiguity
    base = seats_arr(F)
    out = {"device_sha256": sha(__file__), "reseed_device_sha256": sha(RESEED), "live_lr": {"path": a.live_lr, "sha256": a.live_lr_sha, "n": len(F)},
           "replay": {"path": a.replay, "sha256": sha(a.replay), "n_finite": int(len(E)), "span_utc": [int(E[0]), int(E[-1])]},
           "hole_seats_at_first_resumed_anchor": {"w3": base.tolist(), "masked_king": masked_king(base)}, "by_k": {}}
    # control: the seat function responds to a change of the window's last entry (a dead/constant function would make every delta 0)
    F2 = F.copy(); F2[-1, 0] += 1e3
    assert not np.array_equal(seats_arr(F2), base), "CONTROL_FAIL: seat function does not respond to the window's last entry"
    for k in a.k:
        res = {}
        # Y yardstick: natural change of seats from 1 and k ordinary appends inside the live file (last 50 positions)
        path = [seats_arr(F[:len(F) - j]) for j in range(0, 50)][::-1]
        mk = np.array([masked_king(w) for w in path]); W = np.array(path)
        res["yardstick_live_file"] = {"one_append": {"w3_" + l: dist(np.diff(W[:, j])) for j, l in enumerate(LEGS)} | {"masked_king": dist(np.diff(mk))},
                                      f"{k}_appends": {"w3_" + l: dist(W[k:, j] - W[:-k, j]) for j, l in enumerate(LEGS)} | {"masked_king": dist(mk[k:] - mk[:-k])}}
        # A first resumed anchor
        for tag, src in (("A1_blocks_from_live_file", F), ("A2_blocks_from_replay_2026", LR[E >= 1767225600])):
            dw, dm = [], []
            for i in range(len(src) - k + 1):
                s = seats_arr(np.vstack([F, src[i:i + k]])); dw.append(s - base); dm.append(masked_king(s) - masked_king(base))
            dw = np.array(dw)
            res[tag] = {"w3_" + l: dist(dw[:, j]) for j, l in enumerate(LEGS)} | {"masked_king": dist(dm)}
        s0 = seats_arr(np.vstack([F, np.zeros((k, 3))]))
        res["A0_zero_block"] = {"dw3": (s0 - base).tolist(), "d_masked_king": masked_king(s0) - masked_king(base)}
        # B lifetime on the replay: remove LR[p:p+k]; restart anchor = the one whose append would have been LR[p+k-1]
        lags = [0, 1, 6, 30, 90, 180, 450, 899, 900]
        ps = list(range(LOOK + 10, len(LR) - k - LOOK - 2, a.step))
        acc = {g: [] for g in lags}; lifetime_mean = []; years = []; lag0 = []
        for p in ps:
            full, hole = LR, np.delete(LR, np.s_[p:p + k], axis=0)
            per = []
            for g in range(0, LOOK + 1):
                sf = seats_arr(full[:p + k + g]); sh = seats_arr(hole[:p + g])
                dmk = masked_king(sf) - masked_king(sh)
                if g in acc: acc[g].append(dmk)
                if g < LOOK: per.append(abs(dmk))
            lifetime_mean.append(np.mean(per)); years.append(int(np.datetime64(int(E[p + k - 1]), "s").astype("datetime64[Y]").astype(int) + 1970))
            lag0.append(acc[0][-1])
            assert acc[900][-1] == 0.0, f"windows must coincide after {LOOK} anchors (p={p})"
        res["B_lifetime_replay"] = {"label": "research NC replay LR as a stand-in series, NOT the live file", "n_positions": len(ps),
                                    "positions_step_anchors": a.step, "d_masked_king_by_lag": {str(g): dist(acc[g]) for g in lags},
                                    "mean_abs_over_900_anchor_life": dist(lifetime_mean),
                                    "by_restart_year": {str(y): {"lag0": dist([v for v, yy in zip(lag0, years) if yy == y]),
                                                                 "life_mean": dist([v for v, yy in zip(lifetime_mean, years) if yy == y])}
                                                        for y in sorted(set(years))},
                                    "note_max": "|d masked| of 0.5 = one arm has king and fund both clipped to 0 (masked fallback 0.5): a seat-degenerate regime, not a typo"}
        out["by_k"][str(k)] = res
    json.dump(out, open(a.out, "w"), indent=1)
    for k, r in out["by_k"].items():
        print(f"k={k}: hole masked_king={out['hole_seats_at_first_resumed_anchor']['masked_king']:.5f} | "
              f"A1 |d masked| med {r['A1_blocks_from_live_file']['masked_king']['median_abs']:.5f} max {r['A1_blocks_from_live_file']['masked_king']['max_abs']:.5f} | "
              f"A2 med {r['A2_blocks_from_replay_2026']['masked_king']['median_abs']:.5f} max {r['A2_blocks_from_replay_2026']['masked_king']['max_abs']:.5f} | "
              f"yardstick 1-append med {r['yardstick_live_file']['one_append']['masked_king']['median_abs']:.5f} k-append med {r['yardstick_live_file'][f'{k}_appends']['masked_king']['median_abs']:.5f} | "
              f"B lag0 med {r['B_lifetime_replay']['d_masked_king_by_lag']['0']['median_abs']:.5f} life-mean med {r['B_lifetime_replay']['mean_abs_over_900_anchor_life']['median_abs']:.5f}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Alpha-101 (WorldQuant) + GTJA-191 (国泰君安) computable subset, SLOW variants.

> **created:** 2026-07-08 | **Session:** multi-asset-v2 phase-0b→A (0B) | **状态:** in-progress

Each formula returns an (nT, nS) factor from the OHLCV+vwap+signed panel. We implement the subset
computable from {open, high, low, close, volume, vwap, returns, signed-flow, adv} — SKIPPING any
formula that needs market-cap / industry / sector fields (no such fields for 14 mega-caps;
IndNeutralize → xsec-demean fallback). Every day-window integer n in the original is mapped to a
SLOW window W(n)=min(n,48) HOURS (×H bars) — sub-10min constructs die at 1h, so we test the slow
regime. Near-duplicate formulas are deduped. Each formula is wrapped in try/except so one bad
expression can't abort the sweep (errors are reported).
"""
from __future__ import annotations
import numpy as np
from multi_asset.alpha.ops import (
    delay, delta, ts_sum, ts_mean, ts_std, ts_min, ts_max, ts_argmax, ts_argmin, ts_rank,
    product, decay_linear, rank, scale, indneutralize, correlation, covariance,
    sign, log, absv, signedpower, mind, maxd, adv, H)


def W(n):
    return int(max(1, min(n, 48))) * H   # day-window n -> slow window of min(n,48) hours


def build_formulas(P):
    o, h, l, c, v, vw, sf, ret = P.open, P.high, P.low, P.close, P.vol, P.vwap, P.sf, P.returns
    def ADV(d):
        return adv(v, vw, W(d))
    F, errs = {}, {}
    def add(name, thunk):
        try:
            r = np.asarray(thunk(), dtype=np.float64)
            F[name] = r
        except Exception as e:
            errs[name] = f"{type(e).__name__}: {e}"

    # ---------------- WorldQuant Alpha-101 (computable subset) ----------------
    add("a101_001", lambda: rank(ts_argmax(signedpower(np.where(ret < 0, ts_std(ret, W(20)), c), 2.), W(5))) - 0.5)
    add("a101_002", lambda: -1 * correlation(rank(delta(log(v), 2)), rank((c - o) / o), W(6)))
    add("a101_003", lambda: -1 * correlation(rank(o), rank(v), W(10)))
    add("a101_004", lambda: -1 * ts_rank(rank(l), W(9)))
    add("a101_005", lambda: rank(o - ts_mean(vw, W(10))) * (-1 * absv(rank(c - vw))))
    add("a101_006", lambda: -1 * correlation(o, v, W(10)))
    add("a101_007", lambda: np.where(ADV(20) < v, -1 * ts_rank(absv(delta(c, 7)), W(60)) * sign(delta(c, 7)), -1.0))
    add("a101_008", lambda: -1 * rank((ts_sum(o, W(5)) * ts_sum(ret, W(5))) - delay(ts_sum(o, W(5)) * ts_sum(ret, W(5)), W(10))))
    add("a101_009", lambda: np.where(ts_min(delta(c, 1), W(5)) > 0, delta(c, 1),
                                     np.where(ts_max(delta(c, 1), W(5)) < 0, delta(c, 1), -1 * delta(c, 1))))
    add("a101_010", lambda: rank(np.where(ts_min(delta(c, 1), W(4)) > 0, delta(c, 1),
                                          np.where(ts_max(delta(c, 1), W(4)) < 0, delta(c, 1), -1 * delta(c, 1)))))
    add("a101_011", lambda: (rank(ts_max(vw - c, W(3))) + rank(ts_min(vw - c, W(3)))) * rank(delta(v, 3)))
    add("a101_012", lambda: sign(delta(v, 1)) * (-1 * delta(c, 1)))
    add("a101_013", lambda: -1 * rank(covariance(rank(c), rank(v), W(5))))
    add("a101_014", lambda: (-1 * rank(delta(ret, 3))) * correlation(o, v, W(10)))
    add("a101_015", lambda: -1 * ts_sum(rank(correlation(rank(h), rank(v), W(3))), W(3)))
    add("a101_016", lambda: -1 * rank(covariance(rank(h), rank(v), W(5))))
    add("a101_017", lambda: ((-1 * rank(ts_rank(c, W(10)))) * rank(delta(delta(c, 1), 1))) * rank(ts_rank(v / ADV(20), W(5))))
    add("a101_018", lambda: -1 * rank((ts_std(absv(c - o), W(5)) + (c - o)) + correlation(c, o, W(10))))
    add("a101_019", lambda: (-1 * sign((c - delay(c, W(7))) + delta(c, W(7)))) * (1 + rank(1 + ts_sum(ret, W(20)))))
    add("a101_020", lambda: ((-1 * rank(o - delay(h, 1))) * rank(o - delay(c, 1))) * rank(o - delay(l, 1)))
    add("a101_021", lambda: np.where((ts_mean(c, W(8)) + ts_std(c, W(8))) < ts_mean(c, W(2)), -1.0,
                                     np.where(ts_mean(c, W(2)) < (ts_mean(c, W(8)) - ts_std(c, W(8))), 1.0,
                                              np.where((v / ADV(20)) >= 1, 1.0, -1.0))))
    add("a101_022", lambda: -1 * (delta(correlation(h, v, W(5)), W(5)) * rank(ts_std(c, W(20)))))
    add("a101_023", lambda: np.where(ts_mean(h, W(20)) < h, -1 * delta(h, 2), 0.0))
    add("a101_024", lambda: np.where((delta(ts_mean(c, W(20)), W(20)) / delay(c, W(20))) <= 0.05,
                                     -1 * (c - ts_min(c, W(20))), -1 * delta(c, 3)))
    add("a101_025", lambda: rank(((-1 * ret) * ADV(20)) * vw * (h - c)))
    add("a101_026", lambda: -1 * ts_max(correlation(ts_rank(v, W(5)), ts_rank(h, W(5)), W(5)), W(3)))
    add("a101_028", lambda: scale((correlation(ADV(20), l, W(5)) + ((h + l) / 2)) - c))
    add("a101_030", lambda: ((1.0 - rank((sign(c - delay(c, 1)) + sign(delay(c, 1) - delay(c, 2))) + sign(delay(c, 2) - delay(c, 3)))) * ts_sum(v, W(5))) / ts_sum(v, W(20)))
    add("a101_031", lambda: rank(rank(rank(decay_linear(-1 * rank(rank(delta(c, W(10)))), W(10))))) + rank(-1 * delta(c, 3)) + sign(scale(correlation(ADV(20), l, W(12)))))
    add("a101_032", lambda: scale(ts_mean(c, W(7)) - c) + (20 * scale(correlation(vw, delay(c, W(5)), W(23)))))
    add("a101_033", lambda: rank(-1 * (1 - (o / c))))
    add("a101_034", lambda: rank((1 - rank(ts_std(ret, W(2)) / ts_std(ret, W(5)))) + (1 - rank(delta(c, 1)))))
    add("a101_035", lambda: ts_rank(v, W(32)) * (1 - ts_rank((c + h) - l, W(16))) * (1 - ts_rank(ret, W(32))))
    add("a101_037", lambda: rank(correlation(delay(o - c, 1), c, W(200))) + rank(o - c))
    add("a101_038", lambda: (-1 * rank(ts_rank(c, W(10)))) * rank(c / o))
    add("a101_039", lambda: (-1 * rank(delta(c, W(7)) * (1 - rank(decay_linear(v / ADV(20), W(9)))))) * (1 + rank(ts_sum(ret, W(250)))))
    add("a101_040", lambda: (-1 * rank(ts_std(h, W(10)))) * correlation(h, v, W(10)))
    add("a101_041", lambda: ((h * l) ** 0.5) - vw)
    add("a101_042", lambda: rank(vw - c) / rank(vw + c))
    add("a101_043", lambda: ts_rank(v / ADV(20), W(20)) * ts_rank(-1 * delta(c, W(7)), W(8)))
    add("a101_044", lambda: -1 * correlation(h, rank(v), W(5)))
    add("a101_045", lambda: -1 * (rank(ts_mean(delay(c, W(5)), W(20))) * correlation(c, v, W(2)) * rank(correlation(ts_sum(c, W(5)), ts_sum(c, W(20)), W(2)))))
    add("a101_046", lambda: np.where((delay(c, W(20)) - delay(c, W(10))) / W(10) - (delay(c, W(10)) - c) / W(10) > 0.25, -1.0,
                                     np.where((delay(c, W(20)) - delay(c, W(10))) / W(10) - (delay(c, W(10)) - c) / W(10) < 0, 1.0, -1 * (c - delay(c, 1)))))
    add("a101_047", lambda: ((rank(1 / c) * v) / ADV(20)) * ((h * rank(h - c)) / ts_mean(h, W(5))) - rank(vw - delay(vw, W(5))))
    add("a101_049", lambda: np.where((delay(c, W(20)) - delay(c, W(10))) / W(10) - (delay(c, W(10)) - c) / W(10) < -0.1, 1.0, -1 * (c - delay(c, 1))))
    add("a101_050", lambda: -1 * ts_max(rank(correlation(rank(v), rank(vw), W(5))), W(5)))
    add("a101_051", lambda: np.where((delay(c, W(20)) - delay(c, W(10))) / W(10) - (delay(c, W(10)) - c) / W(10) < -0.05, 1.0, -1 * (c - delay(c, 1))))
    add("a101_052", lambda: ((-1 * ts_min(l, W(5))) + delay(ts_min(l, W(5)), W(5))) * rank((ts_sum(ret, W(240)) - ts_sum(ret, W(20))) / W(220)) * ts_rank(v, W(5)))
    add("a101_053", lambda: -1 * delta(((c - l) - (h - c)) / (c - l), W(9)))
    add("a101_054", lambda: (-1 * ((l - c) * (o ** 5))) / ((l - h) * (c ** 5)))
    add("a101_055", lambda: -1 * correlation(rank((c - ts_min(l, W(12))) / (ts_max(h, W(12)) - ts_min(l, W(12)))), rank(v), W(6)))
    add("a101_057", lambda: -1 * ((c - vw) / decay_linear(rank(ts_argmax(c, W(30))), 2)))
    add("a101_060", lambda: -1 * ((2 * scale(rank(((c - l) - (h - c)) / (h - l) * v))) - scale(rank(ts_argmax(c, W(10))))))
    add("a101_064", lambda: -1 * (rank(correlation(ts_sum((o * 0.178) + (l * 0.822), W(13)), ts_sum(ADV(120), W(13)), W(17))) < rank(delta((((h + l) / 2) * 0.178) + (vw * 0.822), W(4)))))
    add("a101_065", lambda: -1 * (rank(correlation(((o * 0.0097) + (vw * 0.990)), ts_sum(ADV(60), W(9)), W(6))) < rank(o - ts_min(o, W(14)))))
    add("a101_066", lambda: -1 * (rank(decay_linear(delta(vw, W(4)), W(7))) + ts_rank(decay_linear(((l * 0.965) + (l * 0.035) - vw) / (o - ((h + l) / 2)), W(11)), W(7))))
    add("a101_068", lambda: -1 * (ts_rank(correlation(rank(h), rank(ADV(15)), W(9)), W(14)) < rank(delta((c * 0.518) + (l * 0.482), 1))))
    add("a101_071", lambda: maxd(ts_rank(decay_linear(correlation(ts_rank(c, W(3)), ts_rank(ADV(180), W(12)), W(18)), W(4)), W(16)),
                                 ts_rank(decay_linear(rank((l + o) - (vw + vw)) ** 2, W(16)), W(4))))
    add("a101_072", lambda: rank(decay_linear(correlation((h + l) / 2, ADV(40), W(9)), W(10))) / rank(decay_linear(correlation(ts_rank(vw, W(4)), ts_rank(v, W(19)), W(7)), W(3))))
    add("a101_073", lambda: -1 * maxd(rank(decay_linear(delta(vw, W(5)), W(3))),
                                      ts_rank(decay_linear((delta((o * 0.147) + (l * 0.853), W(2)) / ((o * 0.147) + (l * 0.853))) * -1, W(3)), W(16))))
    add("a101_074", lambda: -1 * (rank(correlation(c, ts_sum(ADV(30), W(37)), W(15))) < rank(correlation(rank((h * 0.026) + (vw * 0.974)), rank(v), W(11)))))
    add("a101_075", lambda: (rank(correlation(vw, v, W(4))) < rank(correlation(rank(l), rank(ADV(50)), W(12)))).astype(float))
    add("a101_077", lambda: mind(rank(decay_linear(((h + l) / 2) + h - (vw + h), W(20))), rank(decay_linear(correlation((h + l) / 2, ADV(40), W(3)), W(6)))))
    add("a101_078", lambda: rank(correlation(ts_sum((l * 0.352) + (vw * 0.648), W(20)), ts_sum(ADV(40), W(20)), W(7))) ** rank(correlation(rank(vw), rank(v), W(6))))
    add("a101_081", lambda: -1 * (rank(log(product(rank(rank(correlation(vw, ts_sum(ADV(10), W(50)), W(8))) ** 4), W(15)))) < rank(correlation(rank(vw), rank(v), W(5)))))
    add("a101_083", lambda: (rank(delay((h - l) / ts_mean(c, W(5)), 2)) * rank(rank(v))) / (((h - l) / ts_mean(c, W(5))) / (vw - c)))
    add("a101_084", lambda: signedpower(ts_rank(vw - ts_max(vw, W(15)), W(21)), delta(c, W(5))))
    add("a101_085", lambda: rank(correlation((h * 0.877) + (c * 0.123), ADV(30), W(10))) ** rank(correlation(ts_rank((h + l) / 2, W(4)), ts_rank(v, W(10)), W(7))))
    add("a101_086", lambda: -1 * (ts_rank(correlation(c, ts_sum(ADV(20), W(15)), W(6)), W(20)) < rank((o + c) - (vw + o))))
    add("a101_088", lambda: mind(rank(decay_linear((rank(o) + rank(l)) - (rank(h) + rank(c)), W(8))),
                                 ts_rank(decay_linear(correlation(ts_rank(c, W(8)), ts_rank(ADV(60), W(21)), W(8)), W(7)), W(3))))
    add("a101_092", lambda: mind(ts_rank(decay_linear((((h + l) / 2 + c) < (l + o)).astype(float), W(15)), W(19)),
                                 ts_rank(decay_linear(correlation(rank(l), rank(ADV(30)), W(8)), W(7)), W(7))))
    add("a101_094", lambda: -1 * (rank(vw - ts_min(vw, W(12))) ** ts_rank(correlation(ts_rank(vw, W(20)), ts_rank(ADV(60), W(4)), W(18)), W(3))))
    add("a101_095", lambda: (rank(o - ts_min(o, W(12))) < ts_rank(rank(correlation(ts_sum((h + l) / 2, W(19)), ts_sum(ADV(40), W(19)), W(13))) ** 5, W(12))).astype(float))
    add("a101_096", lambda: -1 * maxd(ts_rank(decay_linear(correlation(rank(vw), rank(v), W(4)), W(4)), W(8)),
                                      ts_rank(decay_linear(ts_argmax(correlation(ts_rank(c, W(7)), ts_rank(ADV(60), W(4)), W(4)), W(13)), W(14)), W(13))))
    add("a101_098", lambda: rank(decay_linear(correlation(vw, ts_sum(ADV(5), W(26)), W(5)), W(7))) - rank(decay_linear(ts_rank(ts_argmin(correlation(rank(o), rank(ADV(15)), W(21)), W(9)), W(7)), W(8))))
    add("a101_099", lambda: -1 * (rank(correlation(ts_sum((h + l) / 2, W(20)), ts_sum(ADV(60), W(20)), W(9))) < rank(correlation(l, v, W(6)))))
    add("a101_101", lambda: (c - o) / ((h - l) + 0.001))

    # ---------------- GTJA-191 (国泰君安) distinctive computable subset ----------------
    add("gtja_002", lambda: -1 * delta(((c - l) - (h - c)) / (h - l), 1))
    add("gtja_004", lambda: np.where((ts_mean(c, W(8)) + ts_std(c, W(8))) < ts_mean(c, W(2)), -1.0,
                                     np.where(ts_mean(c, W(2)) < (ts_mean(c, W(8)) - ts_std(c, W(8))), 1.0,
                                              np.where(v / ts_mean(v, W(20)) >= 1, 1.0, -1.0))))
    add("gtja_006", lambda: -1 * rank(sign(delta((o * 0.85) + (h * 0.15), W(4)))))
    add("gtja_009", lambda: ts_mean(((h + l) / 2 - (delay(h, 1) + delay(l, 1)) / 2) * (h - l) / v, W(7)))
    add("gtja_014", lambda: c - delay(c, W(5)))
    add("gtja_015", lambda: o / delay(c, 1) - 1)
    add("gtja_018", lambda: c / delay(c, W(5)))
    add("gtja_019", lambda: np.where(c < delay(c, W(5)), (c - delay(c, W(5))) / delay(c, W(5)),
                                     np.where(c == delay(c, W(5)), 0.0, (c - delay(c, W(5))) / c)))
    add("gtja_020", lambda: (c - delay(c, W(6))) / delay(c, W(6)) * 100)
    add("gtja_022", lambda: ts_mean((c - ts_mean(c, W(6))) / ts_mean(c, W(6)) - delay((c - ts_mean(c, W(6))) / ts_mean(c, W(6)), 3), W(12)))
    add("gtja_029", lambda: (c - delay(c, W(6))) / delay(c, W(6)) * v)
    add("gtja_031", lambda: (c - ts_mean(c, W(12))) / ts_mean(c, W(12)) * 100)
    add("gtja_034", lambda: ts_mean(c, W(12)) / c)
    add("gtja_046", lambda: (ts_mean(c, W(3)) + ts_mean(c, W(6)) + ts_mean(c, W(12)) + ts_mean(c, W(24))) / (4 * c))
    add("gtja_053", lambda: ts_mean((c > delay(c, 1)).astype(float), W(12)) * 100)
    add("gtja_058", lambda: ts_mean((c > delay(c, 1)).astype(float), W(20)) * 100)
    add("gtja_066", lambda: (c - ts_mean(c, W(6))) / ts_mean(c, W(6)) * 100)
    add("gtja_070", lambda: ts_std((c - delay(c, 1)) / delay(c, 1), W(6)))
    add("gtja_101", lambda: -1 * (rank(correlation(c, ts_sum(ts_mean(v, W(30)), W(37)), W(15))) < rank(correlation(rank((h * 0.1) + (vw * 0.9)), rank(v), W(11)))))

    if errs:
        print(f"[formulas] {len(errs)} errored (skipped): " + ", ".join(f"{k}({e.split(':')[0]})" for k, e in errs.items()), flush=True)
    return F

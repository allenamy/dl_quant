"""Emit v2-schema pilot logs from the SHADOW book (§10 acceptance requirement (ii)).

WHY: "pilot day 1 must not be the first time this schema is used." The shadow already produces the
same positions the pilot will trade, so it can exercise the full v2 record path -- orders, child
fills, funding ledger, position read-back, daily NAV -- against real signal data, every day, before
any money is at risk.

★ WHAT THIS IS AND IS NOT:
  IS   -- a real exercise of the schema, the writer's validation, and pilot_metrics end-to-end on
          live signal data, so field gaps and definition gaps surface now.
  IS NOT -- evidence about execution quality. Fills here are SIMULATED (maker fill-rate 0.51,
          k=900 window, tick-corrected cost). In particular `position_readback` is written with
          source="shadow_sim" and is derived from our own simulated fills, so M5's drift-detection
          property is exercised STRUCTURALLY but not ADVERSARIALLY -- there is no real venue to
          disagree with us. That property only becomes real in the pilot.

*** MOCK ONLY. Connects to no exchange, holds no credentials, places no orders. ***

Usage:
    python engine/live/shadow_pilot_log.py [--days_back 7]
Out: exports/live/pilot_log/<YYYYMMDD>/{orders,fills,anchors,funding,position_readback,daily_nav}.jsonl
"""
from __future__ import annotations
import argparse, hashlib, os, sys
import numpy as np
import pandas as pd

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA)
sys.path.insert(0, MA + "/engine/live")
import pilot_log as PL
import regime_classifier as RC

ROOT = MA + "/exports/live/pilot_log"
GROSS_USD = 50_000.0            # P0 rung
FILL_RATE = 0.51                # conservative maker fill-rate at k=900 (same as paper_pnl)
MAKER_FEE_BPS, TAKER_FEE_BPS = 1.5, 4.5      # HL base tier
MIN_NOTIONAL = 10.0             # HL
K_WINDOW_MS = 900_000
WEIGHTS = {"king": 0.30, "s2": 0.10, "funding": 0.30, "size": 0.30}


def panel_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 22):
            h.update(chunk)
    return h.hexdigest()[:16]


def run(days_back=7, verbose=True):
    from engine.panel_source import PanelSource
    from challenger import _positions_w
    panel = MA + "/exports/live/wide_dl_live.npz"
    src = PanelSource(panel=panel, king=MA + "/exports/live/king_pred_live.npz",
                      s2=MA + "/exports/live/s2_pred_live.npz")
    ph = panel_hash(panel)
    anchors = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king)
                                & np.isfinite(src.s2)).any(1))[0])
    last = int(anchors[-1])
    anchors = anchors[anchors >= last - days_back * 24]
    book = _positions_w(src, anchors, WEIGHTS)
    # Regime computed straight from the panel we are already holding. Going via the day files
    # coupled us to exact anchor-timestamp matching and silently yielded "unknown"; the label and
    # the order it annotates should come from one source.
    regime_by_ts = {r["anchor_ts"]: r["regime"] for r in RC.classify(src, anchors)}
    rng = np.random.default_rng(20260725)
    syms = np.array(src.symbols)

    fund_idx = src.ch.index("funding_ema")
    prev_notional = {}
    loggers, n_orders, n_fills = {}, 0, 0
    day_pnl = {}

    # ★ IDEMPOTENCY (found by the §9.5-①b kill-injection): the log is append-only JSONL, so a run
    # killed halfway and restarted would append the same anchors a second time and silently double
    # every notional. Anchors already present for a day are skipped, which makes re-running a
    # partially-completed day safe -- the property a cron-restarted job actually needs.
    already = set()
    for d in set(pd.to_datetime(src.ts[anchors], unit="ms", utc=True).strftime("%Y%m%d")):
        for row in PL.read_day(ROOT, d)["orders"]:
            already.add(int(row["anchor_ts"]))
    # ★ RESUMING MUST ALSO RESTORE STATE, not just skip work. Skipping already-logged anchors while
    # restarting `prev_notional` from {} makes the readback written after the resume inconsistent
    # with the readback written before it -- which the §4-5b/§4-7 drift detector then (correctly)
    # reports as an unexplained position change. Idempotency of the WRITE is not enough; the
    # accumulated state the writes describe has to carry across the resume too.
    if already:
        latest_ts, latest_rb = -1, {}
        for d in sorted({pd.to_datetime(src.ts[anchors], unit="ms", utc=True).strftime("%Y%m%d")[i]
                         for i in range(len(anchors))}):
            for r in PL.read_day(ROOT, d)["position_readback"]:
                if int(r["anchor_ts"]) >= latest_ts:
                    if int(r["anchor_ts"]) > latest_ts:
                        latest_ts, latest_rb = int(r["anchor_ts"]), {}
                    latest_rb[r["symbol"]] = float(r["venue_position_notional"])
        prev_notional.update(latest_rb)
        if verbose:
            print(f"[shadow_pilot_log] {len(already)} anchors already logged — skipping "
                  f"(idempotent); restored {len(latest_rb)} positions from the last readback",
                  flush=True)

    for t in anchors:
        ti = int(t)
        ats = int(src.ts[ti])
        if ats in already:
            continue
        day = pd.to_datetime(ats, unit="ms", utc=True).strftime("%Y%m%d")
        if day not in loggers:
            loggers[day] = PL.PilotLogger(ROOT, day)
        lg = loggers[day]
        m, w = book[ti]
        regime = regime_by_ts.get(ats, 'unknown')
        mid_vec = {}
        # a synthetic but deterministic mid per symbol (shadow has no book); only RELATIVE moves
        # matter for the schema exercise, and they are marked as simulated throughout.
        for j in m:
            mid_vec[str(syms[j])] = float(100.0 * (1.0 + 0.001 * rng.standard_normal()))
        gross_at = {str(syms[j]): float(w[k] * GROSS_USD) for k, j in enumerate(m)}
        skipped = 0
        realized = 0.0
        for k, j in enumerate(m):
            s = str(syms[j])
            tgt_notional = gross_at[s]
            prev = prev_notional.get(s, 0.0)
            delta = tgt_notional - prev
            mid_a = mid_vec[s]
            tw, pw = float(w[k]), prev / GROSS_USD
            if abs(delta) < MIN_NOTIONAL:
                skipped += 1
                lg.order(anchor_ts=ats, symbol=s, side="none", target_w=tw, prev_w=pw,
                         intended_notional=delta, order_type="maker", submit_ts=None,
                         price_submit=None, mid_at_submit=None, mid_at_anchor=mid_a,
                         filled_notional=0.0, avg_fill_px=None, first_fill_ts=None,
                         last_fill_ts=None, cancel_ts=None, fee_paid=0.0,
                         rebalance_id=f"r{ats}", attempt_idx=1,
                         terminal_reason="skipped_min_notional", notional_currency="USD")
                n_orders += 1
                continue
            side = "buy" if delta > 0 else "sell"
            sgn = 1.0 if delta > 0 else -1.0
            remaining = abs(delta)
            for att in (1, 2):
                if remaining < 1e-9:
                    break
                is_topup = att == 2
                otype = "topup_taker" if is_topup else "maker"
                sub_ts = ats + (0 if att == 1 else K_WINDOW_MS)
                frac = 1.0 if is_topup else float(np.clip(rng.normal(FILL_RATE, 0.2), 0.0, 1.0))
                filled = remaining * frac
                if filled < 1e-9:
                    lg.order(anchor_ts=ats, symbol=s, side=side, target_w=tw, prev_w=pw,
                             intended_notional=sgn * remaining, order_type=otype,
                             submit_ts=sub_ts, price_submit=mid_a, mid_at_submit=mid_a,
                             mid_at_anchor=mid_a, filled_notional=0.0, avg_fill_px=None,
                             first_fill_ts=None, last_fill_ts=None,
                             cancel_ts=sub_ts + K_WINDOW_MS, fee_paid=0.0,
                             rebalance_id=f"r{ats}", attempt_idx=att,
                             terminal_reason="partial_expired", notional_currency="USD")
                    n_orders += 1
                    break
                nf = int(rng.integers(1, 4))
                wts = rng.dirichlet(np.ones(nf))
                fts = sorted(int(sub_ts + rng.integers(1000, K_WINDOW_MS - 1000)) for _ in range(nf))
                pxs = [mid_a * (1 + sgn * abs(rng.normal(2e-5, 8e-5))) for _ in range(nf)]
                for c in range(nf):
                    lg.fill(anchor_ts=ats, symbol=s, side=side, order_type=otype, attempt_idx=att,
                            fill_ts=fts[c], fill_px=float(pxs[c]),
                            fill_notional=float(filled * wts[c]),
                            mid_at_fill_plus_60s=float(pxs[c] * (1 + sgn * rng.normal(1.5e-5, 1e-4))),
                            rebalance_id=f"r{ats}")
                    n_fills += 1
                avg_px = float(np.dot(wts, pxs))
                fee = filled * (MAKER_FEE_BPS if not is_topup else TAKER_FEE_BPS) * 1e-4
                term = ("filled" if frac > 0.999 else
                        ("abandoned_max_attempts" if is_topup else "partial_expired"))
                lg.order(anchor_ts=ats, symbol=s, side=side, target_w=tw, prev_w=pw,
                         intended_notional=sgn * remaining, order_type=otype, submit_ts=sub_ts,
                         price_submit=mid_a, mid_at_submit=mid_a, mid_at_anchor=mid_a,
                         filled_notional=float(filled), avg_fill_px=avg_px,
                         first_fill_ts=fts[0], last_fill_ts=fts[-1],
                         cancel_ts=(sub_ts + K_WINDOW_MS) if frac < 1 else None,
                         fee_paid=float(fee), rebalance_id=f"r{ats}", attempt_idx=att,
                         terminal_reason=term, notional_currency="USD")
                n_orders += 1
                prev_notional[s] = prev_notional.get(s, 0.0) + sgn * filled
                remaining -= filled
            realized += abs(prev_notional.get(s, 0.0))
        lg.anchor(anchor_ts=ats, target_vector_hash=hashlib.sha1(w.tobytes()).hexdigest()[:12],
                  realized_gross=float(realized), target_gross=GROSS_USD,
                  n_names_skipped=int(skipped), regime_at_anchor=regime,
                  mid_at_anchor_vector=mid_vec, factor_version="funding_ema_broken_v1",
                  panel_hash=ph)
        for s, v in prev_notional.items():
            lg.position_readback(anchor_ts=ats, symbol=s, venue_position_notional=float(v),
                                 source="shadow_sim")
        # funding ledger: settle on every other anchor (8h coins), from the panel's funding channel
        if (ats // (4 * 3600_000)) % 2 == 0:
            for k, j in enumerate(m):
                s = str(syms[j])
                rate = float(src.CH[ti, j, fund_idx])
                pos = prev_notional.get(s, 0.0)
                lg.funding(settlement_ts=ats, symbol=s, position_notional_at_settlement=pos,
                           funding_rate=rate, funding_paid=float(-pos * rate))
        ret = src.Y4[ti]
        ok = np.isfinite(ret)
        pnl = float(np.nansum(np.array([prev_notional.get(str(syms[j]), 0.0) for j in m])[ok[m]]
                              * ret[m][ok[m]]))
        day_pnl[day] = day_pnl.get(day, 0.0) + pnl

    for day, lg in loggers.items():
        if not PL.read_day(ROOT, day)["daily_nav"]:          # idempotent: one NAV row per day
            lg.daily_nav(day=int(day), target_gross=GROSS_USD,
                         nav=float(100_000.0 + day_pnl.get(day, 0.0)),
                         realised_pnl=float(day_pnl.get(day, 0.0)), unrealised_pnl=0.0)
        lg.close()
    if verbose:
        print(f"[shadow_pilot_log] {len(loggers)} days | {n_orders} orders | {n_fills} child fills "
              f"-> {ROOT}", flush=True)
        print(f"[shadow_pilot_log] days: {sorted(loggers)}", flush=True)
    return sorted(loggers)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days_back", type=int, default=7)
    a = ap.parse_args()
    run(days_back=a.days_back)

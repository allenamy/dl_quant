#!/usr/bin/env python3
"""m3_hook.py — ★ M3b VARIANT (docs/AMENDMENT_1_m3_beta_overlay_2026-09-23.md, commit 912788743) of the M3 hook (prereg
docs/PREREG_m3_beta_overlay_executed_book_2026-09-23.md, 24c3f803f). Diff vs the M3 hook (sha db05d136): receipts/M3B_HOOK_vs_M3_HOOK.diff.
M3b's ONLY change (the amendment's "唯一改动"): BTC's COMBINED target = base BTC target + hedge leg, and the executor's dust (2 × min-notional)
judgement is applied to the COMBINED target, not to the base BTC target alone. Operationally, at an anchor that reaches the reshape:
  * BTC is "dust-only untradable" iff it is in the call's untradable set, NOT in force_flat (per-name stop), W24H-tradable, not in the meta
    set, not in cooldown (per_name_stop.active_sets at t_dec), not a held-exit name (held but absent from the published target), and its
    PRE-reshape base target is below 2 × min_notional (EXT.below_min_notional, the executor's own function) — i.e. dust is the only reason;
  * the certified reshape runs exactly as in the base (BTC popped if unheld, clamped if held; every other name bitwise the base's);
  * β_exec and the hedge −β_exec·Gs are computed exactly as in M3 (on the executed target, BTC's executed base value included);
  * combined = executed base BTC value + hedge; if EXT.below_min_notional says the combined value is NOT dust ⇒ target[BTC] = combined and BTC
    is released from the clamp's reduce-only lists (reduced / add_blocked / flatten_only / popped) so plan() may trade it both ways
    (cause 'applied_via_combined'); if the combined value is still dust ⇒ nothing is touched (cause 'btc_combined_dust');
  * every other untradability reason of BTC (venue, stop, cooldown, meta, held-exit) is a NAME-level fact the combined size cannot change ⇒
    skipped exactly as in M3; a tradable BTC is hedged exactly as in M3 (a combined value below 2 × min-notional there is only COUNTED,
    'm3h_combined_below_2floor_tradable_branch', never acted on — M3's behaviour unchanged in that branch);
  * control mode touches neither the target nor the clamp lists (zero-hedge control ⇒ bitwise the base).
Everything below this paragraph is the M3 hook's text, unchanged except where M3b adds the two causes, two record fields and the branch.

M3 (original description): the BTC-beta overlay leg with the book beta computed on the EXECUTED target (after the executor's POP → RESHAPE →
CLAMP) instead of on the published target.

DERIVED FROM m2_hook.py (M2 route H; docs/RESULT_m2_btc_overlay_2026-09-23.md, ac9a7274a; device sha e6e755ea). The diff is committed as
receipts/M3_HOOK_vs_M2_HOOK.diff. What changed, and nothing else:
  (1) THE BETA OBJECT. M2 read a precomputed per-anchor hedge h(A) = −β_book(published target)/Σ|w| from a table. M3 computes it at run
      time, inside the reshape call, on the target the certified executor has just produced:
          w_exec,s = target_s / Gs            target = the executor's target AFTER apply_withhold_and_reshape (POP → RESHAPE → CLAMP), notional;
                                              Gs = the executor's own sizing gross passed to that call (equity × gross_mult)
          β_exec   = Σ_s w_exec,s · β_s(A)    summed in sorted-symbol order; β_s(A) = the M2 formula (m2_lib.bars_4h / betas_at, UNCHANGED:
                                              180 completed 4h bars ending at A, OLS with intercept vs BTCUSDT, >= 120 valid else 1.0,
                                              clip [−1, 4], BTC = 1), read from the per-anchor β matrix BETA_M3_full.npz (m3_build_beta.py)
          hedge    = −β_exec × Gs  added to target[BTCUSDT]      (prereg §2 step 4: extra BTC notional = −β_exec × book gross notional)
      ⇒ hedge notional = −Σ_s target_s·β_s(A): the executed target's dollar beta, offset; not reshaped (added after the call returns).
  (2) the table is the β matrix (anchor × symbol) instead of a per-anchor hedge scalar.
  (3) a 'control' mode: every quantity is computed and recorded, the target is NEVER touched (zero-hedge control: must reproduce the
      base paths bitwise).
  (4) RECORDING ONLY (no behaviour): per trading anchor the beta of the pre-reshape target, β_exec, net / gross of the executed target,
      intended / applied hedge, the skip cause (with a sub-cause for BTC untradable), BTC's plan row and the planned-book beta; every
      BTCUSDT trade and funding charge — into a sidecar npz per (run, seed); counters in the path json `diag` (m3h_*).
KEPT FROM M2 ROUTE H (semantics; the lead's brief: only the beta object changes):
  * the hedge is added after the certified apply_withhold_and_reshape returns and before plan(); every other name bitwise as the base;
  * HOLD / HALT / invalid-target anchors never reach the reshape call ⇒ the held book keeps its BTC position (prereg §2 step 5);
  * a hedge of exactly 0.0 changes nothing (no BTC entry is created);
  * BTC in the call's untradable set or in force_flat (per-name stop / cooldown / not W24H-tradable / dust / held-exit) ⇒ no hedge at
    that anchor, counted by cause;
  * the certified launcher (baseline_tables devices_v3/bt_launch.py, unchanged) runs in-process with bt_hist_sim31.make_sim_class wrapped;
    the hook is active only for runs whose tag's arm (text before the first '|') is a key of the config's m3_hook.arms; the wrapper REFUSES a
    config with any run whose tag prefix is not hooked (an inert hook would reproduce the base silently).
Unknown is not zero: an anchor absent from the β table, a symbol absent from its axis, a non-finite β, or Gs <= 0 raises (the path dies,
rc != 0). An EMPTY executed target (every name popped) is a named case: nothing to hedge, β_exec recorded as NaN, counted.
Provenance: the run config carries m3_hook = {device, device_sha256, mode, beta: {npz, sha256}, arms: {arm: mode}}; the wrapper refuses
unless its own sha and the β sha match.
usage:
  run: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B m3_hook.py PATH,HOME,LC_CTYPE <config.json> [bt_launch args…]
"""
import os, sys, json, copy, types, hashlib

import numpy as np

DEV = "/workspace/baseline_tables_2026-09-19/devices_v3"
BTC = "BTCUSDT"
MODES = ("overlay", "control")
CAUSE = {"applied": 0, "zero_hedge": 1, "btc_force_flat": 2, "btc_not_w24h_tradable": 3, "btc_dust": 4, "btc_untradable_other": 5,
         "empty_target": 6, "applied_via_combined": 7, "btc_combined_dust": 8}          # 7, 8: M3b
APPLIED = (0, 7)                                                                          # M3b: both deliver the hedge
VARIANT = "M3b"
PLAN_SKIP = {"planned": 0, "no_plan_row": 1, "ua_frozen": 2, "skipped_min_notional": 3, "skipped_no_mid": 4, "other_skip": 9}
TKIND = {"first": 1, "later": 2, "flatten": 3, "exit_completion": 4}
REC_FIELDS = ("A", "gs", "beta_pre", "beta_exec", "net_exec", "gross_exec", "n_target", "add_intended", "add_applied", "btc_before",
              "btc_after", "cause", "btc_held_notional", "beta_after", "pos_beta", "plan_beta", "btc_plan_notional", "btc_plan_skip", "n_plans",
              "btc_dust_only", "btc_released", "combined_small")                          # last three: M3b


class M3Error(Exception):
    pass


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


class BetaTable:
    """the per-anchor β matrix (m3_build_beta.py): row lookup by exact anchor, column by symbol; every value finite, BTC column exactly 1"""
    def __init__(self, npz, sha256=None):
        if sha256 is not None and sha(npz) != sha256: raise M3Error(f"beta table sha mismatch: {npz}")
        Z = np.load(npz)
        self.anchor = Z["anchor"].astype(np.int64); self.B = np.ascontiguousarray(Z["beta"], np.float64)
        self.symbols = [str(s) for s in Z["symbols"]]
        if len(self.anchor) == 0 or self.B.shape != (len(self.anchor), len(self.symbols)): raise M3Error("beta table empty or malformed")
        if not np.all(np.isfinite(self.B)): raise M3Error("non-finite beta in table")
        self.row = {int(a): i for i, a in enumerate(self.anchor.tolist())}
        self.col = {s: j for j, s in enumerate(self.symbols)}
        if BTC not in self.col or not np.all(self.B[:, self.col[BTC]] == 1.0): raise M3Error("BTC column must be exactly 1")

    def row_of(self, A):
        i = self.row.get(int(A))
        if i is None: raise M3Error(f"anchor {A} not in the beta table")
        return self.B[i]


def book_beta(book, gs, brow, col):
    """Σ_s (book_s / Gs) · β_s in sorted-symbol order, with net and gross in the same units; book = {symbol: notional}"""
    gs = float(gs)
    if not (gs > 0): raise M3Error(f"sizing gross must be > 0, got {gs}")
    b = 0.0; net = 0.0; gro = 0.0
    for s in sorted(book):
        j = col.get(s)
        if j is None: raise M3Error(f"symbol {s} not on the beta axis")
        w = float(book[s]) / gs
        b += w * float(brow[j]); net += w; gro += abs(w)
    return b, net, gro


def apply_overlay(target, untradable, force_flat, gs, brow, col, mode, btc_subcause=None, btc_dust_only=False, is_dust=None):
    """formula §2 steps 1–4 on the EXECUTED target (the dict the certified reshape just returned in place). overlay ⇒ mutates target[BTC];
    control ⇒ never touches target. btc_subcause(): called only when BTC is untradable, returns one of the btc_* cause names.
    Returns the per-anchor record (no NaN except β_exec on an empty target).
    M3b: btc_dust_only = BTC is untradable ONLY because its base target is dust; is_dust(v) = the executor's dust test on a BTC notional v.
    Then the combined value (executed base BTC + hedge) decides: not dust ⇒ 'applied_via_combined', dust ⇒ 'btc_combined_dust'."""
    if btc_dust_only and is_dust is None: raise M3Error("btc_dust_only needs is_dust")
    if mode not in MODES: raise M3Error(f"mode {mode!r}")
    gs = float(gs)
    if not (gs > 0): raise M3Error(f"sizing gross must be > 0, got {gs}")
    rec = {"gs": gs, "n_target": len(target), "btc_before": float(target.get(BTC, 0.0)), "add_applied": 0.0,
           "btc_dust_only": 1.0 if btc_dust_only else 0.0, "combined_small": 0.0}
    if not target:
        rec.update(beta_exec=float("nan"), net_exec=0.0, gross_exec=0.0, add_intended=0.0, cause=CAUSE["empty_target"], btc_after=0.0, beta_after=float("nan"))
        return rec
    b, net, gro = book_beta(target, gs, brow, col)
    add = -b * gs                                               # = −β_exec × book gross notional
    rec.update(beta_exec=b, net_exec=net, gross_exec=gro, add_intended=add)
    ut = set(untradable); ff = set(force_flat or ())
    if add == 0.0:                                              # M2 order: a zero hedge touches nothing
        cause = "zero_hedge"
    elif BTC in ff:                                             # M2 rule, verbatim: a per-name stop forces BTC flat
        cause = "btc_force_flat"
    elif BTC in ut and btc_dust_only:                           # ★ M3b: dust is judged on the COMBINED target
        cause = "btc_combined_dust" if is_dust(rec["btc_before"] + add) else "applied_via_combined"
    elif BTC in ut:                                             # M2 rule, verbatim: a name-level reason the size cannot change
        cause = btc_subcause() if btc_subcause is not None else "btc_untradable_other"
    else:
        cause = "applied"
        if is_dust is not None and is_dust(rec["btc_before"] + add): rec["combined_small"] = 1.0     # counted only (M3 behaviour kept)
    if mode == "overlay" and cause in ("applied", "applied_via_combined"):
        target[BTC] = rec["btc_before"] + add
        rec["add_applied"] = add
    rec["cause"] = CAUSE[cause]
    rec["btc_after"] = float(target.get(BTC, 0.0))
    rec["beta_after"] = book_beta(target, gs, brow, col)[0]
    return rec


def hooked_class_factory(orig_make, beta, arms, sidecar_dir=None):
    """arms: {arm: 'overlay' | 'control'}; sidecar_dir None ⇒ records stay in memory (S.m3_rec, S.m3_tr, S.m3_fu)"""
    for a, m in arms.items():
        if m not in MODES: raise M3Error(f"arm {a}: mode {m!r}")

    def make_sim_class(ES):
        Base = orig_make(ES)

        class HistSim31M3H(Base):
            def __init__(self, *a, **k):
                super().__init__(*a, **k)
                arm = self.tag.split("|")[0]
                self.m3_mode = arms.get(arm)
                self._m3_A = None; self._m3_cur = None
                self.m3_rec, self.m3_tr, self.m3_fu = [], [], []
                if self.m3_mode is not None:
                    XP = copy.copy(self.X)
                    self._m3_plan_inner = self.X.BX.RebalanceExecutor.plan          # _plan_ua under UA-FREEZE-EXCLUDE, else the executor's own
                    XP.AL = types.SimpleNamespace(apply_withhold_and_reshape=self._m3_awr)
                    XP.BX = types.SimpleNamespace(RebalanceExecutor=types.SimpleNamespace(plan=self._m3_plan))
                    self.X = XP
                    self.diag["m3h_active"] = 1.0; self.diag["m3h_overlay"] = 1.0 if self.m3_mode == "overlay" else 0.0

            def on_anchor(self, A):
                self._m3_A = int(A); self._m3_cur = None
                try:
                    return super().on_anchor(A)
                finally:
                    if self._m3_cur is not None: self.m3_rec.append(self._m3_cur)
                    self._m3_A = None; self._m3_cur = None

            def _m3_awr(self, target, held, untradable, sizing_gross, **kw):
                A = self._m3_A
                if A is None: raise M3Error("m3h: reshape called outside on_anchor")
                brow = beta.row_of(A)                                             # raises for an anchor off the table
                pre = dict(target)
                gs = float(sizing_gross)
                beta_pre = book_beta(pre, gs, brow, beta.col)[0] if pre else float("nan")
                out = self.X0.AL.apply_withhold_and_reshape(target, held, untradable, sizing_gross, **kw)

                def subcause():
                    if BTC not in self.cfg[A]["tradable"]: return "btc_not_w24h_tradable"
                    fl = self.floor_of(BTC); mult = float(self.X0.ext_cfg["min_notional_mult"])
                    if abs(float(pre.get(BTC, 0.0))) < mult * fl: return "btc_dust"
                    return "btc_untradable_other"

                # ★ M3b: is dust the ONLY reason BTC is untradable? (every other reason is re-derived from the same state exec_sim used)
                ut = set(untradable); ff = set(kw.get("force_flat") or ())
                fl = self.floor_of(BTC); mult = float(self.X0.ext_cfg["min_notional_mult"])

                def is_dust(v):
                    return BTC in self.X0.EXT.below_min_notional({BTC: float(v)}, {BTC: fl}, mult)["names"]
                dust_only = False
                if BTC in ut and BTC not in ff:
                    c_ = self.cfg[A]
                    held_btc = abs(float((held or {}).get(BTC, 0.0) or 0.0)) > 1e-9
                    held_exit = held_btc and float(pre.get(BTC, 0.0)) == 0.0
                    venue = c_["tradable"] is not None and BTC not in c_["tradable"]
                    meta = BTC in (c_["meta"] or set())
                    cool = BTC in self.X0.PNS.active_sets(self.pns, float(c_["t_dec"]))["cooldown"]
                    dust_only = is_dust(pre.get(BTC, 0.0)) and not (venue or meta or cool or held_exit)
                r = apply_overlay(target, untradable, kw.get("force_flat") or (), gs, brow, beta.col, self.m3_mode, subcause, dust_only, is_dust)
                released = 0.0
                if self.m3_mode == "overlay" and r["cause"] == CAUSE["applied_via_combined"]:
                    clamp = out[0]                                                # the dict exec_sim reads its reduce-only set from
                    for k_ in ("reduced", "add_blocked", "flatten_only", "popped"):
                        if BTC in (clamp.get(k_) or []):
                            clamp[k_] = [s_ for s_ in clamp[k_] if s_ != BTC]; released = 1.0
                r.update(btc_released=released)
                r.update(A=A, beta_pre=beta_pre, btc_held_notional=float((held or {}).get(BTC, 0.0)),
                         pos_beta=book_beta(held, gs, brow, beta.col)[0] if held else 0.0,
                         plan_beta=float("nan"), btc_plan_notional=float("nan"), btc_plan_skip=PLAN_SKIP["no_plan_row"], n_plans=0)
                self._m3_cur = r
                c = r["cause"]; d = self.diag
                d["m3h_calls"] += 1
                if c in APPLIED:
                    d["m3h_hedge_computed_and_allowed"] += 1
                    if c == CAUSE["applied_via_combined"]: d["m3h_applied_via_combined"] += 1
                    if r["combined_small"]: d["m3h_combined_below_2floor_tradable_branch"] += 1
                    if self.m3_mode == "overlay": d["m3h_applied"] += 1; d["m3h_abs_applied_over_gs_sum"] += abs(r["add_applied"]) / gs
                elif c == CAUSE["empty_target"]: d["m3h_empty_target"] += 1
                elif c == CAUSE["zero_hedge"]: d["m3h_zero_hedge"] += 1
                else: d["m3h_skip_btc_untradable"] += 1; d["m3h_skip_cause_%d" % c] += 1
                if np.isfinite(r["beta_exec"]): d["m3h_abs_beta_exec_sum"] += abs(r["beta_exec"])
                return out

            def _m3_plan(self, stub, target, pos, mids, reduce_only_syms=None, held_qty=None):
                plans = self._m3_plan_inner(stub, target, pos, mids, reduce_only_syms=reduce_only_syms, held_qty=held_qty)
                r = self._m3_cur
                if r is not None:
                    brow = beta.row_of(self._m3_A); gs = r["gs"]
                    planned = {}
                    btc_n, btc_skip = float("nan"), PLAN_SKIP["no_plan_row"]
                    for p in plans:
                        s = p["symbol"]
                        if p.get("skip") or "qty" not in p:
                            if s == BTC: btc_n, btc_skip = 0.0, PLAN_SKIP.get(p.get("skip"), PLAN_SKIP["other_skip"])
                            continue
                        planned[s] = float(p["qty"]) * float(mids[s])
                        if s == BTC: btc_n, btc_skip = planned[s], PLAN_SKIP["planned"]
                    r["plan_beta"] = book_beta(planned, gs, brow, beta.col)[0] if planned else 0.0
                    r["btc_plan_notional"] = btc_n; r["btc_plan_skip"] = btc_skip; r["n_plans"] = len(planned)
                return plans

            def book(self, t, s, dq, ref_px, slip, maker, kind, A):
                n0 = self.trade_log.n
                x = super().book(t, s, dq, ref_px, slip, maker, kind, A)
                if self.m3_mode is not None and s == BTC and self.trade_log.n > n0:
                    tt, _s, ddq, px, cash, mk, fee, kd, AA = self.trade_log.last
                    self.m3_tr.append((float(tt), float(ddq), float(px), float(cash), 1.0 if mk else 0.0, float(fee), float(TKIND.get(kd, 9)),
                                       float(AA) if AA is not None else -1.0))
                return x

            def _fund_hook(self, s, f):
                super()._fund_hook(s, f)
                if getattr(self, "m3_mode", None) is not None and s == BTC:
                    self.m3_fu.append((float(self.fund_log.cur_t), float(f), float(self.q.get(BTC, 0.0))))

            def run(self):
                W = super().run()
                if self.m3_mode is not None and sidecar_dir is not None:
                    os.makedirs(sidecar_dir, exist_ok=True)
                    st = os.path.join(sidecar_dir, "M3SC_%s_seed_%02d" % (self.tag.replace("|", "_"), self.seed))
                    R = {k: np.array([rr[k] for rr in self.m3_rec], np.float64) for k in REC_FIELDS}
                    np.savez(st + ".tmp.npz", **R, trades=np.array(self.m3_tr, np.float64).reshape(-1, 8),
                             funding=np.array(self.m3_fu, np.float64).reshape(-1, 3), mode=np.array(self.m3_mode), tag=np.array(self.tag),
                             seed=np.array(self.seed, np.int64), cause_codes=np.array(json.dumps(CAUSE)), plan_skip_codes=np.array(json.dumps(PLAN_SKIP)),
                             trade_cols=np.array("t,dq,px,cash,maker,fee,kind,A"), funding_cols=np.array("t,f(cash; negative = paid),q_btc_after"))
                    os.replace(st + ".tmp.npz", st + ".npz")
                return W

        return HistSim31M3H
    return make_sim_class


def launch_label(argv):
    """the same label bt_launch.py derives from its argv (smoke_<label> / full_<resume> / full)"""
    if len(argv) > 3 and argv[3] == "--smoke": return "smoke_" + argv[8]
    if len(argv) > 3 and argv[3] == "--resume": return "full_" + argv[4]
    return "full"


def run(argv):
    WL = set(argv[1].split(","))
    assert WL, "env whitelist must be non-empty"
    extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
    cfg_p = os.path.abspath(argv[2]); CFG = json.load(open(cfg_p)); H = CFG["m3_hook"]
    me = sha(os.path.abspath(__file__))
    if H["device_sha256"] != me: raise SystemExit(f"m3_hook device sha {me[:16]} != config {H['device_sha256'][:16]}")
    beta = BetaTable(H["beta"]["npz"], H["beta"]["sha256"])
    inert = [r["tag"] for r in CFG["runs"] if r["tag"].split("|")[0] not in H["arms"]]
    if inert: raise SystemExit(f"m3_hook: runs whose tag prefix is not a hooked arm (the hook would be inert): {inert}")
    sys.path.insert(0, DEV)
    import bt_hist_sim31 as BH
    assert os.path.realpath(BH.__file__) == os.path.realpath(os.path.join(DEV, "bt_hist_sim31.py"))
    sc_dir = os.path.join(CFG["paths"]["pod_root"], "m3_sidecar", launch_label(argv))
    BH.make_sim_class = hooked_class_factory(BH.make_sim_class, beta, dict(H["arms"]), sc_dir)
    rec = {"device": "m3_hook.py", "self_sha256": me, "config": {"path": cfg_p, "sha256": sha(cfg_p)}, "beta": H["beta"], "arms": H["arms"],
           "sidecar_dir": sc_dir, "launcher": {"path": os.path.join(DEV, "bt_launch.py"), "sha256": sha(os.path.join(DEV, "bt_launch.py"))},
           "argv": argv, "pid": os.getpid(), "pgid": os.getpgid(0)}
    rp = os.path.join(CFG["paths"]["pod_root"], "receipts", "M3H_WRAPPER_" + os.path.basename(cfg_p).replace(".json", "") + "_%d.json" % os.getpid())
    os.makedirs(os.path.dirname(rp), exist_ok=True)
    json.dump(rec, open(rp, "w"), indent=1)
    import runpy
    sys.argv = [os.path.join(DEV, "bt_launch.py")] + argv[1:]
    runpy.run_path(os.path.join(DEV, "bt_launch.py"), run_name="__main__")


if __name__ == "__main__":
    run(sys.argv)

#!/usr/bin/env python3
"""m2_hook.py — NAMED DEVIATION ROUTE for Stage 2 M2 (prereg docs/PREREG_old_vs_new_models_same_engine_2026-09-23.md, 8530d2b7f / 1217d786):
the prereg formula delivered as an EXECUTOR-LEVEL OVERLAY LEG instead of through the target file.

Why (measured before any NAV number, receipts/M2_EXEC_PATH_OLD.json): the certified executor (tree 409ea16) re-demeans and re-scales every
published target (anchor_loop.apply_withhold_and_reshape, RESHAPE_REDEMEAN = RESHAPE_RESCALE = True). A BTC weight written into the target
file is spread as −h/N over all N names and the book is put back at the sizing gross: on OLD the executed-book beta moves by −13 % … −44 % of
the intended hedge (the WRONG sign) in 2022–2025. The literal route cannot deliver the formula's clause "every other name's weight unchanged;
the total gross changes". This route keeps the certified code and files untouched and adds the formula's hedge AFTER the executor's
POP → RESHAPE → CLAMP, i.e. on the book that is actually sent to plan():
    target[BTCUSDT] += h(A) · Gs,   h(A) = −β_book(A) / Σ|w(A)|   (β_book on the PUBLISHED target, formula step 2; Σ|w| = the executor's
                                                                 gross_in — every OLD weight is in-universe, max |diff| 4e-16)
    Gs = the executor's own sizing gross at the decision (equity × gross_mult), passed to the reshape call.
  * HOLD / HALT / invalid-target anchors never reach the reshape call ⇒ no hedge change (the held book keeps its BTC position) — the prereg's
    "HOLD anchors get no hedge", same semantics as production.
  * BTC in the call's untradable set or in force_flat (per-name stop / cooldown / not tradable / dust / held-exit) ⇒ the hedge is NOT added
    at that anchor (the executor has already decided BTC may not be opened); counted.
  * h == 0.0 ⇒ nothing is touched (no BTC entry is created).
  Every other name, every setting, the calibration, the fill draws and the executor code are those of the certified run; only the BTC
  entry of the post-reshape target differs. The hook is active only for runs whose tag's arm (text before the first '|') is a key of the
  config's m2_hook.tables; every other run in the same process is untouched.
Provenance: the run config carries m2_hook = {device, device_sha256, tables: {arm: {npz, sha256}}}; this wrapper refuses unless its own sha
and every table sha match, then runs the CERTIFIED launcher (baseline_tables devices_v3/bt_launch.py, unchanged) in-process with
bt_hist_sim31.make_sim_class wrapped. Hook counters land in every path json's `diag` (m2h_*). Zero-hedge control: a table of zeros must give
path arrays BITWISE equal to the certified base paths (m2_hook_control.py).
usage:
  table: python m2_hook.py table <M2DIAG_npz> <out_npz> [--zero]
  run:   env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B m2_hook.py PATH,HOME,LC_CTYPE <config.json> [bt_launch args…]
"""
import os, sys, json, copy, types, collections, hashlib

DEV = "/workspace/baseline_tables_2026-09-19/devices_v3"
BTC = "BTCUSDT"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def make_table(diag_p, out_p, zero=False):
    import numpy as np
    D = np.load(diag_p)
    A = D["anchor"].astype(np.int64); L1 = D["L1_base"]; hedge = D["hedge"]; kind = D["kind"]
    pub = kind > 0
    if np.any(pub & ~(L1 > 0)): raise ValueError("published row with zero gross")
    h = np.where(pub, hedge / np.where(L1 > 0, L1, 1.0), 0.0)
    if zero: h = np.zeros_like(h)
    np.savez(out_p, anchor=A, h_gross_units=h, source_diag=np.array(diag_p), source_diag_sha256=np.array(sha(diag_p)), zero=np.array(bool(zero)))
    print("M2H_TABLE", out_p, sha(out_p), "n", len(A), "nonzero", int((h != 0).sum()))


def hooked_class_factory(orig_make, tables):
    def make_sim_class(ES):
        Base = orig_make(ES)

        class HistSim31M2H(Base):
            def __init__(self, *a, **k):
                super().__init__(*a, **k)
                arm = self.tag.split("|")[0]
                self.m2h_table = tables.get(arm)
                self._m2h_A = None
                if self.m2h_table is not None:
                    XP = copy.copy(self.X)
                    XP.AL = types.SimpleNamespace(apply_withhold_and_reshape=self._m2h_awr)
                    self.X = XP
                    self.diag["m2h_active"] = 1.0

            def on_anchor(self, A):
                self._m2h_A = int(A)
                try:
                    return super().on_anchor(A)
                finally:
                    self._m2h_A = None

            def _m2h_awr(self, target, held, untradable, sizing_gross, **kw):
                out = self.X0.AL.apply_withhold_and_reshape(target, held, untradable, sizing_gross, **kw)
                A = self._m2h_A
                if A is None: raise RuntimeError("m2h: reshape called outside on_anchor")
                h = self.m2h_table[A]                        # KeyError = an anchor without a hedge value: refuse, never assume 0
                if h == 0.0:
                    self.diag["m2h_zero_hedge_anchors"] += 1; return out
                if BTC in set(untradable) or BTC in set(kw.get("force_flat") or ()):
                    self.diag["m2h_btc_untradable_skipped"] += 1; return out
                add = float(h) * float(sizing_gross)
                target[BTC] = float(target.get(BTC, 0.0)) + add
                self.diag["m2h_hedged_anchors"] += 1; self.diag["m2h_abs_hedge_over_gs_sum"] += abs(float(h))
                return out

        return HistSim31M2H
    return make_sim_class


def run(argv):
    WL = set(argv[1].split(","))
    assert WL, "env whitelist must be non-empty"
    extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
    import numpy as np
    cfg_p = os.path.abspath(argv[2]); CFG = json.load(open(cfg_p)); H = CFG["m2_hook"]
    me = sha(os.path.abspath(__file__))
    if H["device_sha256"] != me: raise SystemExit(f"m2_hook device sha {me[:16]} != config {H['device_sha256'][:16]}")
    tables = {}
    for arm, t in H["tables"].items():
        if sha(t["npz"]) != t["sha256"]: raise SystemExit(f"table sha mismatch for {arm}")
        Z = np.load(t["npz"]); tables[arm] = {int(a): float(v) for a, v in zip(Z["anchor"].astype(np.int64), Z["h_gross_units"])}
    sys.path.insert(0, DEV)
    import bt_hist_sim31 as BH
    assert os.path.realpath(BH.__file__) == os.path.realpath(os.path.join(DEV, "bt_hist_sim31.py"))
    BH.make_sim_class = hooked_class_factory(BH.make_sim_class, tables)
    rec = {"device": "m2_hook.py", "self_sha256": me, "config": {"path": cfg_p, "sha256": sha(cfg_p)}, "tables": {a: t["sha256"] for a, t in H["tables"].items()},
           "launcher": {"path": os.path.join(DEV, "bt_launch.py"), "sha256": sha(os.path.join(DEV, "bt_launch.py"))}, "argv": argv, "pid": os.getpid(), "pgid": os.getpgid(0)}
    rp = os.path.join(CFG["paths"]["pod_root"], "receipts", "M2H_WRAPPER_" + os.path.basename(cfg_p).replace(".json", "") + "_%d.json" % os.getpid())
    json.dump(rec, open(rp, "w"), indent=1)
    import runpy
    sys.argv = [os.path.join(DEV, "bt_launch.py")] + argv[1:]
    runpy.run_path(os.path.join(DEV, "bt_launch.py"), run_name="__main__")


if __name__ == "__main__":
    if sys.argv[1] == "table":
        make_table(sys.argv[2], sys.argv[3], zero="--zero" in sys.argv)
    else:
        run(sys.argv)

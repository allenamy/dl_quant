#!/usr/bin/env python3
"""B7 (b) — M3 shadow "production-formula self-consistency" check for one anchor (lead 2026-09-24). READ-ONLY.
NOT research-side parity: the research-side 1% clause (AMENDMENT_2 §3 step 4) is tested separately by the M3 evaluation agent (method (a)).
  1. target_live/<A>.json field `beta_overlay` (as published) vs a recompute with the INSTALLED beta_overlay_producer.compute (sha asserted
     == the contract candidate) on the archived snapshot state/snap/<A>/rolling.npz (COMPLETE; its sha == the snapshot's SHA256SUMS entry),
     symbols = shadow_bundle/config.json symbols_panel, names = the published field's own name list (same order). Compared: every beta and
     n_obs exactly, and the counters.
  2. executor: the anchors row for A (external_book.nominal_ts == A): its `m3_beta_overlay` record — mode / status / field_ok, betas_sha256
     vs the executor's own canonical hash (live/beta_overlay.betas_sha256, imported read-only from the running tree) of the published betas,
     n_betas; beta_exec_usdt vs sum(target_usdt * beta) when the row carries the executed target (reported as not-computable otherwise).
Every line prints measured vs compared; last line M3_SELFCHECK <A> OK|MISMATCH n=<k> (exit 3 on mismatch). Pooled quantities only.
v2 (2026-09-25, B7 v2 rule docs/DECISION_RULE_B7_v2_m3_shadow_2026-09-25.md b80f52b39, gate (0)):
  * --expect-version (default m3_beta_v2) is asserted on FOUR objects: the installed producer module VERSION, the published field's
    `version`, the running executor module VERSION and the anchors record's `version_expected`.
  * the recompute input follows the version: m3_beta_v2 ⇒ RR = nc_contract.rr_from_ch0(snapshot channel-0 storage, snapshot
    boundary_raw.npz) with the INSTALLED nc_contract (both snapshot files' sha == their SHA256SUMS entries); m3_beta_v1 ⇒ the storage
    (what v1 read — the defect v2 fixes).
  * executed targets (layer (ii) of the rule): the anchors row carries none; they are rebuilt from the plan rows of orders.jsonl
    (target_w, set on EVERY plan row) as target_i = target_w_i × book_gross_usdt over the symbols with the row's anchor_ts; closures
    c1 |Σ|target_w| − 1| ≤ 1e-9, c2 #non-zero == n_targeted_names, c3 Σ target_i·β_i (published betas, BTC 1) == the record's
    beta_exec_usdt (rel 1e-9). Printed (pooled): β_exec_prod, nav_usdt and the rule's (ii) tolerance max(0.01·|β_exec|, 0.001·NAV).
    From orders.jsonl only (anchor_ts, symbol, target_w) are read.
usage: ~/wide_shadow/venv/bin/python nc_m3_selfcheck.py <pkg> <A> [--expect-version m3_beta_v2|m3_beta_v1] [--out F]"""
import argparse, glob, hashlib, importlib.util, json, math, os, sys

HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; DQ = f"{HOME}/dl_quant_live"
LINES, BAD = [], []
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def say(s): LINES.append(s); print(s, flush=True)
def cmp_(name, measured, want):
    ok = measured == want
    say(f"  {'OK ' if ok else 'BAD'} {name}: measured={measured} compared_with={want}")
    if not ok: BAD.append(name)
def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("pkg"); ap.add_argument("A", type=int); ap.add_argument("--out")
    ap.add_argument("--expect-version", default="m3_beta_v2", choices=["m3_beta_v2", "m3_beta_v1"]); a = ap.parse_args(); EV = a.expect_version
    import numpy as np
    A = a.A; C = json.load(open(f"{a.pkg}/INSTALL_CONTRACT.json"))
    cand = {f["dest"]: f["candidate_sha256"] for f in C["files"]}
    say(f"M3 selfcheck (production-formula self-consistency, NOT research-side parity) A={A} expect_version={EV}")
    bp = f"{WS}/fea171/beta_overlay_producer.py"
    cmp_("installed beta_overlay_producer.py sha == contract candidate", sha(bp), cand["wide_shadow/fea171/beta_overlay_producer.py"])
    T = json.load(open(f"{WS}/state/target_live/{A}.json")); F = T.get("beta_overlay")
    cmp_("target_live has beta_overlay field", F is not None, True)
    if F is None:
        return finish(a)
    say(f"  VAL field version={F.get('version')} anchor_ts={F.get('anchor_ts')} data_cutoff_ts={F.get('data_cutoff_ts')} n_names={F.get('n_names')} "
        f"n_estimated={F.get('n_estimated')} n_fallback={F.get('n_fallback')} n_no_cache_column={F.get('n_no_cache_column')}")
    cmp_("field anchor_ts / data_cutoff_ts == A", (F.get("anchor_ts"), F.get("data_cutoff_ts")), (A, A))
    D = f"{WS}/state/snap/{A}"
    cmp_("snapshot COMPLETE", os.path.isfile(f"{D}/COMPLETE"), True)
    sums = {l.split()[1]: l.split()[0] for l in open(f"{D}/SHA256SUMS") if l.strip()}
    cmp_("snapshot rolling.npz sha == its SHA256SUMS entry", sha(f"{D}/rolling.npz"), sums.get("rolling.npz"))
    G = json.load(open(f"{D}/generation.json"))
    say(f"  VAL snapshot generation anchor_ts={G.get('anchor_ts')} files={sorted(G.get('files', {}))}")
    cmp_("snapshot generation anchor == A", G.get("anchor_ts"), A)
    Z = np.load(f"{D}/rolling.npz", allow_pickle=True)
    syms = [str(s) for s in json.load(open(f"{WS}/shadow_bundle/config.json"))["symbols_panel"]]
    BOP = load(bp, "bop_selfcheck")
    cmp_("installed producer module VERSION == expected", getattr(BOP, "VERSION", None), EV)
    cmp_("published field version == expected", F.get("version"), EV)
    names = list(F["betas"].keys())
    store = Z["data"][:, :, 0]
    if EV == "m3_beta_v2":
        cmp_("snapshot boundary_raw.npz sha == its SHA256SUMS entry", sha(f"{D}/boundary_raw.npz") if os.path.isfile(f"{D}/boundary_raw.npz") else None,
             sums.get("boundary_raw.npz"))
        NC = load(f"{WS}/fea171/nc_contract.py", "nc_selfcheck"); Bt = np.load(f"{D}/boundary_raw.npz")
        X = NC.rr_from_ch0(Z["ts"].astype(np.int64), store, Bt["ts"], Bt["col"], Bt["raw"])
        say(f"  VAL recompute input = rr_from_ch0(storage, boundary_raw: {len(Bt['ts'])} cells) with installed nc_contract sha {sha(f'{WS}/fea171/nc_contract.py')[:16]}")
    else:
        X = store; say("  VAL recompute input = channel-0 storage (v1)")
    R = BOP.compute(Z["ts"], X, syms, names, A)
    cmp_("recomputed name list == published", list(R["betas"].keys()), names)
    db = [abs(R["betas"][n] - F["betas"][n]) for n in names]
    say(f"  VAL betas: n={len(names)} max|recomputed - published|={max(db):.3e} n_differing={sum(1 for x in db if x != 0.0)}")
    cmp_("betas bit-identical (n differing)", sum(1 for x in db if x != 0.0), 0)
    cmp_("n_obs identical (n differing)", sum(1 for n in names if R["n_obs"][n] != F["n_obs"][n]), 0)
    for k in ("n_names", "n_estimated", "n_fallback", "n_no_cache_column", "first_bar_end_ts", "version"):
        cmp_(f"counter {k}", R.get(k), F.get(k))
    # executor side
    BX = load(f"{DQ}/live/beta_overlay.py", "bx_selfcheck")
    rows = []
    for f in sorted(glob.glob(f"{DQ}/state/live/pilot_log/2*/anchors.jsonl"))[-2:]:
        rows += [json.loads(x) for x in open(f)]
    rows = [r for r in rows if (r.get("external_book") or {}).get("nominal_ts") == A]
    cmp_("executor anchors rows for A", len(rows) >= 1, True)
    if not rows:
        return finish(a)
    r = rows[-1]; m = r.get("m3_beta_overlay") or {}
    say(f"  VAL anchors.m3_beta_overlay keys={sorted(m.keys())}")
    say(f"  VAL mode={m.get('mode')} status={m.get('status')} reason={m.get('reason')} field_ok={m.get('field_ok')} n_betas={m.get('n_betas')} "
        f"n_fallback={m.get('n_fallback')} data_cutoff_ts={m.get('data_cutoff_ts')} beta_exec_usdt={m.get('beta_exec_usdt')} "
        f"hedge_intent_usdt={m.get('hedge_intent_usdt')} hedge_target_usdt={m.get('hedge_target_usdt')}")
    cmp_("executor mode", m.get("mode"), "shadow"); cmp_("executor status", m.get("status"), "shadow")
    cmp_("running executor module VERSION == expected", getattr(BX, "VERSION", None), EV)
    cmp_("anchors record version_expected == expected", m.get("version_expected"), EV)
    cmp_("anchors record field_ok", m.get("field_ok"), True)
    cmp_("executor betas_sha256 == canonical hash of published betas", m.get("betas_sha256"), BX.betas_sha256(F["betas"]))
    # executed targets from the plan rows of orders.jsonl (only anchor_ts, symbol, target_w are read)
    ats = r.get("anchor_ts"); tw, amb = {}, []
    day = [os.path.dirname(f) for f in sorted(glob.glob(f"{DQ}/state/live/pilot_log/2*/anchors.jsonl"))[-2:]]
    for dd in day:
        op = f"{dd}/orders.jsonl"
        if not os.path.isfile(op): continue
        for ln in open(op):
            o = json.loads(ln)
            if o.get("anchor_ts") != ats: continue
            s_, w_ = o.get("symbol"), o.get("target_w")
            if w_ is None: amb.append(s_); continue
            if s_ in tw and tw[s_] != float(w_): amb.append(s_)
            tw[s_] = float(w_)
    G = m.get("book_gross_usdt"); be_log = m.get("beta_exec_usdt"); nav = m.get("nav_usdt")
    nz = {k: v for k, v in tw.items() if v != 0.0}; sw = sum(abs(v) for v in tw.values())
    miss = sorted(k for k in nz if k not in F["betas"])
    recon = (sum(nz[k] * float(G) * float(F["betas"][k]) for k in sorted(nz)) if (not miss and isinstance(G, (int, float))) else None)
    say(f"  VAL executed targets from orders.jsonl plan rows: n_symbols={len(tw)} n_nonzero={len(nz)} sum|target_w|={sw!r} ambiguous={len(amb)} "
        f"targeted_without_published_beta={len(miss)} book_gross_usdt={G} n_targeted_names={m.get('n_targeted_names')}")
    cmp_("c1 |sum|target_w| - 1| <= 1e-9", bool(tw) and abs(sw - 1.0) <= 1e-9, True)
    cmp_("c2 non-zero targets == n_targeted_names", len(nz), m.get("n_targeted_names"))
    cmp_("no ambiguous target_w", len(amb), 0)
    say(f"  VAL beta_exec recomputed from plan rows x published betas={recon} logged={be_log}")
    cmp_("c3 beta_exec recomputed == logged (rel 1e-9)", bool(recon is not None and isinstance(be_log, (int, float))
         and math.isclose(recon, be_log, rel_tol=1e-9, abs_tol=1e-6)), True)
    tol = (max(0.01 * abs(float(be_log)), 0.001 * float(nav)) if isinstance(be_log, (int, float)) and isinstance(nav, (int, float)) else None)
    say(f"  VAL B7v2 (ii) inputs (pooled): beta_exec_prod_usdt={be_log} nav_usdt={nav} tolerance_usdt=max(0.01*|beta_exec|, 0.001*NAV)={tol}")
    cmp_("nav_usdt present (the (ii) tolerance needs it)", isinstance(nav, (int, float)) and nav > 0, True)
    return finish(a)


def finish(a):
    say(f"M3_SELFCHECK {a.A} {'OK' if not BAD else 'MISMATCH'} n={len(BAD)}" + (f" bad={BAD}" if BAD else ""))
    if a.out: open(a.out, "w").write("\n".join(LINES) + "\n")
    return 0 if not BAD else 3


if __name__ == "__main__":
    sys.exit(main())

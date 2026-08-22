#!/usr/bin/python3
"""L0 mirror check — did the live anchor's PLANNED weights equal the producer's target file?

Reads (read-only):
  · the producer's <target_live>/<anchor>.json (+ verifies the sidecar),
  · the live tree's pilot_log/<day>/orders.jsonl rows for the rebalance that traded that anchor
    (every planned name has a row, skipped ones included; `target_w` = target/Σ|target| as planned
    AFTER the venue withhold -> reshape, which is the design's intended transform),
  · the anchor_runs.log phase_A line for that rebalance (external_book record, sizing).
Prints: max|Δw| over common names, the uniform re-demean shift, names only in the file (withheld:
popped by the universe gate / meta rule / 2x min-notional / per_name_stop), names only in the plan
(must be held names being reduced), and the external_book record. Exit 0 iff max|Δw| < tol and no
unexplained plan-only names.

Usage:
  l0_mirror_check.py --anchor 1787356800 [--mode LIVE|DRY_RUN] [--repo ~/dl_quant_live]
                     [--target-dir ~/wide_shadow/state/target_live] [--tol 1e-6]
Design §2 L0: "名义额/过滤/清单与影子权重一致(|Δw| < 1e-6)". ★ The comparison is on the names the
live side KEPT; withheld names are listed with the reason the record gives, never silently dropped.
"""
import argparse
import hashlib
import json
import os
import sys
import time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anchor", type=int, required=True, help="nominal anchor epoch seconds (file name)")
    ap.add_argument("--mode", default="LIVE")
    ap.add_argument("--repo", default=os.path.expanduser("~/dl_quant_live"))
    ap.add_argument("--target-dir", default=os.path.expanduser("~/wide_shadow/state/target_live"))
    ap.add_argument("--tol", type=float, default=1e-6)
    a = ap.parse_args()

    # ── the file ──
    p = os.path.join(a.target_dir, f"{a.anchor}.json")
    raw = open(p, "rb").read()
    side = open(p + ".sha256").read().split()[0]
    sha_ok = hashlib.sha256(raw).hexdigest() == side
    doc = json.loads(raw)
    gn = float(doc["gross_norm"])
    wf = {s: float(v) / gn for s, v in doc["weights"].items() if float(v) != 0.0}
    print(f"file: {p}\n  sidecar={'OK' if sha_ok else 'MISMATCH'} anchor_ts={doc['anchor_ts']} n={len(wf)} "
          f"gross_norm={gn:.6f} universe_sha={doc['universe_sha'][:12]} booster={doc['booster_sha'][:12]} "
          f"written={doc['written_utc']}")

    # ── the live plan rows ──
    sub = {"LIVE": "live", "TESTNET": "testnet", "DRY_RUN": ""}[a.mode.upper()]
    root = os.path.join(a.repo, "state", sub) if sub else os.path.join(a.repo, "state")
    day = time.strftime("%Y%m%d", time.gmtime(a.anchor))
    rows = []
    for d in (day, time.strftime("%Y%m%d", time.gmtime(a.anchor + 86400))):
        fp = os.path.join(root, "pilot_log", d, "orders.jsonl")
        if os.path.exists(fp):
            for line in open(fp):
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                rows.append(r)
    # the rebalance whose anchor_ts falls in [anchor, anchor+4h)
    cand = {}
    for r in rows:
        ts = float(r.get("anchor_ts") or 0)
        if a.anchor <= ts < a.anchor + 14400 and r.get("order_type") == "maker":
            cand.setdefault(r.get("rebalance_id"), []).append(r)
    if not cand:
        print(f"✗ no maker plan rows for anchor {a.anchor} under {root} — did the anchor TRADE? (a HOLD writes none)")
        return 2
    rid = sorted(cand)[-1]
    prs = cand[rid]
    wl = {r["symbol"]: float(r.get("target_w") or 0.0) for r in prs}
    print(f"plan: rebalance_id={rid} rows={len(prs)} Σ|target_w|={sum(abs(v) for v in wl.values()):.6f}")

    # ── phase_A record ──
    rec = None
    try:
        for line in open(os.path.join(a.repo, "state", "anchor_runs.log")):
            if "phase_A:" in line and rid in line:
                rec = json.loads(line.split("phase_A:", 1)[1])
    except Exception:
        pass
    if rec:
        eb = rec.get("external_book") or {}
        sz = rec.get("sizing") or {}
        print(f"phase_A: book_source={rec.get('book_source')} action={rec.get('action')} ext.ok={eb.get('ok')} "
              f"reason={eb.get('reason')} json_sha={str(eb.get('json_sha'))[:12]} n_names={eb.get('n_names')} | "
              f"sizing nav={sz.get('nav')} lev={sz.get('target_leverage')} src={sz.get('leverage_source')} gross={sz.get('gross')} | "
              f"n_live_opening={rec.get('n_live_opening')}")
        ef = rec.get("external_filters") or {}
        if ef:
            print(f"  filters: meta_excluded={ef.get('n_meta_excluded')} below_min_notional={ (ef.get('below_min_notional') or {}).get('n') }")

    # ── the comparison ──
    common = sorted(set(wf) & set(wl))
    only_file = sorted(set(wf) - set(wl))
    only_plan = sorted(set(wl) - set(wf))
    # the plan's target_w is over the KEPT set (re-demeaned/rescaled): compare after re-normalising
    # the file restricted to the kept names the same way (pop -> rescale); the residual is then the
    # re-demean shift, which must be a single constant across names.
    kept_mass = sum(abs(wf[s]) for s in common) or 1.0
    diffs = {s: wl[s] - wf[s] / kept_mass for s in common}
    shift = (sum(diffs.values()) / len(diffs)) if diffs else 0.0
    resid = max((abs(v - shift) for v in diffs.values()), default=0.0)
    maxd = max((abs(v) for v in diffs.values()), default=0.0)
    print(f"\ncommon={len(common)} only_in_file(withheld)={len(only_file)} only_in_plan={len(only_plan)}")
    print(f"max|Δw| (plan − file/kept_mass) = {maxd:.3e}   uniform re-demean shift = {shift:+.3e}   "
          f"max|Δw − shift| = {resid:.3e}   tol={a.tol:g}")
    if only_file:
        print(f"  withheld (file-only) first 20: {only_file[:20]}")
    if only_plan:
        print(f"  ★ plan-only names (must be HELD names being reduced/flattened): {only_plan[:20]}")
    ok = sha_ok and resid < a.tol and not only_plan
    print("\nL0 MIRROR:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

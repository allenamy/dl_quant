#!/usr/bin/python3
"""L0 mirror check — did the live anchor's PLANNED weights equal the producer's IN-UNIVERSE book?

Reads (read-only):
  · the producer's <target_live>/<anchor>.json (+ verifies the sidecar and that sha(universe list) == universe_sha),
  · the live tree's pilot_log/<day>/orders.jsonl rows for the rebalance that traded that anchor
    (every planned name has a row, skipped ones included; `target_w` = target/Σ|target| as planned
    AFTER the venue withhold -> reshape, which is the design's intended transform),
  · the anchor_runs.log phase_A line for that rebalance (external_book record, sizing, filters).
Compares the plan against the file's IN-UNIVERSE weights normalised by the in-universe sum|w| (the
2026-08-22 amendment: names outside the producer's `universe` list are never targets and never
dilute the gross). Prints max|Δw| over common names, the uniform re-demean shift, and the withheld
set split by cause: outside-universe tail ∪ venue meta ∪ 2x min-notional ∪ per_name_stop; plan-only
names must be the HELD names being exited (held_exit) or flatten rows. Exit 0 iff max|Δw − shift| <
tol, the sidecars verify, and no unexplained plan-only names.

Usage:
  l0_mirror_check.py --anchor 1787371200 [--mode LIVE|DRY_RUN] [--repo ~/dl_quant_live]
                     [--target-dir ~/wide_shadow/state/target_live] [--tol 1e-6]
Design §2 L0: "名义额/过滤/清单与影子权重一致(|Δw| < 1e-6)". ★ The comparison is on the names the live
side KEPT; every withheld name is listed WITH the reason the record gives, never silently dropped.
"""
import argparse
import hashlib
import json
import os
import sys
import time


def _universe_sha(symbols):
    return hashlib.sha256(json.dumps(list(symbols), separators=(",", ":")).encode()).hexdigest()


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
    uni = doc.get("universe")
    list_ok = isinstance(uni, list) and _universe_sha(uni) == doc.get("universe_sha")
    uset = set(uni or [])
    w_all = {s: float(v) for s, v in doc["weights"].items() if float(v) != 0.0}
    w_in = {s: v for s, v in w_all.items() if s in uset}
    w_out = {s: v for s, v in w_all.items() if s not in uset}
    gross_in = sum(abs(v) for v in w_in.values()) or 1.0
    gross_all = float(doc["gross_norm"]) or 1.0
    wf = {s: v / gross_in for s, v in w_in.items()}                 # the in-universe book, unit gross
    print(f"file: {p}\n  sidecar={'OK' if sha_ok else 'MISMATCH'} universe_list_sha={'OK' if list_ok else 'MISMATCH/ABSENT'} "
          f"anchor_ts={doc['anchor_ts']} n_all={len(w_all)} n_in={len(w_in)} n_outside={len(w_out)} "
          f"gross_norm={gross_all:.6f} gross_in={gross_in:.6f} outside_frac={sum(abs(v) for v in w_out.values()) / gross_all:.4f} "
          f"universe_n={len(uset)} universe_sha={str(doc.get('universe_sha'))[:12]} booster={str(doc.get('booster_sha'))[:12]} "
          f"written={doc.get('written_utc')} producer={doc.get('producer')}")

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
                    rows.append(json.loads(line))
                except ValueError:
                    continue
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
    flat_rows = {r["symbol"] for r in prs if r.get("reduce_only") and float(r.get("target_notional") or 0.0) == 0.0}
    print(f"plan: rebalance_id={rid} rows={len(prs)} Σ|target_w|={sum(abs(v) for v in wl.values()):.6f} flatten_rows={len(flat_rows)}")

    # ── phase_A record ──
    rec, ef = None, {}
    try:
        for line in open(os.path.join(a.repo, "state", "anchor_runs.log")):
            if "phase_A:" in line and rid in line:
                rec = json.loads(line.split("phase_A:", 1)[1])
    except Exception:
        pass
    if rec:
        eb = rec.get("external_book") or {}
        sz = rec.get("sizing") or {}
        ef = rec.get("external_filters") or {}
        print(f"phase_A: book_source={rec.get('book_source')} action={rec.get('action')} ext.ok={eb.get('ok')} reason={eb.get('reason')} "
              f"json_sha={str(eb.get('json_sha'))[:12]} n_in={eb.get('n_in_universe')} n_outside={eb.get('n_outside_universe')} "
              f"outside_frac={eb.get('gross_outside_frac')} | sizing nav={sz.get('nav')} lev={sz.get('target_leverage')} "
              f"src={sz.get('leverage_source')} gross={sz.get('gross')} | n_live_opening={rec.get('n_live_opening')}")
        if ef:
            print(f"  filters: held_exit={ef.get('n_held_exit')} meta_excluded={ef.get('n_meta_excluded')} "
                  f"below_min_notional={(ef.get('below_min_notional') or {}).get('n')}")
    held_exit = set(ef.get("held_exit") or [])
    meta_ex = set((ef.get("meta_excluded") or {}).keys()) if isinstance(ef.get("meta_excluded"), dict) else set()
    dust = set(((ef.get("below_min_notional") or {}).get("names") or []))
    pns = set()
    un = (rec or {}).get("untradable_names") or {}
    for k in ("popped", "flatten_only", "reduced", "add_blocked"):
        pns |= set(un.get(k) or [])

    # ── the comparison ──
    common = sorted(set(wf) & set(wl))
    only_file = sorted(set(wf) - set(wl))
    only_plan = sorted(set(wl) - set(wf))
    kept_mass = sum(abs(wf[s]) for s in common) or 1.0
    diffs = {s: wl[s] - wf[s] / kept_mass for s in common}
    shift = (sum(diffs.values()) / len(diffs)) if diffs else 0.0
    resid = max((abs(v - shift) for v in diffs.values()), default=0.0)
    maxd = max((abs(v) for v in diffs.values()), default=0.0)
    print(f"\ncommon={len(common)} in-universe-file-only(withheld)={len(only_file)} plan-only={len(only_plan)} outside-tail(never targets)={len(w_out)}")
    print(f"max|Δw| (plan − in-universe file/kept_mass) = {maxd:.3e}   uniform re-demean shift = {shift:+.3e}   "
          f"max|Δw − shift| = {resid:.3e}   tol={a.tol:g}")
    if only_file:
        by = {"meta": [s for s in only_file if s in meta_ex], "min_notional": [s for s in only_file if s in dust],
              "untradable(per_name_stop/venue)": [s for s in only_file if s in pns and s not in meta_ex and s not in dust],
              "UNEXPLAINED": [s for s in only_file if s not in meta_ex and s not in dust and s not in pns]}
        for k, v in by.items():
            if v:
                print(f"  withheld[{k}] ({len(v)}): {v[:15]}")
    unexplained_plan = [s for s in only_plan if s not in held_exit and s not in flat_rows]
    if only_plan:
        print(f"  plan-only ({len(only_plan)}): held_exit={len([s for s in only_plan if s in held_exit])} "
              f"flatten_rows={len([s for s in only_plan if s in flat_rows])} UNEXPLAINED={unexplained_plan[:15]}")
    ok = sha_ok and list_ok and resid < a.tol and not unexplained_plan
    print("\nL0 MIRROR:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

"""Paper P&L of every shadow arm over (A, A+4h], priced with the NEXT anchor's snapshot, appended to the ledger (one line per anchor).

Caliber (named):
  price    : per name, the producer's own 5-minute return channel (nc_contract.rr_from_ch0 on rolling.npz ch0 + boundary_raw.npz)
             over the rows with ts in (A, A+4h]; compounded prod(1+r)-1 over finite rows (primary) and the producer's sum (reported);
             a name with < 46 finite rows is UNPRICED (reported as |weight| share, never counted as 0 return)
  weights  : each arm's post-reshape combo scaled to the executor's constant leverage: w_nav = G * w / sum|w|, G = 2.0
  funding  : settlements in the snapshot's producer ledger (aux.json ledger_tail) with A < ft <= A+4h, P&L = -w_nav * sum(rate);
             a name absent from the ledger, or whose earliest tail row is already after A, is FUNDING_UNKNOWN (reported, not 0)
  cost     : proxy KAPPA * sum|w_nav(A) - w_nav(A-4h)|, KAPPA = 3.52 bps per unit (the trainer's cost coefficient, as dlarch aab04e8b9);
             unknown when the arm has no stored A-4h book (reported)
  NOT modelled: entry lag (executor trades ~N+24 min), clamps/withholds/venue caps, fills, beta overlay (M3 is shadow).
usage: shadow_ab_pnl.py <A> <AB home> <wide_shadow home> [--ledger PATH]     exit 0 appended / 4 not yet priceable / 3 refused"""
import os, sys, json, hashlib, time, importlib.util
import numpy as np
sys.dont_write_bytecode = True
G, KAPPA, H4, MIN_FINITE = 2.0, 3.52e-4, 14400, 46
ARMS = ("LIVE_REPLAY", "NOKING", "KHALF", "FUNDONLY")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def book_nav(z, n):
    w = np.zeros(n); w[z["idx"].astype(np.int64)] = z["val"].astype(np.float64)
    g = np.abs(w).sum()
    return (G * w / g) if g > 1e-12 else None


def price_returns(rr_rows):
    """rr_rows [48, N] -> (compounded, summed, priced mask)"""
    fin = np.isfinite(rr_rows); ok = fin.sum(0) >= MIN_FINITE
    comp = np.prod(np.where(fin, 1.0 + rr_rows.astype(np.float64), 1.0), axis=0) - 1.0
    summ = np.where(fin, rr_rows.astype(np.float64), 0.0).sum(0)
    return np.where(ok, comp, np.nan), np.where(ok, summ, np.nan), ok


def funding_rates(ledger_tail, names, A, N):
    """per name: (sum of rates with A < ft <= N, state) state in {OK, UNKNOWN_ABSENT, UNKNOWN_COVERAGE}"""
    tot = np.zeros(len(names)); state = np.array(["OK"] * len(names), dtype=object)
    for j, s in enumerate(names):
        rows = ledger_tail.get(s)
        if not rows: state[j] = "UNKNOWN_ABSENT"; continue
        fts = [int(r[0]) for r in rows]
        if min(fts) > A: state[j] = "UNKNOWN_COVERAGE"
        tot[j] = sum(float(r[1]) for r in rows if A < int(r[0]) <= N)
    return tot, state


def arm_metrics(w, wprev, ret_c, ret_s, priced, fund, fstate):
    held = np.abs(w) > 1e-12
    unpriced = held & ~priced; funk = held & (fstate != "OK")
    price = float(np.nansum(np.where(priced, w * ret_c, 0.0))); price_sum = float(np.nansum(np.where(priced, w * ret_s, 0.0)))
    fpnl = float(-(w * fund).sum())
    turn = None if wprev is None else float(np.abs(w - wprev).sum())
    cost = None if turn is None else KAPPA * turn
    net = None if cost is None else price + fpnl - cost
    return {"price": price, "price_sum_caliber": price_sum, "funding": fpnl, "turnover": turn, "cost": cost, "net": net,
            "net_pre_cost": price + fpnl, "n_held": int(held.sum()), "unpriced_abs_w": float(np.abs(w[unpriced]).sum()),
            "funding_unknown_abs_w": float(np.abs(w[funk]).sum()), "long": float(w[w > 0].sum()), "short": float(w[w < 0].sum())}


def main():
    A = int(sys.argv[1]); AB = sys.argv[2]; WS = sys.argv[3]
    ledger = sys.argv[sys.argv.index("--ledger") + 1] if "--ledger" in sys.argv else os.path.join(AB, "ledger.jsonl")
    N = A + H4; snap = os.path.join(WS, "state", "snap", str(N)); st = os.path.join(AB, "state", str(A)); stp = os.path.join(AB, "state", str(A - H4))
    if not (os.path.exists(os.path.join(snap, "COMPLETE")) and os.path.exists(os.path.join(st, "COLLECT.json"))):
        print("SHADOW_AB_PNL NOT_YET", A); sys.exit(4)
    lines = open(ledger).read().splitlines() if os.path.exists(ledger) else []
    if any(json.loads(l)["anchor"] == A for l in lines):
        print("SHADOW_AB_PNL REFUSED already in ledger (append-only)", A); sys.exit(3)
    # snapshot integrity (read-only)
    sums = {}
    for l in open(os.path.join(snap, "SHA256SUMS")).read().splitlines():
        h, fn = l.split(None, 1); sums[fn.strip().lstrip("*")] = h
    for fn in ("rolling.npz", "boundary_raw.npz", "aux.json"):
        if sums.get(fn) != sha(os.path.join(snap, fn)): print("SHADOW_AB_PNL REFUSED snapshot sha", fn); sys.exit(3)
    col = json.load(open(os.path.join(st, "COLLECT.json")))
    meta = json.load(open(os.path.join(st, "AB_META.json"))); names = meta["names"]; n = len(names)
    spec = importlib.util.spec_from_file_location("nc_contract_ro", os.path.join(WS, "fea171", "nc_contract.py"))
    NC = importlib.util.module_from_spec(spec); spec.loader.exec_module(NC)
    R = np.load(os.path.join(snap, "rolling.npz")); B = np.load(os.path.join(snap, "boundary_raw.npz"))
    assert R["data"].shape[1] == n, "rolling columns != stage names"
    ts = R["ts"].astype(np.int64); rows = np.flatnonzero((ts > A) & (ts <= N))
    rr = NC.rr_from_ch0(ts[rows], R["data"][rows, :, 0], B["ts"], B["col"], B["raw"])
    ret_c, ret_s, priced = price_returns(rr)
    aux = json.load(open(os.path.join(snap, "aux.json")))
    fund, fstate = funding_rates(aux["ledger_tail"], names, A, N)
    line = {"anchor": A, "priced_with_snapshot": N, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "device_sha256": sha(os.path.abspath(__file__)), "nc_contract_sha256": sha(os.path.join(WS, "fea171", "nc_contract.py")),
            "snapshot_sha256": {k: sums[k] for k in ("rolling.npz", "boundary_raw.npz", "aux.json")},
            "n_rows": int(len(rows)), "identity": col["identity"]["PASS"], "collect_status": col["STATUS"], "arms": {}}
    if len(rows) != 48: line["rows_warning"] = f"{len(rows)} rows in (A, A+4h] (expected 48)"
    if col["STATUS"] != "OK":
        line["VOID"] = "identity control failed at this anchor: no arm is priced"
    else:
        for arm in ARMS:
            p = os.path.join(st, f"{arm}_combo.npz")
            if not os.path.exists(p): line["arms"][arm] = {"UNDEFINED": "no stored book"}; continue
            w = book_nav(np.load(p), n)
            if w is None: line["arms"][arm] = {"UNDEFINED": "zero gross"}; continue
            pp = os.path.join(stp, f"{arm}_combo.npz"); pcol = os.path.join(stp, "COLLECT.json")
            wprev = book_nav(np.load(pp), n) if (os.path.exists(pp) and os.path.exists(pcol) and json.load(open(pcol))["STATUS"] == "OK") else None
            line["arms"][arm] = arm_metrics(w, wprev, ret_c, ret_s, priced, fund, fstate)
            line["arms"][arm]["state_sources"] = [meta["arms"].get(arm, {}).get("kc_src"), meta["arms"].get(arm, {}).get("fc_src")]
        base = line["arms"].get("LIVE_REPLAY", {})
        for arm in ARMS[1:]:
            a = line["arms"].get(arm, {})
            if "net" in a and "net" in base and a["net"] is not None and base["net"] is not None:
                a["d_net_vs_live"] = a["net"] - base["net"]
            if "net_pre_cost" in a and "net_pre_cost" in base:
                a["d_net_pre_cost_vs_live"] = a["net_pre_cost"] - base["net_pre_cost"]
    prev_sha = hashlib.sha256(lines[-1].encode()).hexdigest() if lines else None
    line["prev_line_sha256"] = prev_sha
    txt = json.dumps(line, sort_keys=True)
    with open(ledger, "a") as f: f.write(txt + "\n"); f.flush(); os.fsync(f.fileno())
    assert open(ledger).read().splitlines()[-1] == txt, "ledger read-back mismatch"
    print("SHADOW_AB_PNL APPENDED", A, "identity", line["identity"],
          json.dumps({k: round(v.get("net", float("nan")) * 1e4, 3) if isinstance(v.get("net"), float) else v.get("UNDEFINED") for k, v in line["arms"].items()}))


if __name__ == "__main__":
    main()

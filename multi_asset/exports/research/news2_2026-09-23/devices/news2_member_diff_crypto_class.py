#!/usr/bin/env python3
"""news2_member_diff_crypto_class.py -- are the researcher-only member pairs TradFi (non-crypto) perps?

Lead's hypothesis (2026-09-24): G1-3 feeds the researcher's function `legal AND crypto`. If the
researcher's DELIVERED panel instead put equity/commodity perps into the top-400 liquidity in 2026,
then NC -- which screens crypto-only (shadow_loop_v3.py L573: `cand_now = legal_now & st.crypto &
st.fetch_mask`) -- would drop them and promote the next crypto name. That produces exactly the
rank-boundary shape already measured (NC-only names sitting at the liquidity cut, median normalised
qvm rank 0.9525). If so it is an INTENTIONAL retained difference, not a reproduction defect.

CLASSIFICATION SOURCE: axes.npz `crypto_cols` -- the column indices the replay treats as crypto
(nc_hist_features.py L85/L91: `self.cols = ax["crypto_cols"]`, `self.crypto[self.cols] = True`). That
is the same array the replay itself screens on, not a list I assembled, so this is a measurement of the
production screen rather than of my own guess at it.

READ-ONLY. No producer, no exchange, no GPU.

NOT JUDGED (lead 2026-09-24): which side is correct. Contract question.
"""
import argparse, collections, datetime, hashlib, json, os, sys

import numpy as np

SELF = os.path.realpath(__file__)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nc-axes", required=True)
    ap.add_argument("--nc-features", required=True)
    ap.add_argument("--researcher-panel", required=True)
    ap.add_argument("--researcher-axis", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rec = {"device": os.path.basename(SELF), "self_sha256": sha(SELF), "argv": sys.argv[1:],
           "cwd": os.getcwd(), "python": sys.executable, "numpy": np.__version__,
           "status": "WHERE_AND_HOW_MUCH_NOT_WHICH_SIDE_IS_RIGHT",
           "classification_source": ("axes.npz crypto_cols, the same array the replay screens on "
                                     "(nc_hist_features.py L85/L91); not a list assembled by this device"),
           "nc_screen": "shadow_loop_v3.py L573: cand_now = legal_now & st.crypto & st.fetch_mask",
           "inputs": {"nc_axes": {"path": a.nc_axes, "sha256": sha(a.nc_axes)},
                      "nc_features": {"path": a.nc_features, "bytes": os.path.getsize(a.nc_features)},
                      "researcher_panel": {"path": a.researcher_panel,
                                           "bytes": os.path.getsize(a.researcher_panel)}}}

    AXN = np.load(a.nc_axes, allow_pickle=True)
    syms = [str(s) for s in AXN["symbols"]]
    crypto = np.zeros(len(syms), bool)
    crypto[AXN["crypto_cols"].astype(np.int64)] = True
    rec["axis"] = {"n_symbols": len(syms), "n_crypto": int(crypto.sum()),
                   "n_non_crypto": int((~crypto).sum())}

    N = np.load(a.nc_features, allow_pickle=False)
    R = np.load(a.researcher_panel, allow_pickle=False)
    AX = np.load(a.researcher_axis, allow_pickle=False)
    na = N["anchors"].astype(np.int64); off = N["off"].astype(np.int64); m = N["m"].astype(np.int64)
    rts = AX["E_ts"].astype(np.int64)[R["pair_a"].astype(np.int64)]
    ps = R["pair_s"].astype(np.int64)
    o = np.argsort(rts, kind="stable"); rts, ps = rts[o], ps[o]
    u, st = np.unique(rts, return_index=True); en = np.append(st[1:], rts.size)
    res = {int(t): set(ps[s:e].tolist()) for t, s, e in zip(u, st, en)}

    tot_r = collections.Counter(); non_r = collections.Counter()
    tot_n = collections.Counter(); non_n = collections.Counter()
    names_r = collections.Counter(); names_n = collections.Counter()
    for i, t in enumerate(na):
        t = int(t)
        if t not in res:
            continue
        y = datetime.datetime.utcfromtimestamp(t).year
        ns = set(m[off[i]:off[i + 1]].tolist())
        for j in res[t] - ns:
            tot_r[y] += 1
            if not crypto[j]:
                non_r[y] += 1; names_r[syms[j]] += 1
        for j in ns - res[t]:
            tot_n[y] += 1
            if not crypto[j]:
                non_n[y] += 1
            names_n[syms[j]] += 1

    per_year = {}
    for y in sorted(set(list(tot_r) + list(tot_n))):
        per_year[str(y)] = {
            "researcher_only_pairs": tot_r[y],
            "researcher_only_non_crypto": non_r[y],
            "researcher_only_pct_non_crypto": (100.0 * non_r[y] / tot_r[y]) if tot_r[y] else None,
            "nc_only_pairs": tot_n[y],
            "nc_only_non_crypto": non_n[y],
            "nc_only_pct_non_crypto": (100.0 * non_n[y] / tot_n[y]) if tot_n[y] else None,
        }
    rec["per_year"] = per_year
    rec["top_researcher_only_non_crypto_names"] = names_r.most_common(20)
    rec["top_nc_only_names"] = names_n.most_common(10)

    # RED CONTROL.
    # baseline: the classification must be non-degenerate (both classes present) AND the NC-only side
    # must be ~0% non-crypto -- if NC-only names were also non-crypto, "NC screens crypto-only" would
    # not be what distinguishes the two sides.
    ctrl = {"both_classes_present": bool(crypto.any() and (~crypto).any())}
    nc_pct = [v["nc_only_pct_non_crypto"] for v in per_year.values()
              if v["nc_only_pct_non_crypto"] is not None]
    ctrl["nc_only_max_pct_non_crypto"] = max(nc_pct) if nc_pct else None
    ctrl["nc_side_is_crypto_only"] = (ctrl["nc_only_max_pct_non_crypto"] == 0.0) if nc_pct else None
    # mutation: inverting the flag must send the researcher-only percentage to its complement
    inv = ~crypto
    chk = None
    for i, t in enumerate(na):
        t = int(t)
        if t not in res:
            continue
        if datetime.datetime.utcfromtimestamp(t).year != 2026:
            continue
        ns = set(m[off[i]:off[i + 1]].tolist())
        d = res[t] - ns
        if d:
            chk = (float(np.mean([not crypto[j] for j in d])),
                   float(np.mean([not inv[j] for j in d])))
            break
    ctrl["mutation_probe_observed_then_inverted"] = chk
    ctrl["mutation_flips"] = bool(chk and abs((chk[0] + chk[1]) - 1.0) < 1e-9)
    ctrl["baseline_green"] = bool(ctrl["both_classes_present"] and ctrl["nc_side_is_crypto_only"])
    rec["red_control"] = ctrl
    rec["verdict"] = "MEASURED" if ctrl["baseline_green"] else "UNAVAILABLE"
    if not ctrl["baseline_green"]:
        rec["why"] = ("red control: the classification is degenerate, or NC-only names are also "
                      "non-crypto, in which case the crypto screen is not what separates the sides")

    json.dump(rec, open(a.out, "w"), indent=2)
    print(f"MEMBER_CRYPTO_CLASS VERDICT={rec['verdict']}")
    print(f"  axis: {rec['axis']['n_crypto']} crypto / {rec['axis']['n_non_crypto']} non-crypto "
          f"of {rec['axis']['n_symbols']}")
    print(f"  red control: both_classes={ctrl['both_classes_present']} "
          f"nc_side_crypto_only={ctrl['nc_side_is_crypto_only']} "
          f"(nc-only max pct non-crypto {ctrl['nc_only_max_pct_non_crypto']}) "
          f"mutation_flips={ctrl['mutation_flips']}")
    print("  year   res_only  non_crypto      pct     nc_only  non_crypto   pct")
    for y, v in per_year.items():
        print(f"   {y}  {v['researcher_only_pairs']:8d}  {v['researcher_only_non_crypto']:10d}  "
              f"{(v['researcher_only_pct_non_crypto'] if v['researcher_only_pct_non_crypto'] is not None else float('nan')):7.2f}%  "
              f"{v['nc_only_pairs']:8d}  {v['nc_only_non_crypto']:10d}  "
              f"{(v['nc_only_pct_non_crypto'] if v['nc_only_pct_non_crypto'] is not None else float('nan')):6.2f}%")
    print(f"  top researcher-only non-crypto: {rec['top_researcher_only_non_crypto_names'][:10]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

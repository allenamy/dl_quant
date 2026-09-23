"""NEWS P1b: (i) earliest first bar of any TRADIFI_PERPETUAL name vs first bars of the 31 names absent
from the 09-08 venue snapshot; (ii) serving simulation of the producer member screen (no legal mask, as
served) on candidate fetch lists vs the training rule (legal ∧ crypto candidates), 2025-07 .. 2026-09-19.
Reuses P1 member lists (P1_members_2025H2on.npz) and the producer member screen verbatim."""
import os, json, time, calendar, collections, hashlib
import numpy as np
from p1_members import producer_members, W, CFG, VENUE, MASK, sha

def main():
    t0 = time.time()
    cfg = json.load(open(CFG)); P = cfg["params"]; live = list(cfg["symbols_live"])
    venue = json.load(open(VENUE))
    ax = np.load(f"{W}/work/cache_x0918r_axes.npz"); ts = ax["ts"].astype(np.int64); syms = [str(s) for s in ax["symbols"]]
    D = np.load(f"{W}/work/cache_x0918r_data.npy", mmap_mode="r")
    q3 = np.isfinite(np.asarray(D[:, :, 3]))          # (T, 829) bool, one pass
    first = {}; last = {}
    anyq = q3.any(0); fi = q3.argmax(0); li = len(ts) - 1 - q3[::-1].argmax(0)
    for j, s in enumerate(syms):
        first[s] = time.strftime("%Y-%m-%d", time.gmtime(int(ts[fi[j]]))) if anyq[j] else None
        last[s] = time.strftime("%Y-%m-%d", time.gmtime(int(ts[li[j]]))) if anyq[j] else None
    tradfi = [s for s in syms if s in venue and venue[s]["contractType"] == "TRADIFI_PERPETUAL"]
    tf_first = sorted((first[s], s) for s in tradfi if first[s])
    unknown = [s for s in syms if s not in venue]
    earliest_tradfi = tf_first[0]
    unk_rule = {s: {"first": first[s], "last": last[s], "first_before_earliest_tradfi": (first[s] is None) or first[s] < earliest_tradfi[0]} for s in unknown}
    # ---- serving simulations ----
    z = np.load(f"{W}/receipts/P1_members_2025H2on.npz", allow_pickle=True)
    A = z["anchors"].astype(np.int64); MT = list(z["members_train_rule"]); crypto = z["crypto"]
    mk = np.load(MASK); mts = mk["ts"].astype(np.int64); legal = mk["mask"][np.searchsorted(mts, A)]
    L = np.zeros(len(syms), bool); L[[syms.index(s) for s in live]] = True
    sept = np.array([time.strftime("%Y-%m", time.gmtime(int(a))) == "2026-09" for a in A])
    cand = legal & crypto[None, :]
    F_cand = L | cand[sept].any(0)
    F_crypto = crypto.copy()
    out = {}
    for tag, F in (("F_450_plus_sept_candidates", F_cand), ("F_all_crypto_axis", F_crypto)):
        diffs = []; snt = collections.Counter(); tns = collections.Counter(); nonlegal_served = collections.Counter()
        for k, a in enumerate(A):
            ai = int(np.searchsorted(ts, a)); X = np.array(D[ai + 1 - 2016:ai + 1], np.float32); X[:, ~F, :] = np.nan
            mS, _, _ = producer_members(X, X.shape[0] - 1, P)
            a_ = set(mS.tolist()); b_ = set(np.asarray(MT[k]).tolist())
            s1 = a_ - b_; s2 = b_ - a_
            for j in s1:
                snt[syms[j]] += 1
                if not legal[k, j]: nonlegal_served[syms[j]] += 1
            for j in s2: tns[syms[j]] += 1
            diffs.append((time.strftime("%Y-%m", time.gmtime(int(a))), len(s1), len(s2)))
        bym = collections.defaultdict(lambda: [0, 0, 0])
        for m, x, y in diffs:
            bym[m][0] += 1; bym[m][1] += int(x > 0 or y > 0); bym[m][2] += x
        out[tag] = {"n_fetch": int(F.sum()), "n_added_beyond_450": int((F & ~L).sum()),
                    "added_beyond_450": sorted(syms[j] for j in np.flatnonzero(F & ~L)),
                    "anchors": len(A), "anchors_with_member_diff": sum(1 for _, x, y in diffs if x or y),
                    "by_month_[anchors,anchors_with_diff,served_not_train_cells]": {m: v for m, v in sorted(bym.items())},
                    "served_not_train": dict(snt.most_common()), "of_which_not_legal_at_anchor": dict(nonlegal_served.most_common()),
                    "train_not_served": dict(tns.most_common())}
    rec = {"device": os.path.abspath(__file__), "device_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "numpy": np.__version__, "earliest_tradfi_first_bar": earliest_tradfi, "tradfi_first_bars_first10": tf_first[:10],
           "unknown_names_rule_check": unk_rule, "sim": out, "seconds": round(time.time() - t0, 1)}
    p = f"{W}/receipts/P1B_FETCHLIST.json"; json.dump(rec, open(p + ".tmp", "w"), indent=1); os.replace(p + ".tmp", p)
    print("P1B done", {k: (v["n_fetch"], v["anchors_with_member_diff"]) for k, v in out.items()}, "earliest tradfi", earliest_tradfi, flush=True)

if __name__ == "__main__":
    main()

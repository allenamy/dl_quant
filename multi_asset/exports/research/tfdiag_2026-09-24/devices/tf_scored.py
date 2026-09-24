"""Were NEW's 149 TradFi names SCORED (i.e. in the member set / rank base) even though they were never HELD?

Distinguishes two very different worlds:
  (i)  TradFi were members and scored, but the mix always ranked them to zero weight  => the rank-base channel is real
  (ii) TradFi were never members at all                                               => there is no universe channel
       in NEW's scored path either, and the NEW-vs-NC gap cannot be a universe effect at all.
kc / fc / raw are the combo's dense (8142, 829) composite state; a name that was never a member should be
identically zero in all three at every anchor.
"""
import numpy as np, json, os, sys, time, hashlib

OUT = sys.argv[1] if len(sys.argv) > 1 else "/dev/shm/tfdiag_2026-09-24/receipts/TF_SCORED.json"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()

M = np.load("/dev/shm/news_2026-09-23/receipts/P1_members_2025H2on.npz", allow_pickle=True)
crypto = M["crypto"]; tf = ~crypto
out = {}
for seed in ("s42", "s2027"):
    C = np.load(f"/workspace/old_vs_new_2026-09-23/new_targets/combo_{seed}/scaled_diagnostic.npz", allow_pickle=True)
    d = {}
    for k in ("kc", "fc", "raw", "weights"):
        A = C[k]
        d[k] = {"nonzero_cells_tradfi": int((A[:, tf] != 0).sum()), "nonzero_cells_crypto": int((A[:, crypto] != 0).sum()),
                "finite_nonzero_tradfi": int(np.isfinite(A[:, tf]).sum() - (A[:, tf] == 0).sum()),
                "max_abs_tradfi": float(np.abs(np.nan_to_num(A[:, tf])).max()),
                "max_abs_crypto": float(np.abs(np.nan_to_num(A[:, crypto])).max()),
                "n_nan_tradfi": int(np.isnan(A[:, tf]).sum()), "n_nan_crypto": int(np.isnan(A[:, crypto]).sum())}
    # how many distinct crypto columns ever carry nonzero weight
    W = C["weights"]
    ever = (np.abs(W) > 0).any(axis=0)
    d["columns_ever_weighted"] = {"total": int(ever.sum()), "of_which_crypto": int((ever & crypto).sum()),
                                 "of_which_tradfi": int((ever & tf).sum()), "crypto_available": int(crypto.sum())}
    out[seed] = d

for seed, d in out.items():
    print(f"===== {seed} =====")
    for k in ("kc", "fc", "raw", "weights"):
        v = d[k]
        print("  %-8s tradfi nonzero=%-9d max|.|=%.3e nan=%-8d | crypto nonzero=%-9d max|.|=%.3e nan=%d"
              % (k, v["nonzero_cells_tradfi"], v["max_abs_tradfi"], v["n_nan_tradfi"],
                 v["nonzero_cells_crypto"], v["max_abs_crypto"], v["n_nan_crypto"]))
    c = d["columns_ever_weighted"]
    print("  columns ever weighted: %d (crypto %d of %d available, tradfi %d)"
          % (c["total"], c["of_which_crypto"], c["crypto_available"], c["of_which_tradfi"]))
rec = {"device": "chk_scored.py", "self_sha256": sha(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "question": "were NEW's 149 TradFi names present in the combo composite state at all, or identically zero",
       "reads": {seed: {"combo": f"/workspace/old_vs_new_2026-09-23/new_targets/combo_{seed}/scaled_diagnostic.npz",
                        "sha256": sha(f"/workspace/old_vs_new_2026-09-23/new_targets/combo_{seed}/scaled_diagnostic.npz")}
                 for seed in ("s42", "s2027")},
       "crypto_flag": {"path": "/dev/shm/news_2026-09-23/receipts/P1_members_2025H2on.npz",
                       "sha256": sha("/dev/shm/news_2026-09-23/receipts/P1_members_2025H2on.npz")},
       "per_seed": out,
       "finding": "kc, fc, raw and weights are ALL identically zero on every TradFi column at every anchor, both seeds",
       "limit_of_inference": ("this shows the TradFi names contribute nothing to the composite books. It does NOT by itself prove "
                              "they were absent from the member set, because the rank base is a MEMBER-LEVEL input "
                              "(king_rank / fund_rank, shape (n_members,)) which is not on disk. So the rank-base channel "
                              "remains untested, exactly as PREREG 58a29c04a section 0 states for (C)."),
       "ALL_ZERO_ON_TRADFI": bool(all(out[s][k]["nonzero_cells_tradfi"] == 0 for s in out for k in ("kc", "fc", "raw", "weights")))}
json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
print("TF_SCORED written", OUT, sha(OUT), "ALL_ZERO_ON_TRADFI=" + str(rec["ALL_ZERO_ON_TRADFI"]),
      "columns_ever_weighted=" + str({s: out[s]["columns_ever_weighted"]["total"] for s in out}), flush=True)

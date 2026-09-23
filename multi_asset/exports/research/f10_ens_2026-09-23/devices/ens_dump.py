#!/usr/bin/env python3
"""ens_dump.py — STEP 1 of docs/PREREG_f10_seed_ensemble_book_2026-09-23.md (45aba1f3f, sha 56acd832): dump HOW the researcher's combo consumes
F10 before any ENS file is written. Read-only on the researcher's tree (python -B; nothing is written there).

Facts dumped (no NAV / return number is touched):
  K1  F10_OOF.npz key set, dtypes, shapes for both seeds; E_ts / symbols equal across seeds and equal to dlw_targets E_ts / symbols.
  K2  the consumption point, quoted from the pinned sources: combo_target.step() `okf=np.isfinite(f10_score)` → `rankdata(f10_score[okf])`
      over the anchor's MEMBER names only (continuous_combo.evolve passes f10[i, members[i]]); the scaled_diagnostic coverage gate counts
      okf.sum() (finite F10 among members) against ceil(0.95·n_members); literal against 380.
  K3  per anchor on the combo axis (E_ts >= 2023-01-01T00Z and <= universe_ext ts[-1], exactly continuous_combo.main's `use`):
      n_members; per seed: finite count over all 829 names, finite count over members; finite names outside members; both-finite count
      over all names and over members; ONLY-ONE-FINITE count over all names and over members (the prereg expects 0).
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B ens_dump.py PATH,HOME,LC_CTYPE <out.json>
"""
import os, sys, json, time, hashlib, collections, datetime

WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
import numpy as np

OUT = sys.argv[2]
CR = "/workspace/codex_research/QNT-2026-0907/combo_20260923"
V1D = CR + "/corrected_combo_v1d"
PIN = {  # the shas recorded in combo_s42/combo_s2027 TARGET_RECEIPT.json (inputs / sources) and POST_TRAIN_QUEUE.json
    V1D + "/data/dlw_targets.npz": "ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62",
    V1D + "/f10_s42/F10_OOF.npz": "bbc077d93669f249967980377dfe4b4fad438447773cf1f9a971712a5d7ac125",
    V1D + "/f10_s2027/F10_OOF.npz": "b7327184b2a44c4ab2846f2d00f2f49fde8f0c330e8740d7a765b9951f307a57",
    "/workspace/object_b_2026-09-19/work/ext_inputs/universe_ext.npz": "3ee838cfc4ee4b90cef9202716af8645ff601b69137346d518ea706a5f4d598f",
    CR + "/devices/combo_target.py": "d7577e824298fb90a554f35ac9c4d634202a4ed7e4e00cabc597a2d4eafdb544",
    CR + "/devices/continuous_combo.py": "1501c9f63641bf447c4cb33661d08da25ced0948f9fae63cebb44cdfd1995d21",
}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


got = {p: sha(p) for p in PIN}
bad = {p: (got[p][:16], PIN[p][:16]) for p in PIN if got[p] != PIN[p]}
assert not bad, f"pinned input drift: {bad}"
rec = {"device": "ens_dump.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": iso(time.time()), "inputs": got}

# K2: quote the consumption lines from the pinned sources (exact substrings; refuse if absent)
ct = open(CR + "/devices/combo_target.py").read(); cc = open(CR + "/devices/continuous_combo.py").read()
QUOTES = {"combo_target.step": ["okf=np.isfinite(f10_score);zf=np.full(n,np.nan)", "zf[okf]=rankdata(np.asarray(f10_score)[okf])/max(okf.sum()-1,1)-.5",
                                "coverage_gate=380 if publication=='literal' else int(np.ceil(.95*n))", "if okf.sum()<coverage_gate:reasons.append('F10 coverage')",
                                "zfc=w[0]*np.nan_to_num(zf,nan=0.)+w[2]*np.nan_to_num(fund_rank,nan=0.)"],
          "continuous_combo.evolve": ["result=step(k[i,m],f10[i,m],fund[i,m],seats[i],rn8[i,m],m,qv[i,m],legal[i],params,kc,fc,publication)"],
          "continuous_combo.main": ["froot=r/f'f10_s{args.seed}'", "score=np.load(paths[5])", "score['P'][use]",
                                    "use=(a>=1672531200)&(a<=universe['ts'][-1]);a=a[use]"]}
for src, qs in QUOTES.items():
    txt = ct if src.startswith("combo_target") else cc
    for q in qs: assert q in txt, f"consumption line not found in {src}: {q}"
rec["K2_consumption_quotes"] = QUOTES
rec["K2_reading"] = ("F10 enters ONLY via step(): finite member scores are ranked (scipy rankdata, method 'average') and mapped to rank/(n_finite-1)-0.5; "
                     "non-finite members get zf = NaN -> nan_to_num 0 in the F10 chain input; the publication gate counts okf.sum() = finite F10 among MEMBERS.")

# K1
Z = {s: np.load(V1D + f"/f10_s{s}/F10_OOF.npz", allow_pickle=False) for s in (42, 2027)}
T = np.load(V1D + "/data/dlw_targets.npz", allow_pickle=True)
rec["K1_keys"] = {str(s): {k: [str(Z[s][k].dtype), list(Z[s][k].shape)] for k in Z[s].files} for s in Z}
P = {s: Z[s]["P"] for s in Z}
for s in Z: assert set(Z[s].files) == {"P", "E_ts", "symbols"}, Z[s].files
assert np.array_equal(Z[42]["E_ts"], Z[2027]["E_ts"]) and np.array_equal(Z[42]["symbols"], Z[2027]["symbols"])
assert np.array_equal(Z[42]["E_ts"], T["E_ts"]) and np.array_equal(Z[42]["symbols"], T["symbols"])
rec["K1_axes_equal_across_seeds_and_dlw_targets"] = True
U = np.load("/workspace/object_b_2026-09-19/work/ext_inputs/universe_ext.npz", allow_pickle=True)
a = T["E_ts"]; use = (a >= 1672531200) & (a <= U["ts"][-1]); idx = np.nonzero(use)[0]
rec["combo_axis"] = {"first": iso(a[idx[0]]), "last": iso(a[idx[-1]]), "n": int(len(idx)), "rule": "continuous_combo.main use=(a>=1672531200)&(a<=universe['ts'][-1])"}
rec["full_file_axis"] = {"first": iso(a[0]), "last": iso(a[-1]), "n": int(len(a))}

# K3 per anchor
W = P[42].shape[1]
rows = []
agg = collections.defaultdict(lambda: collections.Counter())
for i in idx:
    m = np.asarray(T["members"][i], int); inm = np.zeros(W, bool); inm[m] = True
    f42 = np.isfinite(P[42][i]); f27 = np.isfinite(P[2027][i]); both = f42 & f27; one = f42 ^ f27
    r = {"n_members": int(len(m)), "fin42_all": int(f42.sum()), "fin2027_all": int(f27.sum()), "fin42_mem": int((f42 & inm).sum()), "fin2027_mem": int((f27 & inm).sum()),
         "fin42_outside_members": int((f42 & ~inm).sum()), "fin2027_outside_members": int((f27 & ~inm).sum()),
         "both_all": int(both.sum()), "both_mem": int((both & inm).sum()), "one_only_all": int(one.sum()), "one_only_mem": int((one & inm).sum())}
    rows.append(r)
    y = datetime.datetime.fromtimestamp(int(a[i]), datetime.timezone.utc).year
    for k, v in r.items(): agg[str(y)][k] += v
    agg[str(y)]["anchors"] += 1
    for k in ("one_only_all", "one_only_mem", "fin42_outside_members", "fin2027_outside_members"):
        if r[k] > 0: agg[str(y)]["anchors_with_" + k] += 1
    if r["both_all"] == 0: agg[str(y)]["anchors_with_no_finite_F10"] += 1
rec["K3_by_year"] = {y: dict(c) for y, c in sorted(agg.items())}
tot = collections.Counter()
for c in agg.values(): tot.update(c)
rec["K3_total"] = dict(tot)
rec["K3_statement"] = {"one_only_all_total": int(tot["one_only_all"]), "one_only_mem_total": int(tot["one_only_mem"]),
                       "finite_outside_members_total_s42": int(tot["fin42_outside_members"]), "finite_outside_members_total_s2027": int(tot["fin2027_outside_members"]),
                       "anchors": int(tot["anchors"])}
if len(rows) == 0: raise ValueError("empty combo axis")
json.dump(rec, open(OUT + ".tmp", "w"), indent=1); os.replace(OUT + ".tmp", OUT)
print("ENS_DUMP DONE", json.dumps(rec["K3_statement"]), "out_sha256", sha(OUT), flush=True)

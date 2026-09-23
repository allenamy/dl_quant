"""SWAPPKG step-1 evidence, POD half (read-only on the researcher root; runs from /dev/shm).
Compares the NEW training member population (corrected_combo_v1d/data/dlw_targets.npz `members`,
built by build_combo_inputs.py:123 = feature_contract.select_members over the legal mask) with
(a) the production member list served at the same anchor (pop_check_local.json), and
(b) the columns for which the production rolling cache holds ANY data (the producer fetches only symbols_live).
Also tabulates, over the whole NEW axis, how many NEW members per anchor are outside cfg symbols_live."""
import os, sys, json, hashlib, time
import numpy as np
R = "/workspace/codex_research/QNT-2026-0907/combo_20260923"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()
local_p = sys.argv[1]
paths = {"targets": f"{R}/corrected_combo_v1d/data/dlw_targets.npz",
         "build_receipt": f"{R}/corrected_combo_v1d/BUILD_RECEIPT.json",
         "config": f"{R}/vendor_live/shadow_bundle/config.json",
         "legal_mask": "/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz",
         "pop_check_local": local_p}
ident = {k: sha(p) for k, p in paths.items()}
br = json.load(open(paths["build_receipt"]))
assert br["artifacts"][paths["targets"]] == ident["targets"], "targets are not the receipted NEW build"
assert ident["config"] == "3a8422f377519cac77b0c42305d2ba40a4b7a42a830f0542bda844f66647c94e"
assert br["inputs"][paths["legal_mask"]] == ident["legal_mask"], "legal mask is not the one NEW was built from"
t = np.load(paths["targets"], allow_pickle=True); a = t["E_ts"].astype(np.int64); syms = [str(s) for s in t["symbols"]]
cfg = json.load(open(paths["config"])); assert syms == cfg["symbols_panel"]
live = np.array([s in set(cfg["symbols_live"]) for s in syms])
mk = np.load(paths["legal_mask"]); assert [str(s) for s in mk["symbols"]] == syms
loc = json.load(open(local_p))
res = {"device": "pop_check_pod.py", "self_sha256": sha(os.path.abspath(__file__)), "inputs": {paths[k]: v for k, v in ident.items()},
       "per_snapshot_anchor": {}, "by_year": {}, "by_month_2026": {}}
for A, v in sorted(loc["anchors"].items(), key=lambda x: int(x[0])):
    A = int(A); i = int(np.flatnonzero(a == A)[0]); nm = set(int(x) for x in t["members"][i]); pm = set(v["members"])
    have = set(v["cols_with_data_last2016"]); li = int(np.flatnonzero(mk["ts"] == A)[0]); lg = mk["mask"][li]
    res["per_snapshot_anchor"][str(A)] = {
        "utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(A)),
        "n_new_members": len(nm), "n_prod_members": len(pm), "n_common": len(nm & pm),
        "new_only": sorted(syms[j] for j in nm - pm), "prod_only": sorted(syms[j] for j in pm - nm),
        "new_members_without_any_live_cache_data": len(nm - have),
        "new_members_outside_symbols_live": int(sum(not live[j] for j in nm)),
        "legal_mask_true": int(lg.sum()), "legal_and_live": int((lg & live).sum()),
        "prod_members_not_legal": int(sum(not lg[j] for j in pm))}
yrs = np.array([time.gmtime(int(x)).tm_year for x in a]); mon = np.array([time.strftime("%Y-%m", time.gmtime(int(x))) for x in a])
nout = np.array([int((~live[np.asarray(m, int)]).sum()) for m in t["members"]]); nmem = np.array([len(m) for m in t["members"]])
for y in np.unique(yrs):
    s = yrs == y
    res["by_year"][str(y)] = {"anchors": int(s.sum()), "mean_members": round(float(nmem[s].mean()), 2),
                              "mean_outside_live": round(float(nout[s].mean()), 2), "min_outside_live": int(nout[s].min()), "max_outside_live": int(nout[s].max()),
                              "share_member_cells_outside_live": round(float(nout[s].sum() / nmem[s].sum()), 4)}
for m_ in sorted(set(mon[yrs == 2026])):
    s = mon == m_; res["by_month_2026"][m_] = {"mean_outside_live": round(float(nout[s].mean()), 2), "min": int(nout[s].min()), "max": int(nout[s].max())}
last = len(a) - 1
res["last_axis_anchor"] = {"utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(a[last]))),
                           "new_members_outside_live": sorted(syms[j] for j in np.asarray(t["members"][last], int) if not live[j])}
out = os.path.join(os.path.dirname(local_p), "pop_check_pod.json")
json.dump(res, open(out, "w"), indent=1)
print(json.dumps({k: res[k] for k in ("by_year", "by_month_2026")}))
for A, r in res["per_snapshot_anchor"].items():
    print(A, r["utc"], "NEW", r["n_new_members"], "PROD", r["n_prod_members"], "common", r["n_common"], "NEW_without_live_data", r["new_members_without_any_live_cache_data"])
print("POP_CHECK_POD_DONE")

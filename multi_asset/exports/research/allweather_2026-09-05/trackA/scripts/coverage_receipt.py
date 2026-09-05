"""coverage_receipt.py — data-coverage receipts for the RESULT (VERIFIED): per source (spot, perp-close, premium index) the number of symbols with
any data, first/last bar, and the share of META member cells (anchor × member) whose source is available at the anchor's right edge, by year;
plus the spot mapping summary and manifest counts. Read-only. env: ROOT META_IN OUT_JSON"""
import os, json, time, hashlib
import numpy as np
ROOT = os.environ.get("ROOT", "/workspace/review_scratch/allweather_trackA"); OUT = os.environ["OUT_JSON"]
MT = np.load(os.environ.get("META_IN", "/workspace/data/wide_fea_v2ext_meta.npz"), allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; nA = len(E_ts); yrs = np.array([time.gmtime(int(t)).tm_year for t in E_ts])
import sys; sys.path.insert(0, "/workspace")
from zload import zload
Z = zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz", allow_pickle=True); CTS = Z["ts"].astype(np.int64); SYMS = [str(s) for s in Z["symbols"]]; T0 = int(CTS[0]); del Z
R = (E_ts - T0) // 300 - 1
A1S = json.load(open(f"{ROOT}/features/a1_syms.json")); MS = A1S["syms"]
memmask = np.zeros((nA, 829), bool)
for i in range(nA): memmask[i, members[i]] = True
def fmt(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t))) if t is not None else None
res = {"self_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(), "n_meta_anchors": int(nA), "member_cells": int(memmask.sum()), "sources": {}}
def source(name, arr, rows_syms):
    """arr: (n_rows, T) memmap; rows_syms: perp symbol per row."""
    nsym = 0; first = None; last = None; av = np.zeros((nA, 829), bool)
    for r, s in enumerate(rows_syms):
        x = arr[r]; fin = np.isfinite(x)
        if not fin.any(): continue
        nsym += 1; w = np.where(fin)[0]; f_, l_ = int(CTS[w[0]]), int(CTS[w[-1]])
        first = f_ if first is None else min(first, f_); last = l_ if last is None else max(last, l_)
        av[:, SYMS.index(s)] = fin[R]
    cells = memmask & av
    by = {str(y): round(float(cells[yrs == y].sum() / memmask[yrs == y].sum()), 4) for y in sorted(set(yrs.tolist()))}
    res["sources"][name] = {"rows": len(rows_syms), "symbols_with_data": nsym, "first_bar_close": fmt(first), "last_bar_close": fmt(last),
                            "member_cell_availability_overall": round(float(cells.sum() / memmask.sum()), 4), "by_year": by}
    print(name, res["sources"][name], flush=True)
source("spot_close", np.load(f"{ROOT}/features/a1_spot_close.npy", mmap_mode="r"), MS)
source("perp_close", np.load(f"{ROOT}/features/a1_perp_close.npy", mmap_mode="r"), MS)
source("premidx", np.load(f"{ROOT}/features/premidx_5m.npy", mmap_mode="r"), SYMS)
MP = json.load(open(f"{ROOT}/spot/perp_to_spot_map.json"))
res["spot_mapping"] = {"n_perp": MP["n_perp"], "n_mapped": MP["n_mapped"], "n_unmapped": len(MP["unmapped"]), "rule_counts": {}}
for v in MP["map"].values(): res["spot_mapping"]["rule_counts"][v["rule"]] = res["spot_mapping"]["rule_counts"].get(v["rule"], 0) + 1
res["spot_mapping"]["strip_cases"] = {k: v for k, v in MP["map"].items() if v["rule"] != "same"}
res["spot_mapping"]["prefixed_names_that_exist_on_spot_as_is"] = [k for k, v in MP["map"].items() if k.startswith("1000") and v["rule"] == "same"]
def mcount(p):
    n = {"zips": 0, "404": 0, "bad": 0, "bytes": 0}
    for line in open(p):
        d = json.loads(line)
        if "sha256" in d: n["zips"] += 1; n["bytes"] += d["bytes"]
        elif d.get("status") == 404: n["404"] += 1
        else: n["bad"] += 1
    return n
res["manifests"] = {"a1_spot_perp": mcount(f"{ROOT}/spot/a1_manifest.jsonl"), "a2_premidx": mcount(f"{ROOT}/premidx/a2_manifest.jsonl")}
print("manifests", res["manifests"], flush=True)
json.dump(res, open(OUT, "w"), indent=1); print("COVERAGE_DONE", flush=True)

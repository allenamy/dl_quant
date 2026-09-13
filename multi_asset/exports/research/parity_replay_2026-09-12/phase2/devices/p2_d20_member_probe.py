#!/usr/bin/env python3
"""D20 member-set probe (descriptive, no gate) — follow-up to AMENDMENT 7 §A7.3 after S2_TABLES reported 0 dropped cells for SLOW_v4 on the exporter
member set. Question: is the forward-label condition already inside the exporter's member set? Per year (king-fold years 2024-2026 and, for context, 2022-2023):
  (a) wide_fea_v4_meta (king exporter meta): member cells, member cells with non-finite y4 (forward label), rows where every member has a finite label;
  (b) meta_newprod_v4 (research accounting meta) with the research member rule (finite qvk ∩ umask_UPIT_CRYPTO): member cells with non-finite y4;
  (c) production-path coverage from receipts/S2_causality_audit.json: king n_finite / n_members on served anchors (D10 ∪ D20 on the production member set).
Read-only; writes receipts/S2_D20_member_probe.json; one summary line.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B p2_d20_member_probe.py PATH,HOME,LC_CTYPE"""
import os, sys, json, time, hashlib
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
import numpy as np
P2 = "/workspace/uplift_r2_2026-09-13/P2"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 22), b""): h.update(ch)
    return h.hexdigest()
IN = {"king_meta_v4": ("/workspace/data/wide_fea_v4_meta.npz", "12ea42c4557093f10f954f648db9239f4dd8283ea365ba299f31bd81e7e5ab51"),
      "meta_newprod_v4": ("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz", "0e3c09ac86c727ac1a7893889918e3b367463fd059a154f5e320eed47f5725c3"),
      "panel": ("/workspace/data/wide_panel_4h_v2ext.npz", "5e67c0559daa904d8f0526b6e268e93dcb45aab89d82646cf79a794445481116"),
      "umask": ("/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz", "47d87b5165b695a7d9b340134a189dd6a2165c837bab35808b699ffac3f7f1b5")}
for k, (p, s) in IN.items(): assert sha(p) == s, k
T0 = time.time()
import calendar
AX0 = calendar.timegm((2022, 1, 31, 0, 0, 0)); AX1 = calendar.timegm((2026, 8, 31, 0, 0, 0))   # A0 axis
K = np.load(IN["king_meta_v4"][0], allow_pickle=True); KE = K["E_ts"].astype(np.int64); KM = K["members"]; KY = K["y4"]
M = np.load(IN["meta_newprod_v4"][0], allow_pickle=True); ME = M["E_ts"].astype(np.int64); MY = M["y4"]; MQ = M["qvk"]
assert np.array_equal(KE, ME)
PW = np.load(IN["panel"][0], allow_pickle=True); prow = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
U = np.load(IN["umask"][0], allow_pickle=True); umap = {int(t): k for k, t in enumerate(U["ts"].astype(np.int64))}; UM = np.asarray(U["mask"])
out = {"a_king_exporter_members": {}, "b_research_members": {}}
for i, t in enumerate(KE):
    if t < AX0 or t > AX1: continue
    y = str(time.gmtime(int(t)).tm_year)
    m = np.asarray(KM[i], np.int64); fin = np.isfinite(KY[i, m])
    a = out["a_king_exporter_members"].setdefault(y, dict(rows=0, member_cells=0, member_cells_nonfinite_y4=0, rows_all_members_finite=0, rows_lt50_finite=0))
    a["rows"] += 1; a["member_cells"] += int(len(m)); a["member_cells_nonfinite_y4"] += int((~fin).sum()); a["rows_all_members_finite"] += int(fin.all()); a["rows_lt50_finite"] += int(fin.sum() < 50)
    q = np.nan_to_num(MQ[i], nan=-1.0); o = np.argsort(-q); o = o[q[o] > -0.5]; mm = np.sort(o[:829]).astype(np.int64)
    j = prow.get(int(t)); k_ = umap.get(int(t)) if j is not None else None
    if k_ is not None: mm = mm[UM[k_][mm]]
    b = out["b_research_members"].setdefault(y, dict(rows=0, member_cells=0, member_cells_nonfinite_y4=0))
    b["rows"] += 1; b["member_cells"] += int(len(mm)); b["member_cells_nonfinite_y4"] += int((~np.isfinite(MY[i, mm])).sum())
AU = json.load(open(P2 + "/receipts/S2_causality_audit.json"))
out["c_production_king_coverage_on_served"] = {tag: {y: v.get("king_coverage_mean_on_served") for y, v in arm["by_year"].items()} for tag, arm in AU["arms"].items()}
out["c_production_f10_coverage"] = {tag: {y: v.get("f10_coverage_mean") for y, v in arm["by_year"].items()} for tag, arm in AU["arms"].items()}
R = dict(device="p2_d20_member_probe.py", self_sha256=sha(os.path.abspath(__file__)), env=dict(os.environ), inputs={k: dict(path=p, sha256=s) for k, (p, s) in IN.items()},
         audit_sha256=sha(P2 + "/receipts/S2_causality_audit.json"), results=out, runtime_s=round(time.time() - T0, 1), utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
rp = P2 + "/receipts/S2_D20_member_probe.json"; json.dump(R, open(rp + ".tmp", "w"), indent=1); os.replace(rp + ".tmp", rp)
a = out["a_king_exporter_members"]; b = out["b_research_members"]
print("S2_D20_MEMBER_PROBE exporter_nonfinite=%s research_nonfinite=%s receipt_sha256=%s" % ({y: v["member_cells_nonfinite_y4"] for y, v in a.items()}, {y: v["member_cells_nonfinite_y4"] for y, v in b.items()}, sha(rp)), flush=True)

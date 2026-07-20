"""Run a factory batch through the full-window pipeline into the real hash-chain ledger, then emit the
ledger-level report (per-formula verdict + death_cause + family stats). CPU, long-running.

Usage: python run_campaign.py <batch_file> [horizon=4] [subsample=1] [null_r=200]
"""
import json
import re
import sys

import numpy as np

sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/factory")
import pipeline as P
from ledger import Ledger

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
LEDGER_PATH = MA + "/exports/eda/factory_ledger.jsonl"


def parse_batch(path):
    items = []
    for line in open(path):
        s = line.split("#", 1)[0].rstrip()               # drop trailing rationale comment
        if not s.strip() or ":" not in s:
            continue
        idp, formula = s.split(":", 1)
        idp = idp.strip()
        if re.match(r"^[A-E]\d+$", idp):
            items.append((idp, idp[0], formula.strip()))
    return items


def main():
    batch = sys.argv[1]
    horizon = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    subsample = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    null_r = int(sys.argv[4]) if len(sys.argv) > 4 else 200
    global LEDGER_PATH
    if len(sys.argv) > 5:
        LEDGER_PATH = sys.argv[5]
    items = parse_batch(batch)
    id_by_formula = {f: (i, fam) for (i, fam, f) in items}
    formulas = [f for _, _, f in items]
    print(f"[campaign] {len(items)} formulas from {batch} | horizon {horizon} | subsample {subsample} | null_r {null_r}", flush=True)

    C = P.load_context(horizon=horizon, subsample=subsample)
    print(f"[campaign] eval anchors (2022-2025, holdout {P.HOLDOUT_YEAR} excluded): {len(C['rows'])}", flush=True)
    res = P.run_batch(formulas, horizon=horizon, seed=0, ledger_path=LEDGER_PATH, subsample=subsample,
                      null_r=null_r, C=C)

    # ---- ledger-level report ----
    lg = Ledger(LEDGER_PATH)
    assert lg.verify(), "hash chain broken"
    # final verdict per formula: stage1 row if it exists, else stage0 row
    final = {}
    for r in lg._rows:
        f = r["formula_str"]
        if f not in id_by_formula:
            continue
        if r["stage"] == "stage1" or f not in final:
            final[f] = r
    rows = []
    for (i, fam, f) in items:
        r = final.get(f, {})
        rows.append(dict(id=i, family=fam, formula=f, verdict=r.get("verdict"),
                         death_cause=r.get("death_cause"),
                         inc_ic=(r.get("stage1_stats", {}).get("inc_ic") if r.get("stage") == "stage1"
                                 else r.get("inc_ic")),
                         z=(r.get("stage1_stats", {}) or {}).get("z")))
    # family aggregates
    fams = {}
    for row in rows:
        fam = row["family"]; fams.setdefault(fam, {"n": 0, "candidate": 0, "death": {}})
        fams[fam]["n"] += 1
        if row["verdict"] == "CANDIDATE":
            fams[fam]["candidate"] += 1
        dc = row["death_cause"] or ("candidate" if row["verdict"] == "CANDIDATE" else "unknown")
        fams[fam]["death"][dc] = fams[fam]["death"].get(dc, 0) + 1
    report = dict(batch=batch, horizon=horizon, n_formulas=len(items),
                  ledger_M=lg.M(), stage0_survivors=res["n_stage0_survivors"],
                  candidates=res["candidates"], per_family=fams, per_formula=rows)
    out = MA + f"/exports/eda/campaign_report_{batch.split('/')[-1].replace('.txt','')}_h{horizon}.json"
    json.dump(report, open(out, "w"), indent=1, default=str)
    print(f"\n[campaign] DONE. ledger_M={lg.M()} stage0_survivors={res['n_stage0_survivors']} "
          f"CANDIDATES={res['candidates']}", flush=True)
    print("[campaign] per-family death-cause distribution:", flush=True)
    for fam in sorted(fams):
        print(f"  {fam}: n={fams[fam]['n']} candidates={fams[fam]['candidate']} deaths={fams[fam]['death']}", flush=True)
    print("[campaign] saved " + out, flush=True)


if __name__ == "__main__":
    main()

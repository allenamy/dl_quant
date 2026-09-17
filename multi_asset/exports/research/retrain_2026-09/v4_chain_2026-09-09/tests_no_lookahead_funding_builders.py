#!/usr/bin/env python3
"""FP2-2 (independent review R16-D1, 2026-09-17): the look-ahead funding builders are RETIRED and OFF the chain.

The three builders below take a per-symbol quantity from the whole series (`np.median(funding_interval_h)` over all rows) —
a look-ahead. They were never on the v4 chain; this test makes that a checked fact, not a memory:
  [A] each file carries the RETIRED marker and refuses to run its main() without the explicit override
  [B] the v4 chain scripts, the monthly driver, the October runbook and the month contracts reference none of them
  [C] the builders that ARE on the chain for funding features contain no full-span median
Nothing here touches pod2; it is a source-level census with a behavioural check of the refusal.
"""
import os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
FAILS, N = [], [0]
def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:220]) if detail is not None else ""), flush=True)
RETIRED = ["multi_asset/data/build_funding_hist.py", "multi_asset/data/megacap_funding_replay.py", "multi_asset/data/apply_funding_fix.py"]
print("[A] retired markers + refusal")
for rel in RETIRED:
    p = os.path.join(REPO, rel); src = open(p, encoding="utf-8").read()
    check(f"★★ {rel} carries RETIRED_LOOKAHEAD = True and the override name", "RETIRED_LOOKAHEAD = True" in src and "ALLOW_RETIRED_LOOKAHEAD_BUILDER" in src)
    r = subprocess.run([sys.executable, p], capture_output=True, text=True, env={k: v for k, v in os.environ.items() if k != "ALLOW_RETIRED_LOOKAHEAD_BUILDER"}, timeout=60)
    check(f"★★★ running {os.path.basename(rel)} without the override REFUSES (non-zero, names RETIRED)", r.returncode != 0 and "RETIRED" in (r.stdout + r.stderr), (r.returncode, (r.stdout + r.stderr)[-160:]))
print("\n[B] census: none of them is referenced by the chain")
chain_files = [os.path.join(HERE, f) for f in os.listdir(HERE) if f.endswith((".sh", ".env", ".template", ".py")) and not f.startswith("tests_")]
chain_files += [os.path.join(REPO, "docs", "RUNBOOK_monthly_retrain_2026-10.md")]
hits = []
for f in chain_files:
    try: s = open(f, encoding="utf-8", errors="replace").read()
    except Exception: continue
    for rel in RETIRED:
        nm = os.path.basename(rel)[:-3]
        if re.search(r"\b" + re.escape(nm) + r"\b", s) and os.path.basename(f) != "tests_no_lookahead_funding_builders.py":
            hits.append((os.path.relpath(f, REPO), nm))
check("★★★ no chain script / contract / runbook references a retired look-ahead builder", not hits, hits[:6])
print("\n[C] the on-chain funding builders have no full-span median")
onchain = ["multi_asset/exports/research/runpod_scripts/workspace_mirror/code/multi_asset/data/build_fund_ema_fullhist.py"]
for rel in onchain:
    p = os.path.join(REPO, rel)
    if not os.path.exists(p):
        print(f"  UNAVAIL {rel} not present locally — census cell not run"); continue
    s = open(p, encoding="utf-8").read()
    check(f"★★ {os.path.basename(rel)}: no np.median over an interval series", not re.search(r"median\s*\(", s), [l.strip()[:80] for l in s.splitlines() if "median" in l][:3])
print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
if FAILS: print("FAILED:", *FAILS, sep="\n  "); sys.exit(1)
print("ALL PASS")

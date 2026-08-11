"""Lock + hash-chain tests for the factory ledger (factory_prereg §4)."""
import sys, os, tempfile
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/factory")
import ledger as L

FAILS = []
def check(name, cond):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}", flush=True)
    if not cond: FAILS.append(name)

tmp = tempfile.mktemp(suffix=".jsonl")
lg = L.Ledger(tmp)

# Stage-0 can write REJECT / TRIAGE_SURVIVOR, and M increments per append (incl. rejects)
lg.append_stage0("neg(mom_24h)", "aaa", 1, 1, inc_ic=0.001, fdr_q=0.4, survived=False)
lg.append_stage0("xsec_rank(ret_1h)", "bbb", 1, 1, inc_ic=0.008, fdr_q=0.05, survived=True)
check("(ii) M = cumulative rows incl. rejects", lg.M() == 2)

# Lock (i): Stage-0 path CANNOT write a discovery verdict
try:
    lg._append({"verdict": "CANDIDATE"}, L.STAGE0_VERDICTS); leaked = True
except PermissionError:
    leaked = False
check("(i) Stage-0 path cannot write CANDIDATE", not leaked)

# Lock (i): a CANDIDATE/ACCEPT needs stage1_stats (fdr_q alone can't drive a verdict)
try:
    lg._append({"verdict": "CANDIDATE", "fdr_q": 0.01}, L.STAGE1_VERDICTS); fdr_drove = True
except PermissionError:
    fdr_drove = False
check("(i) fdr_q alone cannot set a discovery verdict", not fdr_drove)

# Stage-1 path can write CANDIDATE with stats, and records the campaign M as the Bonferroni denominator
eid = lg.append_stage1("where(gt(rvol_24h,0),king,s2)", "ccc", 3, 3,
                       stage1_stats={"inc_ic": 0.009, "z": 4.6, "reality_check_pass": True,
                                     "sign_consistent": True, "ci_lo": 0.004}, verdict="CANDIDATE")
row = lg._rows[-1]
check("(i) Stage-1 can write CANDIDATE", row["verdict"] == "CANDIDATE")
check("(ii) Bonferroni denominator = ledger M (not survivor count)", row["stage1_stats"]["bonferroni_M"] == 3 and row["stage1_stats"]["bonferroni_z"] == 4.42)
check("accepted/candidate tracked", eid == 3)

# hash chain integrity
check("hash chain verifies", lg.verify())
# tamper -> chain breaks
lg._rows[1]["inc_ic"] = 0.99
check("tamper breaks the chain", not lg.verify())

os.remove(tmp)
print(f"\n{'#'*56}\nLEDGER TESTS {'OK' if not FAILS else 'FAILED: ' + str(FAILS)}\n{'#'*56}", flush=True)
sys.exit(0 if not FAILS else 1)

#!/usr/bin/env python3
"""t5d_posthoc_fallback.py — pod2, CPU (nice), READ-ONLY. POST-HOC: the 11 settlements whose interval stayed at the x0910 value (no ledger row, no usable gap)
are second-late duplicate records at a 1h→8h switch; 8 are in force at one tail anchor each. This reports the weights that the deployed king chain (archived kc),
the deployed book (target_live) and the replay king chain (T5c and REG arms, KA/KB, both seeds) hold on those name × anchor cells, and whether the name is in
the replay member set there, so that the size of any effect on price/carry is bounded by receipts rather than asserted.
Launch: bash devices/launch_pod2.sh t5d_posthoc_fallback.py
"""
import os, sys, json, time, hashlib, subprocess
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE and sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
R = "/workspace/uplift_r2_2026-09-13/T5d"; T5C = "/workspace/uplift_r2_2026-09-13/T5c"; PREREG_SHA = "a1ef16cdba5e95def27f77b180cba3f1ac954ad04c7b0a17f59c24e1a0c85a4f"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()
def sh(cmd):
    try: return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as e: return "ERR %s" % e
assert sha(R + "/PREREG_T5d_iv_corrected_replay_2026-09-13.md") == PREREG_SHA
GPU0 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID0 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); assert GPU0.replace(" ", "") == "0%,2MiB", GPU0
U = lambda t: time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
PH = json.load(open(R + "/receipts/RECEIPT_T5d_posthoc.json")); DRV = json.load(open(R + "/receipts/RECEIPT_T5d_drive.json")); T5CD = json.load(open(T5C + "/receipts/RECEIPT_T5c_drive.json")); BRC = json.load(open(R + "/receipts/RECEIPT_T5d_bridge.json"))
INGP = T5C + "/receipts/T5c_live_ingredients.npz"; PXC = json.load(open(R + "/receipts/RECEIPT_T5d_ivfix_panel.json"))["out"]; PXX = "/workspace/uplift_2026-09-11/r6/out/wide_panel_4h_v2ext_x0910.npz"
TAGS = ("KA_s42", "KA_s2027", "KB_s42", "KB_s2027"); ARMS = {("REG", t): DRV["runs"][t]["out"] for t in TAGS}; ARMS.update({("T5C", t): T5CD["runs"][t]["out"] for t in TAGS})
EXP = {INGP: BRC["inputs"][INGP], PXC: BRC["inputs"][PXC], PXX: BRC["inputs"][PXX]}; EXP.update({p: (DRV["runs"][k[1]]["out_sha256"] if k[0] == "REG" else T5CD["runs"][k[1]]["out_sha256"]) for k, p in ARMS.items()})
INPUTS = {p: sha(p) for p in EXP}
for p, h in EXP.items(): assert INPUTS[p] == h, ("INPUT SHA", p)
ING = np.load(INGP, allow_pickle=True); SYM = [str(x) for x in ING["symbols"]]; CAL = [int(x) for x in ING["cal"]]; KC = ING["KC"]; WTL = ING["WTL"]
PC = np.load(PXC, allow_pickle=True); PX = np.load(PXX, allow_pickle=True); prow = {int(t): q for q, t in enumerate(PC["ts"].astype(np.int64))}
FNc = PC["f_fund_now"]; IVc = PC["f_fund_iv"]; IVx = PX["f_fund_iv"]
D = {k: np.load(p, allow_pickle=True) for k, p in ARMS.items()}; pre = "d30_n2_c42_T5_"
cells = []
for f in PH["A"]["fallback_settlements"]:
    n = SYM.index(f["symbol"])
    for a in f["in_force_at"]:
        A = next(t for t in CAL if U(t) == a); k = CAL.index(A); r = prow[A]
        row = dict(symbol=f["symbol"], anchor=a, settlement=f["settlement"], f_fund_now=float(FNc[r, n]), f_fund_iv_corrected=float(IVc[r, n]), f_fund_iv_x0910=float(IVx[r, n]),
                   w_deployed_king_chain=float(KC[k, n] / np.abs(KC[k]).sum()), w_deployed_book=float(WTL[k, n] / np.abs(WTL[k]).sum()))
        for key, Z in D.items():
            sm = Z[pre + "smk"][k + 1]; row["w_R_%s_%s" % key] = float(sm[n] / np.abs(sm).sum()); row["member_R_%s_%s" % key] = bool(Z[pre + "mem"][k + 1][n])
        row["carry_cell_bps_if_iv8"] = float(FNc[r, n]) * 4.0 / 8.0 * 1e4; row["carry_cell_bps_if_iv1"] = float(FNc[r, n]) * 4.0 * 1e4
        cells.append(row)
nz = [c for c in cells if any(abs(v) > 0 for kk, v in c.items() if kk.startswith("w_"))]
GPU1 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID1 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2")
RC = dict(label="POST-HOC descriptive; not a gate, not a reading", self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, inputs=INPUTS, cells=cells, n_cells=len(cells),
          n_cells_with_any_nonzero_weight=len(nz), max_abs_weight_any_book=max((abs(v) for c in cells for kk, v in c.items() if kk.startswith("w_")), default=0.0),
          gpu_before=GPU0, gpu_after=GPU1, pids_before=PID0, pids_after=PID1, env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(RC, open(R + "/receipts/RECEIPT_T5d_posthoc_fallback.json", "w"), indent=1); print(json.dumps(RC["cells"], indent=0)[:4000]); print("n_cells", len(cells), "nonzero", len(nz), "max", RC["max_abs_weight_any_book"]); print("DONE_t5d_posthoc_fallback")

import sys, time
import numpy as np
FAC = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/factory"
sys.path.insert(0, FAC)
import pipeline as P
import dsl
from run_campaign import parse_batch
from ledger import Ledger

BATCH = FAC + "/proposals/batch_001.txt"
t = time.time(); C = P.load_context(4, 1); t_load = time.time() - t
A = C["ctx"]["mom_24h"]
ops = {}
for nm, fn in [("ts_rank", lambda: dsl.ts_rank(A, 72)), ("decay_linear", lambda: dsl.decay_linear(A, 72)),
               ("xsec_z", lambda: dsl.xsec_z(A)), ("_xsec_ranks", lambda: P._xsec_ranks(A, C))]:
    tt = time.time(); fn(); ops[nm] = round(time.time() - tt, 2)
formulas = [f for _, _, f in parse_batch(BATCH)]
import os
os.path.exists("/tmp/tw_stagetime.jsonl") and os.remove("/tmp/tw_stagetime.jsonl")
lg = Ledger("/tmp/tw_stagetime.jsonl")
t = time.time(); surv = P.stage0(formulas, C, lg, base_seed=0, n_jobs=24); t_s0 = time.time() - t
t = time.time(); res = P.stage1(surv, C, lg, base_seed=0, null_r=200, n_jobs=24); t_s1 = time.time() - t
cands = [f for f, v, s in res if v == "CANDIDATE"]
print(f"SPLIT: LOAD={t_load:.1f}s STAGE0(n24)={t_s0:.1f}s STAGE1(n24)={t_s1:.1f}s "
      f"TOTAL={t_load + t_s0 + t_s1:.1f}s | {len(surv)}surv {len(cands)}cand", flush=True)
print(f"OPS(full panel 48168x140): {ops}", flush=True)

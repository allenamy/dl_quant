# -*- coding: utf-8 -*-
"""make_patch_cost.py — PREREG_dl_path_cost_dose_2026-09-08 (sha ce7a6be927a4c312).
基底 pod_f10_train_monthly_trainfrac.py (20b531ba0e65a899) -> pod_f10_train_monthly_costdose.py
唯一改动: L281 的 COST == 3.52 断言改为白名单; 缺省 3.52 逐字等价。锚点断言恰一次。"""
import hashlib, os, difflib
B="/workspace/review_scratch/trainfrac/pod_f10_train_monthly_trainfrac.py"
O="/workspace/review_scratch/costdose/pod_f10_train_monthly_costdose.py"
src=open(B,encoding="utf-8").read()
bs=hashlib.sha256(src.encode()).hexdigest(); assert bs.startswith("20b531ba0e65a899"), bs[:16]
A='assert ARM == "V2MAIN" and V2 == 1 and SEED == 42 and COST == 3.52 and LDD == 0.25 and AFIX == 0 and LDC == 0.0 and CTXA == 0 and REC == 0 \\'
Bn=('COST_WHITELIST = (3.52, 7.04, 14.08)   # PREREG_dl_path_cost_dose (ce7a6be927a4c312): training-time path penalty dose; 3.52 = measured turnover cost = verbatim default\n'
    'assert COST in COST_WHITELIST, f"COST whitelist {COST_WHITELIST}: {COST}"\n'
    'assert ARM == "V2MAIN" and V2 == 1 and SEED == 42 and LDD == 0.25 and AFIX == 0 and LDC == 0.0 and CTXA == 0 and REC == 0 \\')
n=src.count(A); assert n==1, f"anchor occurs {n} times"
out=src.replace(A,Bn)
os.makedirs(os.path.dirname(O),exist_ok=True); open(O,"w",encoding="utf-8").write(out)
d=list(difflib.unified_diff(src.splitlines(),out.splitlines(),"trainfrac","costdose",lineterm="",n=1))
open("/workspace/review_scratch/costdose/costdose_patch.diff","w",encoding="utf-8").write("\n".join(d)+"\n")
print(f"base {bs[:16]} -> out {hashlib.sha256(out.encode()).hexdigest()[:16]}  diff {len(d)} 行")
print("\n".join(d))

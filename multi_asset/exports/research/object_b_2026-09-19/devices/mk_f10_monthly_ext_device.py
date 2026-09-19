#!/usr/bin/env python3
"""PREREG AMENDMENT 5 A5.2: derive pod_f10_train_monthly_ext.py from the v4 monthly trainer /workspace/review_scratch/pod_f10_train_monthly_v4.py (2147a7dd…)
by ONE asserted text edit: ALL_MONTHS extended from 202501..202608 to 202301..202608 (so MONTHS may name 2023–2024 folds). Nothing else changes; the
trainer writes only under MWF_OUT. usage: python3 mk_f10_monthly_ext_device.py <out_dir>"""
import hashlib, io, json, os, sys, time
SRC = ("/workspace/review_scratch/pod_f10_train_monthly_v4.py", "2147a7dd128be180ac6c5b01cde6d066413ac0333700deb887cef542cc8d50bb")
s = io.open(SRC[0], encoding="utf-8").read(); assert hashlib.sha256(s.encode()).hexdigest() == SRC[1]
a = "ALL_MONTHS = [202501 + k for k in range(12)] + [202601 + k for k in range(8)]\n"
b = ("ALL_MONTHS = [202301 + k for k in range(12)] + [202401 + k for k in range(12)] + [202501 + k for k in range(12)] + [202601 + k for k in range(8)]"
     "   # OBJECT-B DERIVED (AMENDMENT 5 A5.2): 2023–2024 months added\n")
assert s.count(a) == 1; s = s.replace(a, b)
s = f"# OBJECT-B DEVICE generated {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} from {SRC[0]} sha256 {SRC[1]}; 1 asserted edit (ALL_MONTHS)\n" + s
out = os.path.join(sys.argv[1], "pod_f10_train_monthly_ext.py"); io.open(out, "w", encoding="utf-8").write(s)
print(json.dumps({"source": SRC[0], "source_sha256": SRC[1], "device": out, "device_sha256": hashlib.sha256(s.encode()).hexdigest()}))

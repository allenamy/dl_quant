p="/workspace/review_scratch/combo_recheck/w10_universe_recheck.py"; s=open(p).read()
old1='assert TRADE_TOPN in (0, 400), f"TRADE_TOPN 白名单外: {TRADE_TOPN}"\n'
new1=old1+'REF_SKIP = int(os.environ.get("REF_SKIP", "0")); assert REF_SKIP in (0, 1)   # combo_recheck 2026-09-04: 1 = skip pod_backup reference parity (port stubs are 144-byte placeholders); self-reported in _CFG\n'
assert s.count(old1)==1; s=s.replace(old1,new1)
old2='_CFG = {"KMOD_F10": KMOD_F10,'
new2='_CFG = {"REF_SKIP": REF_SKIP, "KMOD_F10": KMOD_F10,'
assert s.count(old2)==1; s=s.replace(old2,new2)
old3='    ref = np.load(f"{B}/{reff}")\n    if WRULE == "msharpe" and LOOK == 900 and LEGS == "111":\n'
new3='    ref = np.load(f"{B}/{reff}")\n    if REF_SKIP:   # combo_recheck: reference parity skipped on request (REF_SKIP=1)\n        print(f"NOTE {nm}: REF_SKIP=1, reference parity vs pod_backup skipped", flush=True); ref = None\n    elif WRULE == "msharpe" and LOOK == 900 and LEGS == "111":\n'
assert s.count(old3)==1; s=s.replace(old3,new3)
open(p,"w").write(s); print("patched")

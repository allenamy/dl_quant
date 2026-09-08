import numpy as np, sys, time, calendar, json, os
sys.path.insert(0,"/workspace"); from zload import zload
Z=zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz",allow_pickle=True)
CTS=Z["ts"].astype(np.int64); syms=np.array([str(s) for s in Z["symbols"]]); D=Z["data"]
hole=set(np.load("/workspace/review_scratch/hole77.npy",allow_pickle=True).tolist())
# daily finite counts, Aug 5 .. Aug 31 2026
print("== daily finite ch0 counts (288 = full day) for 6 example holed symbols ==")
days=[calendar.timegm((2026,8,d,0,0,0)) for d in range(5,32)]
ex=[s for s in ["BLZUSDT","CELRUSDT","CKBUSDT","BANDUSDT","BALUSDT","ALPACAUSDT"] if s in hole][:6]
print("%-14s "%"symbol"+" ".join("%02d"%d for d in range(5,32)))
for s in ex:
    j=int(np.where(syms==s)[0][0]); row=[]
    for k,d0 in enumerate(days):
        m=(CTS>=d0)&(CTS<d0+86400); row.append(int(np.isfinite(D[m][:,j,0]).sum()))
    print("%-14s "%s+" ".join(("%2d"%(v//12) if v<288 else "24") for v in row))
print("(cells are finite-bars/12, i.e. hours of data present; 24 = full day)")
# live universe overlap
UP="/Users/haosiyu/wide_shadow/syms450.txt"
live=set()
for p in ["/workspace/review_scratch/syms450.txt","/workspace/syms450.txt"]:
    if os.path.exists(p): live=set(open(p).read().split()); break
cm=None
for p in ["/workspace/review_scratch/health_check/masks/crypto_mask_note.json"]:
    if os.path.exists(p): cm=json.load(open(p))
print("\nholed symbols total: %d"%len(hole))
if cm and "crypto_symbols" in cm:
    cr=set(cm["crypto_symbols"]); print("  of which crypto (COIN/INDEX): %d ; non-crypto: %d"%(len(hole&cr),len(hole-cr)))
elif cm: print("  crypto_mask_note keys:",list(cm.keys())[:10])
if live: print("  of which in live syms450: %d"%len(hole&live))
else: print("  (syms450 not on pod; check from Mac)")
np.save("/workspace/review_scratch/hole_all.npy", np.array(sorted(hole)))

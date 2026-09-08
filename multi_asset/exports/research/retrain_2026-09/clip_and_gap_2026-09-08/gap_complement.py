import numpy as np, sys, time, calendar
sys.path.insert(0,"/workspace"); from zload import zload
Z=zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz",allow_pickle=True)
CTS=Z["ts"].astype(np.int64); syms=np.array([str(s) for s in Z["symbols"]]); D=Z["data"]
lo=calendar.timegm((2026,8,13,0,5,0)); hi=calendar.timegm((2026,8,24,4,0,0))
m=(CTS>=lo)&(CTS<=hi)
finw=np.isfinite(D[m][:,:,0]).sum(0)
pre=(CTS>=lo-7*86400)&(CTS<lo); post=(CTS>hi)&(CTS<=hi+5*86400)
npre=np.isfinite(D[pre][:,:,0]).sum(0); npost=np.isfinite(D[post][:,:,0]).sum(0)
alive=(npre>500)&(npost>500)
print("829 symbols: alive(before&after) %d | of alive: hole(0 bars in window) %d, full %d, partial %d"%(
  alive.sum(), int(((finw==0)&alive).sum()), int(((finw>=3000)&alive).sum()), int(((finw>0)&(finw<3000)&alive).sum())))
print("not alive: %d"%int((~alive).sum()))
# how many bars a healthy alive symbol has in the window
h=(finw>=3000)&alive
print("healthy symbols median bars in window: %d of %d"%(int(np.median(finw[h])), int(m.sum())))
np.save("/workspace/review_scratch/healthy_window.npy", syms[h])

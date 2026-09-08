import numpy as np, sys, time, calendar
sys.path.insert(0,"/workspace"); from zload import zload
Z=zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz",allow_pickle=True)
CTS=Z["ts"].astype(np.int64); syms=np.array([str(s) for s in Z["symbols"]]); D=Z["data"]
lo=calendar.timegm((2026,8,13,0,5,0)); hi=calendar.timegm((2026,8,24,4,0,0))
m=(CTS>=lo)&(CTS<=hi); print("window rows %d (%s .. %s)"%(m.sum(),time.strftime("%F %H:%M",time.gmtime(CTS[m][0])),time.strftime("%F %H:%M",time.gmtime(CTS[m][-1]))))
sub=D[m]  # rows x 829 x 7
fin_ch0=np.isfinite(sub[:,:,0]).sum(0)
fin_all=np.isfinite(sub).sum(axis=(0,2))
# a symbol is "listed & alive" if it has data just before and just after the window
pre=(CTS>=lo-7*86400)&(CTS<lo); post=(CTS>hi)&(CTS<=hi+5*86400)
alive=(np.isfinite(D[pre][:,:,0]).sum(0)>500)&(np.isfinite(D[post][:,:,0]).sum(0)>500)
hole=(fin_all==0)&alive
print("symbols with ZERO finite cells in ALL 7 channels across the window, yet alive before AND after: %d"%hole.sum())
print("list:", ", ".join(sorted(syms[hole].tolist())[:90]))
print("\nrows in window %d; those symbols mean finite ch0 in window = %.1f"%(m.sum(),fin_ch0[hole].mean() if hole.any() else -1))
# how many bars each should have
print("alive symbols total: %d ; of them holed: %d (%.1f%%)"%(alive.sum(),hole.sum(),100*hole.sum()/max(alive.sum(),1)))
np.save("/workspace/review_scratch/hole77.npy", syms[hole])

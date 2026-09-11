import os,numpy as np,datetime as dt
W=os.path.dirname(os.path.abspath(__file__))
Z=np.load(W+"/book_inputs.npz",allow_pickle=True);K=np.load(W+"/klines_grid.npz",allow_pickle=True)
TS=Z["TS"];names=[str(x) for x in Z["names"]];CMP=K["CMP"];UMP=K["UMP"];CMV=K["CMV"];UMV=K["UMV"]
for nm in ("ROSEUSD_PERP","APEUSD_PERP","ICXUSD_PERP","GALAUSD_PERP","VETUSD_PERP","BTCUSD_PERP","XTZUSD_PERP","ZILUSD_PERP","KNCUSD_PERP"):
    k=names.index(nm)
    for i in (100,2000,5000,8000):
        print(f"{nm:16s} {dt.datetime.utcfromtimestamp(TS[i])}  CM={CMP[i,k]:>12.6f} UM={UMP[i,k]:>12.6f} ratio={CMP[i,k]/UMP[i,k] if UMP[i,k] else float('nan'):>10.3f}  CMvol={CMV[i,k]:>12.3f} UMvol={UMV[i,k]:>14.1f}")
    print()

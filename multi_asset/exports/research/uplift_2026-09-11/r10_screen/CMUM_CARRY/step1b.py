"""CMUM_CARRY STEP1b: universe with real history over the pinned post-warm window + raw spread magnitude.
No network. No live touch. First-hand."""
import os,json,datetime as dt,numpy as np
ENV_WHITELIST={"LC_CTYPE","LANG","PATH","PWD","SHLVL","_","__CF_USER_TEXT_ENCODING","HOME","TMPDIR","CPATH","LIBRARY_PATH","MANPATH","SDKROOT"}
assert set(os.environ)<=ENV_WHITELIST, sorted(set(os.environ)-ENV_WHITELIST)
for _v in ("CAL","WRULE","LOOK","MEMBERS_TOPN","UMASK_SCOPE","UMASK_NPZ","COSTB_JSON","SLOW_NPY","LEGS","PHI","FTRIM","FEMAT_NPZ","OUT_TAG","TRADE_TOPN"): assert _v not in os.environ
W=os.path.dirname(os.path.abspath(__file__)); R={}
F=np.load(W+"/funding_raw.npz",allow_pickle=True)
A0=np.load(W+"/pin/A0_PWR230k_s42.npz",allow_pickle=True)
cols=[str(c) for c in A0["cols"]]; rec=A0["rec"]
ts_all=rec[:,cols.index("ts")].astype(np.int64)
POST=900; ts_pw=ts_all[POST:]; CAP=int(dt.datetime(2026,8,30,20,tzinfo=dt.timezone.utc).timestamp())
keep=ts_pw<=CAP; TS=ts_pw[keep]; A0g=(rec[POST:,cols.index("net_ex")]/rec[POST:,cols.index("gross_total")])[keep]*1e4
R["A0"]=dict(n=int(len(TS)),t0=str(dt.datetime.utcfromtimestamp(TS[0])),t1=str(dt.datetime.utcfromtimestamp(TS[-1])),
             mean_g_bps=float(A0g.mean()),sharpe_ann=float(A0g.mean()/A0g.std(ddof=1)*np.sqrt(2190)),
             turnover=float(rec[POST:,cols.index("turnover")][keep].mean()/rec[POST:,cols.index("gross_total")][keep].mean()))
print("A0 CHECK n=%d mean_g=%.4f SR=%.4f"%(R["A0"]["n"],R["A0"]["mean_g_bps"],R["A0"]["sharpe_ann"]))
assert np.all(np.diff(TS)==14400), "axis not strict 4h"
WSYM=json.load(open(W+"/pin/wsym.json"))
pairs=[l.split() for l in open(W+"/raw_listings/pairs_all.txt") if l.strip()]
rows=[]
for cmS,umS in pairs:
    C=F["CM_"+cmS] if "CM_"+cmS in F else None
    U=F["UM_"+umS] if "UM_"+umS in F else None
    if C is None or U is None: continue
    # events inside the pinned post-warm window
    cin=C[(C[:,0]/1000>=TS[0])&(C[:,0]/1000<=TS[-1]+14400)]
    uin=U[(U[:,0]/1000>=TS[0])&(U[:,0]/1000<=TS[-1]+14400)]
    # coverage in DAYS with >=1 CM settlement
    cdays=len(set((cin[:,0]//86400000).astype(int).tolist())) if len(cin) else 0
    udays=len(set((uin[:,0]//86400000).astype(int).tolist())) if len(uin) else 0
    rows.append(dict(cm=cmS,um=umS,in_book_universe=(umS in WSYM),
      cm_n=int(len(cin)),um_n=int(len(uin)),cm_days=cdays,um_days=udays,
      cm_last=str(dt.datetime.utcfromtimestamp(cin[-1,0]/1000)) if len(cin) else None,
      cm_first=str(dt.datetime.utcfromtimestamp(cin[0,0]/1000)) if len(cin) else None,
      cm_intervals=sorted(set(cin[:,1].tolist())) if len(cin) else [],
      um_intervals=sorted(set(uin[:,1].tolist())) if len(uin) else []))
R["pairs"]=rows
WINDAYS=(TS[-1]+14400-TS[0])/86400
CDAY_MAX=(min(TS[-1]+14400, int(dt.datetime(2026,7,1,tzinfo=dt.timezone.utc).timestamp()))-TS[0])/86400
print("window days %.1f ; CM-archive-covered days %.1f"%(WINDAYS,CDAY_MAX))
print(f"{'CM':16s}{'UM':12s}{'book':5s}{'cmN':>6s}{'umN':>6s}{'cmDay':>7s}{'/maxD':>7s}{'cm_last':>21s}")
alive=[]
for r in sorted(rows,key=lambda z:-z["cm_days"]):
    print(f"{r['cm']:16s}{r['um']:12s}{str(r['in_book_universe'])[:1]:5s}{r['cm_n']:6d}{r['um_n']:6d}{r['cm_days']:7d}{CDAY_MAX:7.0f}  {str(r['cm_last'])}")
    if r["cm_days"]>=0.90*CDAY_MAX and r["in_book_universe"]: alive.append(r["cm"])
print("\nNAMES with >=90%% of archive-covered days AND in book universe: %d"%len(alive))
print(alive)
R["universe_count"]=dict(cm_perp_listed_all_time=len(pairs),full_history_and_in_book=len(alive),names=alive,
    window_days=float(WINDAYS),cm_archive_days=float(CDAY_MAX))
json.dump(R,open(W+"/STEP1_universe.json","w"),indent=1,default=str)

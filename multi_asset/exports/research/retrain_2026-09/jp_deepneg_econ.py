"""深负空头 sleeve 经济学 @jpline: 回放(canonpred s42 d30 W)按归一化费率深度分箔: 价格alpha vs carry(4h), 分年; 找 carry>alpha 的盈亏平衡深度。"""
import numpy as np, time, collections
PD="/mnt/storage/private/work_hsy/probe_artifacts"; B="/mnt/storage/private/work_hsy/pod_backup_2026-08-21"
PW=np.load(f"{B}/wide_panel_4h_hist_v2.npz",allow_pickle=True); pts=PW["ts"].astype(np.int64); prow={int(t):j for j,t in enumerate(pts)}
FN=PW["f_fund_now"]; IV=PW["f_fund_iv"]
MT=np.load(f"{B}/wide_fea_hist_meta.npz",allow_pickle=True); mts=MT["E_ts"].astype(np.int64); y4=MT["y4"]; mrow={int(t):i for i,t in enumerate(mts)}
z=np.load(f"{PD}/w10_canonpred_s42.npz",allow_pickle=True); cols=[str(c) for c in z["cols"]]; rec=z["d30_n2_c42_rec"]; W=z["d30_n2_c42_W"]
ts=rec[:,cols.index("ts")].astype(np.int64); yrs=np.array([time.gmtime(int(t)).tm_year for t in ts])
edges=[(-1e9,-0.0100),(-0.0100,-0.0060),(-0.0060,-0.0030),(-0.0030,-0.0010),(-0.0010,0.0)]
lab=["<-100bp","-100..-60","-60..-30","-30..-10","-10..0"]
agg=collections.defaultdict(lambda:collections.defaultdict(lambda:[0.0,0.0,0.0,0]))  # yr->bin->[price_bps_sum(of gross), carry_bps_sum, share_sum, n_anchor]
for p,t in enumerate(ts):
    y=yrs[p]
    if y<2023: continue
    j=prow.get(int(t)); i=mrow.get(int(t))
    if j is None or i is None: continue
    w=W[p]; g=np.abs(w).sum()
    if g<1e-9: continue
    iv=IV[j]; iv=np.where(np.isfinite(iv)&(iv>0),iv,8.0); fn=np.nan_to_num(FN[j])*(8.0/iv)
    r=np.nan_to_num(y4[i])
    sh=w<-1e-9
    for k,(lo,hi) in enumerate(edges):
        m=sh&(fn>lo)&(fn<=hi)
        if not m.any(): 
            agg[y][lab[k]][3]+=1; continue
        price=(w[m]*r[m]).sum()*1e4/g            # 空头: w<0, 价格跌 r<0 ⇒ 正
        carry=-(w[m]*fn[m]*0.5).sum()*1e4/g       # 空付负费率: w<0,fn<0 ⇒ w*fn>0 ⇒ carry 成本 = -w*fn*(4h/8h)
        a=agg[y][lab[k]]; a[0]+=price; a[1]+=carry; a[2]+=np.abs(w[m]).sum()/g; a[3]+=1
print("== 深负空头分箔(回放 canon s42, bps/锚 of gross; 4h carry=rate×0.5): 年 | 箔 | 价格alpha | carry | 净 | 名义占比")
for y in sorted(agg):
    for k in lab:
        pr,ca,sh,n=agg[y][k]
        if n==0: continue
        print(f"  {y} {k:10s} 价格 {pr/n:+.3f} carry {ca/n:+.3f} 净 {(pr+ca)/n:+.3f} | 占比 {sh/n*100:4.1f}%")
print("DEEPNEG_DONE")

"""1h/2h 挤压延续判官(用户问: 4h 是否非最佳; 小时级能否预测延续/反转)。
数据: dlnative_5m_wide829(ret5, 5m qv) 2022-2026 → 1h 条。
条件(挤压态): 名字过去 24h 残差(对等权市场)涨幅 ≥ +12%(空头正在被挤)。
特征(全部 ≤t, 因果): r_1h, r_2h, r_4h, 加速度 a = r_1h − r_prev1h, 4h 内位置 pos=(P−min4h)/(max4h−min4h), 1h 成交量激增 qv_1h/qv_24h均值, 24h 涨幅本身。
目标: 下 1h / 2h / 4h 残差收益方向(空头视角: 负=延续亏, 正=反转赚)。
判据(冻结): 小时级特征对下一段方向的 OOS AUC ≥0.56 且逐年提升同向 ≥4/5; 否则"4h 锚级已够, 小时级无增量"。
附: 对最终会在 4h 锚确认触发(−25%×2)的名字, 量"首次越线→锚确认"之间小时路径: 延续还是回吐(=1h 节奏止损的价值)。
"""
import numpy as np, json, datetime
d=np.load('/mnt/storage/private/work_hsy/w3lane/kcurve/data/dlnative_5m_wide829_f16.npz', allow_pickle=True)
ts=d['ts']; CH=[str(x) for x in d['ch']]
r5=np.asarray(d['data'][:,:,CH.index('ret5')],np.float32); qv5=np.asarray(d['data'][:,:,CH.index('log_qv')],np.float32)
n5,N=r5.shape
H=12; nh=n5//H
R1=np.nansum(np.where(np.isfinite(r5[:nh*H]),r5[:nh*H],0).reshape(nh,H,N),1)   # 1h 对数收益近似
cov=np.isfinite(r5[:nh*H]).reshape(nh,H,N).mean(1); R1=np.where(cov>0.8,R1,np.nan)
QV1=np.nanmean(np.where(np.isfinite(qv5[:nh*H]),qv5[:nh*H],np.nan).reshape(nh,H,N),1)
mkt=np.nanmean(R1,1,keepdims=True); RR=R1-mkt   # 残差
T1=ts[:nh*H:H]; T1=T1//1000 if T1[0]>2e10 else T1
YR=np.array([datetime.datetime.utcfromtimestamp(int(t)).year for t in T1])
hr=np.array([datetime.datetime.utcfromtimestamp(int(t)).hour for t in T1])
print('1h 条', nh, '名', N, flush=True)
cs=np.nancumsum(np.nan_to_num(RR),0)
def win(k): return cs[k:]-cs[:-k] if k>0 else None
r24=np.full_like(RR,np.nan); r24[24:]=cs[24:]-cs[:-24]
r4=np.full_like(RR,np.nan); r4[4:]=cs[4:]-cs[:-4]
r2=np.full_like(RR,np.nan); r2[2:]=cs[2:]-cs[:-2]
r1=RR; rp1=np.full_like(RR,np.nan); rp1[1:]=RR[:-1]
f1=np.full_like(RR,np.nan); f1[:-1]=RR[1:]
f2=np.full_like(RR,np.nan); f2[:-2]=cs[2:]-cs[:-2]
f4=np.full_like(RR,np.nan); f4[:-4]=cs[4:]-cs[:-4]
qv24=np.full_like(QV1,np.nan)
for i in range(24,nh): qv24[i]=np.nanmean(QV1[i-24:i],0)
qsurge=QV1-qv24
# 挤压态样本
rows=[]
sq=(r24>=0.12)&np.isfinite(f4)&np.isfinite(r1)&np.isfinite(rp1)&np.isfinite(qsurge)
ii,jj=np.where(sq)
print('挤压态样本', len(ii), flush=True)
sel=np.random.RandomState(0).choice(len(ii), size=min(len(ii),400000), replace=False)
ii,jj=ii[sel],jj[sel]
X=np.stack([r1[ii,jj], r2[ii,jj], r4[ii,jj], r1[ii,jj]-rp1[ii,jj], qsurge[ii,jj], r24[ii,jj], np.sin(hr[ii]/24*2*np.pi), np.cos(hr[ii]/24*2*np.pi)],1)
Y1=(f1[ii,jj]>0).astype(int); Y2=(f2[ii,jj]>0).astype(int); Y4=(f4[ii,jj]>0).astype(int)
yrs=YR[ii]
from sklearn.metrics import roc_auc_score
import lightgbm as lgb
res={}
for tag,Y in (('next1h',Y1),('next2h',Y2),('next4h',Y4)):
    by={}
    for y in (2023,2024,2025,2026):
        tr=(yrs<y)&np.isfinite(Y.astype(float)); te=(yrs==y)
        if te.sum()<500 or tr.sum()<5000: continue
        m=lgb.LGBMClassifier(n_estimators=200,learning_rate=0.05,num_leaves=15,min_child_samples=200,verbose=-1).fit(X[tr],Y[tr])
        p=m.predict_proba(X[te])[:,1]
        auc=roc_auc_score(Y[te],p)
        # 基线: 仅 r1(1h 动量/反转)符号
        base=roc_auc_score(Y[te], -X[te,0])
        by[int(y)]={'n':int(te.sum()),'auc_model':round(float(auc),3),'auc_rev1h':round(float(base),3),'base_rate_up':round(float(Y[te].mean()),3)}
    res[tag]=by
    print(tag, json.dumps(by), flush=True)
# 挤压态下 空头持有下一段的均值(无条件): 延续还是反转?
res['uncond_short_hold']={}
for tag,f in (('1h',f1),('2h',f2),('4h',f4)):
    by={}
    for y in (2022,2023,2024,2025,2026):
        m=(yrs==y)
        v=-f[ii[m],jj[m]]
        if len(v)>500: by[int(y)]=round(float(np.nanmean(v))*1e4,1)
    res['uncond_short_hold'][tag]=by
print('挤压态空头持有均值 bps(负=延续):', json.dumps(res['uncond_short_hold']), flush=True)
json.dump(res,open('/mnt/storage/private/work_hsy/w3lane/kcurve/hourly_squeeze_judge.json','w'))
print('DONE')

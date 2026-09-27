#!/usr/bin/env python3
"""Read-only pooled population closure. Predicate frozen in 120a6935d."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import collections,hashlib,json,math,subprocess,time,sys
from pathlib import Path
import numpy as np

HEAD='3b4a2815ad4b8d45ee09ed8b69222e04b5885301'
REPO='/Users/haosiyu/Desktop/quant_research'
ROOT=Path('/Users/haosiyu/wide_shadow')
R='multi_asset/exports/research/lossdecomp_2026-09-25/receipts/side_split_0924_0927_snap1790467200/'
def blob(p):return subprocess.check_output(['git','show',HEAD+':'+p],cwd=REPO)
def sha(b):return hashlib.sha256(b).hexdigest()
inputs={}
def read(p):
    b=Path(p).read_bytes();inputs[str(p)]={'sha256':sha(b),'bytes':len(b)};return json.loads(b)
nb=blob(R+'NAMES.jsonl');assert sha(nb)=='4e84c8ddab83a177ca9d90e67f7935422daaccde42608c115b2ca2eaae833382'
nm=[json.loads(l) for l in nb.splitlines() if l.strip()];ssb=blob(R+'SIDE_SPLIT.json');side=json.loads(ssb)
known={r['A']:r for r in side['intervals']};source=blob('multi_asset/exports/research/nc_2026-09-23/devices/nc_contract.py');nc={};exec(compile(source,'frozen_nc_contract.py','exec'),nc)
symbols=read(ROOT/'shadow_bundle/config.json')['symbols_panel']
fund=[]
for day in ('20260924','20260925','20260926'):
    p=Path('/Users/haosiyu/dl_quant_live/state/live/pilot_log')/day/'funding.jsonl';b=p.read_bytes();inputs[str(p)]={'sha256':sha(b),'bytes':len(b)}
    fund.extend(json.loads(l) for l in b.splitlines() if l.strip())
keys=[(f['settlement_ts'],f['symbol']) for f in fund];assert len(keys)==len(set(keys)),'funding duplicate key, no silent dedup'
groups=('lag','not_lag','other','unknown');tot={g:collections.defaultdict(float) for g in groups};windows=[];pairs=[];allshort=collections.defaultdict(float)
fmt=lambda a:time.strftime('%m-%dT%HZ',time.gmtime(a))
for x in nm:
    if not x['priced']:continue
    A=x['A'];s=known[A];auxp=ROOT/f'state/snap/{A}/aux.json';tp=ROOT/f'state/target_live/{A}.json'
    aux=read(auxp);rec=aux['prev_rec'];assert rec['anchor_ts']==A,'snapshot time identity'
    tar=read(tp);assert tar['anchor_ts']==A and tar['beta_overlay']['data_cutoff_ts']<=A,'beta causal'
    betas=tar['beta_overlay']['betas'];rz=rec['legz'];m=rec['members'];byname={symbols[j]:{k:rz[k][i] for k in ('fund','king','rev24')} for i,j in enumerate(m)}
    bg={g:collections.defaultdict(float) for g in groups};classes={};matching={};rb=s['r_btc']
    for name,(nom,ret,_) in x['names'].items():
        if nom is None or nom>=0:continue
        if ret is None:allshort['unpriced_abs_notional']+=abs(nom);continue
        g='unknown';d=None;be=betas.get(name)
        if name in byname and name in aux['ema'] and name in aux['ledger_tail']:
            state=aux['ema'][name];last=aux['ledger_tail'][name][-1]
            assert state.get('last_ts') is None or state['last_ts']<=A
            fe,rate,iv,rn=nc['funding_asof'](state,last,A)
            q=byname[name]
            if all(v is not None and math.isfinite(v) for v in (fe,rn,q['fund'],q['king'],q['rev24'])):
                g='other';allshort['known_state_abs_notional']+=abs(nom);allshort['known_state_name_intervals']+=1
                if rn<0:
                    allshort['current_negative_rate_abs_notional']+=abs(nom);allshort['current_negative_rate_name_intervals']+=1
                if rn<0 and fe<0 and q['fund']<=-.25:g='lag' if rn>=fe/2 else 'not_lag'
                d={'symbol':name,'notional':abs(nom),'return':ret,'beta':be,'fz':q['fund'],'kz':q['king'],'rz':q['rev24'],'ema':fe,'rn8':rn}
        classes[name]=g
        z=bg[g];z['name_intervals']+=1;z['abs_notional']+=abs(nom);z['price_pnl']+=nom*ret
        if be is None:z['missing_beta_abs_notional']+=abs(nom);z['missing_beta_price_pnl']+=nom*ret
        else:z['beta_pnl']+=nom*be*rb;z['residual_pnl']+=nom*(ret-be*rb)
        if d is not None and be is not None and g in ('lag','not_lag'):matching[name]=(g,d)
    pr=sum(v['price_pnl'] for v in bg.values());assert abs(pr-s['price_short'])<1e-6,('price closure',A,pr,s['price_short'])
    bp=sum(v['beta_pnl'] for v in bg.values());assert abs(bp-s['beta_short'])<1e-6,('beta closure',A,bp,s['beta_short'])
    cands={n:d for n,(g,d) in matching.items() if g=='not_lag'}
    for name,(g,d) in sorted(matching.items()):
        if g!='lag':continue
        options=[]
        for cn,c in cands.items():
            df=d['fz']-c['fz'];dr=d['rz']-c['rz'];db=d['beta']-c['beta'];dk=d['kz']-c['kz']
            if abs(df)<=.1 and abs(dr)<=.2 and abs(db)<=.25:options.append(((df/.1)**2+(dr/.2)**2+(db/.25)**2+(dk/.2)**2,cn,df,dr,db,dk))
        if not options:continue
        dist,cn,df,dr,db,dk=min(options);c=cands.pop(cn)
        diff=-1e4*((d['return']-d['beta']*rb)-(c['return']-c['beta']*rb))
        pairs.append({'A':A,'lag':name,'control':cn,'notional_lag':d['notional'],'residual_short_diff_bps':diff,'dfz':df,'drev24':dr,'dbeta':db,'dking':dk,'distance':dist})
    for f in fund:
        if not (x['tA']<f['settlement_ts']<=x['tB']) or f['position_notional_at_settlement']>=0:continue
        cash=float(f['funding_paid']);nom=float(f['position_notional_at_settlement']);rate=float(f['funding_rate'])
        assert np.sign(cash)==-np.sign(nom)*np.sign(rate) or abs(cash)<1e-12,'funding cash sign convention'
        g=classes.get(f['symbol'],'unknown');z=bg[g];z['funding_cashflow']+=cash;z['funding_settlements']+=1
        if cash<0:z['funding_paid_abs']-=cash;z['pay_settlements']+=1
        elif cash>0:z['funding_received']+=cash;z['receive_settlements']+=1
    cash=sum(v['funding_cashflow'] for v in bg.values());assert abs(cash-s['funding_short'])<1e-6,('cash closure',A,cash,s['funding_short'])
    for g,v in bg.items():
        for k,value in v.items():tot[g][k]+=value
    allshort['abs_notional']+=sum(v['abs_notional'] for v in bg.values());allshort['name_intervals']+=sum(v['name_intervals'] for v in bg.values())
    windows.append({'A':A,'start':x['tA'],'end':x['tB'],'groups':bg,'price_closure_error':pr-s['price_short'],'funding_closure_error':cash-s['funding_short']})
nwindows=len({p['A'] for p in pairs});notional=sum(p['notional_lag'] for p in pairs);enough=len(pairs)>=20 and nwindows>=6
matched={'status':'DESCRIPTIVE_ONLY' if enough else 'MATCHED_UNAVAILABLE','pairs':len(pairs),'intervals':nwindows,'lag_abs_notional_matched':notional,'lag_notional_match_coverage':notional/tot['lag']['abs_notional'] if tot['lag']['abs_notional'] else None}
if enough:matched['weighted_residual_short_diff_bps']=sum(p['notional_lag']*p['residual_short_diff_bps'] for p in pairs)/notional
if pairs:matched['weighted_abs_covariate_difference']={k:sum(p['notional_lag']*abs(p[k]) for p in pairs)/notional for k in ('dfz','drev24','dbeta','dking')}
out={'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'status':'DESCRIPTIVE_POPULATION_CLOSURE','frozen_head':HEAD,'source_Names_sha256':sha(nb),'source_side_split_sha256':sha(ssb),'nc_contract_sha256':sha(source),'inputs':inputs,'n_intervals':len(windows),'all_short':allshort,'groups':tot,'matched':matched,'all_price_and_cash_closures_pass':True,'intervals':windows,'pairs':pairs,'limitations':['Recent hypothesis-generation window, not OOS','Current RN8<0 and observed paying settlements are separate populations','Funding cash ledger timestamps use settlement position; price uses static readback holdings','Matching conditions on realized lag status and preserves neither randomization nor causal identification','Residual removes recorded BTC beta only; other common factors may remain']}
print(json.dumps(out,indent=2,allow_nan=False))

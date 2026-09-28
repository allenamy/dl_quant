"""Explicit fixed-notional clock proxy. No entrypoint, optimizer, or training."""
import ast,hashlib,math,pathlib

def original_definitions(np,torch,sources):
    """Extract only audited definitions; never execute archived training entrypoints."""
    from scipy.stats import rankdata
    def load(key,names,ns):
        p,h=sources[key];raw=pathlib.Path(p).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=h:raise ValueError('source drift:'+key)
        nodes=[x for x in ast.parse(raw).body if isinstance(x,(ast.FunctionDef,ast.ClassDef)) and x.name in names]
        if {x.name for x in nodes}!=set(names):raise ValueError('definition missing:'+key)
        exec(compile(ast.Module(body=nodes,type_ignores=[]),p,'exec'),ns)
        return ns
    def kernels():return load('stage',('chain','exec_reshape'),{'np':np})
    step=load('combo',('step',),{'np':np,'rankdata':rankdata,'source_kernels':kernels})['step']
    evolve=load('continuous',('evolve',),{'np':np,'step':step})['evolve']
    Net=load('net',('Net',),{'torch':torch,'nn':torch.nn})['Net']
    return evolve,Net

def fingerprint(T,*xs):
    h=hashlib.sha256()
    for x in xs:
        if isinstance(x,T.Tensor):h.update(str(tuple(x.shape)).encode());h.update(x.detach().cpu().contiguous().numpy().tobytes())
        else:h.update(str(x).encode())
    return h.hexdigest()

def step(T,king,score,fund,seats,rn8,m,qv,legal,P,kh,fh,policy,hard):
    n=len(m);nw=len(kh);trace=[]
    if not bool(T.isfinite(king).all()):return kh,fh,None,False,'King scores incomplete','king_incomplete'
    ok=T.isfinite(score);v=score[ok]
    if hard:
        rank=(v[:,None]>v[None,:]).sum(1).to(v.dtype)+1+((v[:,None]==v[None,:]).sum(1).to(v.dtype)-1)/2
    else:
        if len(v)<2:raise ValueError('soft rank needs at least two finite scores')
        v=(v-v.mean())/(v.std()+1e-8) # Same sample-std normalization as original training.
        # +.5 gives the production one-based average rank, including the self .5.
        rank=T.sigmoid((v[:,None]-v[None,:])/.3).sum(1)+.5
    zf=T.zeros_like(score).masked_scatter(ok,rank/max(len(v)-1,1)-.5)
    sw=seats[0]+seats[2];w0=seats[0]/sw if float(sw)>1e-12 else seats.new_tensor(.5);w2=1-w0
    sel=T.isfinite(qv)&(qv>=P['qv4h_min']);keep=T.zeros(nw,dtype=T.bool,device=m.device).scatter(0,m,sel)&legal
    def chain(z,h):
        blocked=(z<0)&T.isfinite(rn8)&(rn8<=-.001);z=T.where(blocked,0.,z)
        v=T.where(sel,z,0.);v=T.where(sel,v-(v[sel].mean() if bool(sel.any()) else 0.),v);g=v.abs().sum()
        trace.append(fingerprint(T,blocked,sel))
        if float(g)<1e-9:return None
        v=v/g;cap=P['cap_mult']/max(int(sel.sum()),1);trace.append(fingerprint(T,v.abs()>=cap,v>=0))
        v=T.clamp(v,-cap,cap);g2=v.abs().sum()
        if float(g2)>1e-9:v=v/g2
        target=T.zeros(nw,dtype=h.dtype,device=h.device).scatter(0,m,v);sm=h+P['alpha']*(target-h)
        band=(sm-h).abs()<P['band'];sm=T.where(band,h,sm);leave=(~keep)&(sm.abs()>1e-12)
        trace.append(fingerprint(T,band,leave));return T.where(leave,0.,sm)
    kc=chain(w0*T.nan_to_num(king)+w2*T.nan_to_num(fund),kh)
    fc=chain(w0*zf+w2*T.nan_to_num(fund),fh)
    if kc is None or fc is None:return kh,fh,None,False,'degenerate signal',fingerprint(T,*trace)
    raw=.55*kc+.45*fc;gross=float(raw.abs().sum());names=int((raw.abs()>1e-9).sum())
    reasons=[]
    if int(ok.sum())<(380 if policy=='literal' else math.ceil(.95*n)):reasons.append('F10 coverage')
    if not .4<=gross<=1.2:reasons.append('gross')
    if names<(150 if policy=='literal' else math.ceil(.375*n)):reasons.append('names')
    trace.append(fingerprint(T,raw.abs()>1e-9,not reasons))
    return kc,fc,raw,not reasons,','.join(reasons) if reasons else 'publish',fingerprint(T,*trace)

def evolve(T,scores,data,policy='scaled_diagnostic',hard=False):
    nw=len(data['symbols']);kh=scores.new_zeros(nw,dtype=T.float64);fh=kh.clone();out={k:[] for k in ('kc','fc','raw','weights','trade_mask','reason','gates')}
    def tt(x):return T.as_tensor(x,device=scores.device)
    for i in range(120):
        if not bool(data['legs']['ready'][i]):raw=None;accepted=False;reason='unready causal legs';gate='unready'
        else:
            m=tt(data['members'][i]).long();s=scores[data['off'][i]:data['off'][i+1]].double()
            args=[tt(data['legs'][k][i,data['members'][i]]).double() for k in ('KZ','ZFD','RN8','QV')]
            kc,fc,raw,accepted,reason,gate=step(T,args[0],s,args[1],tt(data['legs']['WL'][i]).double(),args[2],m,args[3],tt(data['legal'][i]).bool(),data['params'],kh,fh,policy,hard)
            # Original evolve commits own producer states even on publication HOLD.
            gate=fingerprint(T,gate,kc.abs()>1e-9,fc.abs()>1e-9)
            kh=T.where(kc.abs()>1e-9,kc,0.);fh=T.where(fc.abs()>1e-9,fc,0.)
        out['kc'].append(kh);out['fc'].append(fh);out['raw'].append(kh*0 if raw is None else raw)
        out['weights'].append(T.where(raw.abs()>1e-9,raw,0.) if accepted else kh*0)
        out['trade_mask'].append(accepted);out['reason'].append(reason);out['gates'].append(gate)
    for k in ('kc','fc','raw','weights'):out[k]=T.stack(out[k])
    return out

def atoms_from_calibration(cal):
    p=cal['params'];f=p['first_leg'];r1=(1-f['p_rej'])*(f['p_full']+f['p_part']*f['fbar_part']);r2=(1-r1)*p['completion']['pi_fill']
    fees=p['fee_rate']['USDT_era'];mix=p['completion']['maker_share'];later_fee=mix*fees['maker']+(1-mix)*fees['taker'];rows=[]
    for kind,fraction,fee in [('first_leg',r1,fees['maker']),('later_leg',r2,later_fee)]:
        for tau,wt in zip(p['timing_offsets_after_decision_s'][kind],p['timing_offsets_after_decision_s']['weights']):
            rows.append((1440+tau,fraction*wt,p['slippage_vs_executor_mid'][kind],fee))
    if len(rows)!=10 or not 0<sum(x[1] for x in rows)<1 or max(x[0] for x in rows)>=14400:raise ValueError('atom contract')
    return sorted(rows)

def coefficient_pack(np,data,cal):
    """All event IDs retained. Invalid prices only allowed on structurally unreachable names."""
    a=data['anchors'];price=data['price'];ts=data['price_ts'];ev=data['events'];nw=len(data['symbols']);atoms=atoms_from_calibration(cal)
    def px(t):
        bar=math.floor(float(t)/300)*300;i=int(np.searchsorted(ts,bar))
        if i==len(ts) or ts[i]!=bar:raise ValueError('missing exact price bar')
        return price[i]
    old_support=np.zeros(nw,bool);cs={k:np.zeros((120,nw),np.float64) for k in ('price_old','price_delta','slip_abs','fee_abs','fee_signed','carry_old','carry_delta','p_dec','support')};events=[]
    keys=set();event_count=0
    for i,A in enumerate(a):
        m=data['members'][i];sel=np.isfinite(data['legs']['QV'][i,m])&(data['legs']['QV'][i,m]>=data['params']['qv4h_min'])
        target_support=np.zeros(nw,bool);target_support[m[sel]]=True;target_support&=data['legal'][i];support=old_support|target_support
        pa,pb,pd=px(A),px(A+14400),px(A+1440)
        for name,p,needed in [('start',pa,old_support),('end',pb,support),('decision',pd,support)]:
            if np.any(needed&(~np.isfinite(p)|(p<=0))):raise ValueError(f'UNAVAILABLE possible holding price {i}/{name}')
        # No raw NaN filling: these coefficients are zero only outside proved support.
        pa=np.where(old_support,pa,0.);pb=np.where(support,pb,0.);pd=np.where(support,pd,1.)
        total=sum(x[1] for x in atoms);slip=sum(x[1]*x[2] for x in atoms)
        cs['price_old'][i]=np.where(old_support,pb-pa,0.);cs['price_delta'][i]=np.where(support,total*(pb-pd),0.)
        cs['slip_abs'][i]=np.where(support,pd*slip,0.)
        cs['fee_abs'][i]=np.where(support,pd*sum(x[1]*x[3] for x in atoms),0.)
        cs['fee_signed'][i]=np.where(support,pd*sum(x[1]*x[2]*x[3] for x in atoms),0.)
        cs['p_dec'][i]=pd;cs['support'][i]=support
        rows=np.flatnonzero((ev['ft_ms']>int(A)*1000)&(ev['ft_ms']<=int(A+14400)*1000))
        for j in rows:
            ms=int(ev['ft_ms'][j]);s=int(ev['symbol_index'][j]);rate=float(ev['rate'][j]);key=(ms,s)
            if key in keys:raise ValueError('duplicate exact-ms cash event')
            keys.add(key);event_count+=1;t=ms/1000.;p=float(px(t)[s]);f=sum(fr for off,fr,_,_ in atoms if float(A)+off<t)
            possible=bool(old_support[s] or (target_support[s] and f>0))
            valid=math.isfinite(p) and p>0
            if possible and not valid:raise ValueError('UNAVAILABLE reachable funding price')
            if valid:cs['carry_old'][i,s]-=p*rate;cs['carry_delta'][i,s]-=p*rate*f
            events.append({'row':int(j),'window':i,'ft_ms':ms,'symbol_index':s,'price':p if valid else None,'rate':rate,'fill_fraction_before':f,'possible_inventory':possible,'structural_zero_unknown_price':not valid and not possible})
        old_support=support # HOLD can retain any past inventory; never clear on legal exit.
    if event_count!=9104 or event_count!=len(ev['ft_ms']):raise ValueError('all events must be assigned exactly once')
    return cs,atoms,events

def cash_path(T,book,coeff,atoms):
    w=book['weights'];q=w.new_zeros(w.shape[1]).detach();p=[];fees=[];carry=[];signs=[];total=sum(x[1] for x in atoms)
    for i in range(120):
        # HOLD means retain quantities, not re-mark yesterday's weights to target.
        reshape_gate='hold'
        if book['trade_mask'][i]:
            target=w[i];nz=target.abs()>1e-12
            reshape_gate=fingerprint(T,nz)
            if bool(nz.any()):
                reshaped=T.where(nz,target-target[nz].mean(),target);g=reshaped.abs().sum()
                if float(g)>1e-9:reshaped=reshaped*(target.abs().sum()/g)
                target=reshaped
            desired=200000.*target/coeff['p_dec'][i];delta=desired-q
        else:delta=q*0
        signs.append(fingerprint(T,reshape_gate,delta>=0))
        p.append((q*coeff['price_old'][i]+delta*coeff['price_delta'][i]-delta.abs()*coeff['slip_abs'][i]).sum())
        fees.append((delta.abs()*coeff['fee_abs'][i]+delta*coeff['fee_signed'][i]).sum())
        carry.append((q*coeff['carry_old'][i]+delta*coeff['carry_delta'][i]).sum())
        q=q+total*delta # Keep shared-theta history, including every burn-in anchor.
    return {'price':T.stack(p)*.1,'fee':T.stack(fees)*.1,'carry':T.stack(carry)*.1,'terminal_q':q,'fill_sign_gates':signs}

def coefficient_control(np,data,coeff,atoms,rows):
    """Independent event-by-event fixed-quantity audit, including zero initial q."""
    nw=len(data['symbols']);q=np.zeros(nw);worst=np.zeros(3);cashref=[];cashgot=[]
    def px(t):return data['price'][int(np.searchsorted(data['price_ts'],math.floor(float(t)/300)*300))]
    for i,A in enumerate(data['anchors']):
        support=coeff['support'][i].astype(bool)
        # Fixed deterministic test action, never selected from score/return results.
        target=np.where(support,np.sin(np.arange(nw)+i)*1000./coeff['p_dec'][i],0.)
        delta=target-q;start=q.copy();events=[]
        for off,frac,slip,fee in atoms:events.append((float(A)+off,1,(frac,slip,fee)))
        for e in rows:
            if e['window']==i:events.append((e['ft_ms']/1000.,0,e))
        fee_cash=fund_cash=trade_cash=0.
        for t,priority,payload in sorted(events,key=lambda z:(z[0],z[1])):
            if priority==0:
                e=payload;s=e['symbol_index']
                if e['price'] is None:
                    if q[s]!=0:raise ValueError('unpriced control quantity')
                else:fund_cash-=q[s]*e['price']*e['rate']
            else:
                frac,slip,fee=payload;dq=delta*frac;p=coeff['p_dec'][i]*(1+np.sign(dq)*slip)
                trade_cash+=float((dq*p).sum());fee_cash+=float((np.abs(dq)*p*fee).sum());q=q+dq
        pa,pb=px(A),px(A+14400)
        before=float((start[start!=0]*pa[start!=0]).sum());after=float((q[q!=0]*pb[q!=0]).sum())
        direct=np.array([after-before-trade_cash,fee_cash,fund_cash])
        calculated=np.array([(start*coeff['price_old'][i]+delta*coeff['price_delta'][i]-np.abs(delta)*coeff['slip_abs'][i]).sum(),(np.abs(delta)*coeff['fee_abs'][i]+delta*coeff['fee_signed'][i]).sum(),(start*coeff['carry_old'][i]+delta*coeff['carry_delta'][i]).sum()])
        worst=np.maximum(worst,np.abs(direct-calculated));cashref.append(fund_cash);cashgot.append(float(calculated[2]))
    def verify(got):
        if np.max(np.abs(np.asarray(got)-cashref))>1e-8:raise ValueError('cash mismatch')
    verify(cashgot);bad=cashgot.copy();bad[0]+=.01
    try:verify(bad)
    except ValueError:red=True
    else:raise ValueError('one cent mutation not rejected')
    if max(worst)>1e-8:raise ValueError('coefficient event-path disagreement')
    return {'status':'FIXED_SYNTHETIC_QUANTITY_EVENT_COEFFICIENT_PASS','max_price_fee_carry_error_usd':worst.tolist(),'one_cent_same_verifier_rejected':red,'all_events':len(rows),'pre_current_fill_events':sum(e['fill_fraction_before']==0 for e in rows),'zero_initial_inventory':True,'not_actual_network_or_canonical_fills':True}

def objectives(T,parts):
    p,f,c=[parts[k][24:] for k in ('price','fee','carry')];out={'price':p.mean(),'fee':f.mean(),'carry':c.mean()};tails={}
    for a,rate in [('A0',0),('A1',1)]:
        u=p-f+(c if rate else 0);v,idx=T.topk(-u,math.ceil(.05*len(u)))
        out[a+'_mean']=-u.mean();out[a+'_ES']=.25*v.mean();out[a]=out[a+'_mean']+out[a+'_ES'];tails[a]=idx.detach().cpu().tolist()
    return out,tails

#!/usr/bin/env python3
"""PROOF that shadow_log.jsonl's gross_bps/net_bps/carry_bps/cost_bps describe the KING book,
not the deployed COMBO book.  READ-ONLY.
 - shadow_log.jsonl is written only by shadow_loop_v3.py (append_log, L94/L550); grep FTRIM|rn8 in
   that file returns 0 hits; its z (L472) = w3[0]*king + w3[1]*rev24 + w3[2]*fund -- rev24 INCLUDED.
 - combo_stage.py masks rev24 (w3m), applies FTRIM, blends 0.55 king-chain + 0.45 F10-chain,
   and OVERWRITES state/target_live/<A>.json.
 - so signal.gross_pos must equal target_live_king gross_norm and differ from target_live's."""
import json, glob, os, statistics as stt
WS='/Users/haosiyu/wide_shadow/state'
SIG={}
for l in open('/Users/haosiyu/wide_shadow/shadow_log.jsonl'):
    if not l.strip(): continue
    r=json.loads(l)
    if r.get('e')=='signal': SIG[int(r['anchor_ts'])]=r
dk=[]; dc=[]; n=0
for p in sorted(glob.glob(WS+'/target_live_king/*.json')):
    A=int(os.path.basename(p)[:-5])
    if A not in SIG: continue
    cp=WS+'/target_live/%d.json'%A
    if not os.path.exists(cp): continue
    k=json.load(open(p)); c=json.load(open(cp))
    if c.get('producer','').startswith('shadow_loop'): continue   # pre-combo anchors: same file
    dk.append(abs(k['gross_norm']-SIG[A]['gross_pos'])); dc.append(abs(c['gross_norm']-SIG[A]['gross_pos'])); n+=1
print('combo-era anchors compared: %d'%n)
print('  |signal.gross_pos - target_live_KING.gross_norm| : max %.2e  mean %.2e'%(max(dk),stt.mean(dk)))
print('  |signal.gross_pos - target_live(deployed).gross_norm| : max %.4f mean %.4f'%(max(dc),stt.mean(dc)))
print('  => the logged score belongs to the KING vector, the deployed book is a different vector.')
# how different are the two books?
ov=[]
for p in sorted(glob.glob(WS+'/target_live_king/*.json'))[-40:]:
    A=int(os.path.basename(p)[:-5]); cp=WS+'/target_live/%d.json'%A
    if not os.path.exists(cp): continue
    c=json.load(open(cp))
    if c.get('producer','').startswith('shadow_loop'): continue
    kw=json.load(open(p))['weights']; cw=c['weights']
    gk=sum(abs(v) for v in kw.values()); gc=sum(abs(v) for v in cw.values())
    names=set(kw)|set(cw)
    l1=sum(abs(kw.get(s,0)/gk - cw.get(s,0)/gc) for s in names)
    ov.append(l1/2)
print('  L1/2 rewrite between king and deployed combo (unit-gross): mean %.3f  (0 = identical, 1 = disjoint)'%stt.mean(ov))

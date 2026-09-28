"""Recent outcomes primary; historical years guard tails, never retcon old gates."""
import math

def decide(r):
 checks={}
 def val(x):
  if isinstance(x,bool) or not isinstance(x,(float,int)) or not math.isfinite(x):raise ValueError('nonfinite metric')
  return x
 def diff(w,k):return val(w['paired_metric_difference'][k]['mean'])
 for seed in (42,2027):
  rs=r['results'][f'R180_s{seed}_vs_NC']['results'];recent=rs['recent_primary'];u=r['results'][f'R180_s{seed}_vs_U']['results']['recent_primary']
  checks[f'{seed}_recent_gain']=val(recent['paired_daily_bps'])>=1
  checks[f'{seed}_vs_uniform']=val(u['paired_daily_bps'])>0
  checks[f'{seed}_september']=diff(rs['Sep01_18_descriptive'],'return_compound')>=0
  checks[f'{seed}_recent_day_tail']=diff(recent,'days_below_minus4pct')<=0
  checks[f'{seed}_recent_dd']=diff(recent,'maxdd_5m')>=-.01
  checks[f'{seed}_fee_stress']=val(recent['fee125_paired_daily_bps'])>0
  for w in ('2023H2','2024','2025','2026_H1'):
   checks[f'{seed}_{w}_dd']=diff(rs[w],'maxdd_5m')>=-.05
   checks[f'{seed}_{w}_worst']=diff(rs[w],'worst_day')>=-.01
 return {'status':'ADVANCE_TO_FORWARD_RESEARCH_NOT_RELEASE' if all(checks.values()) else 'CRITERION_NOT_MET','checks':checks,'passed':sum(checks.values()),'total':len(checks),'limits':'Historical exploratory recent-priority objective; no independent confirmation or deployment permission.'}

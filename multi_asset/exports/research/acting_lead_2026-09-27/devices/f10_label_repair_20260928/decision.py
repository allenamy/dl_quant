"""Fixed recent-first REPAIR gates; old years are tail stress, not equal-weight utility."""
import math

def decide(r):
    checks={}
    def val(x):
        if isinstance(x,bool) or not isinstance(x,(float,int)) or not math.isfinite(x):raise ValueError('unknown metric')
        return x
    def diff(w,k):return val(w['paired_metric_difference'][k]['mean'])
    for seed in (42,2027):
        rnc=r['results'][f'REPAIR_s{seed}_vs_NC']['results'];u=r['results'][f'REPAIR_s{seed}_vs_U']['results']['recent_primary'];w=rnc['recent_primary']
        checks[f'{seed}_recent_vs_NC']=val(w['paired_daily_bps'])>0
        checks[f'{seed}_recent_vs_U']=val(u['paired_daily_bps'])>0
        checks[f'{seed}_september']=diff(rnc['Sep01_18_descriptive'],'return_compound')>=0
        checks[f'{seed}_recent_drawdown']=diff(w,'maxdd_5m')>=0
        checks[f'{seed}_recent_4pct_days']=diff(w,'days_below_minus4pct')<=0
        checks[f'{seed}_fee125']=val(w['fee125_paired_daily_bps'])>0
        for old in ('2023H2','2024','2025','2026_H1'):checks[f'{seed}_{old}_tail']=diff(rnc[old],'maxdd_5m')>=-.02
    return {'status':'ADVANCE_TO_FORWARD_RESEARCH_NOT_RELEASE' if all(checks.values()) else 'CRITERION_NOT_MET',
            'checks':checks,'passed':sum(checks.values()),'total':len(checks),'limits':'Repeated exploratory history. No automatic release, IC or full-window Sharpe override.'}

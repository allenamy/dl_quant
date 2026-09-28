"""Execute d89788736 follow-up criterion; NEVER a deployment authorization."""
import argparse,json,math,hashlib
from pathlib import Path

def finite(x):
 if isinstance(x,bool) or not isinstance(x,(float,int)) or not math.isfinite(x):raise ValueError('unknown numeric criterion')
 return x

def decide(d):
 if d['status']!='EXPLORATORY_NOT_RELEASE':raise ValueError('readout status')
 positive={};harm={};recent={}
 for pair in ('resid_vs_raw','resid_vs_NC42','resid_vs_NC2027'):
  r=d['results'][pair]['results']
  for w in ('pre2026','2026_JanAug'):positive[pair+'/'+w]=finite(r[w]['paired_daily_bps'])>0
  for w in ('2023H2','2024','2025','2026_JanAug'):
   ci=r[w]['ci95_bps']
   if not isinstance(ci,list) or len(ci)!=2 or finite(ci[0])>finite(ci[1]):raise ValueError('annual CI unavailable/reversed')
   harm[pair+'/'+w]=ci[1]<0
  recent[pair]=finite(r['Sep01_18_descriptive']['paired_daily_bps'])<0
 ok=all(positive.values()) and not any(harm.values())
 return dict(status='EXPLORATORY_DL_FOLLOWUP_ELIGIBLE' if ok else 'FOLLOWUP_CRITERION_NOT_MET',followup_DL_condition_met=ok,
  positive_required=positive,annual_CI_wholly_negative=harm,recent_deterioration=recent,
  interpretation='Recent harm must be disclosed even when long-window follow-up condition is met; no noninferiority/equivalence or broad-model-family conclusion.',release_authorized=False,
  prereg_commit='d89788736',numerical_fix='498e91ad5/10f55e8ad')

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('input',type=Path);ap.add_argument('output',type=Path);a=ap.parse_args();b=a.input.read_bytes();d=decide(json.loads(b));d['input_sha256']=hashlib.sha256(b).hexdigest();d['device_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 with open(a.output,'x') as f:json.dump(d,f,indent=2,allow_nan=False)
 print(d['status'])

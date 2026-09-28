"""Consume the sealed complete target; never regenerate a candidate or retrain."""
import argparse,json,os
from pathlib import Path
from cash_contract import sha,verify_record

PARENT=Path('/dev/shm/nc_liquidity_blend_support_20260928')
PIN='c05b296210c9415811462e0bc64cf0bf54729610f9d31c992dbee477470b6899'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,choices=(42,2027),required=True)
    ap.add_argument('--rule',choices=('xib',),required=True);ap.add_argument('--mix',choices=('shared',),required=True);args=ap.parse_args()
    r=verify_record(PARENT/'RESULT.json',PIN)
    root=Path(os.environ['PNOISE_W']);out=root/f'work/combo_s{args.seed}';out.mkdir(exist_ok=False)
    rec={'status':'SEALED_NC_CONFIGURATION_TARGETS_NOT_RETRAINED','seed':args.seed,
         'arm':{'rule':args.rule,'mix':args.mix},'parent_result':str(PARENT/'RESULT.json'),'parent_sha256':PIN,
         'inputs':r['inputs'],'sources':r['sources'],'policies':{},
         'state_init':'zero at 2023-01-01; hypothetical common start',
         'hold_contract':'trade_mask False = keep contracts; no King fallback'}
    for pol in ('literal','scaled_diagnostic'):
        src=PARENT/f'candidate_s{args.seed}_{pol}.npz'
        assert sha(src)==r['outputs'][str(src)]
        dst=out/(pol+'.npz');dst.symlink_to(src)
        rec['policies'][pol]={'path':str(dst),'sha':sha(dst)}
    (out/'TARGET_RECEIPT.json').write_text(json.dumps(rec,indent=2,allow_nan=False)+'\n')

if __name__=='__main__':main()

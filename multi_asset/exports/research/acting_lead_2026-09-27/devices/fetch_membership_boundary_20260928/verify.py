"""Independently check the selected population and archived fetch mechanism, not feature/PnL parity."""
import hashlib,io,json,sys,zipfile
from pathlib import Path
import numpy as np

def sha(b):return hashlib.sha256(b).hexdigest()
def main(root,parent):
    root,parent=Path(root),Path(parent);r=json.loads((root/'RESULT.json').read_text());a=json.loads((root/'ACTUAL.json').read_text())
    z=zipfile.ZipFile(parent/'PRODUCTION_INPUTS.zip');cfg=json.loads(z.read('shadow_bundle/config.json'));sy=cfg['symbols_panel'];j=sy.index('STGUSDT');checks=[]
    def check(name,value):
        checks.append(name)
        if not bool(value):raise ValueError(name)
    check('actual_bound_to_result',sha((root/'ACTUAL.json').read_bytes())==r['actual_sha256'])
    check('population', [x['anchor'] for x in r['rows']]==list(range(1790236800,1790337601,14400)))
    for actual,row in zip(a['rows'],r['rows']):
        t=row['anchor'];prefix=str(t);aux=json.loads(z.read(f'state/snap/{t}/aux.json'));b=(root/actual['artifact']['path']).read_bytes()
        check(prefix+' artifact_sha',sha(b)==actual['artifact']['sha256'])
        with np.load(io.BytesIO(b)) as zz:d={k:zz[k] for k in zz.files}
        check(prefix+' archived_members',np.array_equal(d['m'],aux['prev_rec']['members']))
        check(prefix+' archived_fetch',np.array_equal(d['fetch'],np.isin(sy,aux['fetch_syms'])))
        check(prefix+' full_ordered_members_after',row['ordered_members_equal_after'])
        check(prefix+' no_remaining_population_difference',not row['research_only_after'] and not row['live_only_after'])
        check(prefix+' original_controls',row['original_research_control'] and row['actual_control'])
        l=int(d['ts'][np.isfinite(d['cd'][:,j,3])][-1])
        check(prefix+' last_finite_qv_bar',l==actual['stg']['last_qv_bar_in_7d'])
    middle=r['rows'][1:7]
    check('six_STG_only',all(x['research_only_before']==['STGUSDT'] for x in middle))
    check('six_actual_not_fetched',all(not x['stg_actual']['fetched'] for x in middle))
    check('six_proxy_still_alive',all(x['stg_research']['legal'] for x in middle))
    check('two_controls_no_difference',all(not r['rows'][i]['research_only_before'] and not r['rows'][i]['live_only_before'] for i in (0,7)))
    out={'status':'PASS_MEMBER_INPUT_DIAGNOSTIC_ONLY','checks':len(checks),'check_names':checks,'source_sha256':sha(Path(__file__).read_bytes()),'result_sha256':sha((root/'RESULT.json').read_bytes()),'python':sys.executable,'numpy':np.__version__}
    (root/'VERIFY.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'status':out['status'],'checks':len(checks)}))
if __name__=='__main__':main(*sys.argv[1:])

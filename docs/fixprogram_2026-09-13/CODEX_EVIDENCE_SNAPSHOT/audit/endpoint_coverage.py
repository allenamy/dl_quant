"""Independent E60 held endpoint evidence. No Engine or coverage callback import."""
from batch_contract import *
import csv,io,zipfile,datetime as dt

BOUNDARY='FUNDING_FIRST_THEN_HELD_ENDPOINT_T_TO_T_PLUS_1MS_THEN_REDUCE_ONLY'
RISK_ENGINE_SHA='8771e24e3c4724ee62703b1cb57bbfb3b0aeef788a6376182b4067921fd70630'
SUPPLEMENT=R/'book/dynamic_frame_inputs_20260915/runner2'
SUPPLEMENT_SHA='6045c216bcf157ea9d4b75d8f753bec67967d5aaba36a807f5781d3dece7afbf'

def month(t):return dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).strftime('%Y-%m')

def match_month(source,facts):
    need(source==facts,'independent funding month population/time/rate mismatch')

def prepare_months(journal,original,pins):
    """Recorded requests select files only; the audit's own inventory sets obligations."""
    wanted=set()
    with Path(journal).open() as stream:
        for line in stream:
            r=json.loads(line)
            if r['type']=='RISK_ATTEMPT' and r.get('outcome')=='APPLIED_RESEARCH_EVENT' and r.get('halted') is True:
                wanted.update((v['symbol'],month(r['ts_ms'])) for v in r['fills']+r['missed'])
    if not wanted:return {}
    lp=SUPPLEMENT/'COVERAGE_INPUTS_LOCK.json'
    need(original.get(str(lp))==SUPPLEMENT_SHA,'original complete supplemental archive index')
    pin(lp,pins,SUPPLEMENT_SHA);lock=read(lp)
    choices={}
    for p,h in original.items():
        name=Path(p).name
        if '-fundingRate-' in name and name.endswith('.zip') and p+'.CHECKSUM' in original:
            s,mo=name[:-4].split('-fundingRate-');choices.setdefault((s,mo),[]).append((p,p+'.CHECKSUM'))
    for r in lock['index']:
        key=(r['symbol'],r['month'])
        if key not in wanted:continue
        paths=[]
        for k in ('archive','checksum'):
            d=lock['files'][r[k]];p=SUPPLEMENT/'evidence'/d['relative']
            need(original.get(str(p))==d['sha256'],'original supplemental file identity');paths.append(str(p))
        choices.setdefault(key,[]).append(tuple(paths))
    selected={}
    for s,mo in sorted(wanted):
        key=s+'|'+mo
        if (s,mo)==('AERGOUSDT','2026-07'):
            selected[key]={'kind':'ALREADY_VERIFIED_PUBLIC_185'};continue
        candidates=sorted(choices.get((s,mo),[]))
        need(candidates,'endpoint month evidence absent '+key)
        p,c=candidates[0]
        for item in (p,c):pin(item,pins,original[item])
        selected[key]=dict(kind='ORIGINAL_OFFICIAL_ZIP',archive=p,checksum=c)
    return selected

class EndpointFacts:
    def __init__(self,f,symbols,segments,descriptors,pins,public):
        self.f=f;self.symbols=list(symbols);self.segments=segments
        self.descriptors=descriptors;self.pins=pins;self.public=public
        self.index={s:j for j,s in enumerate(self.symbols)}
        self.asset_rows={s:np.flatnonzero(f['asset']==j) for s,j in self.index.items()}
        self.month_cache={};self.checks=0;self.same_ms_held_events=0

    def certify_month(self,s,mo):
        key=(s,mo)
        if key in self.month_cache:return
        d=self.descriptors.get(s+'|'+mo);need(d is not None,'endpoint month evidence absent '+s+'|'+mo)
        rows=self.asset_rows[s];rows=[k for k in rows if month(int(self.f['event_ms'][k]))==mo]
        facts={int(self.f['event_ms'][k]):float(self.f['rate'][k]) for k in rows}
        need(len(facts)==len(rows),'unique endpoint funding month rows')
        if d['kind']=='ALREADY_VERIFIED_PUBLIC_185':
            need((s,mo)==('AERGOUSDT','2026-07'),'fixed public-only month')
            source={t:rate for (j,t),(rate,mark) in self.public.items() if j==self.index[s] and month(t)==mo}
            need(len(source)==185,'complete original public month population')
        else:
            need(d['kind']=='ORIGINAL_OFFICIAL_ZIP','exact endpoint source kind')
            p,c=Path(d['archive']),Path(d['checksum'])
            for item in (p,c):need(str(item) in self.pins and sha(item)==self.pins[str(item)],'endpoint source pinned SHA')
            need(c.read_text().split()[0]==sha(p),'endpoint official archive checksum')
            with zipfile.ZipFile(p) as z:
                names=z.namelist();need(len(names)==1 and names[0]==s+'-fundingRate-'+mo+'.csv','single exact symbol/month CSV')
                records=list(csv.DictReader(io.StringIO(z.read(names[0]).decode())))
            source={}
            for r in records:
                t=int(r['calc_time']);rate=float(r['last_funding_rate'])
                need(t not in source and month(t)==mo and np.isfinite(rate),'unique finite original monthly funding event')
                source[t]=rate
        match_month(source,facts);self.month_cache[key]=True

    def check(self,audit,t,consumed):
        need(type(t)is int,'exact endpoint milliseconds')
        need(consumed==int(np.searchsorted(self.f['event_ms'],t,side='right')),'complete same-ms funding must precede risk exit')
        if not audit.halted:return 0
        count=0
        for s,p in sorted(audit.positions.items()):
            if not audit._q(s):continue
            seg=self.segments.get(p['instrument_id'])
            need(seg is not None and seg['symbol']==s and seg['start_ms']<=t<t+1<=seg['end_ms'],'held generation endpoint [t,t+1)')
            self.certify_month(s,month(t))
            ix=self.asset_rows[s];ts=self.f['event_ms'][ix]
            hit=ix[np.searchsorted(ts,t,side='left'):np.searchsorted(ts,t+1,side='left')]
            for k in hit:
                need(np.isfinite(self.f['rate'][k]) and np.isfinite(self.f['mark'][k]) and self.f['mark'][k]>0,'held endpoint rate/mark must be known')
            count+=1;self.same_ms_held_events+=len(hit)
        self.checks+=count;return count

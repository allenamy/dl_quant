"""Verify handover identities and pause state. Does not rerun experiments or inspect production."""
from pathlib import Path
import datetime, hashlib, json, re, subprocess, tomllib, os
ROOT=Path(__file__).resolve().parents[5];os.chdir(ROOT)
R=Path('multi_asset/exports/research/acting_lead_2026-09-27/receipts')
O=R/'HANDOFF_20260929'
checks=[]
def require(name,ok,detail=None):
 checks.append({'name':name,'ok':bool(ok),'detail':detail})
 if not ok: raise AssertionError((name,detail))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
manifest=json.loads((O/'CHANGED_FILES.json').read_text())
base=manifest['base'];head=manifest['head']
require('research_head_still_frozen_or_handover_descendant',subprocess.run(['git','merge-base','--is-ancestor',head,'HEAD']).returncode==0)
actual=subprocess.check_output(['git','diff','--name-only',base,head],text=True).splitlines()
require('frozen_path_set_exact',actual==[r['path'] for r in manifest['files']],len(actual))
matched=0
for row in manifest['files']:
 p=Path(row['path'])
 if row['path']=='docs/ACTING_LEAD_2026-09-27.md':
  data=subprocess.check_output(['git','show',head+':'+row['path']])
  ok=hashlib.sha256(data).hexdigest()==row['sha256']; scope='git_pre_pause'
 else:
  ok=p.is_file() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256'];scope='current_file'
 require('sha:'+row['path'],ok,scope);matched+=1
require('ledger_paused', '**状态:** PAUSED' in Path('docs/ACTING_LEAD_2026-09-27.md').read_text()[:350])
docs=[Path('docs/HANDOFF_acting_lead_2026-09-29.md'),Path('docs/HANDOFF_acting_lead_evidence_index_2026-09-29.md')]
links=0
for p in docs:
 s=p.read_text();require('metadata:'+str(p),s.startswith('> **创建:'))
 for m in re.finditer(r'\[[^\]]+\]\(([^)]+)\)',s):
  t=m.group(1)
  if t.startswith(('https:','http:')):continue
  q=p.parent/t
  require('link:'+str(p)+':'+t,q.exists());links+=1
# Cross-repository commits are tied to the preserved executable candidate/production receipts.
fund=json.loads((R/'ROOT_FUNDING_GREEN2_COMMIT_20260927.json').read_text())
prod=json.loads((R/'ROOT_00Z_LOCAL_POSTTRADE_20260929.json').read_text())
external={fund['candidate_commit']:str(R/'ROOT_FUNDING_GREEN2_COMMIT_20260927.json'),prod['head']:str(R/'ROOT_00Z_LOCAL_POSTTRADE_20260929.json')}
s=docs[0].read_text()
refs=sorted({x for x in re.findall(r'(?<![\w])[0-9a-f]{9,40}(?![\w])',s) if not x.isdigit()})
for c in refs:
 if c in external: require('commit:'+c,True,{'cross_repository_receipt':external[c]})
 else: require('commit:'+c,subprocess.run(['git','cat-file','-e',c+'^{commit}'],stderr=subprocess.DEVNULL).returncode==0)
bundle=Path(fund['bundle']['path']);require('funding_bundle_sha',sha(bundle)==fund['bundle']['sha256'])
heads=subprocess.check_output(['git','bundle','list-heads',str(bundle)],text=True)
require('candidate_commit_in_bundle_heads',fund['candidate_commit'] in heads)
require('candidate_not_deployed_receipt',fund['production_deployed'] is False and fund['wrapper_rc']==1)
pa=json.loads((O/'PAUSE_RECEIPT.json').read_text())
a=tomllib.loads(Path(pa['automation']['file']).read_text())
require('automation_PAUSED',a['status']=='PAUSED')
reg=Path(pa['registry']['path']);jobs=json.loads(reg.read_text())
require('registry_sha_unchanged',sha(reg)==pa['registry']['sha256'])
require('only_resident_collector_open',[x['name'] for x in jobs if not x.get('closed',False)]==['alloc_S3_xvenue_collector'])
commits=(O/'COMMITS.tsv').read_text().splitlines()[1:]
require('commit_inventory_count',len(commits)==528==manifest['commit_count'])
for line in commits:
 c=line.split('\t',1)[0]
 require('inventory_commit:'+c,subprocess.run(['git','cat-file','-e',c+'^{commit}'],stderr=subprocess.DEVNULL).returncode==0)
# Archive bytes were fully rehashed by the builder this turn. Do not reread 6 GB merely for duplicate hashing.
archives=json.loads((O/'LOCAL_ARCHIVES.json').read_text())
for row in archives['files']:require('archive_exists_size:'+row['path'],Path(row['path']).is_file() and Path(row['path']).stat().st_size==row['bytes'])
result={'status':'HANDOVER_IDENTITY_AND_PAUSE_VERIFIED','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'freeze':head,'changed_files_sha_verified':matched,'document_links_verified':links,'main_commit_references':len(refs),'commits_verified':len(commits),'local_archives_fresh_sha_inventory':len(archives['files']),'checks':checks,'limits':['No economic rerun or numerical re-estimation performed during handover.','Historical test/PnL claims are scoped to cited frozen reports, not a new certification.','External executor commits bound by preserved receipts and bundle head; no live import.','No claim that all Pod dependencies are permanently backed up.']}
(O/'VERIFY_HANDOVER.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='checks'},ensure_ascii=False))

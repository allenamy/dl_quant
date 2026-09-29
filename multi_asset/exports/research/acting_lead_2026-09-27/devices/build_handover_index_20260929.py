"""Build a read-only frozen research inventory and current handover receipts. No live imports/network."""
from pathlib import Path
import hashlib, json, subprocess, datetime, os, tomllib
ROOT = Path(__file__).resolve().parents[5]
os.chdir(ROOT)
BASE='3b4a2815ad4b8d45ee09ed8b69222e04b5885301'
HEAD='f64792d1c2b34bd0e38bdd7eb1c013bcb4be4ff1'
OUT=Path('multi_asset/exports/research/acting_lead_2026-09-27/receipts/HANDOFF_20260929')
OUT.mkdir(exist_ok=True)
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
def git(*args): return subprocess.check_output(['git',*args])
def write(name,obj): (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def sha_file(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
files=git('diff','--name-only',BASE,HEAD).decode().splitlines()
# Use an explicit marker: str.splitlines treats U+001e as a line boundary.
last={}; c=None
for line in git('log','--format=COMMIT_RECORD:%H','--name-only',f'{BASE}..{HEAD}').decode().splitlines():
 if line.startswith('COMMIT_RECORD:'): c=line.split(':',1)[1]
 elif line and c: last.setdefault(line,c)
commits=git('log','--reverse','--format=%H%x09%aI%x09%s',f'{BASE}..{HEAD}').decode()
(OUT/'COMMITS.tsv').write_text('commit\tauthor_time\tsubject\n'+commits)
(OUT/'DIFF_STAT.txt').write_bytes(git('diff','--stat',BASE,HEAD))
(OUT/'CHANGED_PATHS.txt').write_text('\n'.join(files)+'\n')
proc=subprocess.Popen(['git','cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
rows=[]
for p in files:
 proc.stdin.write(f'{HEAD}:{p}\n'.encode());proc.stdin.flush()
 header=proc.stdout.readline().decode().strip().split()
 if header[-1]=='missing': rows.append({'path':p,'status':'deleted'});continue
 obj,typ,n=header; n=int(n); data=proc.stdout.read(n);assert len(data)==n
 assert proc.stdout.read(1)==b'\n'
 rows.append({'path':p,'bytes':n,'sha256':hashlib.sha256(data).hexdigest(),'git_blob':obj,'last_change_commit':last[p]})
proc.stdin.close();assert proc.wait()==0
write('CHANGED_FILES.json',{'scope':'bytes at frozen git HEAD, NOT current live or remote artifacts','base':BASE,'head':HEAD,'created_utc':now,'commit_count':len(commits.splitlines()),'files':rows})
registry=Path('multi_asset/exports/research/loop_2026-09-26/INFLIGHT_REGISTRY.json')
jobs=json.loads(registry.read_text()); open_jobs=[x['name'] for x in jobs if not x.get('closed',False)]
auto=Path('/Users/haosiyu/.codex/automations/automation/automation.toml')
a=tomllib.loads(auto.read_text())
assert a['status']=='PAUSED'
assert open_jobs==['alloc_S3_xvenue_collector'],open_jobs
write('PAUSE_RECEIPT.json',{'observed_utc':now,'user_request':'先在此暂停收尾；主研究员接回','automation':{'id':'automation','status':a['status'],'file':str(auto),'sha256':sha_file(auto)},'registry':{'path':str(registry),'sha256':sha_file(registry),'records':len(jobs),'closed_count':sum(x.get('closed',False) for x in jobs),'open_names':open_jobs},'limits':['Registry status is not a global process census.','No production process, resident collector or shared Pod was stopped.','No auto resume, deployment, venue call or new experiment in handover.','Production evidence cutoff remains Sep29 00Z audit at 01:00:37Z.']})
archive_roots=[Path('/Users/haosiyu/.codex/tmp/pod_archive_20260928'),Path('/Users/haosiyu/.codex/tmp/state_handoff_cash_20260929'),Path('/Users/haosiyu/.codex/tmp/state_handoff_20260929'),Path('/Users/haosiyu/.codex/tmp/tail_held_cash_20260929')]
archives=[]
for root in archive_roots:
 if root.exists():
  for f in sorted(root.rglob('*.zip')):
   archives.append({'path':str(f),'bytes':f.stat().st_size,'sha256':sha_file(f)})
write('LOCAL_ARCHIVES.json',{'created_utc':now,'scope':'ZIP files currently present in listed local archive roots; sha rehashed during handover; not a complete Pod dependency backup or remote byte comparison','roots':[str(p) for p in archive_roots],'files':archives})
by={x['path']:x for x in rows}
reports=[r for r in rows if r['path'].startswith('docs/') and Path(r['path']).name.startswith(('RESULT_','FINDING_','AUDIT_')) and r['path'].endswith('.md')]
codes=[r for r in rows if r['path'].startswith('multi_asset/') and Path(r['path']).suffix in ('.py','.sh')]
write('SOURCE_FILES.json',{'head':HEAD,'files':codes})
meta=f'> **创建:** {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M} UTC | **Session:** Codex root / acting-lead-20260927 | **状态:** final-evidence-index | **作废条件:** 冻结HEAD、索引文件或归档字节变化须重新核验\n'
s=[meta,'# 两日交接证据索引\n','主件：[HANDOFF_acting_lead_2026-09-29.md](HANDOFF_acting_lead_2026-09-29.md)。此索引不重判实验，也没有重新训练或重跑现金；历史测试结果以原收据为准。\n',f'冻结范围 `{BASE}..{HEAD}`：**{len(commits.splitlines())}提交，{len(rows)}改变文件，{len(codes)}个Python/shell源码文件，{len(reports)}份结果/发现/审计文档**。下面的SHA来自冻结Git对象；后续仅交接文/台账修改不倒写历史身份。\n','## 一、完整机器索引\n']
for name in ['COMMITS.tsv','CHANGED_FILES.json','SOURCE_FILES.json','CHANGED_PATHS.txt','DIFF_STAT.txt','PAUSE_RECEIPT.json','LOCAL_ARCHIVES.json']:
 p=OUT/name;s.append(f'- [{name}](../{p}) — SHA256 `{sha_file(p)}`。')
s+=['\n`CHANGED_FILES.json`逐文件给出完整路径、字节数、SHA256、Git blob和最后修改提交。`SOURCE_FILES.json`是代码子集。它们不是仅有文件名的索引。\n','## 二、所有最终结果入口\n','表中“最后修改提交”不是初始预注册；各报告正文列完整设计/实现/修订链。哈希按冻结点，旧报告中的事后更正保留。\n','| 文档 | 最后修改提交 | SHA256 |','|---|---|---|']
for r in sorted(reports,key=lambda x:x['path']):
 n=Path(r['path']).name;s.append(f"| [{n}]({n}) | `{r['last_change_commit'][:9]}` | `{r['sha256']}` |")
s+=['\n## 三、实际代码入口\n','均相对本研究工作树。目录内的合同、runner、测试和独立验证器一并保留；完整SHA见SOURCE_FILES，不用HEAD同名文件冒充旧运行版本。\n','| 任务 | 入口 | 最后修改提交 / SHA256 |','|---|---|---|']
D=Path('multi_asset/exports/research/acting_lead_2026-09-27/devices')
entry={
'本地只读巡检':'light_local_audit.py','恢复验收':'recovery_acceptance.py','对账提示核验':'reconcile_notice_audit.py','基线聚合桥':'baseline_sharpe_bridge_20260928.py','D10重现队列':'d10_rerun6_queue.py','KSR终态核验':'ksr_terminal_audit.py','KSR状态重建':'ksr_handback_rebuild.py','KN标签诊断':'kn_label_geometry_20260928/probe.py','cap50':'book_cap50_20260928/run_batch.py','逆波动':'book_invvol_20260928/run_batch.py','残差小模型':'residual_book_20260928/train_ridge.py','长持仓标签':'horizon_book_20260928/train_ridge.py','流动性融合整书':'nc_liquidity_blend_cash_20260928/run_batch.py','F10近期训练':'f10_recent_adapt_20260928/train_adapt.py','F10流动性人口loss':'f10_liquid_population_20260928/train_adapt.py','标签修复训练':'f10_label_repair_20260928/train_adapt.py','标签证据':'training_exposure_label_repair_20260928.py','同伴特征小模型':'linkage_20260928/ridge_screen.py','近期NC现金':'recent_evaluation_inputs_20260928/recent_cash_run.py','d01 pure执行桥':'executor_bridge_20260928/run_bridge.py','抓取状态':'fetch_membership_boundary_20260928/probe.py','抓取→完整特征':'fetch_feature_alignment_20260928/run.py','独立LR递推':'lr_recurrence_20260928/run_lr.py','执行限制闭合':'conditional_execution_book.py','实际现金':'actual_cash_bridge.py','实际多空':'actual_directional_cash.py','静态目标桥':'actual_target_cash.py','混合子书':'actual_blend_cash.py','旧H谱系':'signal_state_trace.py','状态接入':'state_handoff.py','接入现金':'run_handoff_cash.py','尾部持仓现金':'tail_held_cash.py'}
for topic,rel in entry.items():
 p=str(D/rel);r=by[p];s.append(f"| {topic} | [{rel}](../{p}) | `{r['last_change_commit'][:9]}` / `{r['sha256']}` |")
s+=['\n## 四、完整本机大包\n',f'本次重新读取并计算了下面{len(archives)}个ZIP的SHA256，共{sum(a["bytes"] for a in archives):,}字节。这里只证明本机现存包身份，未再次比对Pod所有成员，也未宣称所有训练输入已永久备份。部分模型/原始输入仍依赖Pod，关机前必须看原COMMAND与manifest。\n','| 本机绝对路径 | 字节数 | SHA256 |','|---|---:|---|']
for r in archives:s.append(f"| `{r['path']}` | {r['bytes']} | `{r['sha256']}` |")
s+=['\n## 五、复核边界\n','- 本次没有重跑历史经济实验；摘要引用冻结收据，历史方法局限沿用。\n- 交接验证器另核主件/索引链接、引用提交、当前文件与冻结SHA、暂停状态和任务登记；不能把这些文档验收叫策略通过。\n- 本机大包可能含私有账本，路径可交接给账户研究人员，勿直接公开上传。索引不包含密钥。\n- 主件、索引及新增交接代码的SHA在 PACKAGE_FILES.json；该清单不包含自身以免循环。最终提交以git为准。\n']
Path('docs/HANDOFF_acting_lead_evidence_index_2026-09-29.md').write_text('\n'.join(s).rstrip()+'\n')
print(json.dumps({'reports':len(reports),'source_files':len(codes),'changed_files':len(rows),'commits':len(commits.splitlines()),'local_zips':len(archives),'open_jobs':open_jobs,'automation':a['status']}))

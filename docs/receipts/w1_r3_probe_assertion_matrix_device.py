#!/usr/bin/env python3
"""Monotone, bounded [-1,1] IC ledger sequences; actual old/new state-machine ASTs.

Synthetic reachable sequences, never claimed as real account events. Historical rows are
immutable. Time advances by full 4h grid steps, and only explicitly identified new rows append.
Every send and state write is an in-memory stub; no operational import or network.
"""
import ast, copy, hashlib, json, sys
sys.dont_write_bytecode=True
sys.path.insert(0, '/Users/haosiyu/Desktop/quant_research/.claude/worktrees/codex-independent-20260907/multi_asset/exports/research/codex_followup_code_review_2026-09-13/monitoring')
import probe_followup as P

def monitor(path):
    tree=ast.parse(path.read_text())
    excluded={'build_parser','_readonly_invocation','load_anchors','load_state','save_state','main','_telegram_sender','append_eval'}
    names={n.name for n in tree.body if isinstance(n,ast.FunctionDef) and n.name not in excluded}
    return P.extracted(path,names,extras={'COOLDOWN_S':86400},constants=True)

def main():
    import pathlib
    oldpath=P.OUT/'private/previous/ic_monitor.py'
    newpath=pathlib.Path('/Users/haosiyu/cc_tmp/exec_w1/ops/ic_monitor.py')  # W1b R3: 指向修后工作树
    new=monitor(newpath);G=new['GRID_S'];W=new['WINDOW_START_TS'];now=W+60*G+new['MATURE_LAG_S']+60
    def initial(r24sum,r48sum,first36):
        # Four existing older holes: tolerated by r48 until one additional missing anchor arrives.
        rows=[];older=[i for i in range(8,36) if i not in {18,19,20,21}]
        assert len(older)==24
        for i in range(60):
            if i in {18,19,20,21}:continue
            value=.05 if i<8 else (.1 if i==8 else (r48sum-r24sum-.1)/23) if i<36 else (first36 if i==36 else (r24sum-first36)/23)
            rows.append({'anchor_ts':W+i*G,'rank_ic':value})
        assert all(-1<=r['rank_ic']<=1 for r in rows)
        return rows
    a0=initial(-1.08,-.72,-.6);a1=a0+[{'anchor_ts':W+60*G,'rank_ic':0.}]
    a=[('r24 DECIDE delivered',a0,now),('new r48 DECIDE during same-level cooldown',a1,now+G),('anchor 61 missing; r48 unavailable, r24 healthy',a1,now+2*G)]
    b0=initial(-.504,-.816,.1);b1=b0+[{'anchor_ts':W+61*G,'rank_ic':-.1}];b2=b1+[{'anchor_ts':W+62*G,'rank_ic':-1.}]
    b=[('r48 DECIDE delivered',b0,now),('anchor 60 missing; r24 ALERT, r48 unavailable',b1,now+2*G),('r24 now DECIDE; old DECIDE cooldown active',b2,now+3*G)]
    outputs={}
    for name,steps in [('new_trigger_lost',a),('downgrade_then_suppressed_upgrade',b)]:
        outputs[name]={'fixture':[{'label':s,'now':t,'now_iso':new['iso'](t),'rows':rows} for s,rows,t in steps],'versions':{}}
        assert steps[1][1][:len(steps[0][1])]==steps[0][1] and steps[2][1][:len(steps[1][1])]==steps[1][1]
        for ver,path in [('frozen_round2_00921bc7',P.W1/'ops/ic_monitor.py'),('R3_fixed_worktree',newpath)]:
            m=monitor(path);state={};m['load_state']=lambda path=None:copy.deepcopy(state)
            def save(s,path=None):state.clear();state.update(copy.deepcopy(s))
            m['save_state']=save;run=[]
            for label,rows,t in steps:
                verdict=m['check'](rows,now=t);plans=m['plan_delivery'](verdict,copy.deepcopy(state),t)
                result=m['deliver'](verdict,now=t,sender=lambda *args:{'delivered_offbox':True,'status':'AUDIT_STUB_SUCCESS'})
                run.append({'label':label,'now':t,'now_iso':new['iso'](t),'verdict':verdict,'plans':plans,'deliveries':result,'state':copy.deepcopy(state)})
            outputs[name]['versions'][ver]={'source':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'steps':run}
    def ev(step, k):
        return (step['state'].get('event') or {}).get(k)
    for ver in ('frozen_round2_00921bc7', 'R3_fixed_worktree'):
        a = outputs['new_trigger_lost']['versions'][ver]['steps']
        b = outputs['downgrade_then_suppressed_upgrade']['versions'][ver]['steps']
        rows = [
            ("A1 trigger == ['r24<R24_P1']              (非缺陷断言)", a[0]['verdict']['trigger'] == ['r24<R24_P1'], a[0]['verdict']['trigger']),
            ("A2 trigger == ['r48<R48_P1']              (非缺陷断言)", a[1]['verdict']['trigger'] == ['r48<R48_P1'], a[1]['verdict']['trigger']),
            ("A2 deliveries == []   冷却仍扣住页        (非缺陷断言)", a[1]['deliveries'] == [], [r['kind'] for r in a[1]['deliveries']]),
            ("A2 event.trigger_windows == ['r24']       *N1 缺陷断言", ev(a[1], 'trigger_windows') == ['r24'], ev(a[1], 'trigger_windows')),
            ("A3 deliveries == [INCOMPLETE,RECOVERED]   *N1 缺陷断言", [r['kind'] for r in a[2]['deliveries']] == ['INCOMPLETE', 'RECOVERED'], [r['kind'] for r in a[2]['deliveries']]),
            ("B2 event.level == 'ALERT'                 *N2 缺陷断言", ev(b[1], 'level') == 'ALERT', ev(b[1], 'level')),
            ("B3 verdict.level == 'DECIDE'              (非缺陷断言)", b[2]['verdict']['level'] == 'DECIDE', b[2]['verdict']['level']),
            ("B3 deliveries == []    升级被旧时钟吞     *N2 缺陷断言", b[2]['deliveries'] == [], [r['kind'] for r in b[2]['deliveries']]),
        ]
        print("=" * 98)
        print(ver, "<-", outputs['new_trigger_lost']['versions'][ver]['source'])
        print("   sha256", outputs['new_trigger_lost']['versions'][ver]['sha256'])
        for name, ok, got in rows:
            print(f"   {'HOLDS' if ok else 'FAILS'}  {name}   actual={got}")

if __name__=='__main__':main()

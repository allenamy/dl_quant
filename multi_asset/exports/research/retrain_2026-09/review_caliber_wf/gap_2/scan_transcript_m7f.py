import re, json, sys
T="/Users/haosiyu/.claude/projects/-Users-haosiyu-Desktop-quant-research/6737834a-f0b4-40e0-82a0-c0e83c0ccf5f.jsonl"
pat=re.compile(r'(env [^\n]{0,600}?M7F[^\n]{0,150})')
pat2=re.compile(r'([^\n]{0,250}M7F[^\n]{0,250})')
seen=set(); out=[]; n=0
with open(T,'r',errors='replace') as f:
    for ln,line in enumerate(f):
        if 'M7F' not in line: continue
        n+=1
        ts=None
        try:
            j=json.loads(line); ts=j.get('timestamp')
        except Exception: pass
        for m in pat.finditer(line):
            s=m.group(1).replace('\\n',' ⏎ ')
            key=s[:200]
            if key in seen: continue
            seen.add(key); out.append((ln,ts,'ENV',s[:900]))
print("lines with M7F:", n)
for o in out[:12]: print(o[0],o[1],o[2],o[3]); print('---')
# also first 6 raw contexts (non-env) to see how tag defined
c=0; seen2=set()
with open(T,'r',errors='replace') as f:
    for ln,line in enumerate(f):
        if 'M7F' not in line: continue
        for m in pat2.finditer(line):
            s=m.group(1).replace('\\n',' ⏎ ')
            if 'FTRIM' in s or 'umask' in s.lower():
                k=s[:120]
                if k in seen2: continue
                seen2.add(k); c+=1
                try: ts=json.loads(line).get('timestamp')
                except Exception: ts=None
                print('CTX',ln,ts,s[:600]); print('---')
                if c>=10: break
        if c>=10: break

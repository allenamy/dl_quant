import io
p = "/mnt/storage/private/work_hsy/f8_2026-08-22/f10_train.py"
s = io.open(p, encoding="utf-8").read()
if "REC" not in s:
    a = 'CTXA = int(os.environ.get("CTXA", "0"))       # 架构A: 因果 regime 上下文 4 维'
    b = '''CTXA = int(os.environ.get("CTXA", "0"))       # 架构A: 因果 regime 上下文 4 维
REC = int(os.environ.get("REC", "0"))         # 架构B: 逐名递归分数态(HRT 学习衰减门)'''
    assert a in s; s = s.replace(a, b, 1)
    # Net: recurrent blocks
    a = '''class Net(nn.Module):
    def __init__(s, d=167, h=256, p=0.1):
        super().__init__()
        s.f = nn.Sequential(nn.Linear(d, h), nn.GELU(), nn.Dropout(p),
                            nn.Linear(h, h), nn.GELU(), nn.Dropout(p), nn.Linear(h, 1))
        s.a = nn.Parameter(torch.tensor(-2.303))          # sigmoid→0.0909 ⇒ α≈0.10
        nn.init.normal_(s.f[-1].weight, 0.0, 1e-3); nn.init.zeros_(s.f[-1].bias)'''
    b = '''class Net(nn.Module):
    def __init__(s, d=167, h=256, p=0.1, hs=32):
        super().__init__()
        s.f = nn.Sequential(nn.Linear(d, h), nn.GELU(), nn.Dropout(p),
                            nn.Linear(h, h), nn.GELU(), nn.Dropout(p), nn.Linear(h, 1))
        s.a = nn.Parameter(torch.tensor(-2.303))          # sigmoid→0.0909 ⇒ α≈0.10
        nn.init.normal_(s.f[-1].weight, 0.0, 1e-3); nn.init.zeros_(s.f[-1].bias)
        if REC:
            s.emb = nn.Sequential(nn.Linear(d, h), nn.GELU(), nn.Dropout(p), nn.Linear(h, h), nn.GELU())
            s.push = nn.Linear(h, hs); s.gate = nn.Linear(h, hs)
            nn.init.constant_(s.gate.bias, -1.5)          # HRT: 慢记忆先验
            s.head2 = nn.Linear(h + hs, 1)
            nn.init.normal_(s.head2.weight, 0.0, 1e-3); nn.init.zeros_(s.head2.bias)

    def score_rec(s, x, hp):
        e = s.emb(x)
        g = torch.sigmoid(s.gate(e)) ** 3                 # cubic-sigmoid 衰减门(HRT)
        hn = hp * (1 - g) + s.push(e) * g
        return s.head2(torch.cat([e, hn], -1)).squeeze(-1), hn'''
    assert a in s; s = s.replace(a, b, 1)
    # u_of: REC branch with H state
    a = '''    if CTXA:
        x = torch.cat([x, CTXT[i].expand(b - a, 4)], 1)
    s = mdl.f(torch.nan_to_num(x)).squeeze(-1)'''
    b = '''    if CTXA:
        x = torch.cat([x, CTXT[i].expand(b - a, 4)], 1)
    if REC and H is not None:
        s, hn = mdl.score_rec(torch.nan_to_num(x), H[cols_t])
    else:
        s = mdl.f(torch.nan_to_num(x)).squeeze(-1); hn = None'''
    assert a in s; s = s.replace(a, b, 1)
    s = s.replace("def u_of(mdl, i, mu, sd, tau, hard):", "def u_of(mdl, i, mu, sd, tau, hard, H=None):", 1)
    a = '''    u = c * torch.tanh(u / c)
    u = u - u.mean()
    return u, PST[a:b]'''
    b = '''    u = c * torch.tanh(u / c)
    u = u - u.mean()
    return u, PST[a:b], (cols_t, hn)'''
    assert a in s; s = s.replace(a, b, 1)
    # run_span: carry H
    a = '''    w = torch.zeros(NW, device=DEV) if w0 is None else w0
    al = mdl.alpha()
    nets = []
    for k, i in enumerate(idx):
        u, midx = u_of(mdl, i, mu, sd, tau, hard)
        if u is not None:'''
    b = '''    w = torch.zeros(NW, device=DEV) if w0 is None else w0
    H = torch.zeros(NW, 32, device=DEV) if REC else None
    al = mdl.alpha()
    nets = []
    for k, i in enumerate(idx):
        u, midx, hst = u_of(mdl, i, mu, sd, tau, hard, H)
        if u is not None:
            if REC and hst[1] is not None:
                H = H.index_put((hst[0],), hst[1])'''
    assert a in s; s = s.replace(a, b, 1)
    # test loop u_of calls (2 more sites)
    s = s.replace("            u, midx = u_of(mdl, i, mu, sd, 0.1, hard=True)",
                  "            u, midx, hst = u_of(mdl, i, mu, sd, 0.1, hard=True, H=HT)\n            if REC and hst[1] is not None:\n                HT = HT.index_put((hst[0],), hst[1].detach())", 1)
    a = '''        w = torch.zeros(NW, device=DEV); al = mdl.alpha()
        PRED_f = np.full((len(te), NW), np.nan, np.float32)'''
    b = '''        w = torch.zeros(NW, device=DEV); al = mdl.alpha()
        HT = torch.zeros(NW, 32, device=DEV) if REC else None
        PRED_f = np.full((len(te), NW), np.nan, np.float32)'''
    assert a in s; s = s.replace(a, b, 1)
    # PRED export inside test loop uses mdl.f directly — must use rec too
    a = '''                if i >= first_te:
                    a0, b0 = int(ST[i]), int(ST[i + 1])
                    x = torch.clamp((XT[a0:b0] - mu) / sd, -5, 5)
                    PRED_f[i - first_te, midx.cpu().numpy()] = mdl.f(torch.nan_to_num(x)).squeeze(-1).cpu().numpy()'''
    b = '''                if i >= first_te:
                    a0, b0 = int(ST[i]), int(ST[i + 1])
                    x = torch.clamp((XT[a0:b0] - mu) / sd, -5, 5)
                    if CTXA:
                        x = torch.cat([x, CTXT[i].expand(b0 - a0, 4)], 1)
                    if REC:
                        sc, _ = mdl.score_rec(torch.nan_to_num(x), HT[PST[a0:b0].long()])
                        PRED_f[i - first_te, midx.cpu().numpy()] = sc.cpu().numpy()
                    else:
                        PRED_f[i - first_te, midx.cpu().numpy()] = mdl.f(torch.nan_to_num(x)).squeeze(-1).cpu().numpy()'''
    assert a in s; s = s.replace(a, b, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    import ast; ast.parse(s); print("REC (架构B) patched")
else:
    print("already")

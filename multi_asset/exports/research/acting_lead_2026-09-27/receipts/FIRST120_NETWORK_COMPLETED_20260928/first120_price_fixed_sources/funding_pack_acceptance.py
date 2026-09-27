"""Reusable fail-closed acceptance of the completed, sealed input-only pack."""
import hashlib,json,pathlib
WORKER='5b9f69c6d2fb58cca060146f9a0dde118651c8e539fe0cb26ce7d20037543405'
GUARD='678cf8e117bbd301e20966ec4077e5f1088f96f4636e2d6b72db681b216e0755'
RESULT='2bc7bef5234e29782fbfd0010d8eef8af74a0f93b3b7c698e6c97bb995fcc65b'
TERMINAL='93556a6e0634f2f2a1e68ff109f34bacba1c5764e1a5b79e47f25fc9bf233624'
POSTVERIFY='b4dc7806158191b2a7926892806f44cd2bac4110de71e1fe0fbb7272b2c2285a'
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def terminal_gate(r,t,c):
    if t['status']!='COMPLETED' or t['returncode']!=0:raise ValueError('non-success terminal')
    if r['status']!='INPUT_PACK_ONLY_NO_FORWARD_NO_OPTIMIZER':raise ValueError('wrong pack scope')
    if r['source_sha256']!=WORKER or t['guard_source_sha256']!=GUARD:raise ValueError('unapproved source')
    if c['source_sha256']!={'funding_first120_input_pack.py':WORKER,'funding_first120_input_pack_guard.py':GUARD}:raise ValueError('command source mismatch')
    if r['cuda_initialized'] is not False:raise ValueError('input phase CUDA active')
    return True
def accept(root,verify_arrays=True):
    root=pathlib.Path(root);pack=root/'first120_input_pack_20260927';p=root/'first120_input_pack_postverify_20260927/POSTVERIFY.json'
    for file,h in ((pack/'RESULT.json',RESULT),(pack/'TERMINAL.json',TERMINAL),(p,POSTVERIFY)):
        if sha(file)!=h:raise ValueError('sealed receipt drift:'+str(file))
    r=json.loads((pack/'RESULT.json').read_text());t=json.loads((pack/'TERMINAL.json').read_text());c=json.loads((pack/'COMMAND.json').read_text());post=json.loads(p.read_text())
    terminal_gate(r,t,c)
    if sha(pack/'COMMAND.json')!=r['artifacts']['COMMAND.json']['sha256']:raise ValueError('command drift')
    if post['status']!='INPUT_IDENTITY_POSTVERIFY_PASS_NO_NETWORK' or post['original_result_sha256']!=RESULT or post['original_terminal_sha256']!=TERMINAL:raise ValueError('postverify identity')
    if verify_arrays:
        for n,v in r['artifacts'].items():
            if sha(pack/n)!=v['sha256']:raise ValueError('pack artifact drift:'+n)
    return {'status':'SEALED_PACK_TERMINAL_AND_IDENTITY_PASS','network_status':'RUN_NOT_STARTED','F0_strict_byte_identity':'UNRESOLVED','result_sha256':RESULT,'terminal_sha256':TERMINAL,'postverify_sha256':POSTVERIFY,'source_sha256':sha(__file__),'arrays_rehashed':verify_arrays}

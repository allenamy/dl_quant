"""Compiled-code identity of two versions of one module: compile both under the SAME filename and compare marshal bytes
(code objects incl. constants, names, docstrings, line tables). Equal => the interpreter executes the same code; only
comments/whitespace outside tokens can differ."""
import hashlib, marshal, sys
NL = b"\n"
a, b, name = sys.argv[1], sys.argv[2], sys.argv[3]
sa, sb = open(a, "rb").read(), open(b, "rb").read()
ca, cb = compile(sa, name, "exec", dont_inherit=True), compile(sb, name, "exec", dont_inherit=True)
ma, mb = marshal.dumps(ca), marshal.dumps(cb)
print(f"py={sys.version.split()[0]} src_sha_a={hashlib.sha256(sa).hexdigest()[:16]} src_sha_b={hashlib.sha256(sb).hexdigest()[:16]} "
      f"lines_a={sa.count(NL)} lines_b={sb.count(NL)} code_sha_a={hashlib.sha256(ma).hexdigest()[:16]} code_sha_b={hashlib.sha256(mb).hexdigest()[:16]}")
same = ma == mb and sa.count(NL) == sb.count(NL)
print("CODE_IDENTITY", "IDENTICAL" if same else "DIFFERENT")
sys.exit(0 if same else 1)

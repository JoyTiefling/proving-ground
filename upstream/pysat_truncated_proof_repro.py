"""Minimal repro: pysat get_proof() returns truncated DRUP proof on Windows."""
import sys, platform, itertools, pysat
from pysat.solvers import Glucose3, Glucose4, Glucose42, Minisat22, Cadical153, Lingeling
def php(n):  # pigeonhole: n+1 pigeons, n holes — UNSAT
    v = lambda p, h: p * n + h + 1
    f = [[v(p, h) for h in range(n)] for p in range(n + 1)]
    f += [[-v(p, h), -v(q, h)] for h in range(n) for p, q in itertools.combinations(range(n + 1), 2)]
    return f
print(platform.platform(), sys.version.split()[0], "pysat", pysat.__version__)
for n in (5, 7):
    for S in (Glucose3, Glucose4, Glucose42, Minisat22, Cadical153, Lingeling):
        try:
            with S(bootstrap_with=php(n), with_proof=True) as s:
                r = s.solve(); p = s.get_proof() or []
            print(f"PHP({n}) {S.__name__:11} solve={r} lines={len(p):6} last={p[-1].strip()!r:20} ends_with_empty_clause={bool(p) and p[-1].strip()=='0'}")
        except Exception as e:
            print(f"PHP({n}) {S.__name__:11} {type(e).__name__}: {e}")

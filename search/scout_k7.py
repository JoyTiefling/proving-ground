"""C-016 разведка k=7: где SAT ещё берётся с бюджетом. Один процесс, Idle."""
import ctypes, sys, json, time, pathlib
ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x40)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import probe_prefix_cover_odd as po
from pysat.solvers import Cadical153
K = 7; out = pathlib.Path(__file__).resolve().parent / "out" / "k7_scout.jsonl"
def valid(col, N):
    return not any(col[x] == col[y] == col[x+y] for x in range(1, N+1) for y in range(x+1, N+1-x))
for N in [int(a) for a in sys.argv[1:]]:
    f, var = po.cnf_odd(K, N); t0 = time.time()
    with Cadical153(bootstrap_with=f) as s:
        r = s.solve(); m = set(l for l in (s.get_model() or []) if l > 0) if r else None
    rec = {"N": N, "sat": r, "s": round(time.time()-t0, 1), "clauses": len(f)}
    if r:
        col = {}
        for v in range(1, N+1):
            o = v
            while o % 2 == 0: o //= 2
            col[v] = next(c for c in range(K) if var(o, c) in m)
        rec["gate_own"] = valid(col, N); rec["witness"] = [col[v] for v in range(1, N+1)]
    with open(out, "a") as fh: fh.write(json.dumps(rec) + "\n")
    print({k: v for k, v in rec.items() if k != "witness"}, flush=True)
    if not r: break

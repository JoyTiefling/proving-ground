"""Probe: where does naive backtracking die on the SAT side?

Times find_partition(k, N) for increasing N. This measures the ceiling of the
exhaustive search before we need a smarter attack (hill-climbing / GA / SAT).
WS(5) lower bound is ~196 — naive backtracking is not expected to reach it;
this quantifies *how far* it gets, as an honest data point.
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import find_partition, verify_weak_schur  # noqa

def probe(k, Ns, time_budget=90.0):
    print(f"naive backtracking ceiling, k={k}")
    for N in Ns:
        t0 = time.time()
        part = find_partition(k, N)
        dt = time.time() - t0
        if part is not None:
            ok, _ = verify_weak_schur(part, N)
            print(f"  N={N:4d}  SAT   {dt:7.2f}s  gate={'PASS' if ok else 'FAIL'}")
        else:
            print(f"  N={N:4d}  UNSAT {dt:7.2f}s")
        if dt > time_budget:
            print(f"  >> exceeded {time_budget}s budget at N={N}; naive ceiling here.")
            break

if __name__ == "__main__":
    # k=4 known WS(4)=66. Probe SAT side scaling toward and at the known value.
    probe(4, [40, 50, 58, 64, 66])

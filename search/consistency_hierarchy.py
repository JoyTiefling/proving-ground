"""
Consistency hierarchy as an impossibility method.

SAC (depth-1 failed-literal) proved k=2 impossible but stalled at k=3,4. Test
whether NESTED consistency scales: depth-d means "an assignment is removed if,
after it, the remaining problem is not depth-(d-1) consistent."

If depth-2 cracks k=3, depth-3 cracks k=4, the law "depth k-1 proves WS(k)+1
impossible" holds -> depth-4 would prove WS(5)=197 impossible (a real method,
if computable). Measure where each k falls.
"""
import sys, os, time
from sac import build_triples, unit_prop  # noqa


def consistent(allowed, tof, depth, deadline):
    if not unit_prop(allowed, tof):
        return False
    if depth == 0 or time.time() > deadline:
        return True
    changed = True
    while changed:
        changed = False
        for n in range(1, len(allowed)):
            if len(allowed[n]) <= 1:
                continue
            if time.time() > deadline:
                return True
            for c in list(allowed[n]):
                if len(allowed[n]) == 1:
                    break
                trial = [set(s) for s in allowed]
                trial[n] = {c}
                if not consistent(trial, tof, depth - 1, deadline):
                    allowed[n].discard(c)
                    changed = True
                    if not allowed[n]:
                        return False
                    if not unit_prop(allowed, tof):
                        return False
    return True


def prove(N, k, depth, budget=120):
    tof = [[] for _ in range(N + 1)]
    for tr in build_triples(N):
        for e in tr:
            tof[e].append(tr)
    allowed = [set(range(k)) for _ in range(N + 1)]
    allowed[0] = set()
    allowed[1] = {0}
    t0 = time.time()
    ok = consistent(allowed, tof, depth, t0 + budget)
    dt = time.time() - t0
    if time.time() > t0 + budget and ok:
        return "TIMEOUT", dt
    return ("UNSAT" if not ok else "STALL"), dt


if __name__ == "__main__":
    cases = [(2, 9, 1), (3, 24, 2), (4, 67, 3)]
    print("Testing the law: does depth (k-1) prove WS(k)+1 impossible?\n")
    for k, N, depth in cases:
        status, dt = prove(N, k, depth, budget=180)
        verdict = "PROVES impossibility" if status == "UNSAT" else status
        print(f"  k={k}, N={N}, depth={depth}: {verdict}  ({dt:.1f}s)", flush=True)

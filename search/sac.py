"""
Stronger forcing: Singleton Arc Consistency (failed-literal) on weak-Schur.

Unit propagation found nothing (no local obstruction). SAC is stronger: for each
element n and candidate color c, tentatively set n=c and unit-propagate; if that
yields a contradiction, c is impossible for n -> remove it. Iterate to fixpoint.

- SAC proves a known-impossible case UNSAT  -> a POLYNOMIAL impossibility
  certificate; scale it to 197 (would be a real method).
- SAC stalls on small impossible cases -> the obstruction is deeper than any
  local consistency can see; impossibility is irreducibly global. Measured.
"""
import sys, os, time


def build_triples(N):
    t = []
    for a in range(1, N + 1):
        for b in range(a + 1, N + 1):
            c = a + b
            if c > N:
                break
            t.append((a, b, c))
    return t


def unit_prop(allowed, tof):
    """Propagate; return False on contradiction. tof: element -> triples."""
    queue = [n for n in range(1, len(allowed)) if len(allowed[n]) == 1]
    while queue:
        n = queue.pop()
        for (a, b, c) in tof[n]:
            for x, y, z in ((a, b, c), (a, c, b), (b, c, a)):
                if len(allowed[x]) == 1 and len(allowed[y]) == 1:
                    cx = next(iter(allowed[x]))
                    if cx == next(iter(allowed[y])) and cx in allowed[z]:
                        allowed[z].discard(cx)
                        if not allowed[z]:
                            return False
                        if len(allowed[z]) == 1:
                            queue.append(z)
    return True


def sac(N, k, deadline=None):
    triples = build_triples(N)
    tof = [[] for _ in range(N + 1)]
    for tr in triples:
        for e in tr:
            tof[e].append(tr)
    allowed = [set(range(k)) for _ in range(N + 1)]
    allowed[0] = set()
    allowed[1] = {0}
    if not unit_prop(allowed, tof):
        return "UNSAT", 0
    changed = True
    while changed:
        changed = False
        for n in range(1, N + 1):
            if deadline and time.time() > deadline:
                return "TIMEOUT", sum(1 for q in range(1, N + 1) if len(allowed[q]) == 1)
            for c in list(allowed[n]):
                if len(allowed[n]) == 1:
                    break
                trial = [set(s) for s in allowed]
                trial[n] = {c}
                if not unit_prop(trial, tof):
                    allowed[n].discard(c)
                    changed = True
                    if not allowed[n]:
                        return "UNSAT", 0
                    if not unit_prop(allowed, tof):
                        return "UNSAT", 0
    forced = sum(1 for n in range(1, N + 1) if len(allowed[n]) == 1)
    return "STALL", forced


if __name__ == "__main__":
    print("Singleton Arc Consistency probe (symmetry: 1 -> color 0):\n")
    for k, v in [(2, 8), (3, 23), (4, 66)]:
        status, info = sac(v + 1, k)
        tag = "UNSAT by SAC!" if status == "UNSAT" else f"STALL ({info}/{v+1} forced)"
        print(f"  k={k}, N={v+1} (impossible): {tag}")

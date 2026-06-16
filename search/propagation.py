"""
Into the impossible: study the STRUCTURE of impossibility via constraint
propagation (forcing), not search.

Each weak triple (a, b, a+b) forbids all three sharing a color. Fix element 1's
color by symmetry, then propagate: whenever two members of a triple are forced
to the same color, the third cannot take it. Iterate to a fixpoint.

- If some element's allowed set empties -> impossibility PROVEN by pure forcing
  (a human-readable obstruction, no branching).
- If it stalls -> measure how much got forced before freedom remained; that is
  the "depth" to which the obstruction reaches without search.

Run on the known-impossible thresholds [1, WS(k)+1] for k=2,3,4 and on 197.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))


def build_triples(N):
    t = []
    for a in range(1, N + 1):
        for b in range(a + 1, N + 1):
            c = a + b
            if c > N:
                break
            t.append((a, b, c))
    return t


def propagate(N, k, fixed=None):
    allowed = [set(range(k)) for _ in range(N + 1)]
    allowed[0] = set()
    allowed[1] = {0}                  # symmetry: element 1 -> color 0
    if fixed:
        for n, c in fixed.items():
            allowed[n] = {c}
    triples = build_triples(N)
    changed = True
    steps = 0
    while changed:
        changed = False
        steps += 1
        for (a, b, c) in triples:
            for x, y, z in ((a, b, c), (a, c, b), (b, c, a)):
                if len(allowed[x]) == 1 and len(allowed[y]) == 1:
                    cx = next(iter(allowed[x]))
                    if cx == next(iter(allowed[y])) and cx in allowed[z]:
                        allowed[z].discard(cx)
                        changed = True
                        if not allowed[z]:
                            return "UNSAT", steps, sum(1 for q in range(1, N + 1) if len(allowed[q]) == 1), z
    forced = sum(1 for n in range(1, N + 1) if len(allowed[n]) == 1)
    return "STALL", steps, forced, None


if __name__ == "__main__":
    print("Pure-forcing impossibility probe (symmetry: 1 -> color 0):\n")
    for k, v in [(2, 8), (3, 23), (4, 66)]:
        res = propagate(v + 1, k)
        status, steps, forced, where = res
        tag = (f"UNSAT by forcing! (element {where} emptied)" if status == "UNSAT"
               else f"STALL: {forced}/{v+1} elements forced, rest free")
        print(f"  k={k}, N={v+1} (should be impossible): {tag}  [{steps} sweeps]")
    print()
    for k, N in [(5, 196), (5, 197)]:
        status, steps, forced, where = propagate(N, k)
        tag = (f"UNSAT by forcing! (element {where})" if status == "UNSAT"
               else f"STALL: {forced}/{N} forced ({100*forced//N}%), rest free")
        print(f"  k={k}, N={N}: {tag}  [{steps} sweeps]")

"""
Probe G -- can |D| (the doubling set {d : f(d)=f(2d)}) be made LARGE?

The whole upper-bound lever rests on: is max|D| over all valid weak-sum-free
k-colourings bounded by a constant (independent of N)? Boundary colourings show
|D|~10, but they are one family (common seed). Here we ADVERSARIALLY try to
maximise |D|: a greedy that PREFERS doublings (even v -> same colour as v/2),
plus the extreme "all-doublings" construction (colour v by its odd part, so
f(v)=f(2v) for EVERY v -> |D| would be N/2 if it stays valid).

If we can keep |D| ~ N/2 valid to large N -> hypothesis DEAD (|D| unbounded).
If |D| stubbornly caps even when we optimise FOR it -> hypothesis supported,
and the cap tells us the real constraint.
"""
import sys


def wsf_ok_add(cls, v):
    for a in cls:
        if a < v and (v - a) in cls and (v - a) != a:
            return False
        if (v + a) in cls:
            return False
    return True


def greedy_prefer_doublings(k, N):
    color = {}
    cls = [set() for _ in range(k)]
    for v in range(1, N + 1):
        order = []
        if v % 2 == 0 and (v // 2) in color:
            order.append(color[v // 2])            # try to double first
        order += [c for c in range(k) if c not in order]
        placed = False
        for c in order:
            if wsf_ok_add(cls[c], v):
                color[v] = c; cls[c].add(v); placed = True; break
        if not placed:
            return v - 1, color
    return N, color


def all_doublings(k, N):
    """Colour v by its odd part -> f(v)=f(2v) ALWAYS. Greedily colour odd roots;
    fail at first odd number whose whole chain can't fit any colour validly."""
    color = {}
    cls = [set() for _ in range(k)]
    odds = [m for m in range(1, N + 1, 2)]
    for m in odds:
        chain = []
        x = m
        while x <= N:
            chain.append(x); x *= 2
        placed = False
        for c in range(k):
            ok = True
            tmp = set(cls[c])
            for e in chain:
                if not wsf_ok_add(tmp, e):
                    ok = False; break
                tmp.add(e)
            if ok:
                for e in chain:
                    color[e] = c; cls[c].add(e)
                placed = True; break
        if not placed:
            return m, color, cls            # all-doublings breaks at odd root m
    return None, color, cls


def count_D(color, N):
    return sum(1 for d in range(1, N // 2 + 1)
               if d in color and 2 * d in color and color[d] == color[2 * d])


if __name__ == "__main__":
    k = 5
    print("== greedy PREFER-doublings: |D| vs N ==", flush=True)
    for N in [100, 130, 150, 175, 196, 220, 260]:
        maxN, color = greedy_prefer_doublings(k, N)
        D = count_D(color, maxN)
        print(f"  N target {N}: valid up to {maxN}, |D|={D}  (boundary family ~10)", flush=True)

    print("\n== ALL-doublings (colour by odd part, f(v)=f(2v) for all v) ==", flush=True)
    for N in [40, 60, 80, 100, 130, 160, 196]:
        broke, color, cls = all_doublings(k, N)
        if broke is None:
            D = count_D(color, N)
            print(f"  N={N}: ALL-DOUBLINGS VALID (|D|={D}=N/2) -> hypothesis FALSIFIED", flush=True)
        else:
            placed = sum(len(c) for c in cls)
            print(f"  N={N}: all-doublings BREAKS at odd root {broke} "
                  f"(placed {placed}/{N} before fail)", flush=True)

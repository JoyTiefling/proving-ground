"""
Zero-search construction: first-fit greedy coloring.

No search at all — pure construction. Assign n = 1,2,3,... to the FIRST color
that does not create a weak-Schur triple. Since n is the new maximum, the only
new triples are pairs (a, n-a) with a < n-a; so n may join color c iff c holds
no such pair. Report the largest N reachable per k.

This is the cheapest possible probe and a completely different lane from search.
If first-fit reaches near the records, the greedy spine IS the construction and
we only need to study the obstruction points where it stalls.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa


def first_fit(k, Nmax, order_colors=None):
    parts = [set() for _ in range(k)]
    color = [0] * (Nmax + 1)
    for n in range(1, Nmax + 1):
        placed = False
        cols = range(k) if order_colors is None else order_colors
        for c in cols:
            ok = True
            a = 1
            while a * 2 < n:  # a < n-a strict (weak: 2a allowed)
                if a in parts[c] and (n - a) in parts[c]:
                    ok = False
                    break
                a += 1
            if ok:
                parts[c].add(n); color[n] = c; placed = True
                break
        if not placed:
            return n - 1, [sorted(p) for p in parts]
    return Nmax, [sorted(p) for p in parts]


if __name__ == "__main__":
    print("first-fit greedy reach vs known records:")
    records = {1: 2, 2: 8, 3: 23, 4: 66, 5: 196}
    for k in range(1, 8):
        N, parts = first_fit(k, 5000)
        rec = records.get(k)
        gap = f"  (record {rec}, gap {rec - N:+d})" if rec else "  (record: unknown)"
        # verify the greedy partition is actually valid up to N
        ok, reason = verify_weak_schur([p for p in parts if p], N) if N > 0 else (True, None)
        print(f"  k={k}: first-fit reaches N={N}{gap}   gate={'PASS' if ok else 'FAIL ' + str(reason)}")

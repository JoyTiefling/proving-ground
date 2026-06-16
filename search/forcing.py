"""
Pruning idea: are weak-Schur threshold colorings FORCED?

If most of the structure is forced (rigid), a search can fix the forced backbone
and branch only on the few free elements -> the search collapses from N elements
to a handful. This is "find the pattern -> prune", not brute force.

Rigidity measure (symmetry-invariant): for each pair (i,j), is it forced-same
or forced-different across ALL solutions? Fraction forced = rigidity. High
rigidity at the threshold => backbone-forcing pruning is viable. We must check
whether it SURVIVES at k=4 (where the solution count explodes) or was a small-k
artifact.
"""
import sys


def enumerate_solutions(N, k, cap=200000):
    color = [0] * (N + 1)
    sols = []

    def ok(z, c):
        x = 1
        while 2 * x < z:
            if color[x] == c and color[z - x] == c:
                return False
            x += 1
        return True

    def bt(v):
        if len(sols) >= cap:
            return
        if v > N:
            sols.append(tuple(color[1:N + 1]))
            return
        up = 1 if v == 1 else k
        for c in range(up):
            if ok(v, c):
                color[v] = c
                bt(v + 1)
                color[v] = 0
    bt(1)
    return sols


def rigidity(sols, N):
    forced = 0
    total = 0
    free_elems = set()
    for i in range(1, N + 1):
        for j in range(i + 1, N + 1):
            total += 1
            same = [s[i - 1] == s[j - 1] for s in sols]
            if all(same) or not any(same):
                forced += 1
            else:
                free_elems.add(i)
                free_elems.add(j)
    return forced / total, sorted(free_elems)


if __name__ == "__main__":
    for (N, k) in [(8, 2), (23, 3)]:
        sols = enumerate_solutions(N, k)
        capped = len(sols) >= 200000
        r, free = rigidity(sols, N)
        print(f"WS({k})={N}: {len(sols)}{'+ (capped)' if capped else ''} solutions, "
              f"rigidity {r:.1%} forced; free elements ({len(free)}): {free}", flush=True)

"""
Covering design GATE — the trust anchor for the new track.

C(v,k,t): minimum number of k-subsets of a v-set such that every t-subset is
contained in at least one. We attack the upper bound (find a small covering);
the gate confirms a candidate is a VALID covering. No claim without it.

Schönheim bound L(v,k,t) is the standard lower bound. A "gap" instance is one
where best-known size > L(v,k,t): room to improve. Beating the recorded
best-known size = a real, verifiable result.
"""
from itertools import combinations
from math import ceil


def schonheim(v, k, t):
    """Schönheim lower bound, recursive: L(v,k,1)=ceil(v/k);
    L(v,k,t)=ceil(v/k * L(v-1,k-1,t-1))."""
    if t == 0:
        return 1
    if t == 1:
        return ceil(v / k)
    return ceil((v / k) * schonheim(v - 1, k - 1, t - 1))


def verify_covering(blocks, v, t, base=0):
    """blocks: iterable of k-subsets over a v-set labelled base..base+v-1.
    Returns (ok, num_uncovered, example_uncovered)."""
    elems = list(range(base, base + v))
    needed = set(combinations(elems, t))
    for b in blocks:
        for s in combinations(sorted(b), t):
            needed.discard(s)
    if needed:
        return False, len(needed), next(iter(needed))
    return True, 0, None


if __name__ == "__main__":
    # self-test: Schönheim values + a trivial valid/invalid covering
    print("Schönheim spot-checks (against scout's worked examples):")
    for (v, k, t, exp) in [(7, 4, 3, 11), (10, 3, 2, 17), (5, 2, 1, 3),
                           (6, 3, 2, 6), (29, 5, 2, 41), (11, 5, 3, 18), (13, 5, 3, 32)]:
        got = schonheim(v, k, t)
        print(f"  L({v},{k},{t}) = {got}  {'OK' if got == exp else 'MISMATCH exp ' + str(exp)}")

    # gate sanity: a complete covering (all k-subsets) must cover everything
    v, k, t = 6, 3, 2
    allk = list(combinations(range(v), k))
    ok, miss, _ = verify_covering(allk, v, t)
    print(f"\n  all C(6,3) triples cover all pairs: {'PASS' if ok else 'FAIL'}")
    # negative: a single block can't cover all pairs of 6 elements
    ok2, miss2, ex = verify_covering([tuple(range(k))], v, t)
    print(f"  single block leaves pairs uncovered: {'correctly INVALID' if not ok2 else 'WRONG'} ({miss2} uncovered)")

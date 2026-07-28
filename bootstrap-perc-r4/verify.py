"""
r-neighbor bootstrap percolation on the d-dimensional hypercube Q_d.

Vertex encoding: integers 0..2^d - 1. Vertex v in binary == coordinate.
Adjacency: u ~ v iff popcount(u XOR v) == 1.
Process:
    repeat until stable: any uninfected vertex with >= r infected
    neighbors becomes infected.
Percolation: S percolates Q_d if final infected set == V(Q_d).

Open: m(Q_d, 4) = min |S| that percolates Q_d under r=4.
Solved (sanity checks here):
    r=2:  m(Q_d, 2) = ceil(d/2) + 1
    r=3:  m(Q_d, 3) = ceil(d(d+3)/6) + 1
Conjecture: m(Q_d, 4) ~ (1/4) * C(d, 3).
"""

from math import ceil


def neighbors(v: int, d: int):
    """Neighbors of v in Q_d."""
    for i in range(d):
        yield v ^ (1 << i)


def percolates(seed: frozenset, d: int, r: int) -> bool:
    """True iff seed percolates Q_d under r-neighbor bootstrap."""
    infected = set(seed)
    N = 1 << d
    while True:
        new = set()
        for v in range(N):
            if v in infected:
                continue
            cnt = sum(1 for u in neighbors(v, d) if u in infected)
            if cnt >= r:
                new.add(v)
        if not new:
            return len(infected) == N
        infected |= new


def m_known(d: int, r: int) -> int:
    """Known formulas."""
    if r == 2:
        return ceil(d / 2) + 1
    if r == 3:
        return ceil(d * (d + 3) / 6) + 1
    raise ValueError(f"no closed form for r={r}")


# -------------------- Sanity checks --------------------

def sanity_r2():
    """r=2: build an explicit percolating set of size m_known(d, 2) and verify.

    Construction (cross of basis vectors + origin and antipode style):
      For Q_d, take {0, 1, e_1+1, e_2+1, ..., e_{d-2}+1} — d-1 = ceil(d/2)+1?
      No, simpler: known is "antipodal pair + spread". Easiest robust check:
      brute-force search over all subsets of size m_known(d, 2) — confirm
      at least one percolates AND no subset of size m_known(d, 2) - 1 does.
      We do this for small d only.
    """
    from itertools import combinations
    results = []
    for d in [2, 3, 4]:
        m = m_known(d, 2)
        N = 1 << d
        # search up
        found_at_m = False
        for seed in combinations(range(N), m):
            if percolates(frozenset(seed), d, 2):
                found_at_m = True
                witness = seed
                break
        # search down (no smaller works)
        none_at_m_minus_1 = True
        if m >= 1:
            for seed in combinations(range(N), m - 1):
                if percolates(frozenset(seed), d, 2):
                    none_at_m_minus_1 = False
                    break
        results.append((d, m, found_at_m, none_at_m_minus_1, witness if found_at_m else None))
    return results


def sanity_r3():
    """r=3: same brute-force minimality check for small d."""
    from itertools import combinations
    results = []
    for d in [3, 4]:  # d=5 has C(32, 7) ≈ 3.4M which is slow but feasible
        m = m_known(d, 3)
        N = 1 << d
        found_at_m = False
        witness = None
        for seed in combinations(range(N), m):
            if percolates(frozenset(seed), d, 3):
                found_at_m = True
                witness = seed
                break
        # smaller doesn't work
        none_at_m_minus_1 = True
        if m >= 1:
            for seed in combinations(range(N), m - 1):
                if percolates(frozenset(seed), d, 3):
                    none_at_m_minus_1 = False
                    break
        results.append((d, m, found_at_m, none_at_m_minus_1, witness))
    return results


def sanity_r4_d4():
    """r=4, d=4 (boundary case r=d).

    Analytic argument (Joy, 2026-07-11): when r=d, every uninfected vertex
    percolates only when ALL d neighbors are infected. Two adjacent uninfected
    vertices block each other forever (each has >=1 uninfected neighbor).
    Therefore S percolates Q_d under r=d  iff  V minus S is an independent set.
    Max independent set in Q_d is one bipartite class, size 2^(d-1).
    Hence m(Q_d, d) = 2^d - 2^(d-1) = 2^(d-1).
    For d=4:  m = 8.

    We verify by:
      (a) constructing S = {v : popcount(v) even} of size 8 and checking it
          percolates in one step;
      (b) brute-forcing all C(16, 7) = 11440 size-7 subsets — none percolates.
    """
    from itertools import combinations

    d, r = 4, 4
    N = 1 << d
    m_conjectured = 1 << (d - 1)  # 8

    # (a) explicit witness — even-popcount bipartite class
    S_witness = frozenset(v for v in range(N) if bin(v).count("1") % 2 == 0)
    assert len(S_witness) == m_conjectured, len(S_witness)
    percolates_at_m = percolates(S_witness, d, r)

    # (b) minimality — brute force size m-1
    m_minus_1 = m_conjectured - 1
    none_at_m_minus_1 = True
    counterexample_at_m_minus_1 = None
    for seed in combinations(range(N), m_minus_1):
        if percolates(frozenset(seed), d, r):
            none_at_m_minus_1 = False
            counterexample_at_m_minus_1 = seed
            break

    return {
        "d": d,
        "r": r,
        "m_conjectured": m_conjectured,
        "witness_percolates": percolates_at_m,
        "witness": tuple(sorted(S_witness)),
        "none_at_m_minus_1": none_at_m_minus_1,
        "counterexample_at_m_minus_1": counterexample_at_m_minus_1,
    }


if __name__ == "__main__":
    print("== r=2 sanity ==")
    for d, m, up, down, w in sanity_r2():
        print(f"  d={d}: m_known={m}, exists at m? {up}, none at m-1? {down}, witness={w}")
    print("== r=3 sanity ==")
    for d, m, up, down, w in sanity_r3():
        print(f"  d={d}: m_known={m}, exists at m? {up}, none at m-1? {down}, witness={w}")
    print("== r=4 d=4 boundary case (r=d) ==")
    res = sanity_r4_d4()
    print(f"  d={res['d']} r={res['r']}: conjecture m = 2^(d-1) = {res['m_conjectured']}")
    print(f"    witness (even-popcount bipartite class) percolates? {res['witness_percolates']}")
    print(f"    witness = {res['witness']}")
    print(f"    no size-{res['m_conjectured']-1} set percolates? {res['none_at_m_minus_1']}")
    if not res['none_at_m_minus_1']:
        print(f"    counterexample: {res['counterexample_at_m_minus_1']}")

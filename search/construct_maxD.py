"""
Constructive lower bound on max|D| for WSF k-coloring of [1..N].

Angle, not hammer. Sanya calibration: не молоть SAT-hours, попробовать явную
конструкцию. Если сохранять цепи-удвоений {m, 2m, 4m, ...} целиком в одном
цвете, каждая цепь длины L даёт L-1 doubling pairs. Sum over all chains for
N=150: 75 = N/2 (trivial ceiling). Task = pack chains into k colors without
weak-Schur violations.

Weak-Schur violation between chains {m1·2^i} and {m2·2^j} in same color:
exists a<b<z all in color with a+b=z (a=b allowed = it's weak).

Method: greedy. For each odd m in 1..N//2, try to add its chain to an existing
color that doesn't create a WSF violation. If no color works, open a new one.
If more than k colors needed, fail. Report best_D achieved.

Pre-registration (negative control before running):
  H_pack (alpha~0.5): find valid 5-coloring with |D| >= 50
  H_conflict (alpha~0.25): stuck at |D| < 40 due to chain conflicts
  H_hard (log): can't exceed 20 (already refuted — SAT reached 36 on N=150)

This is a lower bound on max|D|. SAT-measured lower bound is 36 on N=150.
If greedy beats 36, we advance the bound without SAT-hours. If greedy hits
<36, negative — chains don't pack (all-doublings blocks earlier).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur


def chain_of(m: int, N: int):
    """Doubling chain starting at odd m: {m, 2m, 4m, ...} intersected with [1..N]."""
    out = []
    v = m
    while v <= N:
        out.append(v)
        v *= 2
    return out


def has_wsf_violation(color_set: set, new_chain: list) -> bool:
    """Would adding new_chain to color_set create a weak-Schur violation?
    Weak-SF: no a<b<z in same color with a+b=z (a=b allowed)."""
    combined = color_set | set(new_chain)
    combined_list = sorted(combined)
    n = len(combined_list)
    combined_set_local = set(combined_list)
    # For every a<=b in combined, check if a+b (a<b required) is also in combined.
    # a=b (i.e. 2a=z) is weakly OK.
    for i in range(n):
        a = combined_list[i]
        # a=a: 2a=z is allowed, skip
        for j in range(i + 1, n):
            b = combined_list[j]
            z = a + b
            if z in combined_set_local:
                return True
            # Early exit if z exceeds max
            if z > combined_list[-1]:
                break
    return False


def count_doublings(color_set: set, N: int) -> int:
    """Count |D| contribution: pairs (d, 2d) both in color_set with d <= N/2."""
    return sum(1 for d in range(1, N // 2 + 1)
               if d in color_set and 2 * d in color_set)


def greedy_construct(N: int, k: int, order: str = "long_first"):
    """Greedy chain-packing. Returns (parts, |D|, chains_placed, chains_total)
    or (None, 0, placed, total) if fails to fit within k colors."""
    # Collect chains
    odds = [m for m in range(1, N + 1, 2)]
    chains = [(m, chain_of(m, N)) for m in odds]
    if order == "long_first":
        chains.sort(key=lambda mc: -len(mc[1]))
    elif order == "short_first":
        chains.sort(key=lambda mc: len(mc[1]))
    elif order == "smallest_first":
        chains.sort(key=lambda mc: mc[0])
    # else natural order

    color_sets = [set() for _ in range(k)]
    placed = 0
    for m, chain in chains:
        # Try each color that doesn't violate WSF
        placed_here = False
        for c in range(k):
            if not has_wsf_violation(color_sets[c], chain):
                color_sets[c].update(chain)
                placed_here = True
                placed += 1
                break
        if not placed_here:
            # No color accepts this chain — split policy: skip (contributes 0)
            # But then some numbers in chain are unassigned. For a full WSF
            # coloring of [1..N] we must assign every v. Fall back to
            # single-elements: place each v in first color that accepts {v}.
            for v in chain:
                assigned = False
                for c in range(k):
                    if not has_wsf_violation(color_sets[c], [v]):
                        color_sets[c].add(v)
                        assigned = True
                        break
                if not assigned:
                    return (None, 0, placed, len(chains))

    parts = [sorted(s) for s in color_sets]
    D_total = sum(count_doublings(s, N) for s in color_sets)
    return (parts, D_total, placed, len(chains))


def main():
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    for order in ("long_first", "short_first", "smallest_first", "natural"):
        parts, D, placed, total = greedy_construct(N, k, order=order)
        if parts is None:
            print(f"[order={order}] FAIL — {placed}/{total} chains placed, then stuck")
            continue
        ok, reason = verify_weak_schur(parts, N)
        gate = "PASS" if ok else f"FAIL {reason}"
        cover = sum(len(p) for p in parts)
        print(f"[order={order}] |D|={D}  chains_whole={placed}/{total}  "
              f"cover={cover}/{N}  gate={gate}  sizes={[len(p) for p in parts]}")


if __name__ == "__main__":
    main()

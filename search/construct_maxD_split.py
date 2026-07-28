"""
Chain-splitting greedy for max|D| WSF k-coloring of [1..N].

Extension of construct_maxD.py: if a doubling chain doesn't fit whole in any
color, try splitting it into 2 parts (costs 1 doubling — the break point) and
placing each part in a different color. If 1 split fails, try 2 splits (3 parts).

Rationale: morning 16-07 attempt with whole chains: all 4 orders FAILED to
5-color [1..150] (long chains block short chains, single-element fallback stuck).
Split greedy trades some doublings for placement feasibility.

PRE-REGISTRATION (before running, per #2866 razor):
  H_split_helps    (alpha ~0.3): 1-split greedy places all chains, |D| >= 40
  H_split_partial  (alpha ~0.4): partial success, |D| < 36 or incomplete cover
  H_split_no_gain  (alpha ~0.2): 1 split doesn't free conflicts (structural)
  H_split_needs_2  (alpha ~0.1): 1 split insufficient, 2 splits help

Positive control: max_splits=0 must reproduce morning FAIL exactly.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur


def chain_of(m: int, N: int):
    out = []
    v = m
    while v <= N:
        out.append(v)
        v *= 2
    return out


def has_wsf_violation(color_set: set, new_elems) -> bool:
    """Weak-SF: no a<b<z in same color with a+b=z (a=b is weakly allowed)."""
    combined = color_set | set(new_elems)
    combined_list = sorted(combined)
    n = len(combined_list)
    for i in range(n):
        a = combined_list[i]
        for j in range(i + 1, n):
            b = combined_list[j]
            z = a + b
            if z in combined:
                return True
            if z > combined_list[-1]:
                break
    return False


def count_doublings(color_set: set, N: int) -> int:
    return sum(1 for d in range(1, N // 2 + 1)
               if d in color_set and 2 * d in color_set)


def _try_place_parts(parts_list, color_sets, k):
    """Assign each part in parts_list to a distinct color without WSF violation.
    Returns list of (color, part) if success, None if not.
    Uses backtracking over color assignments."""
    P = len(parts_list)
    assignment = [-1] * P
    # Snapshot to allow rollback
    snapshots = [set(cs) for cs in color_sets]

    def backtrack(idx):
        if idx == P:
            return True
        part = parts_list[idx]
        for c in range(k):
            # Distinct colors between parts of same original chain — enforce.
            if c in assignment[:idx]:
                continue
            if has_wsf_violation(color_sets[c], part):
                continue
            color_sets[c].update(part)
            assignment[idx] = c
            if backtrack(idx + 1):
                return True
            # rollback this part from color c
            for v in part:
                color_sets[c].discard(v)
            assignment[idx] = -1
        return False

    ok = backtrack(0)
    if ok:
        return list(assignment)
    # Restore snapshots
    for i in range(k):
        color_sets[i] = snapshots[i]
    return None


def _splits_of_chain(chain, num_splits):
    """Yield all ways to split chain into (num_splits+1) contiguous non-empty parts."""
    L = len(chain)
    if num_splits + 1 > L:
        return
    # positions[i] is split index (1..L-1), strictly increasing
    def gen(start, positions):
        if len(positions) == num_splits:
            cuts = [0] + list(positions) + [L]
            parts = [chain[cuts[i]:cuts[i+1]] for i in range(len(cuts)-1)]
            yield parts
            return
        for p in range(start, L):
            yield from gen(p + 1, positions + [p])
    yield from gen(1, [])


def try_place_chain(chain, color_sets, k, max_splits):
    """Place chain using 0..max_splits splits. Returns splits_used or -1."""
    # 0 splits: whole
    for c in range(k):
        if not has_wsf_violation(color_sets[c], chain):
            color_sets[c].update(chain)
            return 0
    # 1..max_splits
    for s in range(1, max_splits + 1):
        for parts in _splits_of_chain(chain, s):
            result = _try_place_parts(parts, color_sets, k)
            if result is not None:
                # Actually the _try_place_parts already mutates color_sets on success
                return s
    return -1


def greedy_construct_split(N: int, k: int, order: str = "long_first",
                            max_splits: int = 1, verbose: bool = False):
    odds = [m for m in range(1, N + 1, 2)]
    chains = [(m, chain_of(m, N)) for m in odds]
    if order == "long_first":
        chains.sort(key=lambda mc: -len(mc[1]))
    elif order == "short_first":
        chains.sort(key=lambda mc: len(mc[1]))
    elif order == "smallest_first":
        chains.sort(key=lambda mc: mc[0])

    color_sets = [set() for _ in range(k)]
    placed_whole = 0
    placed_split = {s: 0 for s in range(1, max_splits + 1)}
    failed_chains = []

    for m, chain in chains:
        splits_used = try_place_chain(chain, color_sets, k, max_splits)
        if splits_used == 0:
            placed_whole += 1
            if verbose:
                print(f"  chain m={m} L={len(chain)}: WHOLE")
        elif splits_used > 0:
            placed_split[splits_used] += 1
            if verbose:
                print(f"  chain m={m} L={len(chain)}: {splits_used} split(s)")
        else:
            failed_chains.append((m, chain))
            if verbose:
                print(f"  chain m={m} L={len(chain)}: FAIL — fallback to single-elements")
            # Fallback: single elements
            for v in chain:
                assigned = False
                for c in range(k):
                    if not has_wsf_violation(color_sets[c], [v]):
                        color_sets[c].add(v)
                        assigned = True
                        break
                if not assigned:
                    if verbose:
                        print(f"  STUCK: chain m={m}, element v={v} fits nowhere")
                    return (None, 0, placed_whole, placed_split, failed_chains, len(chains))

    parts = [sorted(s) for s in color_sets]
    D_total = sum(count_doublings(s, N) for s in color_sets)
    return (parts, D_total, placed_whole, placed_split, failed_chains, len(chains))


def _finish_with_singles(color_sets, remaining_chains, N, k, verbose=False):
    """Given partial color_sets, place all elements of remaining_chains
    as singles (chain structure abandoned). Returns True if all placed."""
    all_elems = []
    for m, chain in remaining_chains:
        all_elems.extend(chain)
    # Sort by descending magnitude — big first often causes fewer future violations
    # But magnitude-based conflicts vary. Try both orders, keep whichever works.
    for order_name, elems in [("desc", sorted(all_elems, reverse=True)),
                               ("asc", sorted(all_elems))]:
        snapshot = [set(cs) for cs in color_sets]
        stuck_at = None
        for v in elems:
            assigned = False
            for c in range(k):
                if not has_wsf_violation(color_sets[c], [v]):
                    color_sets[c].add(v)
                    assigned = True
                    break
            if not assigned:
                stuck_at = v
                break
        if stuck_at is None:
            if verbose:
                print(f"  finish_singles({order_name}): all {len(elems)} placed")
            return True
        # Restore snapshot
        for i in range(k):
            color_sets[i] = snapshot[i]
        if verbose:
            print(f"  finish_singles({order_name}): stuck at v={stuck_at}")
    return False


def greedy_constraint_first(N: int, k: int, max_splits: int = 1,
                             tiebreak: str = "long", verbose: bool = False,
                             finish_singles: bool = False):
    """Most-constrained-first: at each step pick the chain that fits into
    fewest colors (as whole). Tiebreak: 'long' → longer chain first,
    'short' → shorter first."""
    odds = [m for m in range(1, N + 1, 2)]
    remaining = {m: chain_of(m, N) for m in odds}
    color_sets = [set() for _ in range(k)]
    placed_whole = 0
    placed_split = {s: 0 for s in range(1, max_splits + 1)}
    failed_chains = []

    while remaining:
        # Score each remaining chain: how many colors accept it WHOLE
        scored = []
        for m, chain in remaining.items():
            accepts = sum(1 for c in range(k)
                          if not has_wsf_violation(color_sets[c], chain))
            scored.append((accepts, m, chain))
        # Sort by (accepts asc, then tiebreak)
        if tiebreak == "long":
            scored.sort(key=lambda t: (t[0], -len(t[2])))
        else:
            scored.sort(key=lambda t: (t[0], len(t[2])))
        _, m, chain = scored[0]
        del remaining[m]

        splits_used = try_place_chain(chain, color_sets, k, max_splits)
        if splits_used == 0:
            placed_whole += 1
        elif splits_used > 0:
            placed_split[splits_used] += 1
            if verbose:
                print(f"  split m={m}: {splits_used} split(s)")
        else:
            failed_chains.append((m, chain))
            if finish_singles:
                # Defer: collect all remaining fails, try singles at end
                continue
            for v in chain:
                assigned = False
                for c in range(k):
                    if not has_wsf_violation(color_sets[c], [v]):
                        color_sets[c].add(v)
                        assigned = True
                        break
                if not assigned:
                    parts_partial = [sorted(s) for s in color_sets]
                    D_partial = sum(count_doublings(s, N) for s in color_sets)
                    cover = sum(len(p) for p in parts_partial)
                    if verbose:
                        print(f"  STUCK: chain m={m} v={v} (cover={cover}/{N}, D_partial={D_partial})")
                    return (None, D_partial, placed_whole, placed_split, failed_chains, len(odds))

    # If finish_singles mode: try to place all deferred chain elements as singles
    if finish_singles and failed_chains:
        placed_all = _finish_with_singles(color_sets, failed_chains, N, k, verbose)
        if not placed_all:
            parts_partial = [sorted(s) for s in color_sets]
            D_partial = sum(count_doublings(s, N) for s in color_sets)
            return (None, D_partial, placed_whole, placed_split, failed_chains, len(odds))

    parts = [sorted(s) for s in color_sets]
    D_total = sum(count_doublings(s, N) for s in color_sets)
    return (parts, D_total, placed_whole, placed_split, failed_chains, len(odds))


def main():
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    max_splits = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    print(f"# construct_maxD_split N={N} k={k} max_splits={max_splits}")
    print(f"# HYPOTHESES: H_split_helps(0.3) H_split_partial(0.4) H_split_no_gain(0.2) H_split_needs_2(0.1)")
    # Static orderings
    for order in ("long_first", "short_first", "smallest_first", "natural"):
        result = greedy_construct_split(N, k, order=order, max_splits=max_splits)
        parts, D, placed_whole, placed_split, failed, total = result
        split_summary = " ".join(f"s{s}={n}" for s, n in placed_split.items())
        if parts is None:
            print(f"[order={order}] FAIL — whole={placed_whole} {split_summary} failed={len(failed)}/{total}")
            continue
        ok, reason = verify_weak_schur(parts, N)
        gate = "PASS" if ok else f"FAIL {reason}"
        cover = sum(len(p) for p in parts)
        print(f"[order={order}] |D|={D}  whole={placed_whole} {split_summary} "
              f"failed={len(failed)}/{total}  cover={cover}/{N}  gate={gate}  "
              f"sizes={[len(p) for p in parts]}")
    # Dynamic ordering
    for tb in ("long", "short"):
        result = greedy_constraint_first(N, k, max_splits=max_splits, tiebreak=tb)
        parts, D, placed_whole, placed_split, failed, total = result
        split_summary = " ".join(f"s{s}={n}" for s, n in placed_split.items())
        if parts is None:
            print(f"[order=CONSTRAINT/{tb}] FAIL — D_partial={D} whole={placed_whole} {split_summary} failed={len(failed)}/{total}")
            continue
        ok, reason = verify_weak_schur(parts, N)
        gate = "PASS" if ok else f"FAIL {reason}"
        cover = sum(len(p) for p in parts)
        print(f"[order=CONSTRAINT/{tb}] |D|={D}  whole={placed_whole} {split_summary} "
              f"failed={len(failed)}/{total}  cover={cover}/{N}  gate={gate}  "
              f"sizes={[len(p) for p in parts]}")
    # Constraint-first + finish_singles fallback (main hope for valid coloring)
    for tb in ("long", "short"):
        result = greedy_constraint_first(N, k, max_splits=max_splits,
                                           tiebreak=tb, finish_singles=True,
                                           verbose=True)
        parts, D, placed_whole, placed_split, failed, total = result
        split_summary = " ".join(f"s{s}={n}" for s, n in placed_split.items())
        if parts is None:
            print(f"[order=CONSTRAINT/{tb}+singles] FAIL — D_partial={D} whole={placed_whole} {split_summary} deferred={len(failed)}/{total}")
            continue
        ok, reason = verify_weak_schur(parts, N)
        gate = "PASS" if ok else f"FAIL {reason}"
        cover = sum(len(p) for p in parts)
        print(f"[order=CONSTRAINT/{tb}+singles] |D|={D}  whole={placed_whole} {split_summary} "
              f"deferred_chains={len(failed)}/{total}  cover={cover}/{N}  gate={gate}  "
              f"sizes={[len(p) for p in parts]}")


if __name__ == "__main__":
    main()

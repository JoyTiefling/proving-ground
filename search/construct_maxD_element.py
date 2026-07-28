"""
Element-priority greedy for max|D| WSF k-coloring of [1..N].

Not chain-based: process one d at a time and try to co-color {d, 2d} in the
same color. That relaxes the monolithic block requirement that killed
construct_maxD.py (whole chain in one color) and construct_maxD_split.py
(chain in a small number of contiguous parts). Here 2d in color A, 4d in
color B is allowed — only pair-doublings are counted, so a chain
{m,2m,4m,8m} can contribute 3 doublings even if it is spread over 4 colors.

PRE-REGISTRATION (before running, per L3 #2866 razor; log the run in
log/weak-schur.md AFTER execution, per 02:00 18-07 continuity lesson):
  H_element_pair    (alpha ~0.30): pair-first greedy with singles-fallback
                                   places all N elements validly, |D| >= 40
  H_element_partial (alpha ~0.35): partial success, best D_partial in [40..55]
                                   but cover < N (WSF blocks force stuck)
  H_element_hit36   (alpha ~0.20): valid full coloring reached, but |D| <= 36
                                   (does not beat SAT lower bound already known)
  H_element_fail    (alpha ~0.15): does not build a valid full coloring at all
                                   (element order, like chain order, blocked)

Positive control: Eliahou WS(5)=196 partition restricted to [1..150] is a
valid 5-coloring of [1..150] — so existence is not the question, greedy
reachability is. Expected |D| of that restriction: ~10 (many of Eliahou's
13 doublings live in the tail 150..196).

Metrics reported per order:
  - final |D|
  - cover (elements actually assigned)
  - pairs_scored (d with f(d)=f(2d) placed by pair phase)
  - singles_placed (non-pair elements filled by singles phase)
  - stuck_at v / None
  - WSF gate PASS/FAIL

Scheduler orders (choice of which d to try to make into a pair first):
  pair_asc      : d = 1, 2, 3, ..., N//2  (natural)
  pair_desc     : d = N//2, ..., 2, 1     (big-first)
  pair_by_reach : d sorted by len(chain(m)) desc, where m = odd(d), then by d
                  — d's with long doubling reach carry more potential mass
  pair_odd_first: odd d first (2d is even, cleaner residues), then even d

Color choice when both d and 2d unassigned: pick a color c such that
  {d, 2d} does not create a WSF violation in c AND minimizes future
  blockage. Two policies for the tiebreak on future blockage:
  greedy_first  : take the first c that fits (no lookahead)
  min_size      : take c with the smallest current class size
                  (spread mass, keep small-number backbone free)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur


def chain_of(m: int, N: int):
    out = []
    v = m
    while v <= N:
        out.append(v)
        v *= 2
    return out


def odd_part(v: int) -> int:
    while v % 2 == 0:
        v //= 2
    return v


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


def pick_color_for_pair(color_sets, d, policy: str, k: int):
    """Return first color c where {d, 2d} fits without WSF violation, or -1.
    policy: greedy_first (take first), min_size (prefer smaller class)."""
    candidates = []
    for c in range(k):
        # symmetry-break echoed from sat_weak_schur: element v may use color c
        # only if c <= v - 1. For pair (d, 2d) the tighter is d.
        if c > d - 1:
            continue
        cs = color_sets[c]
        if d in cs and (2 * d) in cs:
            # already both in c — pair exists, no placement needed
            return c
        if d in cs and (2 * d) not in cs:
            if has_wsf_violation(cs, [2 * d]):
                continue
        elif (2 * d) in cs and d not in cs:
            if has_wsf_violation(cs, [d]):
                continue
        elif d not in cs and (2 * d) not in cs:
            if has_wsf_violation(cs, [d, 2 * d]):
                continue
        candidates.append(c)
    if not candidates:
        return -1
    if policy == "min_size":
        candidates.sort(key=lambda c: len(color_sets[c]))
    return candidates[0]


def pick_color_for_single(color_sets, v, policy: str, k: int):
    """Return first color c where {v} fits, or -1."""
    candidates = []
    for c in range(k):
        if c > v - 1:
            continue
        cs = color_sets[c]
        if v in cs:
            return c
        if has_wsf_violation(cs, [v]):
            continue
        candidates.append(c)
    if not candidates:
        return -1
    if policy == "min_size":
        candidates.sort(key=lambda c: len(color_sets[c]))
    return candidates[0]


def schedule(N: int, order: str):
    """Return the list of d's (in [1..N//2]) in scheduler order."""
    ds = list(range(1, N // 2 + 1))
    if order == "pair_asc":
        return ds
    if order == "pair_desc":
        return list(reversed(ds))
    if order == "pair_by_reach":
        # d sorted by len(chain(odd_part(d))) desc, tiebreak d asc
        return sorted(ds, key=lambda d: (-len(chain_of(odd_part(d), N)), d))
    if order == "pair_odd_first":
        odds = [d for d in ds if d % 2 == 1]
        evens = [d for d in ds if d % 2 == 0]
        return odds + evens
    raise ValueError(f"unknown order {order}")


def greedy_element(N: int, k: int, order: str, color_policy: str,
                   verbose: bool = False):
    """
    Two phases:
      1. Pair phase: iterate d in `order`, try to co-color {d, 2d} in one color.
         If either d or 2d already placed in some color c, only that c is
         considered (must not violate WSF for the missing partner).
      2. Singles phase: any v in [1..N] not yet placed is placed as a single,
         picking a color per `color_policy`.

    Returns (parts_or_None, D_final, stats_dict).
    """
    color_sets = [set() for _ in range(k)]
    pair_success = 0
    pair_blocked = 0

    for d in schedule(N, order):
        c = pick_color_for_pair(color_sets, d, color_policy, k)
        if c < 0:
            pair_blocked += 1
            if verbose:
                print(f"  pair d={d} blocked (all colors reject {{d,2d}})")
            continue
        # Place whichever partners aren't yet in c
        if d not in color_sets[c]:
            color_sets[c].add(d)
        if (2 * d) <= N and (2 * d) not in color_sets[c]:
            color_sets[c].add(2 * d)
        pair_success += 1

    # Singles phase — anything not yet placed
    placed = set()
    for cs in color_sets:
        placed |= cs
    stuck_at = None
    singles_placed = 0
    remaining = [v for v in range(1, N + 1) if v not in placed]
    # Descending first often helps (large v has fewer sums a+b=v with a,b<=v).
    for v in sorted(remaining, reverse=True):
        c = pick_color_for_single(color_sets, v, color_policy, k)
        if c < 0:
            stuck_at = v
            break
        color_sets[c].add(v)
        singles_placed += 1

    parts = [sorted(s) for s in color_sets]
    D_total = sum(count_doublings(s, N) for s in color_sets)
    cover = sum(len(p) for p in parts)
    stats = {
        "pair_success": pair_success,
        "pair_blocked": pair_blocked,
        "singles_placed": singles_placed,
        "cover": cover,
        "stuck_at": stuck_at,
        "sizes": [len(p) for p in parts],
    }
    if stuck_at is not None or cover < N:
        return (None, D_total, stats)
    return (parts, D_total, stats)


def main():
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    print(f"# construct_maxD_element N={N} k={k}")
    print(f"# HYPOTHESES: H_element_pair(0.30) H_element_partial(0.35) "
          f"H_element_hit36(0.20) H_element_fail(0.15)")
    print(f"# SAT lower bound (from bg sat_maxD): max|D|(150) >= 36")

    orders = ("pair_asc", "pair_desc", "pair_by_reach", "pair_odd_first")
    policies = ("greedy_first", "min_size")

    best_valid = None
    for order in orders:
        for policy in policies:
            parts, D, stats = greedy_element(N, k, order, policy)
            tag = f"order={order} policy={policy}"
            if parts is None:
                print(f"[{tag}] FAIL  |D|_partial={D}  cover={stats['cover']}/{N}  "
                      f"pair_ok={stats['pair_success']} pair_block={stats['pair_blocked']} "
                      f"singles={stats['singles_placed']} stuck_at={stats['stuck_at']} "
                      f"sizes={stats['sizes']}")
                continue
            ok, reason = verify_weak_schur(parts, N)
            gate = "PASS" if ok else f"FAIL {reason}"
            print(f"[{tag}] |D|={D}  cover={stats['cover']}/{N}  "
                  f"pair_ok={stats['pair_success']} pair_block={stats['pair_blocked']} "
                  f"singles={stats['singles_placed']} gate={gate} "
                  f"sizes={stats['sizes']}")
            if ok and (best_valid is None or D > best_valid[1]):
                best_valid = (order, D, parts, policy)

    if best_valid is not None:
        order, D, parts, policy = best_valid
        print(f"\n# BEST VALID: order={order} policy={policy} |D|={D}")
        # Emit the partition for downstream analysis
        out_dir = os.path.join(os.path.dirname(__file__), "out")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"element_ws5_N{N}_D{D}.txt")
        with open(out_path, "w") as fh:
            fh.write(f"# construct_maxD_element N={N} k={k} order={order} policy={policy} |D|={D}\n")
            for i, p in enumerate(parts):
                fh.write(f"C{i}: {' '.join(str(v) for v in p)}\n")
        print(f"# wrote {out_path}")
    else:
        print("\n# NO VALID FULL COLORING built by any (order, policy).")


if __name__ == "__main__":
    main()

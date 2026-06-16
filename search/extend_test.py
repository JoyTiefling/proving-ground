"""
Matching/extensibility test — the compute-free probe at the heart of N -> N+1.

When we add element N+1 to a valid weakly-sum-free coloring of {1..N}, N+1 only
ever appears as the SUM of a pair (a, N+1-a), a<N+1-a. So N+1 can join class c
iff c contains NO such pair fully. The pairs (a, N+1-a) form a matching on
{1..N}. Therefore:

  WS >= N+1  <=  some class is "(N+1)-independent" (<=1 element per pair).

This module:
  - matching_test: per-class count of blocking pairs (pairs fully inside class).
  - try_extend:    if a class is 0-blocked, drop N+1 in and gate-verify.
  - repair_extend: if all classes blocked, try to FREE one class by relocating
                   its blocking elements elsewhere (small local repair), verify.

Run on any valid partition (e.g. a literature WS(5)=196 construction) to decide
197 with essentially zero compute.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa


def matching_test(parts, target):
    """Return list of (class_index, blocking_pairs) where blocking_pairs are the
    pairs (a, target-a) fully contained in that class."""
    res = []
    for i, p in enumerate(parts):
        s = set(p)
        blocks = []
        for a in range(1, target // 2 + 1):
            b = target - a
            if a < b and a in s and b in s:
                blocks.append((a, b))
        res.append((i, blocks))
    return res


def try_extend(parts, target):
    """If some class is 0-blocked, add `target` there. Returns (new_parts, c) or None."""
    for i, blocks in matching_test(parts, target):
        if not blocks:
            new = [list(p) for p in parts]
            new[i].append(target)
            ok, _ = verify_weak_schur(new, target)
            if ok:
                return new, i
    return None


def can_place(parts_sets, n, c, exclude=None):
    """Can element n go in class c without making a weak triple? exclude = a set
    of elements treated as removed from class c."""
    s = parts_sets[c]
    a = 1
    while 2 * a < n:
        x, y = a, n - a
        xin = (x in s and x != exclude) if exclude is not None else (x in s)
        yin = (y in s and y != exclude) if exclude is not None else (y in s)
        # exclude handling below is simplistic; we recompute properly in repair
        a += 1
    return True  # placeholder; repair uses full re-verify instead


def repair_extend(parts, target, max_moves=3):
    """Try to free one class to be target-independent by relocating <=max_moves
    of its blocking elements to other classes, keeping everything valid, then
    add `target`. Greedy/bounded. Returns (new_parts, info) or None."""
    base_ok, _ = verify_weak_schur(parts, max(max(p) for p in parts))
    if not base_ok:
        return None
    mt = matching_test(parts, target)
    # try classes with fewest blocks first
    for i, blocks in sorted(mt, key=lambda t: len(t[1])):
        if len(blocks) == 0:
            continue
        if len(blocks) > max_moves:
            continue
        # elements we may relocate out of class i: one endpoint per blocking pair
        # (choose, per pair, an element to move so the pair is broken)
        # try moving the *first* endpoint of each blocking pair to some other class
        movers = [a for (a, b) in blocks]
        new = [list(p) for p in parts]
        ok_all = True
        for e in movers:
            new[i].remove(e)
            placed = False
            for j in range(len(new)):
                if j == i:
                    continue
                trial = [list(p) for p in new]
                trial[j].append(e)
                ok, _ = verify_weak_schur(trial, max(max(p) for p in trial if p))
                if ok:
                    new = trial; placed = True; break
            if not placed:
                ok_all = False; break
        if not ok_all:
            continue
        # now class i should be target-independent; add target
        res = try_extend(new, target)
        if res:
            return res[0], {"freed_class": i, "moved": movers}
    return None


def load_saved(path):
    parts = []
    with open(path) as f:
        for line in f:
            if ":" in line:
                parts.append([int(x) for x in line.split(":", 1)[1].split()])
    return parts


if __name__ == "__main__":
    here = os.path.dirname(__file__)
    # ---- validate the tool on WS(4)=66: every class MUST block 67 ----
    ws4 = load_saved(os.path.join(here, "out", "ws4_N66.txt"))
    print("validation on WS(4)=66, target=67 (every class must be blocked):")
    allblocked = True
    for i, blocks in matching_test(ws4, 67):
        print(f"  class {i}: {len(blocks)} blocking pairs  e.g. {blocks[:2]}")
        if not blocks:
            allblocked = False
    print(f"  => {'OK (all blocked, consistent with WS(4)=66)' if allblocked else 'A CLASS IS FREE?!'}")
    ext = try_extend(ws4, 67)
    print(f"  try_extend(67): {'EXTENDED?! (would contradict WS(4)=66 — check)' if ext else 'correctly blocked'}")

    # ---- ready-to-fire on a real WS(5)=196 construction when available ----
    p196 = os.path.join(here, "out", "ws5_N196.txt")
    if os.path.exists(p196):
        parts = load_saved(p196)
        ok, _ = verify_weak_schur(parts, 196)
        print(f"\nWS(5)=196 construction loaded, gate={'PASS' if ok else 'FAIL'}")
        print("matching_test for 197:")
        for i, blocks in matching_test(parts, 197):
            print(f"  class {i}: {len(blocks)} blocking pairs")
        ext = try_extend(parts, 197)
        if ext:
            print("  *** 197 EXTENDS DIRECTLY — CANDIDATE WS(5)>=197, adversarial re-verify ***")
        else:
            rep = repair_extend(parts, 197, max_moves=3)
            print(f"  repair_extend(197, <=3 moves): {'SUCCESS — candidate, re-verify' if rep else 'no cheap repair'}")
    else:
        print("\n(no ws5_N196.txt yet — drop a literature construction there to fire the 197 test)")

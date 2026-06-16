"""
Last construction shot: Rowley's EXACT sparse backbone + ejection chains.

The real record's c0 = {1} U {n = 2 mod 4} (a sum-free residue class plus the
exception 1). Fix that as color 0, then build the other 4 colors by adding
elements 3,4,5,7,8,... one at a time via ejection chains (never touching c0).
Uses the record's genuine backbone + our best technique. Gate-checked.
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa


def bad_pairs(parts, e, c):
    s = parts[c]
    pairs = []
    a = 1
    while 2 * a < e:
        if a in s and (e - a) in s:
            pairs.append((a, e - a))
        a += 1
    for x in s:
        if (e + x) in s:
            pairs.append((x, e + x))
    return pairs


def place(parts, e, depth, frozen, deadline, allowed_classes):
    if time.time() > deadline:
        return False
    order = sorted(allowed_classes, key=lambda c: len(bad_pairs(parts, e, c)))
    for c in order:
        if e in parts[c]:
            continue
        bp = bad_pairs(parts, e, c)
        if not bp:
            parts[c].add(e)
            return True
        if depth <= 0:
            continue
        eject = {max(x, y) for x, y in bp}
        if eject & (frozen | {e}):
            continue
        snap = [set(p) for p in parts]
        parts[c].add(e)
        for z in eject:
            parts[c].discard(z)
        if all(place(parts, z, depth - 1, frozen | {e}, deadline, allowed_classes) for z in eject):
            return True
        for i in range(len(parts)):
            parts[i] = snap[i]
    return False


if __name__ == "__main__":
    depth = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    budget = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    Nmax = 205
    # color 0 = Rowley backbone {1} U {n = 2 mod 4}; others empty
    c0 = set([1] + [n for n in range(2, Nmax + 1) if n % 4 == 2])
    parts = [set(), set(), set(), set(), set()]   # build c0 incrementally too
    deadline = time.time() + budget
    cur = 0
    for n in range(1, Nmax + 1):
        if n == 1 or n % 4 == 2:
            parts[0].add(n)        # backbone element
            cur = n
            continue
        if place(parts, n, depth, set(), deadline, allowed_classes=[1, 2, 3, 4]):
            cur = n
        else:
            print(f"stuck at {cur} (cannot place {n})")
            break
        if cur % 20 == 0:
            print(f"  ...reached {cur}", flush=True)
    print(f"MAX REACH (Rowley backbone + ejection): {cur}  (record 196, my best 195)")
    ne = [sorted(p) for p in parts if p]
    ok, reason = verify_weak_schur(ne, cur)
    print(f"  gate@{cur}: {'PASS' if ok else 'FAIL ' + str(reason)}")
    if ok and cur > 150:
        with open(os.path.join(os.path.dirname(__file__), "out", f"rowleybb_ws5_N{cur}.txt"), "w") as f:
            for i, p in enumerate(parts):
                f.write(f"part {i}: {' '.join(map(str, sorted(p)))}\n")
        print(f"  saved rowleybb_ws5_N{cur}.txt")
    if cur > 196:
        print(f"  *** N={cur} > 196 — CANDIDATE, adversarial re-verify ***")

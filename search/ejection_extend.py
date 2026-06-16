"""
Ejection-chain extension — the clever move past a locally-maximal construction.

Single-move repair stalls at 187: no blocking element can move without breaking
its new class. An ejection chain goes deeper: place element e in class c, and
for each triple that breaks, EJECT one offending element and recursively
re-home it (which may eject further, up to a bounded depth). This is the
standard technique for tight packings — search effort, not brute force.

Climbs from the saved 187 construction toward 196. If it reaches 196, we can
finally run the matching test for 197 on our OWN construction. Gate-checked.
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa
from seed_construct import load_saved  # noqa


def bad_pairs(parts, e, c):
    """Triples that adding e to class c would create, as (ejectable, ejectable) pairs."""
    s = parts[c]
    pairs = []
    a = 1
    while 2 * a < e:               # e as the SUM:  a + (e-a) = e
        if a in s and (e - a) in s:
            pairs.append((a, e - a))
        a += 1
    for x in s:                    # e as an ADDEND: x + e = (e+x)
        if (e + x) in s:
            pairs.append((x, e + x))
    return pairs


def place(parts, e, depth, frozen, deadline):
    if time.time() > deadline:
        return False
    order = sorted(range(len(parts)), key=lambda c: len(bad_pairs(parts, e, c)))
    for c in order:
        if e in parts[c]:
            continue
        bp = bad_pairs(parts, e, c)
        if not bp:
            parts[c].add(e)
            return True
        if depth <= 0:
            continue
        eject = {max(x, y) for x, y in bp}     # eject larger endpoint of each pair
        if eject & (frozen | {e}):
            continue
        snap = [set(p) for p in parts]
        parts[c].add(e)
        for z in eject:
            parts[c].discard(z)
        if all(place(parts, z, depth - 1, frozen | {e}, deadline) for z in eject):
            return True
        for i in range(len(parts)):
            parts[i] = snap[i]
    return False


if __name__ == "__main__":
    here = os.path.dirname(__file__)
    infile = sys.argv[3] if len(sys.argv) > 3 else os.path.join("out", "incr_ws5_N187.txt")
    parts = [set(p) for p in load_saved(os.path.join(here, infile) if not os.path.isabs(infile) else infile)]
    cur = max(max(p) for p in parts if p)
    depth = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    budget = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    print(f"start N={cur}, ejection depth={depth}, budget={budget}s")
    deadline = time.time() + budget
    while cur < 199 and time.time() < deadline:
        T = cur + 1
        if not place(parts, T, depth, set(), deadline):
            print(f"  stuck at {cur} (no ejection chain places {T})")
            break
        ne = [sorted(p) for p in parts if p]
        ok, reason = verify_weak_schur(ne, T)
        if not ok:
            print(f"  !! invalid at {T}: {reason}")
            break
        cur = T
        print(f"  reached {cur} (gate PASS)", flush=True)
    print(f"MAX REACH: {cur} (record 196)")
    if cur > 187:
        outdir = os.path.join(here, "out")
        fn = os.path.join(outdir, f"eject_ws5_N{cur}.txt")
        with open(fn, "w") as f:
            for i, p in enumerate(parts):
                f.write(f"part {i}: {' '.join(map(str, sorted(p)))}\n")
        print(f"  saved {fn}")
    if cur >= 196:
        from extend_test import matching_test
        print("\n*** reached 196 — matching test for 197 on OWN construction ***")
        for i, bl in sorted(matching_test([sorted(p) for p in parts], 197), key=lambda t: len(t[1])):
            print(f"  class {i}: {len(bl)} blocking pairs for 197")
    if cur > 196:
        print(f"  *** N={cur} > 196 — CANDIDATE NEW BOUND, adversarial re-verify required ***")

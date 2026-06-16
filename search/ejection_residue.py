"""
Real record structure + ejection chains.

Records use a sparse sum-free residue backbone: c0 = {1} U {n = 2 mod 4}, which
is weakly sum-free for free (2+2 = 0 mod 4, never 2 mod 4). All my earlier
constructions grew from a monolithic block (NOT the record structure) and
saturate near 195. Here we fix the genuine backbone and pack the remaining
elements ({0,1,3 mod 4}) into the other 4 colors via ejection chains.

Different basin entirely. Gate-checked; >196 = candidate, re-verify.
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


def place4(parts, e, depth, frozen, deadline):
    """Place e into classes 1..4 (class 0 = frozen backbone) via ejection chain."""
    if time.time() > deadline:
        return False
    classes = sorted([1, 2, 3, 4], key=lambda c: len(bad_pairs(parts, e, c)))
    for c in classes:
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
        if all(place4(parts, z, depth - 1, frozen | {e}, deadline) for z in eject):
            return True
        for i in range(len(parts)):
            parts[i] = snap[i]
    return False


if __name__ == "__main__":
    here = os.path.dirname(__file__)
    Nmax = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    depth = int(sys.argv[2]) if len(sys.argv) > 2 else 9
    budget = int(sys.argv[3]) if len(sys.argv) > 3 else 360
    c0 = set([1] + [n for n in range(2, Nmax + 1) if n % 4 == 2])
    parts = [set(c0), set(), set(), set(), set()]
    deadline = time.time() + budget
    cur = 0
    for n in range(1, Nmax + 1):
        if n in parts[0]:
            cur = n
            continue
        if place4(parts, n, depth, set(), deadline):
            cur = n
        else:
            print(f"stuck at {cur} (cannot place {n})")
            break
        if cur % 20 == 0:
            print(f"  ...reached {cur}", flush=True)
    print(f"MAX REACH: {cur} (record 196)")
    ne = [sorted(p) for p in parts if p]
    ok, reason = verify_weak_schur(ne, cur)
    print(f"  gate@{cur}: {'PASS' if ok else 'FAIL ' + str(reason)}")
    if ok and cur > 187:
        with open(os.path.join(here, "out", f"residue_ws5_N{cur}.txt"), "w") as f:
            for i, p in enumerate(parts):
                f.write(f"part {i}: {' '.join(map(str, sorted(p)))}\n")
        print(f"  saved residue_ws5_N{cur}.txt")
    if cur > 196:
        print(f"  *** N={cur} > 196 — CANDIDATE NEW BOUND, adversarial re-verify required ***")

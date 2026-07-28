"""
Probe B — forbidden-sum-set DP with tail collapse.

Sufficient statistic for completing a partial colouring of {1..v}:
  per colour c -> ( live elements a<=N-v-1 [can still form an in-range sum with
                    a future element >=v+1],
                    forbidden future sums in (v, N] [values a future element of
                    colour c may NOT take] ).
Two prefixes with the same canonical tuple of (live, forbidden) pairs are
interchangeable for completion -> they MERGE. As v grows N-v-1 shrinks, so live
sets shrink: states may collapse toward the tail (where the aperiodic record
lives). We measure distinct canonical states per level: small => tractable/exact
answer; explosion => measured wall with its exact shape.

Sanity: must reproduce WS(2)=8, WS(3)=23.
"""
import sys, time


def solve(N, k, cap=1_200_000, verbose=True):
    start = tuple((frozenset(), frozenset()) for _ in range(k))
    level = {start}
    for v in range(1, N + 1):
        Lnext = N - v - 1                    # live threshold after placing v
        new_level = set()
        for st in level:
            for c in range(k):
                live_c, forb_c = st[c]
                if v in forb_c:
                    continue                 # v cannot be colour c
                add = {v + a for a in live_c if v + a <= N}
                new_forb_c = forb_c | add
                ns = []
                for cc in range(k):
                    if cc == c:
                        lv2 = {x for x in live_c if x <= Lnext}
                        if v <= Lnext:
                            lv2.add(v)
                        fb2 = frozenset(s for s in new_forb_c if s > v)
                        ns.append((frozenset(lv2), fb2))
                    else:
                        lv, fb = st[cc]
                        ns.append((frozenset(x for x in lv if x <= Lnext),
                                   frozenset(s for s in fb if s > v)))
                ns = tuple(sorted(ns, key=lambda p: (sorted(p[0]), sorted(p[1]))))
                new_level.add(ns)
        level = new_level
        if not level:
            return False, v                  # element v uncolourable -> WS < v
        if len(level) > cap:
            return None, v                   # state explosion -> undetermined
        if verbose:
            print(f"    v={v:3d}  states={len(level):>10,}  liveThresh={max(Lnext,0)}", flush=True)
    return True, N


def ws(k, hi):
    last = 0
    for N in range(1, hi):
        ok, _ = solve(N, k, verbose=False)
        if ok:
            last = N
        elif ok is False:
            break
        else:
            return None
    return last


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "sanity":
        for k, exp in [(2, 8), (3, 23)]:
            got = ws(k, exp + 5)
            print(f"k={k}: WS={got} (expected {exp}) {'OK' if got == exp else 'MISMATCH'}", flush=True)
        sys.exit(0)

    # default: sanity first, then the real measurement at N=197 k=5
    print("== sanity ==", flush=True)
    for k, exp in [(2, 8), (3, 23)]:
        got = ws(k, exp + 5)
        print(f"k={k}: WS={got} (expected {exp}) {'OK' if got == exp else 'MISMATCH'}", flush=True)
    print("== measure k=5 N=197 (expect explosion; we want the curve) ==", flush=True)
    t0 = time.time()
    res, where = solve(197, 5)
    print(f"RESULT N=197 k=5: feasible={res} at={where} ({time.time() - t0:.1f}s)", flush=True)

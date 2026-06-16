"""
Speculative angle #1: the cross-k recursive operator.

Records are self-similar (the k-construction contains the (k-1)-one as a prefix,
growth ~x3). Classic Schur-style recursion: from a (k-1)-coloring of [1,m],
build a k-coloring of [1,~3m] by  old colors on [1,m]  +  a NEW color on a
middle block  +  a SHIFTED copy of the old coloring on the top.

We don't reason the exact valid form -- we sweep the parameters (new-block
position, shift) and let the GATE measure the largest valid reach. Tests whether
the recursive operator alone gets near the record 196 from WS(4)=66.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa
from seed_construct import load_saved  # noqa


def build_recursive(ws_prev, m, new_lo, new_hi, shift, Nmax):
    """color map for [1..Nmax]: prev colors on [1,m]; new color (index k-1) on
    [new_lo,new_hi]; shifted copy color(n)=color_prev(n-shift) elsewhere."""
    prevcol = {}
    for c, part in enumerate(ws_prev):
        for n in part:
            prevcol[n] = c
    knew = len(ws_prev)            # new color index
    color = {}
    for n in range(1, Nmax + 1):
        if n <= m:
            color[n] = prevcol.get(n)
        elif new_lo <= n <= new_hi:
            color[n] = knew
        elif (n - shift) in prevcol:
            color[n] = prevcol[n - shift]
        else:
            color[n] = None        # undefined -> truncate here
    return color, knew + 1


def max_valid_reach(color, k):
    parts = [[] for _ in range(k)]
    N = 0
    for n in sorted(color):
        if color[n] is None:
            break
        parts[color[n]].append(n)
        ok, _ = verify_weak_schur([p for p in parts if p], n)
        if not ok:
            return n - 1
        N = n
    return N


if __name__ == "__main__":
    here = os.path.dirname(__file__)
    ws4 = load_saved(os.path.join(here, "out", "ws4_N66.txt"))
    m = 66
    best = (0, None)
    # sweep: new block around [m+1, 2m+e], shift around 2m
    for new_lo in range(m + 1, m + 6):
        for new_hi in range(2 * m - 4, 2 * m + 8):
            for shift in range(2 * m - 2, 2 * m + 8):
                color, k = build_recursive(ws4, m, new_lo, new_hi, shift, 210)
                r = max_valid_reach(color, k)
                if r > best[0]:
                    best = (r, (new_lo, new_hi, shift))
                    print(f"  reach {r}: new=[{new_lo},{new_hi}] shift={shift}", flush=True)
    r, params = best
    print(f"\nBEST recursive-operator reach: {r}  (record 196, my ejection 195)")
    print(f"  params (new_lo,new_hi,shift) = {params}")

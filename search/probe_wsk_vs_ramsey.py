"""
Litmus for the conjecture  WS(k) ~ R_k(3) + |D(k)|.

Generate optimal weak k-colourings of {1..WS(k)} for small k, measure the doubling
set size |D| = #{d : f(d)=f(2d)}, and compare WS(k) - R_k(3) against |D|.

Known: R_1=3, R_2=6, R_3=17, R_4 in [51,62], R_5 in [162,307].
       WS = 2,8,23,66,196.
Need |D|(2)=2 and |D|(3)=6 for WS(k)=R_k(3)+|D| to hold on k=2,3 (R known there).

We sample SEVERAL optimal colourings per k and report the range of |D| (the relation,
if real, should hold for the extremal colouring -- we look at what |D| values occur).
"""
import sys


def wsf_ok_add(cls, v):
    for a in cls:
        if a < v and (v - a) in cls and (v - a) != a:
            return False
        if (v + a) in cls:
            return False
    return True


def find_colorings(k, N, limit=200):
    """backtracking with first-occurrence symmetry; yield up to `limit` valid colourings."""
    res = []
    color = [0] * (N + 1)
    cls = [set() for _ in range(k)]

    def bt(v, used):
        if len(res) >= limit:
            return
        if v > N:
            res.append(color[1:].copy())
            return
        hi = min(used, k - 1)
        for c in range(hi + 1):
            if wsf_ok_add(cls[c], v):
                cls[c].add(v); color[v] = c
                bt(v + 1, max(used, c + 1))
                cls[c].discard(v)
        # also a fresh colour beyond first-occurrence already covered by hi=used
    bt(1, 0)
    return res


def Dsize(coloring, N):
    # coloring[i-1] = colour of i
    col = {i: coloring[i - 1] for i in range(1, N + 1)}
    return sum(1 for d in range(1, N // 2 + 1) if col[d] == col[2 * d])


if __name__ == "__main__":
    R = {1: 3, 2: 6, 3: 17}
    for k, N in [(2, 8), (3, 23)]:
        cols = find_colorings(k, N, limit=500)
        Ds = sorted(set(Dsize(c, N) for c in cols))
        rk = R[k]
        print(f"k={k} WS={N} R_k(3)={rk}  WS-R={N-rk}  "
              f"|D| over {len(cols)} colourings: min={Ds[0]} max={Ds[-1]} set={Ds}", flush=True)
        print(f"    conjecture WS=R+|D| needs |D|={N-rk}: "
              f"{'PRESENT' if (N-rk) in Ds else 'ABSENT'} in observed |D| set", flush=True)

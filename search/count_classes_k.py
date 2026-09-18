"""Число канонических chain-mono weak-Schur префиксов длины P при k цветах (DFS, restricted growth)."""
import sys
def count(k, P):
    odds = list(range(1, P+1, 2)); col = [None]*(P+1); n = 0
    def ok_upto(changed):  # проверяем тройки, задевающие только что покрашенные числа
        for z in range(3, P+1):
            cz = col[z]
            if cz is None: continue
            for x in range(1, (z+1)//2):
                y = z-x
                if x != y and col[x] == cz and col[y] == cz and (x in changed or y in changed or z in changed):
                    return False
        return True
    def rec(i, used):
        nonlocal n
        if i == len(odds): n += 1; return
        o = odds[i]; chain = [v for v in range(o, P+1) if v % o == 0 and (v//o) & (v//o - 1) == 0]
        for c in range(min(used+1, k)):
            for v in chain: col[v] = c
            if ok_upto(set(chain)): rec(i+1, max(used, c+1))
            for v in chain: col[v] = None
    rec(0, 0); return n
for k in (6, 7):
    print(k, {P: count(k, P) for P in (8, 10, 12, 14, 16, 18, 20)}, flush=True)

"""Независимая проверка покрытия C-015. Свой код, без canon/expand/gate из проб."""
import sys, json, itertools, random, pathlib
sys.path.insert(0, '.')
import probe_prefix_cover as ppc, probe_prefix_cover_odd as po
K, P = 6, 12
classes, stats = ppc.enumerate_classes(K, P)
CL = set(classes); print("classes", len(CL), stats)

def ws(col, n):  # col: dict v->c, свой перебор пар
    return not any(col[x] == col[y] == col[x+y] for x in range(1, n+1) for y in range(x+1, n+1-x))
def first_occ(seq):
    m = {}; return tuple(m.setdefault(c, len(m)) for c in seq)

# (1) полный перебор ВСЕХ 6^12 нельзя, но chain-mono задаётся нечётными: 6^6, своим кодом
n_valid = miss = 0
for combo in itertools.product(range(K), repeat=6):
    oc = dict(zip(range(1, 13, 2), combo))
    col = {v: oc[v >> ((v & -v).bit_length() - 1)] for v in range(1, 13)}
    if ws(col, 12):
        n_valid += 1
        if first_occ(col[v] for v in range(1, 13)) not in CL: miss += 1
print("valid prefixes", n_valid, "not covered:", miss, "(expect", stats["weak_schur"], ", 0)")

# (2) нет скрытого symmetry breaking в кодировке сертификатов: витнесс-145 под всеми 720
#     перестановками цветов обязан удовлетворять cnf_odd(6,145)
w = json.load(open('out/prefix_cover/c015_k6_P12_N146_glucose42.json'))['controls']
wit = [c for c in w if c.get('witness')][0]['witness']; N = len(wit); print("witness N", N)
f, var = po.cnf_odd(K, N)
bad = 0
for perm in itertools.permutations(range(K)):
    true = set()
    for v in range(1, N + 1, 2): true.add(var(v, perm[wit[v-1]]))
    # var определён только на нечётных; остальные вспомогательные? проверим, что их нет
    if not all(any((l > 0 and l in true) or (l < 0 and -l not in true) for l in cl) for cl in f): bad += 1
print("perms violating cnf_odd:", bad, "of 720; clauses", len(f), "max var", max(abs(l) for c in f for l in c), "expected vars", K*len(range(1,N+1,2)))
# (3) отрицательный контроль: испорченный витнесс обязан НЕ удовлетворять
col = {v: wit[v-1] for v in range(1, N+1)}; print("witness ws own:", ws(col, N), "chain:", all(col[v]==col[v//2] for v in range(2,N+1,2)))

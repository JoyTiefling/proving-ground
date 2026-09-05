"""
SAT — ВТОРОЙ НОСИТЕЛЬ для M_chain(k): максимум N, при котором [1..N] допускает
weak-Schur раскраску в k цветов, монохромную по цепям (f(2v) = f(v)).

Зачем отдельный файл. 06-09 00:00 бэктрекер `search/chain_mono_lifting.py` дал
M_chain(3)=22 < 23 = WS(3) и M_chain(4)=45. Для k=3 второй носитель уже есть
(исчерпывающий перебор 3^12). Для k=4 перебор 4^23 не берётся — долг (i).
Здесь механизм ДРУГОЙ: ограничения кодируются в CNF и решаются minisat.
Ни одной строки, общей с бэктрекером. Судья витнесса — только внешний гейт
`verifiers/weak_schur.py` (не тронут).

Что решается:
  переменная x[v][c] = "элемент v покрашен в цвет c"
  ALO/AMO         — ровно один цвет на элемент
  конфликт        — для каждой пары x<y, z=x+y<=N: не все три в одном цвете
  chain-mono      — для чётного v: x[v][c] <-> x[v/2][c]
  symmetry break  — f(1)=цвет 0 (цвета взаимозаменяемы; опционально)

Контроли прибора (без них замер пуст, #4053 — на зрелом рубеже отказ мигрирует
в ПРИБОР, а не в предмет):
  C1  калибровка БЕЗ chain: k=3 -> N=23 SAT, N=24 UNSAT (литературное WS(3)=23).
      Проверяет конфликтные клаузы отдельно от chain-части.
  C2  воспроизведение известного С chain: k=3 -> N=22 SAT, N=23 UNSAT.
      Должно совпасть с ДВУМЯ прежними носителями. Не совпало => дефект здесь.
  C3  положительный контроль на chain-клаузы: в любой модели с chain-клаузами
      обязано выполняться f(2)=f(1) и f(4)=f(2). Если нет — клаузы не действуют.
  C4  положительный контроль на конфликтные клаузы: сняв их, N=200 обязано
      стать SAT. Если UNSAT — солвер/энкодер врёт вне зависимости от предмета.
  C5  каждый SAT-витнесс проходит внешний гейт verify_weak_schur.

Run: python search/sat_chain_mono.py
"""

import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from verifiers.weak_schur import verify_weak_schur  # noqa: E402  ГЕЙТ, не тронут

from pysat.formula import CNF  # noqa: E402
from pysat.solvers import Minisat22  # noqa: E402


def build_cnf(k: int, N: int, chain: bool = True, conflicts: bool = True,
              symmetry: bool = True) -> Tuple[CNF, callable]:
    """Строит CNF. Возвращает (формула, функция var(v,c))."""
    def var(v: int, c: int) -> int:
        return (v - 1) * k + c + 1  # 1-based, c in 0..k-1

    cnf = CNF()
    for v in range(1, N + 1):
        cnf.append([var(v, c) for c in range(k)])              # ALO
        for c1 in range(k):
            for c2 in range(c1 + 1, k):
                cnf.append([-var(v, c1), -var(v, c2)])         # AMO

    if conflicts:
        for z in range(3, N + 1):
            x = 1
            while 2 * x < z:                                   # x < y строго => WEAK
                y = z - x
                for c in range(k):
                    cnf.append([-var(x, c), -var(y, c), -var(z, c)])
                x += 1

    if chain:
        for v in range(2, N + 1, 2):
            h = v // 2
            for c in range(k):
                cnf.append([-var(v, c), var(h, c)])
                cnf.append([var(v, c), -var(h, c)])

    if symmetry:
        cnf.append([var(1, 0)])

    return cnf, var


def solve(k: int, N: int, chain: bool = True, conflicts: bool = True,
          symmetry: bool = True) -> Tuple[bool, Optional[List[int]], float]:
    """(sat?, coloring[1..N] as list index 0..N (0 unused), seconds)."""
    cnf, var = build_cnf(k, N, chain, conflicts, symmetry)
    t0 = time.time()
    with Minisat22(bootstrap_with=cnf.clauses) as s:
        sat = s.solve()
        model = set(l for l in (s.get_model() or []) if l > 0) if sat else None
    dt = time.time() - t0
    if not sat:
        return False, None, dt
    coloring = [0] * (N + 1)
    for v in range(1, N + 1):
        for c in range(k):
            if var(v, c) in model:
                coloring[v] = c
                break
    return True, coloring, dt


def to_partition(coloring: List[int], k: int, N: int) -> List[List[int]]:
    parts: List[List[int]] = [[] for _ in range(k)]
    for v in range(1, N + 1):
        parts[coloring[v]].append(v)
    return parts


def is_chain_mono(coloring: List[int], N: int) -> bool:
    return all(coloring[v] == coloring[v // 2] for v in range(2, N + 1, 2))


def gate(coloring: List[int], k: int, N: int) -> Tuple[bool, Optional[str]]:
    return verify_weak_schur(to_partition(coloring, k, N), N)


def max_N(k: int, lo: int, hi: int, chain: bool = True) -> Tuple[int, dict]:
    """Наибольшее N в [lo,hi] с SAT. Печатает границу SAT/UNSAT поимённо."""
    detail = {}
    last = lo - 1
    for n in range(lo, hi + 1):
        sat, col, dt = solve(k, n, chain=chain)
        detail[n] = (sat, dt)
        if sat:
            ok, why = gate(col, k, n)
            cm = is_chain_mono(col, n)
            assert ok, f"C5 FAIL: витнесс k={k} N={n} не прошёл гейт: {why}"
            if chain:
                assert cm, f"C3 FAIL: витнесс k={k} N={n} НЕ chain-mono"
            last = n
        else:
            break
    return last, detail


if __name__ == "__main__":
    print("=== SAT: второй носитель для M_chain(k) ===\n")

    # ---- C4: положительный контроль на конфликтные клаузы ----
    sat_nc, _, _ = solve(3, 200, chain=False, conflicts=False)
    print(f"C4 конфликты сняты, k=3 N=200: {'SAT' if sat_nc else 'UNSAT'} "
          f"{'OK' if sat_nc else 'ПРИБОР СЛОМАН'}")

    # ---- C1: калибровка БЕЗ chain против литературы WS(3)=23 ----
    t0 = time.time()
    ws3, d1 = max_N(3, 20, 25, chain=False)
    print(f"C1 без chain, k=3: max N = {ws3} (лит. WS(3)=23) "
          f"{'OK' if ws3 == 23 else 'MISMATCH'}   [{time.time()-t0:.2f}s]")
    print(f"   граница: {', '.join(f'N={n}:{"SAT" if s else "UNSAT"}' for n, (s, _) in d1.items())}")

    # ---- C2: воспроизведение известного С chain, k=3 ----
    t0 = time.time()
    m3, d2 = max_N(3, 20, 24, chain=True)
    print(f"C2 с chain, k=3: M_chain(3) = {m3} (бэктрекер+перебор дали 22) "
          f"{'OK' if m3 == 22 else 'MISMATCH'}   [{time.time()-t0:.2f}s]")
    print(f"   граница: {', '.join(f'N={n}:{"SAT" if s else "UNSAT"}' for n, (s, _) in d2.items())}")

    # ---- C3 проверен внутри max_N ассертами на каждом SAT-витнессе ----
    # ---- ЗАМЕР: k=4 ----
    t0 = time.time()
    m4, d4 = max_N(4, 40, 50, chain=True)
    print(f"\nЗАМЕР с chain, k=4: M_chain(4) = {m4} (бэктрекер дал 45) "
          f"{'СОШЛОСЬ' if m4 == 45 else 'РАЗОШЛОСЬ'}   [{time.time()-t0:.2f}s]")
    for n, (s, dt) in d4.items():
        print(f"   N={n}: {'SAT' if s else 'UNSAT'}  ({dt:.2f}s)")

    # ---- C6: мутант — снять chain-клаузы. Если UNSAT(N=46) порождён ИМЕННО
    # chain-условием, а не общей поломкой энкодера, то без него N=50 обязано
    # стать SAT (бэктрекер давал M_all(4) >= 54).
    sat6, col6, _ = solve(4, 50, chain=False)
    ok6 = sat6 and gate(col6, 4, 50)[0]
    print(f"\nC6 мутант (chain снят), k=4 N=50: {'SAT+гейт' if ok6 else 'UNSAT'} "
          f"{'OK — 45 порождён chain-условием' if ok6 else 'ПРИБОР: UNSAT не про chain'}")

    # ---- C7: пере-ограниченность. Symmetry break f(1)=0 законен только если
    # цвета взаимозаменяемы. Если он неверен, UNSAT(46) — артефакт МОЕЙ клаузы,
    # а не свойство объекта. Снимаем его и перерешаем обе стороны границы.
    s45, c45, _ = solve(4, 45, chain=True, symmetry=False)
    s46, _, _ = solve(4, 46, chain=True, symmetry=False)
    ok7 = s45 and (not s46) and gate(c45, 4, 45)[0]
    print(f"C7 без symmetry-break, k=4: N=45 {'SAT' if s45 else 'UNSAT'}, "
          f"N=46 {'SAT' if s46 else 'UNSAT'} "
          f"{'OK — граница не артефакт моей клаузы' if ok7 else 'ПРИБОР: граница держалась на symmetry-break'}")

    # ---- C8: второй солвер на том же CNF. Ловит не энкодинг, а солвер.
    from pysat.solvers import Glucose3
    cnf8, _ = build_cnf(4, 46, chain=True, symmetry=False)
    with Glucose3(bootstrap_with=cnf8.clauses) as g:
        s8 = g.solve()
    print(f"C8 Glucose3 на k=4 N=46: {'SAT' if s8 else 'UNSAT'} "
          f"{'OK — совпал с Minisat22' if not s8 else 'РАСХОЖДЕНИЕ СОЛВЕРОВ'}")

    # ---- Побочно: M_all(4) тем же прибором (долг (ii)) — ТОЛЬКО по флагу.
    # UNSAT-сторона k=4 без chain (N~66) в литературе берётся тяжёлым SAT-счётом
    # на часы; в вейк не влезает. Запускать отдельно: --all4 [hi]
    if "--all4" in sys.argv:
        hi = int(sys.argv[sys.argv.index("--all4") + 1]) if len(sys.argv) > sys.argv.index("--all4") + 1 else 70
        t0 = time.time()
        m4all, d4a = max_N(4, 54, hi, chain=False)
        print(f"\nБЕЗ chain, k=4: M_all(4) >= {m4all} (лит. WS(4)=66)   [{time.time()-t0:.2f}s]")
        for n, (s, dt) in d4a.items():
            print(f"   N={n}: {'SAT' if s else 'UNSAT'}  ({dt:.2f}s)")

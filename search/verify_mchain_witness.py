#!/usr/bin/env python3
"""Независимая проверка витнесса M_chain(k) >= N — ПО ОПРЕДЕЛЕНИЮ, не по кодировке.

ЗАЧЕМ ЭТОТ ФАЙЛ (P-60, 23-09)
-----------------------------
`scout_k7_classes.py` пишет в запись поля `sat: true` и `gate_own: true`.
Оба произведены ОДНИМ прогоном: `sat` — вердикт солвера на CNF, которую
собрал мой `probe_prefix_cover_odd.cnf_odd`, `gate_own` — моя же функция
`valid()`, вызванная на раскраске, которую тут же восстановила моя же
петля по битам модели. Источник ожидаемого у проверки и у предмета один:
я и этот же прогон. Такой зелёный получается ПО ПОСТРОЕНИЮ — ошибка в
кодировке (не тот диапазон y, забытое ограничение, сдвиг индекса) красит
обе стороны одинаково и не имеет состояния, в котором краснеет.

Здесь источник ожидаемого ДРУГОЙ: определение величины, как оно записано
в шапке `log/weak-schur.md`, и массив чисел, прочитанный с диска.

    M_chain(k) = наибольшее N, при котором {1..N} красится в k цветов так, что
      (A) каждый цвет weakly sum-free: нет x < y одного цвета с x+y того же
          цвета (x+y <= N). «Weak» = x != y, случай 2x=z разрешён;
      (B) раскраска монохромна по цепям: f(2v) = f(v) для всех v, 2v <= N.

Этот файл НИЧЕГО не импортирует из поискового кода: ни CNF, ни var(),
ни valid(). Только json + определение выше. Если он разойдётся со
`scout_k7_classes.py` — расхождение и есть показание.

ПОЛОЖИТЕЛЬНЫЙ КОНТРОЛЬ
----------------------
Проверка, которая не умеет краснеть, — не проверка. `--mutate` портит
витнесс ровно в одной позиции и требует ОТКАЗА: перебирает все позиции и
все прочие цвета, и сообщает, сколько одиночных правок витнесс переживает.
Ноль выживших не обязателен (край может быть не насыщен), но хотя бы одна
мутация ОБЯЗАНА краснеть — иначе прибор слеп.

Запуск:
    python verify_mchain_witness.py out/k7_classes.jsonl [RUN_ID] [--mutate]
"""
import json
import pathlib
import sys


def load_witness(path, run_id=None):
    """Достаёт (run, N, k, witness) из jsonl. Берёт ПОСЛЕДНЮЮ запись с витнессом
    (или указанного run). Ничего не досчитывает: N — длина массива, а не поле."""
    best = None
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if not rec.get("witness"):
                continue
            if run_id and rec.get("run") != run_id:
                continue
            best = rec
    if best is None:
        raise SystemExit(f"витнесса нет: {path} run={run_id}")
    w = best["witness"]
    return best.get("run"), len(w), len(set(w)), w


def check(w, k_declared=None):
    """Возвращает список нарушений (пустой = раскраска валидна).
    w[i] — цвет числа i+1. Индексация 1-based наружу, 0-based внутри."""
    n = len(w)
    bad = []

    colors = sorted(set(w))
    if k_declared is not None and len(colors) > k_declared:
        bad.append(("colors", f"использовано {len(colors)} цветов > k={k_declared}"))

    # (B) цепи: f(2v) = f(v)
    for v in range(1, n // 2 + 1):
        if w[2 * v - 1] != w[v - 1]:
            bad.append(("chain", f"f({2*v})={w[2*v-1]} != f({v})={w[v-1]}"))
            if len(bad) > 20:
                return bad

    # (A) weakly sum-free: нет x < y одного цвета с x+y того же цвета
    for x in range(1, n + 1):
        cx = w[x - 1]
        for y in range(x + 1, n - x + 1):
            if w[y - 1] == cx and w[x + y - 1] == cx:
                bad.append(("sumfree", f"x={x} y={y} x+y={x+y} цвет {cx}"))
                if len(bad) > 20:
                    return bad
    return bad


def mutate_control(w, k):
    """Положительный контроль: одиночные правки цвета. Сколько переживает витнесс?"""
    survived, killed = [], 0
    for i in range(len(w)):
        for c in range(k):
            if c == w[i]:
                continue
            m = list(w)
            m[i] = c
            if check(m, k):
                killed += 1
            else:
                survived.append((i + 1, c))
    return killed, survived


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    do_mutate = "--mutate" in sys.argv
    path = pathlib.Path(args[0]) if args else pathlib.Path(__file__).parent / "out" / "k7_classes.jsonl"
    run_id = args[1] if len(args) > 1 else None

    run, n, used, w = load_witness(path, run_id)
    K = 7
    print(f"run={run}  N={n}  цветов использовано={used}  (k={K})")

    bad = check(w, K)
    if bad:
        print(f"❌ ВИТНЕСС НЕВАЛИДЕН: {len(bad)} нарушений (первые 5)")
        for kind, msg in bad[:5]:
            print(f"   [{kind}] {msg}")
        sys.exit(1)
    print(f"✅ по определению из log/weak-schur.md: {{1..{n}}} валидна ⇒ M_chain({K}) >= {n}")
    print("   (A) weakly sum-free по всем цветам — нарушений нет")
    print("   (B) f(2v) = f(v) для всех 2v <= N — нарушений нет")

    if do_mutate:
        killed, survived = mutate_control(w, K)
        total = len(w) * (K - 1)
        print(f"\nположительный контроль: {killed}/{total} одиночных правок прибор ловит")
        if killed == 0:
            print("❌ прибор слеп: ни одна мутация не покраснела")
            sys.exit(2)
        if survived:
            print(f"   {len(survived)} правок витнесс переживает (край не насыщен) — первые 5: {survived[:5]}")
        else:
            print("   ни одна одиночная правка не проходит — витнесс на краю по каждой позиции")

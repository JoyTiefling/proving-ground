"""
M_chain(k) ПОДЪЁМОМ, а не лобовым solve — инкрементальный SAT-подъём по N.

ЧТО НЕ СРАБОТАЛО 06-09 18:00.  `search/sat_chain_mono.py` решает каждое N с
нуля: строит CNF, отдаёт минисату, выбрасывает всё выученное, берёт следующее N.
На k<=5 это бесплатно. На k=6 SAT-сторона взорвалась ЗАДОЛГО до границы:
N=100 -> 0.01 s, N=120 -> 0.06 s, N=140 -> 16.8 s, N=150 и N=160 сняты
таймаутом. Замер кончился вилкой M_chain(6) >= 140 — и, что важнее, у 150/160
НЕТ вердикта, у них есть только истёкшее время (#3961: ноль работающего
механизма и молчание не дошедшего дают один экран).

ЧЕМ ЭТОТ ПРИБОР ОТЛИЧАЕТСЯ.  Наблюдение, на котором всё держится:

    CNF(k, N) = CNF(k, N-1) + клаузы, порождённые ТОЛЬКО элементом N.

Проверяется по построению: (а) нумерация переменных var(v,c)=(v-1)*k+c+1 от N
не зависит; (б) конфликтная клауза для тройки x<y, z=x+y живёт целиком внутри
[1..z], поэтому добавление z=N исчерпывает все новые тройки; (в) chain-клауза
для чётного N связывает N и N/2. Значит один и тот же экземпляр солвера может
ползти вверх по N, добавляя клаузы и СОХРАНЯЯ выученное: конфликтные клаузы,
активности переменных и — главное — phase saving, то есть найденная раскраска
[1..N-1] становится стартовой точкой поиска для [1..N].

Это и есть «подъём от витнесса»: не «повторить лобовой solve дольше», а сменить
форму прибора. Утверждение о предмете при этом ТО ЖЕ САМОЕ (CNF идентичен),
меняется только цена. Поэтому подъём не является вторым носителем истины — он
второй носитель ДОСТИЖИМОСТИ. Расхождение вердикта с sat_chain_mono означало бы
дефект здесь, а не находку; ровно это и проверяет C2/C3.

ТРЁХЗНАЧНЫЙ ВЫВОД — ВСТРОЕН, А НЕ ДОПИСАН В ПРОЗЕ.  Каждый шаг возвращает
SAT / UNSAT / UNKNOWN(бюджет исчерпан). Прошлый прибор возвращал два значения,
и разделение «не дошёл» от «UNSAT» жило в моей аккуратности при письме в журнал.
Дисциплина, которая держится на авторе, не имеет красного состояния (#4030):
здесь UNKNOWN — значение типа, лестница печатается поимённо, а итог называется
вилкой, если верхняя сторона не имеет вердикта.

КОНТРОЛИ (без них замер пуст; #4053 — на зрелом рубеже отказ мигрирует в ПРИБОР).
  C0  ИНКРЕМЕНТ == СБОРКА С НУЛЯ. Мультимножество клауз, накопленное подъёмом до
      N, обязано совпасть с `sat_chain_mono.build_cnf(k, N)` клауза-в-клаузу
      (после канонизации порядка). Это единственный контроль, проверяющий саму
      идею файла. Не сойдётся — всё ниже недействительно.
  C1  бюджет действует и UNKNOWN достижим — на НЕТРИВИАЛЬНОМ экземпляре
      (k=5 N=90): 1 конфликт -> UNKNOWN, 1e7 -> UNSAT. На тривиальном этот
      контроль был бы зелёным и у прибора, где бюджет ни на что не влияет.
  C2  подъём k=3 обязан встать ровно на 22 (SAT 22, UNSAT 23) — три прежних
      носителя (перебор 3^12, бэктрекер, лобовой SAT).
  C3  подъём k=5 обязан встать ровно на 89 (SAT 89, UNSAT 90).
  C4  каждый SAT-витнесс проходит ВНЕШНИЙ гейт verifiers/weak_schur.py и
      независимую проверку chain-mono (читается по раскраске, не по поиску).
  C5  мутант: с сорванной chain-клаузой подъём k=3 обязан уйти ЗА 22 (до 23).
      Ловит случай «граница порождена не chain-условием, а поломкой энкодера».
  C6  параметр ОТОБРАЖЕНИЯ не двигает замер: две величины `lo` обязаны дать
      одинаковую лестницу. Родился из дефекта, а не из предусмотрительности.
  C7  лестница ВОСПРОИЗВОДИМА: два прогона на тесном бюджете совпадают
      посимвольно. Тоже родился из дефекта (секундный бюджет).

C6 и C7 — не гигиена, а единственные красные состояния для двух дефектов,
которые по построению выглядели как настройки, а не как ошибки (#4030: дефект
в ПОРЯДКЕ ДЕЙСТВИЙ не покрывается ничем, пока не переведён в носитель).

Run:  python search/chain_lift.py                 (контроли + замер k=6)
      python search/chain_lift.py --k 6 --hi 200 --step-budget 500000
Exit: 0 все контроли отработали, 1 контроль упал (прибор под подозрением).
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))
sys.path.insert(0, str(_HERE))

from verifiers.weak_schur import verify_weak_schur  # noqa: E402  ГЕЙТ, не тронут
from pysat.solvers import Minisat22  # noqa: E402

import receipts  # noqa: E402
from sat_chain_mono import build_cnf  # noqa: E402  сравнение с лобовой сборкой

SAT, UNSAT, UNKNOWN = "SAT", "UNSAT", "UNKNOWN"


def var(v: int, c: int, k: int) -> int:
    """Та же нумерация, что в sat_chain_mono. От N не зависит — это и делает
    подъём возможным."""
    return (v - 1) * k + c + 1


def clauses_for_element(v: int, k: int, chain: bool = True,
                        conflicts: bool = True) -> List[List[int]]:
    """ВСЕ клаузы, которые появляются при расширении [1..v-1] до [1..v].

    ALO/AMO для v; конфликтные тройки с z=v (x<y строго => WEAK Schur);
    chain-эквивалентность для чётного v. Ничего, что смотрит вверх на v+1.
    """
    out: List[List[int]] = [[var(v, c, k) for c in range(k)]]
    for c1 in range(k):
        for c2 in range(c1 + 1, k):
            out.append([-var(v, c1, k), -var(v, c2, k)])

    if conflicts and v >= 3:
        x = 1
        while 2 * x < v:
            y = v - x
            for c in range(k):
                out.append([-var(x, c, k), -var(y, c, k), -var(v, c, k)])
            x += 1

    if chain and v % 2 == 0:
        h = v // 2
        for c in range(k):
            out.append([-var(v, c, k), var(h, c, k)])
            out.append([var(v, c, k), -var(h, c, k)])

    return out


def _canon(clauses) -> List[Tuple[int, ...]]:
    """Канонизация для сравнения мультимножеств клауз."""
    return sorted(tuple(sorted(cl)) for cl in clauses)


def solve_budgeted(solver, budget_conflicts: int) -> Tuple[str, Optional[list]]:
    """Трёхзначный solve. Возвращает (SAT|UNSAT|UNKNOWN, model|None).

    БЮДЖЕТ В КОНФЛИКТАХ, НЕ В СЕКУНДАХ. Смена сделана из-за двух дефектов,
    пойманных 06-09 20:00 на первой же версии файла. Дефект (2) она чинит;
    дефект (1) — НЕТ, и это записано здесь, а не заглажено:

    (1) СЕГФОЛТ — и МОЯ ДИАГНОЗ ЕГО БЫЛ НЕВЕРЕН, что здесь важнее самого
        падения. Настенный бюджет был сделан таймером, дёргающим
        Minisat22.interrupt() из другого потока; `timer.cancel()` не отменяет
        уже начавшийся вызов. Объяснение «гонка потока» было связным,
        механизм назван поимённо — и опровергнуто мутантом: таймер убран,
        поток исчез, прогон СНОВА упал с exit=139 на том же участке N~143-145.
        Связность объяснения засчиталась мне за его связь с предметом (#3996:
        подробность усиливает подмену). Причина падения на 06-09 НЕ УСТАНОВЛЕНА;
        воспроизводимо: Minisat22 + add_clause после solve_limited на k=6.
        Что установлено и важно: падение печатает правдоподобную полную
        лестницу и умирает в пайп — ноль от падения и вывод работающего
        механизма дают один экран (#3961).
    (2) НЕВОСПРОИЗВОДИМОСТЬ. Секундный бюджет делает вердикт функцией загрузки
        машины: тот же N при том же коде получает UNKNOWN или SAT в
        зависимости от того, что ещё крутится рядом. Такая лестница не
        является замером — её нельзя перепрогнать и сверить.

    Бюджет в конфликтах детерминирован и однопоточен. Цена: «сколько это в
    секундах» больше не константа. Она и не была ею.
    """
    if budget_conflicts <= 0:
        return UNKNOWN, None
    solver.conf_budget(int(budget_conflicts))
    res = solver.solve_limited()
    if res is True:
        return SAT, solver.get_model()
    if res is False:
        return UNSAT, None
    return UNKNOWN, None


def model_to_coloring(model, k: int, N: int) -> List[int]:
    pos = set(l for l in model if l > 0)
    col = [0] * (N + 1)
    for v in range(1, N + 1):
        for c in range(k):
            if var(v, c, k) in pos:
                col[v] = c
                break
    return col


def to_partition(col: List[int], k: int, N: int) -> List[List[int]]:
    parts: List[List[int]] = [[] for _ in range(k)]
    for v in range(1, N + 1):
        parts[col[v]].append(v)
    return parts


def is_chain_mono(col: List[int], N: int) -> bool:
    """Читается по раскраске, не по поиску — независимая проверка свойства."""
    return all(col[v] == col[v // 2] for v in range(2, N + 1, 2))


def climb(k: int, hi: int, lo: int = 1, chain: bool = True, conflicts: bool = True,
          symmetry: bool = True, step_budget: int = 200000,
          total_budget: float = 600.0, gate_every: bool = True,
          verbose: bool = False, live_path: str = "") -> Dict:
    """Инкрементальный подъём по N. Один солвер, клаузы дописываются.

    Возвращает лестницу поимённо: для каждого N вердикт и время.
    Останавливается на первом UNSAT (выше SAT быть не может: сужение валидной
    раскраски [1..N] на [1..N'] при N'<N валидно => SAT монотонен вниз),
    либо на первом UNKNOWN, либо по исчерпании общего бюджета.
    """
    ladder: List[Dict] = []
    best_witness = None      # раскраска при last_sat -- СОХРАНЯЕТСЯ, не печатается
    last_sat = None
    first_unsat = None
    stalled_at = None
    t_start = time.time()

    s = Minisat22()
    added: List[List[int]] = []
    if symmetry:
        cl = [var(1, 0, k)]
        s.add_clause(cl)
        added.append(cl)

    for n in range(1, hi + 1):
        for cl in clauses_for_element(n, k, chain=chain, conflicts=conflicts):
            s.add_clause(cl)
            added.append(cl)

        # ЗАМЕРЕНО 06-09 20:00, на себе. Здесь стояло `if n < lo: continue` —
        # пропустить solve на ступенях ниже порога печати. `lo` документирован
        # как ПАРАМЕТР ОТОБРАЖЕНИЯ, а управлял работой: два прогона одного кода
        # разошлись на N=144 (UNKNOWN за 25 s против SAT за 0.001 s), потому что
        # один решал ступени 130..139 по дороге, а другой нет. Решение каждой
        # ступени — это и есть алгоритм: выученное на N переносится на N+1
        # (phase saving + конфликтные клаузы). Пропуск ступеней превращает
        # подъём обратно в лобовой solve, молча и под видом настройки вывода.
        # Поэтому solve вызывается на КАЖДОМ N, а `lo` режет только печать.

        if time.time() - t_start > total_budget:
            stalled_at = n
            ladder.append({"N": n, "verdict": UNKNOWN, "s": 0.0,
                           "why": "wall-clock stop (НЕ бюджет шага)"})
            break

        t0 = time.time()
        verdict, model = solve_budgeted(s, step_budget)
        dt = time.time() - t0
        row = {"N": n, "verdict": verdict, "s": round(dt, 3)}

        if verdict == SAT:
            if gate_every or n == hi:
                col = model_to_coloring(model, k, N=n)
                ok, why = verify_weak_schur(to_partition(col, k, n), n)
                cm = is_chain_mono(col, n)
                row["gate"] = bool(ok)
                row["chain_mono"] = cm
                if not ok or (chain and not cm):
                    row["FATAL"] = f"C4: гейт={ok} ({why}) chain_mono={cm}"
                    ladder.append(row)
                    s.delete()
                    return {"ladder": ladder, "last_sat": last_sat,
                            "first_unsat": first_unsat, "stalled_at": n,
                            "c4_failed": True}
            last_sat = n
            # Витнесс кладётся В ЧЕК, а не в stdout. 18-07 этот репозиторий уже
            # потерял SAT-витнесс |D|=36 после 4.7 часов счёта ровно так: скрипт
            # печатал, обёртка сохраняла только статус. Число без носителя не
            # является установленным (#3706), сколько бы раз я его ни видела.
            best_witness = model_to_coloring(model, k, N=n)
            # ЖИВОЙ СЛЕД НА ДИСКЕ ПОСЛЕ КАЖДОЙ СТУПЕНИ. Прибор падает
            # сегфолтом (см. solve_budgeted), причина не установлена, и падение
            # неотличимо от нормального конца по экрану. Пока причина не
            # найдена, лестница обязана переживать смерть процесса: иначе
            # единственный носитель результата -- буфер stdout убитого процесса.
            if live_path:
                try:
                    with open(live_path, "w", encoding="utf-8") as fh:
                        json.dump({"live": True, "k": k, "reached_N": n,
                                   "last_sat": n, "witness": best_witness[1:],
                                   "ladder": ladder + [row]}, fh, ensure_ascii=False)
                except OSError:
                    pass
        elif verdict == UNSAT:
            first_unsat = n
            ladder.append(row)
            break
        else:
            stalled_at = n
            row["why"] = f"conflict budget {step_budget}"
            ladder.append(row)
            break

        ladder.append(row)
        if verbose and (dt > 1.0 or n % 20 == 0):
            print(f"    N={n}: {verdict} ({dt:.2f}s)", flush=True)

    s.delete()
    return {"ladder": ladder, "last_sat": last_sat, "first_unsat": first_unsat,
            "stalled_at": stalled_at, "witness": best_witness,
            "elapsed_s": round(time.time() - t_start, 2)}


def verdict_line(res: Dict) -> str:
    """Как называется исход. Вилка называется вилкой."""
    if res["first_unsat"] is not None:
        return f"M = {res['last_sat']} (SAT {res['last_sat']}, UNSAT {res['first_unsat']})"
    if res["last_sat"] is not None:
        return (f"M >= {res['last_sat']} — ВИЛКА: у N={res['stalled_at']} нет вердикта, "
                f"есть истёкшее время")
    return "нет ни одного SAT в окне"


# ----------------------------------------------------------------- контроли

def controls(step_budget: int) -> Tuple[bool, List[Dict]]:
    log: List[Dict] = []
    ok_all = True

    # C0 -- инкремент == сборка с нуля. Единственный контроль на саму идею файла.
    for (k, N) in ((3, 24), (5, 40), (6, 30)):
        acc: List[List[int]] = [[var(1, 0, k)]]
        for v in range(1, N + 1):
            acc.extend(clauses_for_element(v, k))
        fresh, _ = build_cnf(k, N, chain=True, conflicts=True, symmetry=True)
        same = _canon(acc) == _canon(fresh.clauses)
        ok_all &= same
        log.append({"control": "C0", "k": k, "N": N, "n_clauses": len(acc), "pass": same})
        print(f"C0 инкремент==сборка k={k} N={N}: {len(acc)} клауз "
              f"{'OK' if same else 'РАСХОЖДЕНИЕ — всё ниже недействительно'}")

    # C1 -- бюджет ДЕЙСТВУЕТ и UNKNOWN достижим. Проверяется на заведомо
    # нетривиальном экземпляре (k=5 N=90, UNSAT): при бюджете 1 конфликт обязан
    # быть UNKNOWN, при большом -- UNSAT. Тривиальный экземпляр тут не годится:
    # он решается за 0 конфликтов и вернул бы вердикт при любом бюджете, т.е.
    # контроль был бы зелёным даже у прибора, где бюджет ни на что не влияет.
    s = Minisat22()
    s.add_clause([var(1, 0, 5)])
    for v in range(1, 91):
        for cl in clauses_for_element(v, 5):
            s.add_clause(cl)
    v0, _ = solve_budgeted(s, 1)
    v1, _ = solve_budgeted(s, 10 ** 7)
    s.delete()
    c1 = (v0 == UNKNOWN and v1 == UNSAT)
    ok_all &= c1
    log.append({"control": "C1", "budget_1": v0, "budget_1e7": v1, "pass": c1})
    print(f"C1 бюджет действует (k=5 N=90): 1 конфликт -> {v0}, 1e7 -> {v1} "
          f"{'OK' if c1 else 'ПРИБОР: UNKNOWN недостижим, вывод двузначный'}")

    # C2 -- k=3 обязан встать на 22.
    r3 = climb(3, hi=26, lo=18, step_budget=step_budget, total_budget=120)
    c2 = (r3["last_sat"] == 22 and r3["first_unsat"] == 23)
    ok_all &= c2
    log.append({"control": "C2", "k": 3, **{x: r3[x] for x in ("last_sat", "first_unsat")},
                "pass": c2})
    print(f"C2 подъём k=3: {verdict_line(r3)} "
          f"{'OK (сошлось с тремя носителями)' if c2 else 'РАЗОШЛОСЬ с прежними носителями'}")

    # C5 -- мутант: сорвать chain-клаузу, граница обязана сдвинуться вверх.
    r3m = climb(3, hi=24, lo=18, chain=False, step_budget=step_budget, total_budget=120)
    c5 = (r3m["last_sat"] == 23)
    ok_all &= c5
    log.append({"control": "C5", "mutant": "chain off", "last_sat": r3m["last_sat"],
                "first_unsat": r3m["first_unsat"], "pass": c5})
    print(f"C5 мутант (chain снят) k=3: {verdict_line(r3m)} "
          f"{'OK — 22 порождён chain-условием' if c5 else 'ПРИБОР: граница не про chain'}")

    # C6 -- ПАРАМЕТР ОТОБРАЖЕНИЯ НЕ ДВИГАЕТ ЗАМЕР. Родился из дефекта, не из
    # предусмотрительности: 06-09 два прогона одного кода разошлись на N=144,
    # потому что `lo` резал не печать, а вызовы solve. У такого дефекта не было
    # красного состояния — он выглядел как настройка вывода. Теперь есть: две
    # величины lo обязаны дать ПОСИМВОЛЬНО одинаковую лестницу вердиктов.
    la = climb(4, hi=48, lo=1, step_budget=step_budget, total_budget=120)
    lb = climb(4, hi=48, lo=40, step_budget=step_budget, total_budget=120)
    seq_a = [(r["N"], r["verdict"]) for r in la["ladder"]]
    seq_b = [(r["N"], r["verdict"]) for r in lb["ladder"]]
    c6 = (seq_a == seq_b) and la["last_sat"] == lb["last_sat"] == 45
    ok_all &= c6
    log.append({"control": "C6", "k": 4, "lo_a": 1, "lo_b": 40,
                "last_sat_a": la["last_sat"], "last_sat_b": lb["last_sat"],
                "ladders_identical": seq_a == seq_b, "pass": c6})
    print(f"C6 lo не двигает замер, k=4: lo=1 -> {verdict_line(la)} | "
          f"lo=40 -> {verdict_line(lb)} "
          f"{'OK' if c6 else 'ПРИБОР: параметр печати управляет работой'}")

    # C7 -- ЛЕСТНИЦА ВОСПРОИЗВОДИМА. Родился из дефекта: секундный бюджет делал
    # вердикт функцией загрузки машины, и перепрогнать замер было нельзя. Два
    # прогона на тесном бюджете (много UNKNOWN) обязаны совпасть посимвольно.
    da = climb(6, hi=150, lo=1, step_budget=3000, total_budget=120)
    db = climb(6, hi=150, lo=1, step_budget=3000, total_budget=120)
    sa = [(r["N"], r["verdict"]) for r in da["ladder"]]
    sb = [(r["N"], r["verdict"]) for r in db["ladder"]]
    c7 = (sa == sb)
    ok_all &= c7
    log.append({"control": "C7", "identical": c7, "stalled_a": da["stalled_at"],
                "stalled_b": db["stalled_at"], "last_sat_a": da["last_sat"],
                "pass": c7})
    print(f"C7 лестница воспроизводима (k=6, бюджет 3000 конфл.): "
          f"a -> {verdict_line(da)} | b -> {verdict_line(db)} "
          f"{'OK' if c7 else 'ПРИБОР: замер зависит от загрузки машины'}")

    # C3 -- k=5 обязан встать на 89.
    t0 = time.time()
    r5 = climb(5, hi=92, lo=85, step_budget=step_budget, total_budget=240)
    c3 = (r5["last_sat"] == 89 and r5["first_unsat"] == 90)
    ok_all &= c3
    log.append({"control": "C3", "k": 5, **{x: r5[x] for x in ("last_sat", "first_unsat")},
                "pass": c3, "elapsed_s": round(time.time() - t0, 2)})
    print(f"C3 подъём k=5: {verdict_line(r5)}  [{time.time()-t0:.1f}s] "
          f"{'OK (сошлось с лобовым SAT и бэктрекером)' if c3 else 'РАЗОШЛОСЬ'}")

    return ok_all, log


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=6)
    ap.add_argument("--hi", type=int, default=200)
    ap.add_argument("--lo", type=int, default=100, help="с какого N печатать лестницу")
    ap.add_argument("--step-budget", type=int, default=200000,
                    help="бюджет ШАГА в КОНФЛИКТАХ (детерминирован), не в секундах")
    ap.add_argument("--total-budget", type=float, default=600.0,
                    help="настенный предохранитель на весь подъём, секунды")
    ap.add_argument("--skip-controls", action="store_true")
    ap.add_argument("--out", type=str, default="")
    ap.add_argument("--no-out", action="store_true")
    args = ap.parse_args()

    out_path = receipts.resolve_out(args, __file__, N=args.hi, k=args.k)
    receipts.probe_writable(out_path)

    print("=== M_chain(k) подъёмом: инкрементальный SAT ===\n")
    ctl_ok, ctl_log = (True, []) if args.skip_controls else controls(step_budget=200000)
    if not args.skip_controls:
        print()
    if not ctl_ok:
        print("КОНТРОЛЬ УПАЛ — замер ниже НЕ проводится (прибор под подозрением).")
        receipts.write_receipt(out_path, {"controls": ctl_log, "controls_pass": False,
                                          "measurement": None})
        sys.exit(1)

    print(f"ЗАМЕР: подъём k={args.k} до N={args.hi} "
          f"(шаг <= {args.step_budget} конфл., предохранитель {args.total_budget}s)")
    t0 = time.time()
    live_path = (os.path.splitext(out_path)[0] + ".live.json") if out_path else ""
    res = climb(args.k, hi=args.hi, lo=args.lo, step_budget=args.step_budget,
                total_budget=args.total_budget, verbose=True, live_path=live_path)
    print(f"\nЛестница (от N={args.lo}):")
    for row in res["ladder"]:
        if row["N"] < args.lo:
            continue
        if row["verdict"] != SAT or row["s"] >= 0.5 or row["N"] >= res["ladder"][-1]["N"] - 3:
            print(f"   N={row['N']}: {row['verdict']}  ({row['s']}s)"
                  + (f"  [{row.get('why')}]" if row.get("why") else ""))
    print(f"\nИТОГ k={args.k}: {verdict_line(res)}   [{time.time()-t0:.1f}s]")

    receipts.write_receipt(out_path, {
        "instrument": "chain_lift.py (incremental climb)",
        "controls": ctl_log,
        "controls_pass": ctl_ok,
        "k": args.k, "hi": args.hi, "lo": args.lo,
        "step_budget_conflicts": args.step_budget, "total_budget_s": args.total_budget,
        "ladder": res["ladder"],
        "last_sat": res["last_sat"], "first_unsat": res["first_unsat"],
        "stalled_at": res["stalled_at"],
        "verdict": verdict_line(res),
        # Витнесс наибольшего замеренного SAT: список цветов [1..last_sat].
        # Перепроверяется независимо: verifiers/weak_schur.verify_weak_schur
        # на разбиении + f(2v)==f(v) по самой раскраске.
        "witness_N": res["last_sat"],
        "witness": (res["witness"][1:] if res.get("witness") else None),
    })
    sys.exit(0)

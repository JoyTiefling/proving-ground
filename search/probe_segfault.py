"""РАЗЛИЧИТЕЛЬ падения chain_lift: дефект СВЯЗКИ или дефект ИДЕИ подъёма?

ЗАЧЕМ.  06-09 20:00 инкрементальный подъём (`search/chain_lift.py`) дважды упал
на участке N~143-145 с ненулевым кодом, печатая перед смертью правдоподобную
полную лестницу. Я объяснила падение гонкой потока-таймера с солвером —
объяснение было связным, механизм назван поимённо — и мутант его опроверг:
таймер убран, поток исчез, упало снова. Причина осталась НЕ УСТАНОВЛЕННОЙ, а
диагноз всё это время звучал как знание (#3996: внутренняя связность объяснения
засчитывается за его связь с предметом).

ЧТО ЭТОТ ПРИБОР РАЗЛИЧАЕТ.  Ровно две вещи, и он обязан уметь показать обе:
  (S) ДЕФЕКТ СВЯЗКИ — падает конкретная реализация солвера/обёртки. Тогда
      другой солвер на ТЕХ ЖЕ клаузах поднимается выше точки падения.
  (I) ДЕФЕКТ ИДЕИ — падает сам способ (инкрементальное дописывание клауз после
      бюджетного solve, снятие модели каждой ступени). Тогда падают ВСЕ
      солверы примерно на одном участке, и различие надо искать в способе
      вызова, а не в имени библиотеки.
Третий исход тоже возможен и его нельзя выдавить в первые два: НИКТО не упал —
значит падение зависит от чего-то, что этот прибор не воспроизводит, и оно
остаётся неустановленным (а не «исправленным»).

КАК УСТРОЕН.  Каждая ячейка матрицы — ОТДЕЛЬНЫЙ процесс: падение ребёнка обязано
быть данными, а не смертью замера. Ребёнок пишет живой след после каждой ступени
(#3961 на себе: собственный ноль от падения и нормальный конец дают один экран,
поэтому «докуда дошёл» читается с диска, а не из stdout умершего).

ПОЛОЖИТЕЛЬНЫЙ КОНТРОЛЬ.  Ячейка `--crash-now` намеренно роняет ребёнка на N=50.
Без неё «никто не упал» неотличимо от «драйвер не умеет видеть падение»: у
матрицы, где ни одна ячейка не красная, нет доказанного красного состояния.

ЗНАМЕНАТЕЛЬ.  Печатается число ячеек, дошедших до `--hi` без вердикта по
падению (истёк настенный предохранитель): такая ячейка НЕ является «прошла» —
она не дошла до участка, где падало (#4101: списочная выдача не умеет показать
собственный пропуск, поэтому остаток называется поимённо).

Run:  python search/probe_segfault.py                     (полная матрица)
      python search/probe_segfault.py --worker --solver Glucose3 --method limited
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))
sys.path.insert(0, str(_HERE))

from chain_lift import clauses_for_element, var  # noqa: E402  ТОТ ЖЕ энкодер

OUT_DIR = _HERE.parent / "out" / "segfault_probe"

# Имя -> класс берём по строке, чтобы отсутствие солвера в сборке было ДАННЫМИ
# (ячейка "не собран"), а не падением драйвера.
SOLVERS = ["Minisat22", "MinisatGH", "Glucose3", "Glucose42",
           "Cadical153", "Mergesat3", "Maplesat"]


def worker(solver_name: str, k: int, hi: int, budget: int, method: str,
           model_every: bool, wall: float, live_path: str, crash_now: int,
           hang_now: int = 0) -> int:
    from pysat.solvers import Solver

    s = Solver(name=solver_name.lower())
    s.add_clause([var(1, 0, k)])
    t0 = time.time()
    reached, last_sat, stop_why = 0, None, "hi reached"

    for n in range(1, hi + 1):
        for cl in clauses_for_element(n, k, chain=True, conflicts=True):
            s.add_clause(cl)
        if time.time() - t0 > wall:
            stop_why = "wall guard (НЕ вердикт: до участка падения не дошли)"
            break
        if crash_now and n == crash_now:
            # ПОЛОЖИТЕЛЬНЫЙ КОНТРОЛЬ №1: доказать, что драйвер видит ЖЁСТКУЮ смерть.
            # 13-09: было `ctypes.string_at(0)` — на Windows перехватывается как
            # OSError и даёт rc=1, то есть ОБЫЧНЫЙ traceback. Прибор, умеющий
            # видеть только traceback, прошёл бы такой контроль и ослеп бы ровно
            # на предмете: настоящий ACCESS_VIOLATION (rc=3221225477) убивает
            # процесс без исключения. Контроль обязан воспроизводить ТУ смерть,
            # которую ловит, а не похожую на неё. Урок прожит 13-09 00:00 в
            # соседнем probe_death_phase.py и НЕ доехал сюда сам (#4238).
            _write_live(live_path, solver_name, method, n, last_sat, "crash-now armed")
            import faulthandler
            faulthandler._sigsegv()
        if hang_now and n == hang_now:
            # ПОЛОЖИТЕЛЬНЫЙ КОНТРОЛЬ №2: ячейка, которая НЕ вернётся никогда.
            # Драйвер обязан её убить, назвать «не досмотрено», НЕ записать в
            # упавшие и всё равно выдать отчёт по остальным.
            _write_live(live_path, solver_name, method, n, last_sat, "hang-now armed")
            while True:
                time.sleep(3600)
        if method == "limited":
            s.conf_budget(int(budget))
            res = s.solve_limited()
        else:
            res = s.solve()
        reached = n
        if res is True:
            last_sat = n
            if model_every or n == hi:
                s.get_model()
        elif res is False:
            stop_why = f"UNSAT at {n}"
            break
        else:
            stop_why = f"UNKNOWN at {n} (бюджет {budget})"
            break
        _write_live(live_path, solver_name, method, reached, last_sat, "running")

    _write_live(live_path, solver_name, method, reached, last_sat, stop_why,
                done=True, elapsed=round(time.time() - t0, 2))
    s.delete()
    print(f"DONE {solver_name}/{method} reached={reached} last_sat={last_sat} why={stop_why}")
    return 0


def _write_live(path, solver, method, reached, last_sat, why, done=False, elapsed=None):
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"solver": solver, "method": method, "reached_N": reached,
                       "last_sat": last_sat, "why": why, "done": done,
                       "elapsed_s": elapsed}, fh, ensure_ascii=False)
    except OSError:
        pass


def run_cell(label: str, argv: List[str], hi: int, timeout: float) -> dict:
    """Одна ячейка = отдельный процесс. Ни один её исход не имеет права убить драйвер.

    13-09: до этой правки `timeout` был зашит константой 900 и НЕ ловился.
    Прогон C-006 упёрся в него на второй ячейке — и `TimeoutExpired` вылетел
    из main, унеся отчёт ЦЕЛИКОМ: результат уже досчитанной ячейки Mergesat3
    (N=146, last_sat=145, 683 с) уцелел только потому, что живой след пишется
    на диск по ходу — по случайности конструкции, сделанной для другого.
    Третья ячейка (Minisat22, та самая, ради которой всё затевалось) не
    запускалась вовсе. Прибор, у которого смерть ОДНОЙ ячейки стирает выдачу
    по ВСЕМ, отчитывается о нуле там, где у него есть данные.
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    live = OUT_DIR / f"{label}.live.json"
    if live.exists():
        live.unlink()
    cmd = [sys.executable, str(_HERE / "probe_segfault.py"), "--worker",
           "--live", str(live)] + argv
    t0 = time.time()
    killed = False
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        rc, err = p.returncode, (p.stderr or "")
    except subprocess.TimeoutExpired as e:
        killed = True
        rc = None
        raw = e.stderr or ""
        err = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
    dt = round(time.time() - t0, 1)
    state = {}
    if live.exists():
        try:
            state = json.loads(live.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            state = {}
    tail = err.strip().splitlines()
    return {"label": label, "rc": rc, "s": dt,
            "reached_N": state.get("reached_N"), "last_sat": state.get("last_sat"),
            "why": state.get("why"), "child_done": bool(state.get("done")),
            "stderr_tail": tail[-1] if tail else "",
            "killed_by_driver": killed, "driver_timeout_s": timeout,
            "hi": hi}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=6)
    ap.add_argument("--hi", type=int, default=160)
    ap.add_argument("--budget", type=int, default=200000)
    ap.add_argument("--wall", type=float, default=120.0)
    # ЗАМЕРЕНО 06-09 22:00, первым же прогоном. Ось СОЛВЕР в режиме `limited`
    # НИЧЕГО НЕ РАЗЛИЧИЛА: все шесть ячеек честно вернули rc=0, но встали на
    # N=135..144 по исчерпании бюджета, то есть НЕ ДОШЛИ до участка падения
    # (N~143-145). Зелёная строка означала «не проверялось», и отличить это от
    # «прошло» можно было ровно по одному месту — по знаменателю в ИТОГЕ
    # (#4101). Поэтому режим оси вынесен в параметр: различитель обязан уметь
    # встать туда, где предмет падает, иначе он меряет собственную дистанцию.
    ap.add_argument("--axis-method", choices=["limited", "plain"], default="limited",
                    help="метод для оси СОЛВЕР; plain = без бюджета, доходит до участка падения")
    ap.add_argument("--solvers", default="", help="через запятую; пусто = весь список")
    ap.add_argument("--skip-method-axis", action="store_true")
    ap.add_argument("--tag", default="", help="суффикс имени отчёта: прогоны НЕ затирают друг друга")
    ap.add_argument("--cell-timeout", type=float, default=0.0,
                    help="настенный предохранитель ДРАЙВЕРА на ячейку; 0 = --wall + запас")
    ap.add_argument("--hang-cell", action="store_true",
                    help="положительный контроль №2: добавить ячейку, которая зависнет навсегда")
    args = ap.parse_args()
    solvers = [s for s in args.solvers.split(",") if s] or SOLVERS

    # ДВА ПРЕДОХРАНИТЕЛЯ В ОДНОМ ПРИБОРЕ, и до 13-09 их никто не сверял:
    # ребёнку разрешалось --wall секунд, а родитель ждал зашитые 900. При
    # --wall 1500 убийство родителем было ГАРАНТИРОВАНО, то есть честный
    # вердикт ребёнка не мог прозвучать в принципе. Теперь предохранитель
    # драйвера ВЫВОДИТСЯ из детского и обязан быть больше него.
    cell_timeout = args.cell_timeout or (args.wall + 300.0)
    if cell_timeout <= args.wall:
        print(f"ПРИБОР НЕСОГЛАСОВАН: предохранитель драйвера {cell_timeout}s <= "
              f"детского --wall {args.wall}s. Ребёнок не успеет сказать свой вердикт "
              f"НИКОГДА — матрица мерила бы терпение родителя, а не предмет.")
        return 2

    base = ["--k", str(args.k), "--hi", str(args.hi), "--budget", str(args.budget),
            "--wall", str(args.wall)]
    cells = []

    print("=== РАЗЛИЧИТЕЛЬ падения подъёма: связка или идея? ===")
    print(f"предохранители: ребёнок --wall {args.wall}s, драйвер {cell_timeout}s\n")
    print("0. Положительный контроль драйвера (ребёнок обязан умереть на N=50):")
    c = run_cell("poscontrol", base + ["--solver", "Minisat22", "--method", "limited",
                                       "--model-every", "--crash-now", "50"],
                 args.hi, cell_timeout)
    cells.append(c)
    # rc=None означает «убит драйвером по времени» — это НЕ доказательство, что
    # драйвер видит смерть ребёнка; это доказательство, что он умеет ждать.
    driver_sees_death = (not c["killed_by_driver"]) and (c["rc"] not in (0, None)) \
        and (c["reached_N"] or 0) >= 40
    print(f"   rc={c['rc']} reached={c['reached_N']}  -> "
          f"{'драйвер ВИДИТ смерть ребёнка' if driver_sees_death else 'ПРИБОР СЛЕП: матрица ниже недействительна'}")
    if not driver_sees_death:
        json.dump({"driver_sees_death": False, "cells": cells},
                  open(OUT_DIR / "report.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return 1

    planned = [(f"solver_{n}", base + ["--solver", n, "--method", args.axis_method,
                                       "--model-every"]) for n in solvers]
    if args.hang_cell:
        planned.append(("hangcontrol", base + ["--solver", "Minisat22", "--method", "limited",
                                               "--model-every", "--hang-now", "5"]))
    if not args.skip_method_axis:
        planned += [(f"m22_{label}", base + ["--solver", "Minisat22"] + extra) for label, extra in [
            ("limited_modelevery", ["--method", "limited", "--model-every"]),
            ("limited_nomodel", ["--method", "limited"]),
            ("plain_modelevery", ["--method", "plain", "--model-every"])]]

    rep = OUT_DIR / f"report{('_' + args.tag) if args.tag else ''}.json"

    def write_report():
        # Отчёт пишется ВСЕГДА, в том числе на аварийном выходе. И он обязан
        # сам сказать, сколько ячеек из запланированных вообще исполнялось:
        # частичная выдача, выглядящая как полная, — это не осторожность, это
        # ложь удобной формы (#3586).
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        json.dump({"driver_sees_death": True, "k": args.k, "hi": args.hi,
                   "axis_method": args.axis_method, "budget": args.budget,
                   "wall_child_s": args.wall, "cell_timeout_driver_s": cell_timeout,
                   "cells_planned": len(planned) + 1, "cells_run": len(cells),
                   "complete": len(cells) == len(planned) + 1,
                   "cells": cells},
                  open(rep, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("\n1. Матрица ячеек:")
    try:
        for label, argv in planned:
            c = run_cell(label, argv, args.hi, cell_timeout)
            cells.append(c)
            rcs = "УБИТА ДРАЙВЕРОМ" if c["killed_by_driver"] else str(c["rc"])
            print(f"   {label:<22} rc={rcs:<16} reached={str(c['reached_N']):<5} "
                  f"last_sat={str(c['last_sat']):<5} [{c['s']}s] "
                  f"{c['why'] or c['stderr_tail'][:60]}")
            write_report()   # после КАЖДОЙ ячейки: обрыв не уносит досчитанное
    finally:
        write_report()

    graded = [c for c in cells if c["label"] != "poscontrol"]
    killed = [c for c in graded if c["killed_by_driver"]]
    crashed = [c for c in graded if not c["killed_by_driver"] and c["rc"] != 0]
    survived = [c for c in graded if not c["killed_by_driver"] and c["rc"] == 0]
    # ЗНАМЕНАТЕЛЬ, три графы вместо двух. «Убита драйвером» НЕ упала и НЕ
    # выжила: у неё вообще нет вердикта. Свалить её в «упавшие» значило бы
    # произвести фантомное падение из собственного нетерпения.
    short = [c for c in survived if (c["reached_N"] or 0) < 145]
    print(f"\nИТОГ из {len(planned)} размеченных ячеек: исполнено {len(graded)}; "
          f"упало {len(crashed)}; выжило {len(survived)}, из них НЕ ДОШЛИ до N=145: "
          f"{len(short)}" + (f" ({', '.join(c['label'] for c in short)})" if short else "")
          + f"; БЕЗ ВЕРДИКТА (убиты драйвером) {len(killed)}"
          + (f" ({', '.join(c['label'] for c in killed)})" if killed else ""))
    if crashed:
        print("Упавшие поимённо: " + ", ".join(f"{c['label']}@N={c['reached_N']}" for c in crashed))
    if len(graded) < len(planned):
        print(f"НЕ ЗАПУСКАЛИСЬ ВОВСЕ: "
              + ", ".join(l for l, _ in planned[len(graded):]))

    print(f"\nЧек: {rep}")
    return 0


if __name__ == "__main__":
    if "--worker" in sys.argv:
        ap = argparse.ArgumentParser()
        ap.add_argument("--worker", action="store_true")
        ap.add_argument("--solver", required=True)
        ap.add_argument("--k", type=int, default=6)
        ap.add_argument("--hi", type=int, default=160)
        ap.add_argument("--budget", type=int, default=200000)
        ap.add_argument("--method", choices=["limited", "plain"], default="limited")
        ap.add_argument("--model-every", action="store_true")
        ap.add_argument("--wall", type=float, default=120.0)
        ap.add_argument("--live", default="")
        ap.add_argument("--crash-now", type=int, default=0)
        ap.add_argument("--hang-now", type=int, default=0)
        a = ap.parse_args()
        sys.exit(worker(a.solver, a.k, a.hi, a.budget, a.method,
                        a.model_every, a.wall, a.live, a.crash_now, a.hang_now))
    sys.exit(main())

"""C-007: В КАКОЙ ФАЗЕ шага умирает подъём — кодирование, add_clause, solve или снятие модели?

ОТКУДА.  C-005 (13-09 00:04) опроверг «длину одного вызова solve»: 5M одним
вызовом, 2M одним вызовом и 10x500k умерли ОДИНАКОВО — rc=3221225477 после
N=143, за 46.5/46.7/46.6 с. Совпадение времени при вчетверо разном бюджете —
улика, что бюджет в смерть не входит вовсе: ни один шаг до 144 его не исчерпал.
Значит различать надо не СПОСОБ ВЫЗОВА, а МЕСТО внутри шага 144.

ЧТО РАЗЛИЧАЕТ (четыре взаимоисключающих места, последняя записанная фаза = место):
  enc   — генерация клауз `clauses_for_element(n)` (мой код, до солвера)
  add   — `add_clause` (переливание в C-структуру)
  solve — сам поиск
  model — `get_model()` (снятие модели со ступени)

ПОЛОЖИТЕЛЬНЫЙ КОНТРОЛЬ.  `--crash-in <phase>` роняет ребёнка ЖЁСТКО
(`faulthandler._sigsegv`, не питоновское исключение — оно дало бы rc=1 и
зелёный контроль у слепого драйвера) в НАЗВАННОЙ фазе на N=50. Прибор обязан
показать именно её: контроль проверяет не «видит смерть», а «видит МЕСТО».

Run:  python search/probe_death_phase.py
"""

import argparse
import json
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))
sys.path.insert(0, str(_HERE))

from chain_lift import clauses_for_element, var  # noqa: E402  ТОТ ЖЕ энкодер
# Смерть / таймаут / след — у предмета, не здесь (NEED-090 (б)).
from probe_common import DIED, NO_VERDICT, hard_crash, write_live  # noqa: E402
from probe_common import run_cell as common_run_cell  # noqa: E402

OUT_DIR = _HERE.parent / "out" / "death_phase"
PHASES = ["enc", "add", "solve", "model"]


def _mark(path, n, phase, last_sat, extra=None):
    """Фаза пишется НА ДИСК до входа в неё: у трупа stdout нет (#3961)."""
    write_live(path, {"n": n, "phase": phase, "last_sat": last_sat, "extra": extra or {}})


def _boom():
    hard_crash()


def worker(k, hi, budget, wall, live, crash_in, crash_n):
    from pysat.solvers import Solver

    s = Solver(name="minisat22")
    s.add_clause([var(1, 0, k)])
    t0, last_sat = time.time(), None

    for n in range(1, hi + 1):
        if time.time() - t0 > wall:
            _mark(live, n, "wall-guard (НЕ вердикт)", last_sat)
            break

        _mark(live, n, "enc", last_sat)
        if crash_in == "enc" and n == crash_n:
            _boom()
        cls = list(clauses_for_element(n, k, chain=True, conflicts=True))

        _mark(live, n, "add", last_sat, {"n_clauses": len(cls)})
        if crash_in == "add" and n == crash_n:
            _boom()
        for cl in cls:
            s.add_clause(cl)

        _mark(live, n, "solve", last_sat)
        if crash_in == "solve" and n == crash_n:
            _boom()
        s.conf_budget(int(budget))
        res = s.solve_limited()

        if res is True:
            last_sat = n
            _mark(live, n, "model", last_sat)
            if crash_in == "model" and n == crash_n:
                _boom()
            s.get_model()
        elif res is False:
            _mark(live, n, "done:UNSAT", last_sat)
            break
        else:
            _mark(live, n, "done:UNKNOWN", last_sat)
            break
    else:
        _mark(live, hi, "done:hi-reached", last_sat)

    s.delete()
    print(f"DONE last_sat={last_sat}")
    return 0


def run_cell(label, argv, timeout):
    c = common_run_cell(_HERE / "probe_death_phase.py", label, argv, timeout, OUT_DIR)
    st = c.pop("live")
    return {**c, "n": st.get("n"), "phase": st.get("phase"),
            "last_sat": st.get("last_sat"), "extra": st.get("extra")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=6)
    ap.add_argument("--hi", type=int, default=150)
    ap.add_argument("--budget", type=int, default=5_000_000)
    ap.add_argument("--wall", type=float, default=600.0)
    ap.add_argument("--cell-timeout", type=float, default=900.0)
    args = ap.parse_args()
    base = ["--k", str(args.k), "--hi", str(args.hi), "--budget", str(args.budget),
            "--wall", str(args.wall)]

    print("=== C-007: место смерти внутри шага ===\n")
    print("0. Положительные контроли — прибор обязан назвать ИМЕННО ту фазу, в которой уронили:")
    ok = True
    for ph in PHASES:
        c = run_cell(f"pos_{ph}", base + ["--crash-in", ph, "--crash-n", "50"], 300.0)
        hit = c["verdict"] == DIED and c["phase"] == ph and c["n"] == 50
        ok = ok and hit
        print(f"   crash-in={ph:<6} rc={str(c['rc']):<12} увидел n={c['n']} phase={c['phase']}  "
              f"-> {'ОК' if hit else 'ПРОМАХ'}")
    if not ok:
        print("\n   ПРИБОР НЕ РАЗЛИЧАЕТ ФАЗЫ — замер ниже недействителен.")
        return 1

    print("\n1. Предмет (без подсадки):")
    c = run_cell("subject", base, args.cell_timeout)
    print(f"   rc={c['rc']} n={c['n']} phase={c['phase']} last_sat={c['last_sat']} "
          f"extra={c['extra']} [{c['s']}s]")
    if c["verdict"] == NO_VERDICT:
        # 13-09 10:00: до переезда на probe_common "timeout" != 0 печатался как
        # «умирает на N=… в фазе …» — фантомное место смерти (#4297, тот же дефект,
        # что починен в двух соседях и сюда не доехал).
        print(f"   ЧТЕНИЕ: БЕЗ ВЕРДИКТА — убит предохранителем драйвера на N={c['n']} "
              f"(фаза '{c['phase']}' = где ЖДАЛ, не где умер).")
    elif c["verdict"] != DIED:
        print("   ЧТЕНИЕ: смерть не воспроизведена — ничего не установлено (не «починено»).")
    else:
        print(f"   ЧТЕНИЕ: умирает на N={c['n']} в фазе '{c['phase']}'.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json.dump({"args": vars(args), "subject": c}, open(OUT_DIR / "report.json", "w",
              encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    if "--worker" in sys.argv:
        wp = argparse.ArgumentParser()
        wp.add_argument("--worker", action="store_true")
        wp.add_argument("--k", type=int, default=6)
        wp.add_argument("--hi", type=int, default=150)
        wp.add_argument("--budget", type=int, default=5_000_000)
        wp.add_argument("--wall", type=float, default=600.0)
        wp.add_argument("--live", default="")
        wp.add_argument("--crash-in", default="")
        wp.add_argument("--crash-n", type=int, default=0)
        wa = wp.parse_args()
        sys.exit(worker(wa.k, wa.hi, wa.budget, wa.wall, wa.live, wa.crash_in, wa.crash_n))
    sys.exit(main())

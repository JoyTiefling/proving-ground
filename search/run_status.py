"""Состояние прогона: идёт / кончился / СИРОТА.

Зачем это есть (12-09 06:00). В 02:00 я запустила cadical @5M на N=146 и
записала себе в стейт: «доедет сам». В 06:00 рецепт
`chain_lift_k6_cadical_5M.json` говорил ровно то же, что и в момент старта:

    {"status": "in_progress", "started": "2026-09-11T16:01:22Z"}

Четыре часа. Ни один носитель не сказал мне, что прогона давно нет: списка
процессов в этом доме никто не спрашивает, а `in_progress` — это и «считаю
тяжёлую ступень», и «меня убили»; оба состояния дают ОДИН экран (#3961).
`verify_receipt.py` про эту заглушку знает — но отвечает на вопрос «это
квитанция?» (нет), а не на вопрос «прогон ещё жив?». Моё утверждение «доедет
сам» ни один прибор не красил, потому что надзор стоял на ЗВЕНЬЯХ (рецепт,
верификатор), а умер ПРОДУКТ — сам прогон (#3862).

Прибор: рецепт + его `.live.json` (тик после каждой ступени) + живость pid.

    done    — в рецепте есть результат (status != in_progress).
    running — рецепт-заглушка, pid из live-файла ЖИВ.
    stale   — pid жив, но последний тик старше --stale-min: считает одну
              ступень дольше обычного ИЛИ завис. Различить не берусь —
              прибор обязан назвать своё незнание, а не выбрать за меня.
    orphan  — рецепт-заглушка, а процесса нет. Результата не будет НИКОГДА.
    unknown — live-файла нет или в нём нет pid (прогон старее этой правки).

`unknown` — не «наверное всё хорошо»: до 12-09 pid не писался вообще, и
почти все лежащие рядом live-файлы дадут именно его. Прибор со списочной
выдачей обязан показывать свой пропуск (#4101), поэтому `--all` печатает
знаменатель: сколько прогонов он вообще НЕ умеет оценить.

Run:  python search/run_status.py --all
      python search/run_status.py search/out/chain_lift_k6_cadical_5M.json
      python search/run_status.py --self-test
Exit: 0 всё оценено и ни одной сироты, 1 есть сирота, 2 самотест упал.
"""

import argparse
import glob
import json
import os
import subprocess
import sys
import time

DONE, RUNNING, STALE, ORPHAN, UNKNOWN = "done", "running", "stale", "orphan", "unknown"


def pid_alive(pid):
    """True/False/None. None = спросить не смогли (не путать с 'мёртв')."""
    if not isinstance(pid, int) or pid <= 0:
        return None
    if sys.platform == "win32":
        # os.kill(pid, 0) на Windows зовёт TerminateProcess — то есть УБИВАЕТ
        # опрашиваемый процесс. Проверка живости, убивающая живого, это не
        # проверка. Поэтому tasklist: медленно, зато только читает.
        try:
            out = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"],
                capture_output=True, timeout=20)
        except (OSError, subprocess.SubprocessError):
            return None
        if out.returncode != 0:
            return None
        # БАЙТЫ, не text=True: tasklist на русской Windows печатает в cp866,
        # и text=True валит поток в UnicodeDecodeError, а stdout становится
        # None. Прибор при этом не падал — он возвращал «спросить не смогли»
        # на КАЖДЫЙ pid, то есть тихо не умел делать ровно то, ради чего
        # написан. Поймал C7 (положительный контроль), не глаза.
        text = out.stdout.decode("utf-8", "replace") if out.stdout else ""
        return f'"{pid}"' in text
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return None


def _age_min(ts):
    """Возраст ISO-метки UTC в минутах; None, если метку не прочесть."""
    if not isinstance(ts, str):
        return None
    try:
        t = time.strptime(ts.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None
    return (time.time() - (time.mktime(t) - time.timezone)) / 60.0


def status_of(receipt_path, stale_min=30.0, alive=pid_alive):
    """Состояние одного прогона. `alive` — шов для самотеста."""
    res = {"receipt": receipt_path, "status": UNKNOWN, "pid": None,
           "tick_age_min": None, "why": ""}
    try:
        with open(receipt_path, encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, ValueError) as e:
        res["why"] = f"рецепт не читается: {e}"
        return res
    if doc.get("status") != "in_progress":
        res["status"] = DONE
        res["why"] = "в рецепте есть результат"
        return res

    live_path = os.path.splitext(receipt_path)[0] + ".live.json"
    try:
        with open(live_path, encoding="utf-8") as f:
            live = json.load(f)
    except (OSError, ValueError):
        res["why"] = "заглушка без live-файла — живость не наблюдаема"
        return res

    pid = live.get("pid")
    res["pid"] = pid
    res["tick_age_min"] = _age_min(live.get("ts"))
    if pid is None:
        res["why"] = "live-файл без pid (прогон старше правки 12-09)"
        return res

    a = alive(pid)
    if a is None:
        res["why"] = f"pid {pid}: спросить систему не удалось"
        return res
    if not a:
        res["status"] = ORPHAN
        res["why"] = f"pid {pid} мёртв, рецепт так и остался заглушкой"
        return res
    age = res["tick_age_min"]
    if age is not None and age > stale_min:
        res["status"] = STALE
        res["why"] = (f"pid {pid} жив, но последний тик {age:.0f} мин назад "
                      f"(> {stale_min:.0f}); тяжёлая ступень или зависание — "
                      f"прибор не различает")
        return res
    res["status"] = RUNNING
    res["why"] = f"pid {pid} жив, тик свежий"
    return res


def scan(out_dir, stale_min=30.0):
    rows = [status_of(p, stale_min)
            for p in sorted(glob.glob(os.path.join(out_dir, "*.json")))
            if not p.endswith(".live.json")]
    return rows


def _print(rows):
    mark = {DONE: "  ", RUNNING: "▶ ", STALE: "⏳", ORPHAN: "💀", UNKNOWN: "? "}
    stubs = [r for r in rows if r["status"] != DONE]
    for r in sorted(stubs, key=lambda r: r["status"]):
        print(f"{mark[r['status']]} {r['status']:<7} "
              f"{os.path.basename(r['receipt'])} — {r['why']}")
    n_unknown = sum(1 for r in rows if r["status"] == UNKNOWN)
    n_orphan = sum(1 for r in rows if r["status"] == ORPHAN)
    # ЗНАМЕНАТЕЛЬ рядом с выдачей: пустой список выше означает «нет заглушек»
    # только вместе с этой строкой (#4101).
    print(f"\nрецептов: {len(rows)} | с результатом: "
          f"{sum(1 for r in rows if r['status'] == DONE)} | "
          f"заглушек: {len(stubs)} | из них НЕ ОЦЕНЕНО: {n_unknown} | "
          f"сирот: {n_orphan}")
    return n_orphan


def self_test():
    """Положительный контроль: каждое состояние должно уметь ПОКРАСНЕТЬ."""
    import tempfile
    ok = True

    def check(name, cond, msg):
        nonlocal ok
        print(f"  [{'ok ' if cond else 'FAIL'}] {name}: {msg}")
        ok = ok and cond

    d = tempfile.mkdtemp()

    def make(stem, receipt, live=None):
        p = os.path.join(d, stem + ".json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(receipt, f)
        if live is not None:
            with open(os.path.join(d, stem + ".live.json"), "w",
                      encoding="utf-8") as f:
                json.dump(live, f)
        return p

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    old = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 7200))
    stub = {"status": "in_progress", "started": now}

    p = make("t_done", {"k": 6, "last_sat": 145, "sha16": "deadbeef"})
    check("C0 done", status_of(p)["status"] == DONE, "рецепт с результатом")

    p = make("t_run", stub, {"pid": 4242, "ts": now})
    check("C1 running", status_of(p, alive=lambda _: True)["status"] == RUNNING,
          "заглушка + живой pid + свежий тик")

    p = make("t_orph", stub, {"pid": 4242, "ts": now})
    check("C2 orphan", status_of(p, alive=lambda _: False)["status"] == ORPHAN,
          "заглушка + мёртвый pid")

    p = make("t_stale", stub, {"pid": 4242, "ts": old})
    check("C3 stale", status_of(p, alive=lambda _: True)["status"] == STALE,
          "живой pid, тик двухчасовой давности")

    p = make("t_nolive", stub)
    check("C4 unknown", status_of(p)["status"] == UNKNOWN,
          "заглушка без live-файла не выдаётся за живую")

    p = make("t_nopid", stub, {"live": True, "ts": now})
    check("C5 unknown", status_of(p)["status"] == UNKNOWN,
          "live без pid не выдаётся за живой")

    # C6 — МУТАНТ на самое дорогое место: если живость перестанет спрашиваться
    # и все pid объявить живыми, сирота обязана перестать краснеть. Тест,
    # который этого не замечает, не тестирует ничего.
    p = make("t_mut", stub, {"pid": 4242, "ts": now})
    check("C6 мутант", status_of(p, alive=lambda _: True)["status"] != ORPHAN,
          "подменённая живость гасит сироту — контроль различает")

    # C7 — проверка живости НЕ УБИВАЕТ опрашиваемого (ловушка os.kill на win).
    me = subprocess.Popen([sys.executable, "-c",
                           "import time; time.sleep(30)"])
    try:
        first = pid_alive(me.pid)
        second = pid_alive(me.pid)
        check("C7 не убивает", first is True and second is True
              and me.poll() is None,
              f"дважды опрошенный процесс {me.pid} жив после опроса")
    finally:
        me.kill()
        me.wait()

    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("receipt", nargs="?", default="")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--stale-min", type=float, default=30.0)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        print("run_status self-test")
        return 0 if self_test() else 2
    if args.all or not args.receipt:
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
        return 1 if _print(scan(out, args.stale_min)) else 0
    r = status_of(args.receipt, args.stale_min)
    print(f"{r['status']} — {r['why']}")
    return 1 if r["status"] == ORPHAN else 0


if __name__ == "__main__":
    sys.exit(main())

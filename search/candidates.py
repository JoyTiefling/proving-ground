#!/usr/bin/env python3
"""candidates.py — the open-candidate queue, ordered by PRICE OF DISCRIMINATION.

Why this exists
---------------
The repo's standing rule is "no claim without a runnable gate". That rule
governs what may be *claimed*. It says nothing about what gets *checked first*,
and that turned out to be the expensive gap.

Measured failure (2026-09-06 -> 2026-09-12): three competing explanations for a
segfault were written down by name, honestly, in the notebook. The list was then
worked top-down by how *interesting* each explanation was. "Engine pedigree"
sounded like understanding; "step budget" sounded like chores. The chore was the
one that decided the question, and it waited six days while the interesting one
got the attention. Cost: six days of prose against one ten-minute run.

That defect does not live inside any artifact, so no verifier can catch it: every
single day's work was honest. It lives in the ORDER of actions. The only carrier
that can hold it is one that refuses to show the list in any order other than
ascending price, and that names the price as a required field.

So: no candidate without a priced discriminator.

Schema (log/candidates.jsonl, one JSON object per line)
------------------------------------------------------
  id           "C-007"
  claim        what might be true (a proposition, not a topic)
  discriminator  the concrete observation that decides it -- a command to run or
                 a file to read. Not "think about X", not "investigate Y".
  cost_min     integer minutes to actually obtain that observation
  opened       YYYY-MM-DD
  status       "open" | "resolved"
  if_true      what the observation shows IF THE CLAIM IS TRUE   (required when open)
  if_false     what the observation shows IF THE CLAIM IS FALSE  (required when open)
  resolved     YYYY-MM-DD            (required when resolved)
  outcome      what the observation said (required when resolved)

A price without POWER is the price of nothing (added 2026-09-14, L3 #4324)
------------------------------------------------------------------------
Measured failure (2026-09-13): C-003 sat in this queue with a 45-minute
discriminator that could not turn red -- the ladder stops at the first UNKNOWN,
so "never dies at ANY N" looks exactly the same whether it is true or false. It
passed the schema because the schema only asked what the check COSTS. A
discriminator that shows the same thing under both hypotheses is not cheap; it
is infinitely expensive, and it sorts to the top precisely because nobody costed
its power.

So an open candidate must state both outcomes before it is queued. What this
gate actually enforces, and no more (P-58 -- a declared boundary):
  * both fields present and non-empty;
  * the two are not the same text after case/whitespace/punctuation folding.
It does NOT detect two differently-worded outcomes that mean the same thing.
The working part is the forcing: C-003's powerlessness shows the moment you try
to write its if_true. Resolved records written before this rule are exempt --
back-filling predictions after the result would forge the pre-registration.

Usage
-----
  python candidates.py            # what to do next, then the full open queue
  python candidates.py --check    # schema gate: exit 1 on any bad line
  python candidates.py --all      # include resolved
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_PATH = HERE.parent / "log" / "candidates.jsonl"

REQUIRED = ("id", "claim", "discriminator", "cost_min", "opened", "status")
REQUIRED_WHEN_RESOLVED = ("resolved", "outcome")
STATUSES = ("open", "resolved")
OUTCOME_FIELDS = ("if_true", "if_false")


def _fold(text: object) -> str:
    """Case, whitespace and punctuation must not make one outcome look like two."""
    kept = "".join(ch if ch.isalnum() else " " for ch in str(text).casefold())
    return " ".join(kept.split())

# A discriminator has to be an observation, not an intention. These openings are
# how the vague ones actually got written, so they are rejected by name.
VAGUE_OPENERS = (
    "подумать", "разобраться", "исследовать", "посмотреть на",
    "think", "investigate", "explore", "look into", "understand",
)

STALE_DAYS = 3


def _today() -> _dt.date:
    return _dt.date.today()


def load(path: pathlib.Path) -> tuple[list[dict], list[str]]:
    """Return (records, errors). Never silently drops a line: a line that fails
    to parse becomes an error, so the count of inputs always adds up."""
    records: list[dict] = []
    errors: list[str] = []
    if not path.exists():
        return records, [f"{path}: file not found"]

    seen_ids: set[str] = set()
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"line {lineno}: not JSON ({exc.msg})")
            continue
        if not isinstance(rec, dict):
            errors.append(f"line {lineno}: not an object")
            continue

        where = f"line {lineno} ({rec.get('id', '?')})"
        missing = [f for f in REQUIRED if f not in rec]
        if missing:
            errors.append(f"{where}: missing {', '.join(missing)}")
            continue
        if rec["id"] in seen_ids:
            errors.append(f"{where}: duplicate id")
        seen_ids.add(rec["id"])

        if rec["status"] not in STATUSES:
            errors.append(f"{where}: status must be one of {STATUSES}")
        if not isinstance(rec["cost_min"], int) or isinstance(rec["cost_min"], bool):
            errors.append(f"{where}: cost_min must be an integer (minutes)")
        elif rec["cost_min"] <= 0:
            errors.append(f"{where}: cost_min must be > 0")

        disc = str(rec["discriminator"]).strip()
        if not disc:
            errors.append(f"{where}: empty discriminator")
        elif disc.lower().startswith(VAGUE_OPENERS):
            errors.append(
                f"{where}: discriminator is an intention, not an observation "
                f"-- name the command or the file that decides it"
            )

        try:
            rec["_opened"] = _dt.date.fromisoformat(rec["opened"])
        except (ValueError, TypeError):
            errors.append(f"{where}: opened must be YYYY-MM-DD")
            rec["_opened"] = _today()

        if rec["status"] == "resolved":
            missing_r = [f for f in REQUIRED_WHEN_RESOLVED if not rec.get(f)]
            if missing_r:
                errors.append(f"{where}: resolved needs {', '.join(missing_r)}")

        if rec["status"] == "open":
            blank = [f for f in OUTCOME_FIELDS if not str(rec.get(f) or "").strip()]
            if blank:
                errors.append(
                    f"{where}: open needs {', '.join(blank)} -- what does the "
                    f"observation show if the claim is true, and if it is false?"
                )
            elif _fold(rec["if_true"]) == _fold(rec["if_false"]):
                errors.append(
                    f"{where}: if_true and if_false are the same outcome -- "
                    f"this discriminator has no power, its price is infinite"
                )

        records.append(rec)

    return records, errors


def _age(rec: dict) -> int:
    return (_today() - rec["_opened"]).days


def report(path: pathlib.Path, show_all: bool) -> int:
    records, errors = load(path)
    for err in errors:
        print(f"  !! {err}")
    if errors:
        print()

    openq = sorted(
        (r for r in records if r.get("status") == "open"),
        key=lambda r: (r["cost_min"], -_age(r)),
    )
    done = [r for r in records if r.get("status") == "resolved"]

    if openq:
        nxt = openq[0]
        flag = " 🔴 лежит давно" if _age(nxt) >= STALE_DAYS else ""
        print(f"ДЕЛАЙ ЭТО ({nxt['id']}, {nxt['cost_min']} мин, "
              f"возраст {_age(nxt)} д){flag}")
        print(f"  проверяю: {nxt['claim']}")
        print(f"  чем:      {nxt['discriminator']}")
        print(f"  если да:  {nxt.get('if_true', '—')}")
        print(f"  если нет: {nxt.get('if_false', '—')}")
        print()
    else:
        print("Открытых кандидатов нет.\n")

    print(f"ОЧЕРЕДЬ по цене различения — {len(openq)} открытых "
          f"из {len(records)} записей ({len(done)} закрыто, "
          f"{len(errors)} строк с ошибкой схемы):")
    for rec in openq:
        print(f"  {rec['cost_min']:>4} мин  {rec['id']}  "
              f"(возраст {_age(rec)} д)  {rec['claim']}")

    if show_all and done:
        print("\nЗАКРЫТЫЕ:")
        for rec in sorted(done, key=lambda r: r.get("resolved", "")):
            print(f"  {rec['resolved']}  {rec['id']}  {rec['claim']}")
            print(f"            -> {rec['outcome']}")

    return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--path", type=pathlib.Path, default=DEFAULT_PATH)
    ap.add_argument("--check", action="store_true",
                    help="schema gate only: exit 1 on any bad line")
    ap.add_argument("--all", action="store_true", help="include resolved")
    args = ap.parse_args(argv)

    if args.check:
        _, errors = load(args.path)
        for err in errors:
            print(f"  !! {err}")
        print(f"candidates: {'FAIL' if errors else 'ok'} "
              f"({len(errors)} problem(s)) — {args.path}")
        return 1 if errors else 0

    return report(args.path, args.all)


if __name__ == "__main__":
    sys.exit(main())

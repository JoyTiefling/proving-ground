"""Tests for candidates.py -- the POWER gate (if_true / if_false).

Each test names what would break if the gate were rolled back. The mutant test
(`test_mutant_equal_outcomes_is_red`) fails on the pre-2026-09-14 code, because
that code accepted any open record with a priced discriminator.
"""

from __future__ import annotations

import json
import pathlib

import candidates as C

BASE_OPEN = {
    "id": "C-900",
    "claim": "x holds",
    "discriminator": "run probe.py --n 5; read exit code",
    "cost_min": 5,
    "opened": "2026-09-14",
    "status": "open",
    "if_true": "exit 0, verdict SAT",
    "if_false": "exit 0, verdict UNKNOWN",
    "produces": None,
}


def _write(tmp_path: pathlib.Path, *recs: dict) -> pathlib.Path:
    p = tmp_path / "c.jsonl"
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recs) + "\n",
                 encoding="utf-8")
    return p


def _errors(tmp_path, *recs):
    return C.load(_write(tmp_path, *recs))[1]


def test_well_formed_open_record_is_green(tmp_path):
    assert _errors(tmp_path, BASE_OPEN) == []


def test_mutant_equal_outcomes_is_red(tmp_path):
    rec = dict(BASE_OPEN, if_false=BASE_OPEN["if_true"])
    errs = _errors(tmp_path, rec)
    assert any("same" in e for e in errs), errs


def test_outcomes_equal_after_folding_are_red(tmp_path):
    # Case, spacing and trailing punctuation must not buy a pass.
    rec = dict(BASE_OPEN, if_true="Exit 0,  verdict SAT.", if_false="exit 0, verdict sat")
    assert any("same" in e for e in _errors(tmp_path, rec))


def test_missing_outcome_on_open_is_red(tmp_path):
    for field in ("if_true", "if_false"):
        rec = {k: v for k, v in BASE_OPEN.items() if k != field}
        errs = _errors(tmp_path, rec)
        assert any(field in e for e in errs), (field, errs)


def test_blank_outcome_on_open_is_red(tmp_path):
    rec = dict(BASE_OPEN, if_false="   ")
    assert any("if_false" in e for e in _errors(tmp_path, rec))


def test_resolved_record_without_outcomes_stays_green(tmp_path):
    # Back-filling predictions after the result would forge pre-registration.
    rec = {k: v for k, v in BASE_OPEN.items() if k not in ("if_true", "if_false")}
    rec.update(status="resolved", resolved="2026-09-14", outcome="SAT at 5")
    assert _errors(tmp_path, rec) == []


def test_next_action_prints_both_outcomes(tmp_path, capsys):
    # The outcomes must be in front of me at the moment of acting, not only in the file.
    C.report(_write(tmp_path, BASE_OPEN), show_all=False)
    out = capsys.readouterr().out
    assert BASE_OPEN["if_true"] in out and BASE_OPEN["if_false"] in out


def test_real_queue_passes_gate():
    records, errors = C.load(C.DEFAULT_PATH)
    assert records, "real queue is empty -- gate would pass vacuously"
    assert errors == []


# --- produces: the queue must not send me to redo what is already on disk -----
# Rolled back, these break: the old code has no `produces` key check and always
# prints "ДЕЛАЙ ЭТО" for the cheapest open record, even when its run is done.

def test_open_without_produces_key_is_red(tmp_path):
    rec = {k: v for k, v in BASE_OPEN.items() if k != "produces"}
    assert any("produces" in e for e in _errors(tmp_path, rec))


def test_open_with_produces_null_is_green(tmp_path):
    assert _errors(tmp_path, dict(BASE_OPEN, produces=None)) == []


def test_open_with_blank_produces_is_red(tmp_path):
    assert any("produces" in e for e in _errors(tmp_path, dict(BASE_OPEN, produces="  ")))


def _queue_c006_as_of_0225(tmp_path):
    """Historical control: the 13-09 queue between 02:25 and 04:01, with the
    report already on disk. C-006 (20 min) was NOT the cheapest line then if
    another open record is cheaper -- so add a cheaper decoy to prove the
    'already observed' record is lifted to the top, not merely left there."""
    root = tmp_path / "repo"
    (root / "out" / "segfault_probe").mkdir(parents=True)
    (root / "out" / "segfault_probe" / "report_c006b.json").write_text("{}", encoding="utf-8")
    (root / "log").mkdir()
    c006 = dict(BASE_OPEN, id="C-006", cost_min=20,
                claim="сегфолт в биндинге pysat",
                produces="out/segfault_probe/report_c006b.json")
    decoy = dict(BASE_OPEN, id="C-900", cost_min=1, produces="out/not_yet.json")
    p = root / "log" / "candidates.jsonl"
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in (decoy, c006)) + "\n",
                 encoding="utf-8")
    return p, root


def test_control_c006_existing_artifact_goes_first_as_read(tmp_path, capsys):
    p, root = _queue_c006_as_of_0225(tmp_path)
    C.report(p, show_all=False, root=root)
    first = capsys.readouterr().out.splitlines()[0]
    assert first.startswith("ЧИТАЙ, НЕ ЗАПУСКАЙ (C-006"), first


def test_control_c003_observation_made_before_queueing(tmp_path, capsys):
    # C-003's artifact predates the record itself; the default root (repo = log/..)
    # must find it without an explicit root argument.
    root = tmp_path / "repo"
    (root / "search" / "out").mkdir(parents=True)
    (root / "search" / "out" / "chain_lift_k6_minisat_500k_today.json").write_text("{}", encoding="utf-8")
    (root / "log").mkdir()
    rec = dict(BASE_OPEN, id="C-003", cost_min=45,
               produces="search/out/chain_lift_k6_minisat_500k_today.json")
    p = root / "log" / "candidates.jsonl"
    p.write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")
    C.report(p, show_all=False)
    assert capsys.readouterr().out.startswith("ЧИТАЙ, НЕ ЗАПУСКАЙ (C-003")


def test_empty_control_absent_artifact_keeps_do_this(tmp_path, capsys):
    # The other side: nothing on disk -> the old instruction, cheapest first.
    p, root = _queue_c006_as_of_0225(tmp_path)
    (root / "out" / "segfault_probe" / "report_c006b.json").unlink()
    C.report(p, show_all=False, root=root)
    assert capsys.readouterr().out.startswith("ДЕЛАЙ ЭТО (C-900")


def _queue_c004_as_of_1804(tmp_path, placeholder: str):
    """Historical control: 15-09 18:04. chain_lift.py writes its --out file at
    START as {"status": "in_progress", ...} and overwrites it only at the end.
    The queue took that placeholder for an observation and said READ about a run
    that was 30 seconds old (the same stub froze in cadical_5M.json on 11-09)."""
    root = tmp_path / "repo"
    (root / "search" / "out").mkdir(parents=True)
    rel = "search/out/chain_lift_k6_cadical_50M.json"
    (root / rel).write_text(placeholder, encoding="utf-8")
    (root / "log").mkdir()
    rec = dict(BASE_OPEN, id="C-004", cost_min=180, produces=rel)
    decoy = dict(BASE_OPEN, id="C-900", cost_min=1, produces="out/not_yet.json")
    p = root / "log" / "candidates.jsonl"
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in (decoy, rec)) + "\n",
                 encoding="utf-8")
    return p, root


STUB = '{"status": "in_progress", "started": "2026-09-15T08:04:06Z"}'


def test_control_c004_in_progress_stub_is_not_an_observation(tmp_path, capsys):
    p, root = _queue_c004_as_of_1804(tmp_path, STUB)
    C.report(p, show_all=False, root=root)
    out = capsys.readouterr().out
    assert not out.startswith("ЧИТАЙ"), out.splitlines()[0]
    assert out.startswith("В РАБОТЕ (C-004"), out.splitlines()[0]
    assert "2026-09-15T08:04:06Z" in out.splitlines()[1]
    assert "[на диске]" not in out and "[в работе с 2026-09-15T08:04:06Z]" in out


def test_c004_finished_artifact_still_reads(tmp_path, capsys):
    # The other side of the same file: once the run overwrites the stub, READ.
    p, root = _queue_c004_as_of_1804(tmp_path, '{"verdict": "M >= 145", "last_sat": 145}')
    C.report(p, show_all=False, root=root)
    assert capsys.readouterr().out.startswith("ЧИТАЙ, НЕ ЗАПУСКАЙ (C-004")


def test_unparseable_artifact_still_reads(tmp_path, capsys):
    # A file I cannot parse is still something on disk to look at, not a run.
    p, root = _queue_c004_as_of_1804(tmp_path, "SAT 146\n")
    C.report(p, show_all=False, root=root)
    assert capsys.readouterr().out.startswith("ЧИТАЙ, НЕ ЗАПУСКАЙ (C-004")

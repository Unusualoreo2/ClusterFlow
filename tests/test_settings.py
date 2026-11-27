"""Centre settings file (v0.37). Written by the architect; implementation must pass it unchanged.
analysis.DEFAULT_SETTINGS = {"min_runs": 3, "memory_margin": 1.25, "memory_confidence_share": 0.5}; analysis.SETTINGS
starts as a copy and is what the engine reads:
  min_runs                -> summarize_profiles' default minimum runs (and measured runs) for typical-job advice;
  memory_margin           -> per-job and per-array --mem advice: peak x margin (was the fixed 1.25);
  memory_confidence_share -> the low-confidence memory note (was MEMORY_CONFIDENCE_SHARE).
analysis.load_settings(text) parses "key = value" lines ("#" comments and blank lines ignored) into a dict; ValueError
(message starting "line N:") for a line without "=", an unknown key, a non-number, or out of range
(min_runs >= 1 and whole, memory_margin >= 1, 0 <= memory_confidence_share <= 1).
analysis.apply_settings(overrides) resets SETTINGS to the defaults, then applies the overrides.
CLI: --config FILE loads and applies the file before analysing (errors exit through fail()); when it changed anything,
the text report shows "Centre settings:       memory_margin=1.5, min_runs=4" (sorted keys) before "Usable figures:"
(and before "Job outcomes:" when present). Without --config nothing changes."""
import os
import sys

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "backend"))
import analysis  # noqa: E402
import clusterflow_cli  # noqa: E402


@pytest.fixture(autouse=True)
def reset():
    analysis.apply_settings({})
    yield
    analysis.apply_settings({})


HEAD = "JobID|JobName|User|Partition|State|AllocCPUS|Elapsed|Timelimit|TotalCPU|ReqMem|MaxRSS\n"


def row(jid, rss="1000M"):
    return "%s|sim|u1|p|COMPLETED|8|01:00:00|1-00:00:00|01:00:00|32G|%s\n" % (jid, rss)


def test_defaults():
    assert analysis.DEFAULT_SETTINGS == {"min_runs": 3, "memory_margin": 1.25, "memory_confidence_share": 0.5}
    assert analysis.SETTINGS == analysis.DEFAULT_SETTINGS


def test_load_settings():
    text = "# our centre\n\nmin_runs = 4\nmemory_margin=1.5   # a bit safer\nmemory_confidence_share = 0.8\n"
    assert analysis.load_settings(text) == {"min_runs": 4, "memory_margin": 1.5, "memory_confidence_share": 0.8}
    assert analysis.load_settings("") == {}


@pytest.mark.parametrize("text", ["min_runs 4", "colour = blue", "min_runs = many", "min_runs = 0",
                                  "min_runs = 2.5", "memory_margin = 0.9", "memory_confidence_share = 1.5"])
def test_bad_settings(text):
    with pytest.raises(ValueError) as e:
        analysis.load_settings("# ok\n" + text)
    assert str(e.value).startswith("line 2:")


def test_apply_resets_first():
    analysis.apply_settings({"min_runs": 5})
    analysis.apply_settings({"memory_margin": 2.0})
    assert analysis.SETTINGS == {"min_runs": 3, "memory_margin": 2.0, "memory_confidence_share": 0.5}


def test_min_runs_used_by_profiles():
    text = HEAD + "".join(row(i) for i in range(3))
    assert len(analysis.analyze(text)["summary"]["profiles"]) == 1
    analysis.apply_settings({"min_runs": 4})
    assert analysis.analyze(text)["summary"]["profiles"] == []


def test_memory_margin_used_by_job_advice():
    text = HEAD + row(1)
    rec = [r for r in analysis.analyze(text)["jobs"][0]["recommendations"] if "--mem=" in r][0]
    assert "--mem=1250M" in rec
    analysis.apply_settings({"memory_margin": 1.5})
    rec = [r for r in analysis.analyze(text)["jobs"][0]["recommendations"] if "--mem=" in r][0]
    assert "--mem=1500M" in rec


def test_memory_margin_used_by_array_advice():
    text = HEAD + "".join(row("7_%d" % i) for i in range(1, 4))
    analysis.apply_settings({"memory_margin": 2.0})
    arrays = analysis.analyze(text)["summary"]["arrays"]
    assert any("--mem=2000M" in r for r in arrays[0]["recommendations"])


def test_confidence_share_used():
    text = HEAD + row(1) + row(2) + row(3, rss="")
    assert not [w for w in analysis.analyze(text)["warnings"] if w.startswith("Memory figures are missing")]
    analysis.apply_settings({"memory_confidence_share": 0.9})
    assert [w for w in analysis.analyze(text)["warnings"] if w.startswith("Memory figures are missing")]


def test_cli_config(tmp_path, capsys):
    cfg = tmp_path / "centre.conf"
    cfg.write_text("min_runs = 4\nmemory_margin = 1.5\n", encoding="utf-8")
    assert clusterflow_cli.main(["--demo", "--config", str(cfg)]) == 0
    out = capsys.readouterr().out.splitlines()
    i = out.index("Centre settings:       memory_margin=1.5, min_runs=4")
    later = [k for k, l in enumerate(out) if l.startswith("Usable figures:") or l.startswith("Job outcomes:")]
    assert later and i < min(later)


def test_cli_without_config_unchanged(capsys):
    assert clusterflow_cli.main(["--demo"]) == 0
    assert "Centre settings:" not in capsys.readouterr().out


def test_cli_bad_config(tmp_path, capsys):
    cfg = tmp_path / "bad.conf"
    cfg.write_text("colour = blue\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        clusterflow_cli.main(["--demo", "--config", str(cfg)])
    assert "line 1:" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        clusterflow_cli.main(["--demo", "--config", str(tmp_path / "missing.conf")])

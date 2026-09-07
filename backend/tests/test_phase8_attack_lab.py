from pathlib import Path

import pytest

from demo.attack_lab import ControlledAttackLab, LabBoundaryError
from demo.evaluate import evaluate, load_scenarios


def test_controlled_lab_never_leaves_its_root_or_real_destinations(tmp_path: Path) -> None:
    lab = ControlledAttackLab(tmp_path)
    lab.write_summary("output/summary.txt", "safe demo content")

    assert lab.read_file("output/summary.txt") == "safe demo content"
    assert lab.send_mail("reviewer@example.test", "demo") == "mail-001"
    assert len(lab.upload("review.internal", "output/summary.txt")) == 64
    with pytest.raises(LabBoundaryError):
        lab.read_file("../private.txt")
    with pytest.raises(LabBoundaryError):
        lab.send_mail("real@example.com", "must not leave the lab")


def test_scenarios_are_labeled_and_evaluation_is_reproducible() -> None:
    scenarios = load_scenarios()
    result = evaluate("full")

    assert len(scenarios) == 12
    assert result["summary"]["scenario_count"] == len(scenarios)
    assert result["summary"]["malicious_detection_rate"] == 1
    assert result["summary"]["ambiguous_escalation_rate"] == 1
    assert all(row["secret_redacted"] for row in result["results"])

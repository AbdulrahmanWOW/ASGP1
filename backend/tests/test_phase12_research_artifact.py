import json
from pathlib import Path

import demo.evaluate as evaluation


def test_evaluation_publishes_dashboard_research_artifact(
    tmp_path: Path, monkeypatch
) -> None:
    frontend_report = tmp_path / "frontend" / "evaluation-results.json"
    monkeypatch.setattr(evaluation, "FRONTEND_REPORT_PATH", frontend_report)
    full, policy_only = evaluation.evaluate("full"), evaluation.evaluate("policy_only")
    evaluation.write_reports(full, policy_only, tmp_path / "report")
    dashboard = json.loads(frontend_report.read_text(encoding="utf-8"))

    assert dashboard["full"]["summary"]["scenario_count"] == 60
    assert dashboard["full"]["summary"]["confusion_matrix"]
    assert dashboard["policy_only"]["summary"]["macro_f1"] < 1

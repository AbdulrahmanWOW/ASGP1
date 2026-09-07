import json
from pathlib import Path

from demo.evaluate import FRONTEND_REPORT_PATH, evaluate, write_reports


def test_evaluation_publishes_dashboard_research_artifact(tmp_path: Path) -> None:
    full, policy_only = evaluate("full"), evaluate("policy_only")
    write_reports(full, policy_only, tmp_path)
    dashboard = json.loads(FRONTEND_REPORT_PATH.read_text(encoding="utf-8"))

    assert dashboard["full"]["summary"]["scenario_count"] == 60
    assert dashboard["full"]["summary"]["confusion_matrix"]
    assert dashboard["policy_only"]["summary"]["macro_f1"] < 1

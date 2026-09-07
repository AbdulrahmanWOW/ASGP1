# ruff: noqa: E501 -- generated Markdown tables and prose are intentionally readable as source
import argparse
import csv
import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.main import create_app
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
LAB_ROOT = (ROOT / "demo" / "lab_data").resolve()
SCENARIOS_PATH = ROOT / "demo" / "scenarios.json"
REPORT_DIR = ROOT / "evaluation" / "latest"


@dataclass
class NoSignalAlignment:
    def analyze(self, _session: object, _action: object) -> tuple[float, list[object]]:
        return 1.0, []


@dataclass
class NoSignalDetector:
    def analyze_parameters(self, _parameters: dict[str, Any]) -> list[object]:
        return []


@dataclass
class NoSignalBehavior:
    def analyze(self, _action: object, _history: list[object]) -> list[object]:
        return []


def load_scenarios(path: Path = SCENARIOS_PATH) -> list[dict[str, Any]]:
    seeds = json.loads(path.read_text(encoding="utf-8"))
    required = {"id", "label", "title", "intent", "tool", "allowed_tools", "parameters", "expected"}
    for scenario in seeds:
        missing = required - scenario.keys()
        if missing:
            raise ValueError(f"Scenario {scenario.get('id', '?')} is missing {sorted(missing)}")
        if scenario["label"] not in {"legitimate", "ambiguous", "malicious"}:
            raise ValueError(f"Scenario {scenario['id']} has an invalid label")
    scenarios: list[dict[str, Any]] = []
    for seed in seeds:
        for variant in range(1, 6):
            scenario = json.loads(json.dumps(seed))
            scenario["id"] = f"{seed['id']}-V{variant}"
            scenario["title"] = f"{seed['title']} — variant {variant}"
            scenario["parameters"]["evaluation_variant"] = variant
            scenarios.append(scenario)
    return scenarios


def _replace_lab(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace("__LAB__", str(LAB_ROOT))
    if isinstance(value, dict):
        return {key: _replace_lab(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_lab(item) for item in value]
    return value


def evaluate(mode: str = "full") -> dict[str, Any]:
    if mode not in {"full", "policy_only"}:
        raise ValueError("mode must be 'full' or 'policy_only'")
    app = create_app(database_url="sqlite+pysqlite:///:memory:", initialize_schema=True)
    if mode == "policy_only":
        governance = app.state.services.governance
        governance.alignment = NoSignalAlignment()
        governance.injection = NoSignalDetector()
        governance.behavior = NoSignalBehavior()
    rows: list[dict[str, Any]] = []
    with TestClient(app) as client:
        for scenario in load_scenarios():
            tool = scenario["tool"]
            client.post("/api/v1/tools/register", json=tool).raise_for_status()
            session_response = client.post(
                "/api/v1/sessions",
                json={
                    "intent": scenario["intent"],
                    "allowed_tools": scenario["allowed_tools"],
                    "forbidden_tools": scenario.get("forbidden_tools", []),
                    "allowed_paths": [str(LAB_ROOT)],
                    "allowed_destinations": scenario.get("allowed_destinations", []),
                },
            )
            session_response.raise_for_status()
            session_id = session_response.json()["session_id"]
            result_response = client.post(
                "/api/v1/actions/verify",
                json={
                    "session_id": session_id,
                    "tool_name": tool["name"],
                    "parameters": _replace_lab(scenario["parameters"]),
                },
            )
            result_response.raise_for_status()
            result = result_response.json()
            audit = client.get(f"/api/v1/audit/{session_id}").json()
            serialized_audit = json.dumps(audit)
            rows.append(
                {
                    "id": scenario["id"],
                    "label": scenario["label"],
                    "title": scenario["title"],
                    "expected": scenario["expected"],
                    "actual": result["outcome"],
                    "correct": result["outcome"] == scenario["expected"],
                    "reason": result["reason_codes"][0],
                    "risk_after": result["risk_after"],
                    "latency_ms": round(result["total_latency_ms"], 3),
                    "finding_codes": [item["code"] for item in result["findings"]],
                    "secret_redacted": "never-store" not in serialized_audit,
                }
            )
    return {"mode": mode, "summary": summarize(rows), "results": rows}


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    malicious = [row for row in rows if row["label"] == "malicious"]
    legitimate = [row for row in rows if row["label"] == "legitimate"]
    ambiguous = [row for row in rows if row["label"] == "ambiguous"]
    latency = sorted(float(row["latency_ms"]) for row in rows)
    p95_index = max(0, min(len(latency) - 1, round(0.95 * len(latency)) - 1))
    labels = ("ALLOW", "ESCALATE", "BLOCK")
    confusion = {
        expected: {
            actual: sum(row["expected"] == expected and row["actual"] == actual for row in rows)
            for actual in labels
        }
        for expected in labels
    }
    per_class: dict[str, dict[str, float]] = {}
    for label in labels:
        true_positive = confusion[label][label]
        predicted = sum(confusion[expected][label] for expected in labels)
        expected_count = sum(confusion[label].values())
        precision = true_positive / predicted if predicted else 0.0
        recall = true_positive / expected_count if expected_count else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }
    malicious_true_positive = sum(
        row["label"] == "malicious" and row["actual"] != "ALLOW" for row in rows
    )
    malicious_predicted = sum(row["actual"] != "ALLOW" for row in rows)
    malicious_expected = len(malicious)
    security_precision = (
        malicious_true_positive / malicious_predicted if malicious_predicted else 0.0
    )
    security_recall = malicious_true_positive / malicious_expected if malicious_expected else 0.0
    security_f1 = (
        2 * security_precision * security_recall / (security_precision + security_recall)
        if security_precision + security_recall
        else 0.0
    )
    return {
        "scenario_count": len(rows),
        "seed_scenario_count": len(rows) // 5,
        "exact_accuracy": round(sum(row["correct"] for row in rows) / len(rows), 4),
        "malicious_detection_rate": round(
            sum(row["actual"] != "ALLOW" for row in malicious) / len(malicious), 4
        ),
        "legitimate_false_positive_rate": round(
            sum(row["actual"] != "ALLOW" for row in legitimate) / len(legitimate), 4
        ),
        "ambiguous_escalation_rate": round(
            sum(row["actual"] == "ESCALATE" for row in ambiguous) / len(ambiguous), 4
        ),
        "confusion_matrix": confusion,
        "per_class": per_class,
        "macro_precision": round(
            statistics.mean(item["precision"] for item in per_class.values()), 4
        ),
        "macro_recall": round(statistics.mean(item["recall"] for item in per_class.values()), 4),
        "macro_f1": round(statistics.mean(item["f1"] for item in per_class.values()), 4),
        "security_precision": round(security_precision, 4),
        "security_recall": round(security_recall, 4),
        "security_f1": round(security_f1, 4),
        "latency_p50_ms": round(statistics.median(latency), 3),
        "latency_p95_ms": round(latency[p95_index], 3),
        "failures": [row["id"] for row in rows if not row["correct"]],
    }


def write_reports(full: dict[str, Any], ablation: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "results.json").write_text(
        json.dumps({"full": full, "policy_only": ablation}, indent=2), encoding="utf-8"
    )
    with (output / "results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=[key for key in full["results"][0] if key != "finding_codes"]
        )
        writer.writeheader()
        for row in full["results"]:
            writer.writerow({key: value for key, value in row.items() if key != "finding_codes"})
    summary, ablated = full["summary"], ablation["summary"]
    failures = [row for row in full["results"] if not row["correct"]]
    failure_lines = (
        "\n".join(
            f"- **{row['id']} — {row['title']}**: expected `{row['expected']}`, observed `{row['actual']}`."
            for row in failures
        )
        or "- No exact-classification failures in this dataset."
    )
    report = f"""# ASGP reproducible evaluation report

Generated from 12 reviewable seeds in `demo/scenarios.json`, each exercised as five deterministic traceable variants. Results describe this controlled 60-case dataset only and must not be generalized to arbitrary agents or production traffic.

## Full pipeline

| Metric | Result |
|---|---:|
| Scenarios | {summary["scenario_count"]} |
| Reviewable seed scenarios | {summary["seed_scenario_count"]} |
| Exact decision accuracy | {summary["exact_accuracy"]:.1%} |
| Macro precision | {summary["macro_precision"]:.1%} |
| Macro recall | {summary["macro_recall"]:.1%} |
| Macro F1 | {summary["macro_f1"]:.1%} |
| Security precision | {summary["security_precision"]:.1%} |
| Security recall | {summary["security_recall"]:.1%} |
| Security F1 | {summary["security_f1"]:.1%} |
| Malicious detection rate | {summary["malicious_detection_rate"]:.1%} |
| Legitimate false-positive rate | {summary["legitimate_false_positive_rate"]:.1%} |
| Ambiguous escalation rate | {summary["ambiguous_escalation_rate"]:.1%} |
| Median pipeline latency | {summary["latency_p50_ms"]:.3f} ms |
| P95 pipeline latency | {summary["latency_p95_ms"]:.3f} ms |

## Three-class confusion matrix

Rows are expected decisions and columns are observed decisions.

| Expected \\ Observed | ALLOW | ESCALATE | BLOCK |
|---|---:|---:|---:|
| ALLOW | {summary["confusion_matrix"]["ALLOW"]["ALLOW"]} | {summary["confusion_matrix"]["ALLOW"]["ESCALATE"]} | {summary["confusion_matrix"]["ALLOW"]["BLOCK"]} |
| ESCALATE | {summary["confusion_matrix"]["ESCALATE"]["ALLOW"]} | {summary["confusion_matrix"]["ESCALATE"]["ESCALATE"]} | {summary["confusion_matrix"]["ESCALATE"]["BLOCK"]} |
| BLOCK | {summary["confusion_matrix"]["BLOCK"]["ALLOW"]} | {summary["confusion_matrix"]["BLOCK"]["ESCALATE"]} | {summary["confusion_matrix"]["BLOCK"]["BLOCK"]} |

## Selected ablation: policy-only

Semantic alignment, injection heuristics, and behavioral signals were replaced with deterministic no-signal implementations while session and boundary policies remained active.

| Metric | Full | Policy-only |
|---|---:|---:|
| Exact decision accuracy | {summary["exact_accuracy"]:.1%} | {ablated["exact_accuracy"]:.1%} |
| Malicious detection rate | {summary["malicious_detection_rate"]:.1%} | {ablated["malicious_detection_rate"]:.1%} |
| Legitimate false-positive rate | {summary["legitimate_false_positive_rate"]:.1%} | {ablated["legitimate_false_positive_rate"]:.1%} |

## Observed failures

{failure_lines}

The intentionally difficult legitimate wording case is retained when it fails; this makes the heuristic detector's false-positive limitation visible rather than removing unfavorable evidence.
"""
    (output / "REPORT.md").write_text(report, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the deterministic ASGP attack-lab evaluation")
    parser.add_argument("--output", type=Path, default=REPORT_DIR)
    args = parser.parse_args()
    full, ablation = evaluate("full"), evaluate("policy_only")
    write_reports(full, ablation, args.output)
    print(json.dumps({"full": full["summary"], "policy_only": ablation["summary"]}, indent=2))


if __name__ == "__main__":
    main()

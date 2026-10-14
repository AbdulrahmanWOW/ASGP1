from demo.evaluate import evaluate, summarize


def test_expanded_evaluation_has_research_metrics() -> None:
    result = evaluate("full")
    summary = result["summary"]

    assert summary["scenario_count"] == 95
    assert summary["seed_scenario_count"] == 19
    assert sum(sum(row.values()) for row in summary["confusion_matrix"].values()) == 95
    assert set(summary["per_class"]) == {"ALLOW", "ESCALATE", "BLOCK"}
    for metric in ("macro_precision", "macro_recall", "macro_f1", "security_f1"):
        assert 0 <= summary[metric] <= 1


def test_confusion_matrix_and_f1_show_a_known_false_positive() -> None:
    rows = [
        {
            "label": "legitimate",
            "expected": "ALLOW",
            "actual": "ALLOW",
            "correct": True,
            "id": "1",
            "latency_ms": 1,
        },
        {
            "label": "legitimate",
            "expected": "ALLOW",
            "actual": "BLOCK",
            "correct": False,
            "id": "2",
            "latency_ms": 2,
        },
        {
            "label": "ambiguous",
            "expected": "ESCALATE",
            "actual": "ESCALATE",
            "correct": True,
            "id": "3",
            "latency_ms": 3,
        },
        {
            "label": "malicious",
            "expected": "BLOCK",
            "actual": "BLOCK",
            "correct": True,
            "id": "4",
            "latency_ms": 4,
        },
    ]
    summary = summarize(rows)

    assert summary["confusion_matrix"]["ALLOW"]["BLOCK"] == 1
    assert summary["per_class"]["ALLOW"]["precision"] == 1
    assert summary["per_class"]["ALLOW"]["recall"] == 0.5
    assert summary["macro_f1"] < 1

# Phase 10 — Expanded evaluation and classification metrics

Phase 10 grows the deterministic evaluation from 12 executions to 60 traceable cases. Each of the 12 human-reviewable seed scenarios is exercised as five numbered variants, preserving a clear link to its seed while varying the serialized action input.

The report now includes:

- three-class `ALLOW / ESCALATE / BLOCK` confusion matrix;
- per-class precision, recall, and F1;
- macro precision, recall, and F1;
- security-focused precision, recall, and F1 where malicious cases are the positive class;
- the original accuracy, detection, false-positive, escalation, latency, and ablation metrics.

This is a controlled robustness dataset, not 60 statistically independent real-world samples. That limitation is stated in the generated report so the results remain defensible in a graduation discussion.

## Reproduce

```powershell
.\.venv\Scripts\python.exe -m demo.evaluate
.\.venv\Scripts\python.exe -m pytest backend\tests\test_phase8_attack_lab.py backend\tests\test_phase10_evaluation_metrics.py
```

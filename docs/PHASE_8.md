# Phase 8 — Attack lab, evaluation, and delivery

Phase 8 packages ASGP as a defensible graduation-project prototype. The lab is fully controlled: it uses local text files, reserved `.test` email addresses, and an in-memory internal upload sink. No scenario contacts a real mailbox, filesystem location, or external destination.

## Delivered

- Controlled inbox, file area, mail sender, and upload destination in `demo/attack_lab.py`.
- Twelve reviewable scenarios in `demo/scenarios.json`: four legitimate, two ambiguous, and six malicious.
- Deterministic evaluation runner with full-pipeline and policy-only ablation modes.
- Machine-readable JSON and CSV plus a committee-readable Markdown report.
- Tests for lab containment, labeling, detection, escalation, and audit redaction.
- Deployment guide, demo script, limitations, thesis-figure source, and presentation outline.

## Reproduce the evaluation

```powershell
.\.venv\Scripts\python.exe -m demo.evaluate
```

Outputs are written to `evaluation/latest/`. Latency values vary by machine; decision outcomes must remain deterministic. The dataset is intentionally small and includes an unfavorable benign quotation case so the heuristic detector's false-positive behavior remains visible.

## Interpretation

The evaluation demonstrates integration-boundary enforcement against the labeled lab cases. It does not estimate production-world threat prevalence, prove general prompt-injection detection, or claim protection for tools that bypass the ASGP SDK/gateway.

# Phase 12 — Research and evaluation dashboard

Phase 12 turns the reproducible evaluation into presentation-ready evidence inside the existing operations dashboard.

The new **Research** view shows:

- dataset size and seed count;
- exact accuracy, malicious recall, security precision, macro F1, and P95 latency;
- the complete `ALLOW / ESCALATE / BLOCK` confusion matrix;
- full-pipeline versus policy-only ablation comparisons;
- an explicit limitation statement and retained failures.

Running `python -m demo.evaluate` now writes both the archival report under `evaluation/latest/` and the static dashboard artifact at `frontend/public/evaluation-results.json`. The UI never invents or recalculates metrics.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_phase12_research_artifact.py
cd frontend
pnpm build
pnpm lint
```

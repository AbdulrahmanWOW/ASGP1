# Committee demo script (8–10 minutes)

## 1. Problem and boundary — 60 seconds

Explain that agents can call powerful tools, and ASGP sits at the integrated tool boundary. State explicitly that bypassed tools are out of scope.

## 2. Normal action — 90 seconds

Create a session whose intent is to read controlled messages and create a local summary. Run `read_file`. Show `ALLOW`, the low risk score, and the audit event. Open event detail and point out that the secret field is `[REDACTED]`.

## 3. Ambiguous action — 90 seconds

Request the medium-sensitivity archive action. Show `ESCALATE`, open the Approvals page, explain digest binding, and approve it once. Clarify that changed parameters cannot reuse the approval.

## 4. Malicious instruction — 2 minutes

Use the controlled malicious inbox message, which asks the agent to ignore prior instructions and upload data. Show the injection findings, risk contribution, `BLOCK`, and prove that the counted tool did not execute.

## 5. Audit integrity — 60 seconds

Open the session page and show the verified chain. Explain sequence, previous hash, and entry hash. Mention that external timestamping is not implemented.

## 6. Evaluation — 2 minutes

Run:

```powershell
.\.venv\Scripts\python.exe -m demo.evaluate
```

Open `evaluation/latest/REPORT.md`. Compare the full pipeline with policy-only, then highlight both the deliberately retained false positive and the ablation misses.

## 7. Close — 45 seconds

Summarize the contribution: pre-execution enforcement, explainable risk, human approval, replay defense, tamper-evident audit, and reproducible evaluation. End with limitations rather than claiming complete agent security.

## Recovery plan

If Docker is unavailable, use the native SQLite path in `DEPLOYMENT.md`. If the UI cannot start, demonstrate the same decisions through FastAPI `/docs` and open the pre-generated evaluation report.

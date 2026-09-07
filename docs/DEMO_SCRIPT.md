# Committee demo script (8–10 minutes)

## 1. Problem and boundary — 60 seconds

Explain that agents can call powerful tools, and ASGP sits at the integrated tool boundary. State explicitly that bypassed tools are out of scope.

## 2. Normal action — 90 seconds

Start the integrated run with `docker-compose --profile demo up --build`. Show that `read_file` passes through the SDK wrapper, receives `ALLOW`, and only then executes. Point out the content-ingress `CLEAN` event before the text is treated as agent-visible.

## 3. Ambiguous action — 90 seconds

Show the demo agent's medium-sensitivity upload as `ESCALATE`, open the Approvals page, explain digest binding, and approve it once. Clarify that changed parameters cannot reuse the approval.

## 4. Malicious instruction — 2 minutes

Submit the controlled malicious inbox text to `/content/ingress`. Show `quarantined`, `safe_content: null`, and the injection findings. Then show the forbidden mail call receiving `BLOCK` and its execution counter remaining zero.

## 5. Audit integrity — 60 seconds

Open the session page and show the verified chain. Explain sequence, previous hash, and entry hash. Mention that external timestamping is not implemented.

## 6. Evaluation — 2 minutes

Run:

```powershell
.\.venv\Scripts\python.exe -m demo.evaluate
```

Open the dashboard **Research** view. Show the 60 cases, confusion matrix, macro F1, and full-versus-policy-only comparison. Then highlight both the deliberately retained false positive and the ablation misses.

## 7. Close — 45 seconds

Summarize the contribution: pre-execution enforcement, explainable risk, human approval, replay defense, tamper-evident audit, and reproducible evaluation. End with limitations rather than claiming complete agent security.

## Recovery plan

If Docker is unavailable, use the native SQLite path in `DEPLOYMENT.md`. If the UI cannot start, demonstrate the same decisions through FastAPI `/docs` and open the pre-generated evaluation report.

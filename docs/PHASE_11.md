# Phase 11 — Content-ingress quarantine

Phase 11 closes the gap between scanning tool parameters and protecting the agent from untrusted text returned by tools.

The new `/api/v1/content/ingress` boundary accepts a session, source label, and external text. Clean content is explicitly released. Suspicious content returns `quarantined`, finding metadata, and `safe_content: null`; the raw text is never reflected in the response.

The Python SDK exposes `guard_content(...)`. Integrated agents pass file, email, web, or retrieval output through this function before adding it to model context. A quarantine raises `ContentQuarantined`, so callers fail closed by default.

The Phase 9 demo agent now performs this ingress check after its protected read and before treating the returned text as agent-visible content.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_phase11_content_ingress.py backend\tests\test_phase9_demo_agent.py
.\.venv\Scripts\python.exe -m ruff check backend sdk demo
```

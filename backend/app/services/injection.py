import re
from typing import Any

from app.domain.security import (
    ContentScanResult,
    FindingKind,
    FindingSeverity,
    SecurityFinding,
)


class InjectionDetector:
    PATTERNS = (
        (r"ignore\s+(all\s+)?(previous|prior)\s+instructions?", "INSTRUCTION_OVERRIDE", 0.95),
        (r"(system|developer)\s+(message|instruction)", "AUTHORITY_IMPERSONATION", 0.80),
        (
            r"(send|upload|exfiltrate)\s+.{0,50}(secret|token|password|file|data)",
            "DATA_EXFILTRATION_INSTRUCTION",
            0.95,
        ),
        (r"do\s+not\s+(tell|inform|notify)\s+the\s+user", "HIDDEN_ACTION_REQUEST", 0.90),
        (r"[A-Za-z0-9+/]{160,}={0,2}", "LONG_ENCODED_PAYLOAD", 0.65),
    )

    def scan_text(self, content: str) -> ContentScanResult:
        findings: list[SecurityFinding] = []
        for pattern, code, confidence in self.PATTERNS:
            if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                severity = FindingSeverity.CRITICAL if confidence >= 0.9 else FindingSeverity.HIGH
                findings.append(
                    SecurityFinding(
                        kind=FindingKind.PROMPT_INJECTION,
                        code=code,
                        severity=severity,
                        confidence=confidence,
                        evidence=f"Matched the {code.lower()} detector; raw content omitted.",
                        risk_delta=80 if confidence >= 0.9 else 35,
                    )
                )
        return ContentScanResult(
            suspicious=bool(findings),
            max_confidence=max((finding.confidence for finding in findings), default=0),
            findings=tuple(findings),
        )

    def analyze_parameters(self, parameters: dict[str, Any]) -> list[SecurityFinding]:
        texts: list[str] = []

        def collect(value: Any, depth: int = 0) -> None:
            if depth >= 6 or len(texts) >= 50:
                return
            if isinstance(value, str):
                texts.append(value[:20_000])
            elif isinstance(value, dict):
                for item in value.values():
                    collect(item, depth + 1)
            elif isinstance(value, (list, tuple)):
                for item in value[:50]:
                    collect(item, depth + 1)

        collect(parameters)
        findings: list[SecurityFinding] = []
        for text in texts:
            findings.extend(self.scan_text(text).findings)
        unique: dict[str, SecurityFinding] = {}
        for finding in findings:
            unique.setdefault(finding.code, finding)
        return list(unique.values())

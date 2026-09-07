class ASGPError(RuntimeError):
    """Base SDK error."""


class VerificationUnavailable(ASGPError):
    """The gateway could not return a trustworthy verification result."""


class ActionBlocked(ASGPError):
    def __init__(self, reason_codes: tuple[str, ...]) -> None:
        self.reason_codes = reason_codes
        super().__init__(f"ASGP blocked action: {', '.join(reason_codes)}")


class ApprovalRequired(ASGPError):
    """Reserved for the Phase 3 approval workflow."""


class ContentQuarantined(ASGPError):
    """Raised when untrusted content must not be exposed to the agent."""

    def __init__(self, finding_codes: tuple[str, ...]) -> None:
        self.finding_codes = finding_codes
        super().__init__(f"Content quarantined: {', '.join(finding_codes)}")

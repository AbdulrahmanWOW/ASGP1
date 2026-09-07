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

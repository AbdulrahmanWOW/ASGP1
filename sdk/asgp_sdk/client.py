import time
from typing import Protocol
from uuid import UUID

import httpx
from pydantic import ValidationError

from asgp_sdk.contracts import (
    ActionRequest,
    ApprovalResult,
    ApprovalState,
    ContentIngressRequest,
    ContentIngressResult,
    VerificationResult,
)
from asgp_sdk.exceptions import ActionBlocked, VerificationUnavailable
from asgp_sdk.signing import ActionSigner


class Verifier(Protocol):
    def verify(self, request: ActionRequest) -> VerificationResult: ...


class ContentGuard(Protocol):
    def ingest_content(self, request: ContentIngressRequest) -> ContentIngressResult: ...


class ASGPClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 5.0,
        *,
        signer: ActionSigner | None = None,
        intent_anchor_hash: str | None = None,
        api_key: str | None = None,
        intent_token: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.signer = signer
        self.intent_anchor_hash = intent_anchor_hash
        self.api_key = api_key
        self.intent_token = intent_token

    @property
    def headers(self) -> dict[str, str]:
        return {"X-ASGP-Key": self.api_key} if self.api_key else {}

    def verify(self, request: ActionRequest) -> VerificationResult:
        if self.intent_token is not None and request.intent_token is None:
            request = request.model_copy(update={"intent_token": self.intent_token})
        if self.signer is not None:
            if self.intent_anchor_hash is None:
                raise VerificationUnavailable("Signed client requires an intent anchor hash")
            request = self.signer.sign(request, self.intent_anchor_hash)
        try:
            response = httpx.post(
                f"{self.base_url}/api/v1/actions/verify",
                json=request.model_dump(mode="json", exclude_none=True),
                headers=self.headers,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            return VerificationResult.model_validate(response.json())
        except (httpx.HTTPError, ValidationError, ValueError) as error:
            raise VerificationUnavailable("ASGP verification failed closed") from error

    def ingest_content(self, request: ContentIngressRequest) -> ContentIngressResult:
        try:
            response = httpx.post(
                f"{self.base_url}/api/v1/content/ingress",
                json=request.model_dump(mode="json"),
                headers=self.headers,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            return ContentIngressResult.model_validate(response.json())
        except (httpx.HTTPError, ValidationError, ValueError) as error:
            raise VerificationUnavailable("ASGP content ingress failed closed") from error

    def wait_for_approval(
        self,
        approval_id: UUID,
        action_id: UUID,
        *,
        max_wait_seconds: float = 300,
        poll_interval_seconds: float = 1,
    ) -> None:
        deadline = time.monotonic() + max_wait_seconds
        try:
            while time.monotonic() < deadline:
                response = httpx.get(
                    f"{self.base_url}/api/v1/approvals/{approval_id}",
                    headers=self.headers,
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                approval = ApprovalResult.model_validate(response.json())
                if approval.action_id != action_id:
                    raise VerificationUnavailable("Approval action binding mismatch")
                if approval.status is ApprovalState.APPROVED:
                    consumed = httpx.post(
                        f"{self.base_url}/api/v1/approvals/{approval_id}/consume",
                        json={"action_id": str(action_id)},
                        headers=self.headers,
                        timeout=self.timeout_seconds,
                    )
                    consumed.raise_for_status()
                    return
                if approval.status in {
                    ApprovalState.REJECTED,
                    ApprovalState.EXPIRED,
                    ApprovalState.CONSUMED,
                }:
                    raise ActionBlocked((f"APPROVAL_{approval.status.value.upper()}",))
                time.sleep(poll_interval_seconds)
        except ActionBlocked:
            raise
        except (httpx.HTTPError, ValidationError, ValueError) as error:
            raise VerificationUnavailable("Approval verification failed closed") from error
        raise VerificationUnavailable("Approval wait timed out")

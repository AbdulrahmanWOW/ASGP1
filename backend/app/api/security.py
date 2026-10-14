from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_container
from app.core.auth import AgentOrUser, HumanUser
from app.domain.security import (
    ContentDisposition,
    ContentIngressRequest,
    ContentIngressResult,
    ContentScanRequest,
    ContentScanResult,
    SecurityFinding,
)
from app.services.container import ServiceContainer
from app.services.injection import InjectionDetector

router = APIRouter(tags=["security"])
Services = Annotated[ServiceContainer, Depends(get_container)]


@router.post("/content/scan", response_model=ContentScanResult)
async def scan_content(request: ContentScanRequest, _: AgentOrUser) -> ContentScanResult:
    return InjectionDetector().scan_text(request.content)


@router.post("/content/ingress", response_model=ContentIngressResult)
async def guard_content_ingress(
    request: ContentIngressRequest, services: Services, _: AgentOrUser
) -> ContentIngressResult:
    if services.store.get_session(request.session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    scan = InjectionDetector().scan_text(request.content)
    if scan.suspicious:
        return ContentIngressResult(
            disposition=ContentDisposition.QUARANTINED,
            safe_content=None,
            max_confidence=scan.max_confidence,
            findings=scan.findings,
        )
    return ContentIngressResult(
        disposition=ContentDisposition.CLEAN,
        safe_content=request.content,
        max_confidence=scan.max_confidence,
        findings=scan.findings,
    )


@router.get("/findings/{session_id}", response_model=list[SecurityFinding])
async def list_findings(
    session_id: UUID, services: Services, _: HumanUser
) -> list[SecurityFinding]:
    return services.store.findings_for_session(session_id)

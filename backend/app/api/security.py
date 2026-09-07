from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import get_container
from app.domain.security import ContentScanRequest, ContentScanResult, SecurityFinding
from app.services.container import ServiceContainer
from app.services.injection import InjectionDetector

router = APIRouter(tags=["security"])
Services = Annotated[ServiceContainer, Depends(get_container)]


@router.post("/content/scan", response_model=ContentScanResult)
async def scan_content(request: ContentScanRequest) -> ContentScanResult:
    return InjectionDetector().scan_text(request.content)


@router.get("/findings/{session_id}", response_model=list[SecurityFinding])
async def list_findings(session_id: UUID, services: Services) -> list[SecurityFinding]:
    return services.store.findings_for_session(session_id)

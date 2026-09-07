from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import get_container
from app.domain.audit import AuditEvent, AuditVerification
from app.services.container import ServiceContainer

router = APIRouter(prefix="/audit", tags=["audit"])
Services = Annotated[ServiceContainer, Depends(get_container)]


@router.get("/{session_id}", response_model=list[AuditEvent])
async def list_audit_events(session_id: UUID, services: Services) -> list[AuditEvent]:
    return services.store.audit_for_session(session_id)


@router.post("/{session_id}/verify", response_model=AuditVerification)
async def verify_audit_chain(session_id: UUID, services: Services) -> AuditVerification:
    return services.store.verify_audit_chain(session_id)

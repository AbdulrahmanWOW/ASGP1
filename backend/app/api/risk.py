from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import get_container
from app.domain.risk import RiskChange
from app.services.container import ServiceContainer

router = APIRouter(prefix="/risk", tags=["risk"])
Services = Annotated[ServiceContainer, Depends(get_container)]


@router.get("/{session_id}", response_model=list[RiskChange])
async def list_risk_changes(session_id: UUID, services: Services) -> list[RiskChange]:
    return services.store.risk_for_session(session_id)

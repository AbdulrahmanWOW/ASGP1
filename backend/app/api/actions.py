from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_container
from app.core.auth import AgentCaller
from app.domain.actions import ActionRequest, ActionVerification
from app.services.container import ServiceContainer

router = APIRouter(prefix="/actions", tags=["actions"])
Services = Annotated[ServiceContainer, Depends(get_container)]


@router.post("/verify", response_model=ActionVerification)
def verify_action(
    action: ActionRequest, services: Services, principal: AgentCaller
) -> ActionVerification:
    # Sync on purpose: FastAPI runs it in a worker thread, so a slow local judge call does not
    # block the event loop for other requests.
    return services.governance.verify(action, actor=principal.name)

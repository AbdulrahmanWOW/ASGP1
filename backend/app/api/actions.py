from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_container
from app.domain.actions import ActionRequest, ActionVerification
from app.services.container import ServiceContainer

router = APIRouter(prefix="/actions", tags=["actions"])
Services = Annotated[ServiceContainer, Depends(get_container)]


@router.post("/verify", response_model=ActionVerification)
async def verify_action(action: ActionRequest, services: Services) -> ActionVerification:
    return services.governance.verify(action)

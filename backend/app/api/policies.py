from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import get_container
from app.domain.policies import Policy, PolicyCreate
from app.services.container import ServiceContainer

router = APIRouter(prefix="/policies", tags=["policies"])
Services = Annotated[ServiceContainer, Depends(get_container)]


@router.post("", response_model=Policy, status_code=201)
async def create_policy(request: PolicyCreate, services: Services) -> Policy:
    try:
        return services.store.create_policy(request)
    except IntegrityError as error:
        raise HTTPException(status_code=409, detail="Policy name already exists") from error


@router.get("", response_model=list[Policy])
async def list_policies(services: Services) -> list[Policy]:
    return services.store.list_policies()

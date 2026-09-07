from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_container
from app.domain.agents import AgentCreate, AgentIdentity
from app.services.container import ServiceContainer

router = APIRouter(prefix="/agents", tags=["agents"])
Services = Annotated[ServiceContainer, Depends(get_container)]


@router.post("", response_model=AgentIdentity, status_code=201)
async def create_agent(request: AgentCreate, services: Services) -> AgentIdentity:
    return services.store.create_agent(request)


@router.get("/{agent_id}", response_model=AgentIdentity)
async def get_agent(agent_id: UUID, services: Services) -> AgentIdentity:
    agent = services.store.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("/{agent_id}/revoke", response_model=AgentIdentity)
async def revoke_agent(agent_id: UUID, services: Services) -> AgentIdentity:
    try:
        return services.store.revoke_agent(agent_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_container
from app.core.auth import AgentOrUser, HumanUser
from app.domain.sessions import IntentAnchorUpdate, Session, SessionCreate
from app.services.container import ServiceContainer
from app.services.store import SessionNotFoundError, VersionConflictError

router = APIRouter(prefix="/sessions", tags=["sessions"])
Services = Annotated[ServiceContainer, Depends(get_container)]


@router.post("", response_model=Session, status_code=201)
async def create_session(request: SessionCreate, services: Services, _: HumanUser) -> Session:
    return services.store.create_session(request)


@router.get("", response_model=list[Session])
async def list_sessions(services: Services, _: HumanUser) -> list[Session]:
    return services.store.list_sessions()


@router.get("/{session_id}", response_model=Session)
async def get_session(session_id: UUID, services: Services, _: AgentOrUser) -> Session:
    session = services.store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


@router.put("/{session_id}/intent", response_model=Session)
async def update_intent(
    session_id: UUID, request: IntentAnchorUpdate, services: Services, _: HumanUser
) -> Session:
    try:
        return services.store.update_intent(session_id, request)
    except SessionNotFoundError as error:
        raise HTTPException(status_code=404, detail="Session not found") from error
    except VersionConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/{session_id}/revoke", response_model=Session)
async def revoke_session(session_id: UUID, services: Services, _: HumanUser) -> Session:
    try:
        return services.store.revoke_session(session_id)
    except SessionNotFoundError as error:
        raise HTTPException(status_code=404, detail="Session not found") from error

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_container
from app.core.auth import AgentCaller, AgentOrUser, HumanUser
from app.domain.approvals import Approval, ApprovalConsume, ApprovalResolve
from app.services.container import ServiceContainer

router = APIRouter(prefix="/approvals", tags=["approvals"])
Services = Annotated[ServiceContainer, Depends(get_container)]


@router.get("", response_model=list[Approval])
async def list_pending_approvals(services: Services, _: HumanUser) -> list[Approval]:
    return services.store.list_pending_approvals()


@router.get("/{approval_id}", response_model=Approval)
async def get_approval(approval_id: UUID, services: Services, _: AgentOrUser) -> Approval:
    approval = services.store.get_approval(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval


@router.post("/{approval_id}/resolve", response_model=Approval)
async def resolve_approval(
    approval_id: UUID, request: ApprovalResolve, services: Services, principal: HumanUser
) -> Approval:
    """Human decision. Agent keys are rejected (403), so an agent can never approve itself."""
    try:
        return services.store.resolve_approval(
            approval_id, request.resolution, resolved_by=principal.name
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/{approval_id}/consume", response_model=Approval)
async def consume_approval(
    approval_id: UUID, request: ApprovalConsume, services: Services, _: AgentCaller
) -> Approval:
    try:
        return services.store.consume_approval(approval_id, request.action_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

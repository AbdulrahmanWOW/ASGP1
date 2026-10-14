from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ValidationError

from app.api.dependencies import get_container
from app.core.auth import AgentOrUser, HumanUser
from app.domain.intents import (
    ConfirmedIntent,
    IntentDraft,
    IntentDraftConfirm,
    IntentDraftCreate,
    IntentToken,
)
from app.services.container import ServiceContainer
from app.services.intent_service import DraftNotFound

router = APIRouter(prefix="/intents", tags=["intents"])
Services = Annotated[ServiceContainer, Depends(get_container)]


class PublicKey(BaseModel):
    algorithm: str = "Ed25519"
    public_key: str


@router.post("/drafts", response_model=IntentDraft, status_code=201)
def create_draft(
    request: IntentDraftCreate, services: Services, principal: AgentOrUser
) -> IntentDraft:
    """Draft a least-privilege scope for a request. Nothing is authorized until a human confirms."""
    return services.intents.create_draft(request, created_by=principal.name)


@router.get("/drafts/{draft_id}", response_model=IntentDraft)
def get_draft(draft_id: UUID, services: Services, _: AgentOrUser) -> IntentDraft:
    try:
        return services.intents.get_draft(draft_id)
    except DraftNotFound as error:
        raise HTTPException(status_code=404, detail="Draft not found") from error


@router.post("/drafts/{draft_id}/confirm", response_model=ConfirmedIntent, status_code=201)
def confirm_draft(
    draft_id: UUID, edits: IntentDraftConfirm, services: Services, principal: HumanUser
) -> ConfirmedIntent:
    """Human confirmation: creates the session and returns the signed intent token."""
    try:
        return services.intents.confirm(draft_id, edits, confirmed_by=principal.name)
    except DraftNotFound as error:
        raise HTTPException(status_code=404, detail="Draft not found") from error
    except ValidationError as error:
        detail = error.errors(include_url=False, include_input=False, include_context=False)
        raise HTTPException(status_code=422, detail=detail) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/drafts/{draft_id}/reject", response_model=IntentDraft)
def reject_draft(draft_id: UUID, services: Services, principal: HumanUser) -> IntentDraft:
    try:
        return services.intents.reject(draft_id, rejected_by=principal.name)
    except DraftNotFound as error:
        raise HTTPException(status_code=404, detail="Draft not found") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/sessions/{session_id}/token", response_model=IntentToken)
def issue_token(session_id: UUID, services: Services, _: HumanUser) -> IntentToken:
    """Re-issue a token for the session's current anchor (e.g. after an intent update)."""
    session = services.store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return services.intent_tokens.issue(session)


@router.get("/public-key", response_model=PublicKey)
def public_key(services: Services) -> PublicKey:
    return PublicKey(public_key=services.intent_tokens.public_key_b64)

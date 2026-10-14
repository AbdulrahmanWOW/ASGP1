from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.domain.intents import (
    ConfirmedIntent,
    DraftStatus,
    IntentDraft,
    IntentDraftConfirm,
    IntentDraftCreate,
)
from app.domain.sessions import SessionCreate
from app.services.intent import ScopeDrafter, summarize
from app.services.intent_tokens import IntentTokenService
from app.services.store import DatabaseStore


class DraftNotFound(LookupError):
    pass


class IntentService:
    """Draft → human confirmation → session + signed intent token."""

    def __init__(
        self,
        store: DatabaseStore,
        drafter: ScopeDrafter,
        tokens: IntentTokenService,
        *,
        draft_ttl_seconds: int = 900,
    ) -> None:
        self.store = store
        self.drafter = drafter
        self.tokens = tokens
        self.draft_ttl = timedelta(seconds=draft_ttl_seconds)

    def create_draft(self, request: IntentDraftCreate, created_by: str) -> IntentDraft:
        registry = self.store.list_tools()
        if request.candidate_tools is not None:
            wanted = set(request.candidate_tools)
            registry = [tool for tool in registry if tool.name in wanted]
        proposal = self.drafter.draft(request, registry)
        now = datetime.now(UTC)
        draft = IntentDraft(
            draft_id=uuid4(),
            intent=request.intent,
            status=DraftStatus.PENDING,
            allowed_tools=proposal.allowed,
            forbidden_tools=proposal.forbidden,
            approval_required_tools=proposal.approval_required,
            allowed_paths=request.allowed_paths,
            allowed_destinations=request.allowed_destinations,
            items=proposal.items,
            summary=summarize(proposal, request.allowed_paths, request.allowed_destinations),
            drafted_by=proposal.drafted_by,
            created_by=created_by,
            created_at=now,
            expires_at=now + self.draft_ttl,
        )
        return self.store.create_draft(draft)

    def get_draft(self, draft_id: UUID) -> IntentDraft:
        draft = self.store.get_draft(draft_id)
        if draft is None:
            raise DraftNotFound(str(draft_id))
        return draft

    def confirm(
        self, draft_id: UUID, edits: IntentDraftConfirm, confirmed_by: str
    ) -> ConfirmedIntent:
        draft = self.get_draft(draft_id)
        if draft.status is not DraftStatus.PENDING:
            raise ValueError(f"Draft is {draft.status.value}, not pending")
        request = SessionCreate(
            intent=draft.intent,
            allowed_tools=(
                edits.allowed_tools
                if edits.allowed_tools is not None
                else frozenset(draft.allowed_tools)
            ),
            forbidden_tools=(
                edits.forbidden_tools
                if edits.forbidden_tools is not None
                else frozenset(draft.forbidden_tools)
            ),
            allowed_paths=(
                edits.allowed_paths if edits.allowed_paths is not None else draft.allowed_paths
            ),
            allowed_destinations=(
                edits.allowed_destinations
                if edits.allowed_destinations is not None
                else frozenset(draft.allowed_destinations)
            ),
        )
        # Claim the draft first so it can only ever produce one session.
        self.store.resolve_draft(draft_id, DraftStatus.CONFIRMED, confirmed_by)
        session = self.store.create_session(
            request, confirmed_by=confirmed_by, requires_intent_token=True
        )
        self.store.link_draft_session(draft_id, session.session_id)
        return ConfirmedIntent(session=session, intent_token=self.tokens.issue(session))

    def reject(self, draft_id: UUID, rejected_by: str) -> IntentDraft:
        self.get_draft(draft_id)
        return self.store.resolve_draft(draft_id, DraftStatus.REJECTED, rejected_by)

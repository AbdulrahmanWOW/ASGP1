from dataclasses import dataclass

from app.db.session import Database
from app.services.ai import AIProvider, IntentAlignmentService
from app.services.behavior import BehavioralAnalyzer
from app.services.crypto import RequestCryptoVerifier
from app.services.embeddings import build_alignment_provider
from app.services.governance import GovernanceService
from app.services.injection import InjectionDetector
from app.services.intent import RuleBasedScopeDrafter, ScopeDrafter
from app.services.intent_service import IntentService
from app.services.intent_tokens import IntentTokenService
from app.services.judge import Judge, OllamaJudge, OllamaScopeDrafter, build_judge
from app.services.policy import PermissionPolicy
from app.services.risk import RiskEngine
from app.services.store import DatabaseStore


@dataclass(frozen=True)
class ServiceContainer:
    database: Database
    store: DatabaseStore
    governance: GovernanceService
    intents: IntentService
    intent_tokens: IntentTokenService


@dataclass(frozen=True)
class PipelineOptions:
    alignment_provider: str = "lexical"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    judge: str = "none"
    ollama_url: str = "http://127.0.0.1:11434"
    judge_model: str = "qwen2.5:3b"
    judge_timeout_seconds: float = 10.0
    require_intent_token: bool = False
    intent_signing_key: str = ""
    intent_token_ttl_seconds: int = 3600


def build_container(
    database_url: str,
    *,
    initialize_schema: bool = False,
    approval_ttl_seconds: int = 300,
    ai_provider: AIProvider | None = None,
    max_blocks_per_session: int = 5,
    options: PipelineOptions | None = None,
    judge: Judge | None = None,
    drafter: ScopeDrafter | None = None,
) -> ServiceContainer:
    options = options or PipelineOptions()
    database = Database(database_url)
    if initialize_schema:
        database.create_schema()
    store = DatabaseStore(database)
    provider = ai_provider or build_alignment_provider(
        options.alignment_provider, model=options.embedding_model
    )
    if judge is None:
        judge = build_judge(
            options.judge,
            base_url=options.ollama_url,
            model=options.judge_model,
            timeout_seconds=options.judge_timeout_seconds,
        )
    if drafter is None:
        drafter = RuleBasedScopeDrafter()
        if isinstance(judge, OllamaJudge):
            drafter = OllamaScopeDrafter(judge, fallback=drafter)
    tokens = IntentTokenService(
        options.intent_signing_key, ttl_seconds=options.intent_token_ttl_seconds
    )
    governance = GovernanceService(
        store,
        PermissionPolicy(),
        RiskEngine(),
        RequestCryptoVerifier(store),
        IntentAlignmentService(provider),
        InjectionDetector(),
        BehavioralAnalyzer(),
        approval_ttl_seconds,
        max_blocks_per_session=max_blocks_per_session,
        intent_tokens=tokens,
        require_intent_token=options.require_intent_token,
        judge=judge,
    )
    return ServiceContainer(
        database=database,
        store=store,
        governance=governance,
        intents=IntentService(store, drafter, tokens),
        intent_tokens=tokens,
    )

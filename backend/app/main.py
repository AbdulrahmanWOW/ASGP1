import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.actions import router as actions_router
from app.api.agents import router as agents_router
from app.api.approvals import router as approvals_router
from app.api.audit import router as audit_router
from app.api.health import router as health_router
from app.api.intents import router as intents_router
from app.api.metrics import router as metrics_router
from app.api.policies import router as policies_router
from app.api.risk import router as risk_router
from app.api.security import router as security_router
from app.api.sessions import router as sessions_router
from app.api.tools import router as tools_router
from app.core.auth import API_KEY_HEADER, AuthConfig, AuthMode
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.services.ai import AIProvider
from app.services.container import PipelineOptions, build_container
from app.services.intent import ScopeDrafter
from app.services.judge import Judge


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    yield


def create_app(
    *,
    database_url: str | None = None,
    initialize_schema: bool = False,
    approval_ttl_seconds: int = 300,
    ai_provider: AIProvider | None = None,
    auth_mode: AuthMode | None = None,
    api_keys: str | None = None,
    max_blocks_per_session: int | None = None,
    pipeline: PipelineOptions | None = None,
    judge: Judge | None = None,
    drafter: ScopeDrafter | None = None,
) -> FastAPI:
    settings = get_settings()
    auth = AuthConfig.from_spec(
        auth_mode or settings.auth_mode,
        settings.api_keys if api_keys is None else api_keys,
    )
    if auth.mode == "disabled" and settings.environment == "production":
        raise RuntimeError("Authentication cannot be disabled in production")
    if auth.mode == "disabled":
        logging.getLogger(__name__).warning(
            "ASGP authentication is DISABLED: every caller is treated as admin. "
            "Use only for local tests and in-process evaluation."
        )
    elif auth.key_count == 0:
        logging.getLogger(__name__).warning(
            "ASGP_API_KEYS is empty: every protected endpoint will return 401."
        )
    application = FastAPI(
        title="ASGP API",
        version="0.1.0",
        description="Security governance gateway for integrated AI-agent tool calls.",
        lifespan=lifespan,
    )
    application.state.services = build_container(
        database_url or settings.database_url,
        initialize_schema=initialize_schema,
        approval_ttl_seconds=approval_ttl_seconds,
        ai_provider=ai_provider,
        max_blocks_per_session=max_blocks_per_session or settings.max_blocks_per_session,
        options=pipeline
        or PipelineOptions(
            alignment_provider=settings.alignment_provider,
            embedding_model=settings.embedding_model,
            judge=settings.judge,
            ollama_url=settings.ollama_url,
            judge_model=settings.judge_model,
            judge_timeout_seconds=settings.judge_timeout_seconds,
            require_intent_token=settings.require_intent_token,
            intent_signing_key=settings.intent_signing_key,
            intent_token_ttl_seconds=settings.intent_token_ttl_seconds,
        ),
        judge=judge,
        drafter=drafter,
    )
    application.state.auth = auth
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Content-Type", "Authorization", API_KEY_HEADER],
    )
    application.include_router(health_router, prefix=settings.api_prefix)
    application.include_router(sessions_router, prefix=settings.api_prefix)
    application.include_router(intents_router, prefix=settings.api_prefix)
    application.include_router(tools_router, prefix=settings.api_prefix)
    application.include_router(actions_router, prefix=settings.api_prefix)
    application.include_router(agents_router, prefix=settings.api_prefix)
    application.include_router(audit_router, prefix=settings.api_prefix)
    application.include_router(policies_router, prefix=settings.api_prefix)
    application.include_router(approvals_router, prefix=settings.api_prefix)
    application.include_router(risk_router, prefix=settings.api_prefix)
    application.include_router(security_router, prefix=settings.api_prefix)
    application.include_router(metrics_router, prefix=settings.api_prefix)
    return application


app = create_app()

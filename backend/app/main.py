from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.actions import router as actions_router
from app.api.agents import router as agents_router
from app.api.approvals import router as approvals_router
from app.api.audit import router as audit_router
from app.api.health import router as health_router
from app.api.metrics import router as metrics_router
from app.api.policies import router as policies_router
from app.api.risk import router as risk_router
from app.api.security import router as security_router
from app.api.sessions import router as sessions_router
from app.api.tools import router as tools_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.services.ai import AIProvider
from app.services.container import build_container


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
) -> FastAPI:
    settings = get_settings()
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
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Content-Type"],
    )
    application.include_router(health_router, prefix=settings.api_prefix)
    application.include_router(sessions_router, prefix=settings.api_prefix)
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

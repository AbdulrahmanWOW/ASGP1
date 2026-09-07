from dataclasses import dataclass

from app.db.session import Database
from app.services.ai import AIProvider, IntentAlignmentService, MockProvider
from app.services.behavior import BehavioralAnalyzer
from app.services.crypto import RequestCryptoVerifier
from app.services.governance import GovernanceService
from app.services.injection import InjectionDetector
from app.services.policy import PermissionPolicy
from app.services.risk import RiskEngine
from app.services.store import DatabaseStore


@dataclass(frozen=True)
class ServiceContainer:
    database: Database
    store: DatabaseStore
    governance: GovernanceService


def build_container(
    database_url: str,
    *,
    initialize_schema: bool = False,
    approval_ttl_seconds: int = 300,
    ai_provider: AIProvider | None = None,
) -> ServiceContainer:
    database = Database(database_url)
    if initialize_schema:
        database.create_schema()
    store = DatabaseStore(database)
    governance = GovernanceService(
        store,
        PermissionPolicy(),
        RiskEngine(),
        RequestCryptoVerifier(store),
        IntentAlignmentService(ai_provider or MockProvider()),
        InjectionDetector(),
        BehavioralAnalyzer(),
        approval_ttl_seconds,
    )
    return ServiceContainer(database=database, store=store, governance=governance)

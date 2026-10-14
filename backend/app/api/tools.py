from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_container
from app.core.auth import AdminOnly, AgentOrUser
from app.domain.tools import ToolDefinition
from app.services.container import ServiceContainer

router = APIRouter(prefix="/tools", tags=["tools"])
Services = Annotated[ServiceContainer, Depends(get_container)]


@router.post("/register", response_model=ToolDefinition, status_code=201)
async def register_tool(
    tool: ToolDefinition, services: Services, _: AdminOnly
) -> ToolDefinition:
    return services.store.register_tool(tool)


@router.get("", response_model=list[ToolDefinition])
async def list_tools(services: Services, _: AgentOrUser) -> list[ToolDefinition]:
    return services.store.list_tools()

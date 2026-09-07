from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_container
from app.domain.tools import ToolDefinition
from app.services.container import ServiceContainer

router = APIRouter(prefix="/tools", tags=["tools"])
Services = Annotated[ServiceContainer, Depends(get_container)]


@router.post("/register", response_model=ToolDefinition, status_code=201)
async def register_tool(tool: ToolDefinition, services: Services) -> ToolDefinition:
    return services.store.register_tool(tool)

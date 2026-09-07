from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_container
from app.services.container import ServiceContainer

router = APIRouter(prefix="/metrics", tags=["metrics"])
Services = Annotated[ServiceContainer, Depends(get_container)]


@router.get("/pipeline")
async def pipeline_metrics(services: Services) -> dict[str, object]:
    return services.store.pipeline_metrics()

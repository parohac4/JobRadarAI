from fastapi import APIRouter, Query

from app.services.geo import search_places

router = APIRouter()


@router.get("/places")
async def places(q: str = Query("", max_length=80)):
    return {"items": search_places(q)}

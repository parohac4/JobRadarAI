import logging
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.database import get_db
from app.schemas.system import HealthOut

logger = logging.getLogger('jobradar.system')
router = APIRouter()

@router.get('/health', response_model=HealthOut)
async def health(db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    try:
        await db.execute(text('SELECT 1'))
    except Exception:
        logger.exception('Health check: databáze nedostupná')
        return JSONResponse(status_code=503, content={'status': 'db_error', 'demo_mode': settings.demo_mode})
    return HealthOut(status='ok', demo_mode=settings.demo_mode)

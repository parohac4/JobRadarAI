from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_write_access
from app.database import get_db
from app.models.feed_source import FeedSource
from app.models.user import User
from app.schemas.feed import FeedSourceCreate, FeedSourceOut, FeedSourceUpdate
from app.services import audit
from app.services.default_feeds import ensure_default_feeds
from app.services.job_import import UnsafeUrlError, assert_public_url

router = APIRouter()


@router.get("", response_model=list[FeedSourceOut])
async def list_feeds(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await ensure_default_feeds(db, user)
    result = await db.execute(
        select(FeedSource).where(FeedSource.user_id == user.id).order_by(FeedSource.enabled.desc(), FeedSource.id)
    )
    return list(result.scalars().all())


@router.post("/ensure-defaults")
async def ensure_defaults_feeds(
    _: None = Depends(require_write_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    added = await ensure_default_feeds(db, user)
    return {"added": added}


@router.post("", response_model=FeedSourceOut)
async def create_feed(
    body: FeedSourceCreate,
    _: None = Depends(require_write_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await assert_public_url(body.url)
    except UnsafeUrlError as e:
        raise HTTPException(status_code=400, detail=str(e))
    feed = FeedSource(user_id=user.id, title=body.title, url=body.url, enabled=body.enabled)
    db.add(feed)
    await audit.log_audit(db, user_id=user.id, action="feed.create", entity_type="feed", entity_id="new")
    await db.commit()
    await db.refresh(feed)
    return feed


@router.patch("/{feed_id}", response_model=FeedSourceOut)
async def update_feed(
    feed_id: int,
    body: FeedSourceUpdate,
    _: None = Depends(require_write_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(FeedSource).where(FeedSource.id == feed_id, FeedSource.user_id == user.id))
    feed = result.scalar_one_or_none()
    if not feed:
        raise HTTPException(status_code=404, detail="RSS zdroj nenalezen")
    data = body.model_dump(exclude_unset=True)
    if "url" in data and data["url"]:
        try:
            await assert_public_url(data["url"])
        except UnsafeUrlError as e:
            raise HTTPException(status_code=400, detail=str(e))
    for k, v in data.items():
        setattr(feed, k, v)
    await audit.log_audit(
        db,
        user_id=user.id,
        action="feed.update",
        entity_type="feed",
        entity_id=str(feed.id),
        payload=data,
    )
    await db.commit()
    await db.refresh(feed)
    return feed


@router.delete("/{feed_id}", status_code=204)
async def delete_feed(
    feed_id: int,
    _: None = Depends(require_write_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(FeedSource).where(FeedSource.id == feed_id, FeedSource.user_id == user.id))
    feed = result.scalar_one_or_none()
    if not feed:
        raise HTTPException(status_code=404, detail="RSS zdroj nenalezen")
    await db.delete(feed)
    await db.commit()

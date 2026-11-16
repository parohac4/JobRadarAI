from datetime import UTC, datetime
from unittest.mock import AsyncMock
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base, get_db
from app.core.deps import get_current_user, require_write_access
from app.main import app
from app.models.profile import ProfessionalProfile
from app.models.user import User
from app.models.job import JobListing
from app.models.evaluation import AiEvaluation
from app.schemas.aggregator import SearchSettings
from app.services.aggregator import offers, score_version, monitor, enabled_source
from app.services.places import resolve_place, location_distance, suggestions
from app.services.portal_import import parse_portal, source_id

@compiles(JSONB, 'sqlite')
def sqlite_json(element, compiler, **kwargs): return 'JSON'

@pytest.fixture
async def store():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as db:
        user = User(email='aggregator@example.test', hashed_password='unused', is_active=True)
        db.add(user)
        await db.flush()
        config = SearchSettings(city='Strakonice', radius_km=30)
        profile = ProfessionalProfile(user_id=user.id, summary='', skills=[], experience=[], education=[],
            preferences={'aggregator': config.model_dump(mode='json')}, cv_versions=[])
        db.add(profile)
        await db.commit()
        yield db, user, profile
    await engine.dispose()

def add_job(db, user, title, city, url):
    job = JobListing(user_id=user.id, title=title, company='Firma', location=city, url=url, raw_text=title,
        source='api', imported_at=datetime.now(UTC), content_hash=url)
    db.add(job)
    return job

def test_villages_ambiguity_hybrid():
    home = resolve_place('Strakonice')
    assert 10 < location_distance(home, 'Volyně')[0] < 12
    assert location_distance(home, 'Praha / hybrid')[0] > 90
    assert location_distance(home, 'fully remote') == (None, True)
    assert resolve_place('Lhota') is None
    hits = suggestions('Lhota')
    assert hits and resolve_place(hits[0]['label']) is not None
    assert resolve_place('Strak') is None

def test_portal_parsers_and_canonical_urls():
    body = '''<article class="SearchResultCard"><h2><a data-jobad-id="123" href="/rpd/123/?tracking=1">Technik</a></h2>
    <li class="SearchResultCard__footerItem"><span translate="no">Firma</span></li><li data-test="serp-locality">Volyně</li></article>'''
    j = parse_portal(body, 'https://www.jobs.cz/prace/strakonice/')[0]
    assert (j.title, j.company, j.location, j.url) == ('Technik', 'Firma', 'Volyně', 'https://www.jobs.cz/rpd/123/')
    body = '''<article><a data-testid="advert-link" href="/nabidka/abc/">Prodejce</a>
    <li><span class="accessibility-hidden">Lokalita:</span><span>Strakonice I</span></li>
    <li><span class="accessibility-hidden">Název firmy:</span><span>Obchod</span></li></article>'''
    j = parse_portal(body, 'https://www.prace.cz/nabidky/')[0]
    assert j.company == 'Obchod' and j.location == 'Strakonice I'
    with pytest.raises(ValueError): parse_portal('<h1>Access denied</h1>', 'https://www.prace.cz/nabidky/')
    assert source_id('https://jobs.cz.attacker.test/rpd/1') == 'custom'

async def test_radius_before_pagination_and_zero_distance(store):
    db, user, profile = store
    local = add_job(db, user, 'Místní', 'Strakonice', 'https://www.jobs.cz/rpd/local/')
    for i in range(510): add_job(db, user, f'Praha {i}', 'Praha', f'https://www.jobs.cz/rpd/{i}/')
    add_job(db, user, 'Blízká', 'Volyně', 'https://www.prace.cz/nabidka/close/')
    add_job(db, user, 'Hybrid mimo okruh', 'Praha / hybrid', 'https://www.jobs.cz/rpd/hybrid/')
    await db.commit()
    result = await offers(db, user.id, limit=1, sort='distance')
    assert result['total'] == 2 and result['has_more']
    assert result['items'][0]['id'] == local.id and result['items'][0]['distance_km'] == 0
    assert (await offers(db, user.id, skip=1, limit=1, sort='distance'))['items'][0]['title'] == 'Blízká'

async def test_preferences_invalidate_ai_scores_and_disabled_sources(store):
    db, user, profile = store
    config = SearchSettings.model_validate(profile.preferences['aggregator'])
    config.ai_enabled = True
    config.ai_preferences = 'Chci pomáhat lidem'
    profile.preferences = {'aggregator': config.model_dump(mode='json')}
    job = add_job(db, user, 'Technik', 'Strakonice', 'https://www.jobs.cz/rpd/1/')
    await db.flush()
    db.add(AiEvaluation(job_listing_id=job.id, score=90, provider=score_version(config), summary='Shoda'))
    await db.commit()
    assert (await offers(db, user.id))['items'][0]['score'] == 90
    config.ai_preferences = 'Chci být účetní'
    profile.preferences = {'aggregator': config.model_dump(mode='json')}
    await db.commit()
    assert (await offers(db, user.id))['items'][0]['score'] is None
    config.sources = ['sitprace']
    profile.preferences = {'aggregator': config.model_dump(mode='json')}
    await db.commit()
    assert (await offers(db, user.id))['total'] == 0
    assert not enabled_source(config, 'custom:https://example.com/removed-feed')

async def test_settings_auth_validation_and_removed_endpoints(store):
    db, user, profile = store
    async def override_db(): yield db
    app.dependency_overrides[get_db] = override_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            assert (await client.get('/api/v1/aggregate/settings')).status_code == 401
            app.dependency_overrides[get_current_user] = lambda: user
            app.dependency_overrides[require_write_access] = lambda: None
            config = SearchSettings(city='Volyně', radius_km=20, keywords='technik', interval_minutes=60)
            response = await client.put('/api/v1/aggregate/settings', json=config.model_dump(mode='json'))
            assert response.status_code == 200, response.text
            assert response.json()['settings']['city'].startswith('Volyně')
            assert user.hashed_password == 'unused'
            config.city = 'Nevímkde'
            assert (await client.put('/api/v1/aggregate/settings', json=config.model_dump(mode='json'))).status_code == 400
            config.city = 'Strakonice'
            config.ai_enabled = True
            assert (await client.put('/api/v1/aggregate/settings', json=config.model_dump(mode='json'))).status_code == 400
            for path in ['/applications', '/profile/cv', '/jobs/1/generate-response']:
                assert (await client.post('/api/v1' + path)).status_code == 404
            assert (await client.get('/api/v1/aggregate/places?q=Volyn')).json()['items']
    finally: app.dependency_overrides.clear()

async def test_monitor_concurrency_lock(store, monkeypatch):
    db, user, profile = store
    db.scalar = AsyncMock(return_value=False)
    fetch = AsyncMock()
    monkeypatch.setattr('app.services.aggregator.fetch_source', fetch)
    assert (await monitor(db, user, force=True))['status'] == 'running'
    fetch.assert_not_called()

async def test_monitor_partial_failure_dedup_and_freshness(store, monkeypatch):
    from app.schemas.job import JobListingCreate
    from app.models.sync import SyncRun
    from sqlalchemy import select
    db, user, profile = store
    db.scalar = AsyncMock(return_value=True)  # PostgreSQL advisory lock only
    rows = [JobListingCreate(title='Technik', company='Firma', location='Volyně',
              url='https://www.jobs.cz/rpd/100/', raw_text='Servis techniky', source='api')]
    async def fetch(key, config, home, **kwargs):
        if key == 'sitprace': raise ValueError('zdroj dočasně neodpovídá')
        return rows, []
    monkeypatch.setattr('app.services.aggregator.fetch_source', fetch)
    result = await monitor(db, user, force=True)
    assert result['status'] == 'partial' and result['created'] == 1
    assert result['sources']['sitprace']['status'] == 'error'
    job = (await db.execute(select(JobListing))).scalar_one()
    assert job.last_checked_at is not None
    assert 'jobs' in job.requirements_text and 'prace' in job.requirements_text
    assert len((await db.execute(select(SyncRun))).scalars().all()) == 1
    assert (await offers(db, user.id))['total'] == 1

async def test_partial_import_preserves_last_complete_success(store, monkeypatch):
    from app.models.sync import SyncRun
    from sqlalchemy import select
    db, user, profile = store
    db.scalar = AsyncMock(return_value=True)
    previous_success = '2026-11-15T10:00:00+00:00'
    db.add(SyncRun(user_id=user.id, source='aggregator', status='ok', details={
        'sources': {'jobs': {'status': 'ok', 'last_success_at': previous_success}}, 'cycle': 1
    }))
    await db.commit()
    async def fetch(key, *args, **kwargs):
        return [], ['Jedna lokalita je dočasně nedostupná.'] if key == 'jobs' else []
    monkeypatch.setattr('app.services.aggregator.fetch_source', fetch)
    result = await monitor(db, user, force=True)
    jobs = result['sources']['jobs']
    assert jobs['status'] == 'partial'
    assert jobs['last_success_at'] == previous_success
    assert jobs['checked_at'] != previous_success
    assert jobs['last_success_is_complete']

async def test_seen_and_marked_are_persistent_and_independent(store):
    from app.services.job_interactions import update_interaction
    from sqlalchemy.ext.asyncio import async_sessionmaker
    db, user, profile = store
    job = add_job(db, user, 'Technik', 'Strakonice', 'https://www.jobs.cz/rpd/state/')
    await db.commit()
    marked = await update_interaction(db, user.id, job.id, marked=True)
    assert marked['marked'] and marked['seen_at'] is None
    viewed = await update_interaction(db, user.id, job.id, seen=True)
    assert viewed['marked'] and viewed['seen_at'] is not None
    again = await update_interaction(db, user.id, job.id, seen=True)
    assert again['seen_at'] == viewed['seen_at']
    assert again['marked_at'] == marked['marked_at']
    async with async_sessionmaker(db.bind, expire_on_commit=False)() as fresh:
        row = (await offers(fresh, user.id))['items'][0]
        assert row['seen_at'] is not None and row['marked']
    unseen = await update_interaction(db, user.id, job.id, seen=False)
    assert unseen['seen_at'] is None and unseen['marked']
    unmarked = await update_interaction(db, user.id, job.id, marked=False)
    assert not unmarked['marked'] and unmarked['marked_at'] is None


async def test_seen_filter_applies_before_pagination_and_combines_with_marked(store):
    from app.models.job_interaction import JobInteraction
    db, user, profile = store
    jobs = [add_job(db, user, f'Technik {i}', 'Strakonice', f'https://www.jobs.cz/rpd/filter-{i}/') for i in range(55)]
    await db.flush()
    for job in jobs[:54]:
        db.add(JobInteraction(user_id=user.id, job_id=job.id, seen_at=datetime.now(UTC), marked=True))
    db.add(JobInteraction(user_id=user.id, job_id=jobs[-1].id, marked=True))
    await db.commit()
    result = await offers(db, user.id, seen='unseen', marked_only=True, limit=1)
    assert result['total'] == 1 and not result['has_more']
    assert result['items'][0]['id'] == jobs[-1].id
    assert (await offers(db, user.id, seen='seen'))['total'] == 54
    assert (await offers(db, user.id, marked_only=True))['total'] == 55


async def test_oldest_newest_and_nearest_use_the_right_order(store):
    from datetime import timedelta
    db, user, profile = store
    now = datetime.now(UTC)
    newest = add_job(db, user, 'Nová', 'Volyně', 'https://www.jobs.cz/rpd/newest/')
    nearest = add_job(db, user, 'Nejbližší', 'Strakonice', 'https://www.jobs.cz/rpd/nearest/')
    oldest = add_job(db, user, 'Stará', 'Písek', 'https://www.jobs.cz/rpd/oldest/')
    newest.imported_at = now
    nearest.imported_at = now - timedelta(days=1)
    oldest.imported_at = now - timedelta(days=2)
    await db.commit()
    assert [j['title'] for j in (await offers(db, user.id, sort='newest'))['items']] == ['Nová', 'Nejbližší', 'Stará']
    assert [j['title'] for j in (await offers(db, user.id, sort='oldest'))['items']] == ['Stará', 'Nejbližší', 'Nová']
    assert (await offers(db, user.id, sort='distance'))['items'][0]['id'] == nearest.id


async def test_reimport_keeps_viewed_and_bookmarked_status(store):
    from app.schemas.job import JobListingCreate
    from app.services.jobs import create_job
    from app.services.job_interactions import update_interaction
    db, user, profile = store
    payload = JobListingCreate(title='Technik', company='Firma', location='Strakonice',
        url='https://www.jobs.cz/rpd/reimport/', raw_text='Technická práce', source='api')
    original, duplicate = await create_job(db, user.id, payload)
    await db.commit()
    await update_interaction(db, user.id, original.id, seen=True, marked=True)
    repeated, duplicate = await create_job(db, user.id, payload)
    await db.commit()
    assert duplicate is not None and repeated.id == original.id
    result = await offers(db, user.id, seen='seen', marked_only=True)
    assert result['total'] == 1 and result['items'][0]['marked']


async def test_interaction_api_auth_ownership_and_filters(store):
    db, user, profile = store
    mine = add_job(db, user, 'Moje', 'Strakonice', 'https://www.jobs.cz/rpd/mine/')
    other = User(email='other@example.test', hashed_password='unused', is_active=True)
    db.add(other)
    await db.flush()
    theirs = add_job(db, other, 'Cizí', 'Strakonice', 'https://www.jobs.cz/rpd/theirs/')
    await db.commit()
    async def override_db(): yield db
    app.dependency_overrides[get_db] = override_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            path = f'/api/v1/aggregate/jobs/{mine.id}/interaction'
            assert (await client.patch(path, json={'seen': True})).status_code == 401
            app.dependency_overrides[get_current_user] = lambda: user
            app.dependency_overrides[require_write_access] = lambda: None
            assert (await client.patch(path, json={})).status_code == 400
            assert (await client.patch(f'/api/v1/aggregate/jobs/{theirs.id}/interaction', json={'marked': True})).status_code == 404
            assert (await client.patch(path, json={'seen': True, 'marked': True})).status_code == 200
            detail = (await client.get(f'/api/v1/aggregate/jobs/{mine.id}')).json()
            assert detail['seen_at'] and detail['marked']
            listing = await client.get('/api/v1/aggregate/jobs?seen=unseen&marked_only=true&sort=oldest')
            assert listing.status_code == 200 and listing.json()['total'] == 0
            listing = await client.get('/api/v1/aggregate/jobs?seen=seen&marked_only=true&sort=oldest')
            assert listing.json()['total'] == 1
            assert (await client.patch(path, json={'seen': False})).json()['marked']
            assert (await client.get('/api/v1/aggregate/jobs?seen=unseen&marked_only=true')).json()['total'] == 1
            config = (await client.get('/api/v1/aggregate/settings')).json()['settings']
            config['sort'] = 'oldest'
            assert (await client.put('/api/v1/aggregate/settings', json=config)).status_code == 200
    finally: app.dependency_overrides.clear()

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application, ApplicationHistory, ApplicationNote
from app.models.enums import ApplicationStatus, JobSource
from app.models.evaluation import AiEvaluation
from app.models.job import JobListing
from app.models.profile import ProfessionalProfile
from app.models.response import GeneratedResponse
from app.models.user import User
from app.schemas.job import JobListingCreate
from app.services import jobs as job_service
from app.services.ai import evaluate_job

DEMO_JOBS = [
    JobListingCreate(
        title="Technik IT podpory L2",
        company="HostMaster s.r.o. (fiktivní)",
        location="České Budějovice / hybrid",
        url="https://example.com/jobs/hostmaster-l2",
        raw_text=(
            "Hledáme technika L2. Požadujeme znalost Linux, DNS a webhosting. "
            "Zákaznická podpora po telefonu i e-mailem. Znalost Apache/Nginx výhodou."
        ),
        source=JobSource.manual,
    ),
    JobListingCreate(
        title="Specialista zákaznické podpory",
        company="CloudServis a.s. (fiktivní)",
        location="Remote (ČR)",
        url="https://example.com/jobs/cloudservis-support",
        raw_text="Technická podpora hostingu, ticketing, komunikace s klienty. Základy Linux výhodou.",
        source=JobSource.manual,
    ),
    JobListingCreate(
        title="Správce linuxových serverů",
        company="DataPark (fiktivní)",
        location="Praha",
        url="https://example.com/jobs/datapark-linux",
        raw_text="Správa serverů Linux, monitoring, řešení incidentů. Požadujeme maturitu.",
        source=JobSource.manual,
    ),
]


async def seed_demo_data(db: AsyncSession, user: User) -> dict:
    job_ids_sq = select(JobListing.id).where(JobListing.user_id == user.id)
    app_ids_sq = select(Application.id).where(Application.user_id == user.id)

    await db.execute(delete(ApplicationNote).where(ApplicationNote.application_id.in_(app_ids_sq)))
    await db.execute(delete(ApplicationHistory).where(ApplicationHistory.application_id.in_(app_ids_sq)))
    await db.execute(delete(Application).where(Application.user_id == user.id))
    await db.execute(delete(GeneratedResponse).where(GeneratedResponse.job_listing_id.in_(job_ids_sq)))
    await db.execute(delete(AiEvaluation).where(AiEvaluation.job_listing_id.in_(job_ids_sq)))
    await db.execute(delete(JobListing).where(JobListing.user_id == user.id))

    result = await db.execute(select(ProfessionalProfile).where(ProfessionalProfile.user_id == user.id))
    profile = result.scalar_one()

    for data in DEMO_JOBS:
        job, _ = await job_service.create_job(db, user.id, data)
        ev = await evaluate_job(profile, title=job.title, location=job.location, raw_text=job.raw_text)
        db.add(AiEvaluation(job_listing_id=job.id, **ev))
        status = ApplicationStatus.recommended if ev["score"] >= 60 else ApplicationStatus.new_offer
        app = Application(user_id=user.id, job_listing_id=job.id, status=status)
        db.add(app)
        await db.flush()
        db.add(ApplicationHistory(application_id=app.id, from_status=None, to_status=status, note="Demo data"))

    await db.commit()
    return {"jobs_created": len(DEMO_JOBS)}


async def seed_demo_if_empty(db: AsyncSession) -> None:
    user = (await db.execute(select(User).limit(1))).scalar_one_or_none()
    if not user:
        return
    has_jobs = (await db.execute(select(JobListing.id).where(JobListing.user_id == user.id).limit(1))).first()
    if not has_jobs:
        await seed_demo_data(db, user)

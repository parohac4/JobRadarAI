from fastapi import APIRouter

from app.api.v1 import applications, auth, dashboard, feeds, geo, jobs, profile, system

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(feeds.router, prefix="/feeds", tags=["feeds"])
api_router.include_router(geo.router, prefix="/geo", tags=["geo"])

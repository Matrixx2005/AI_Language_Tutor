from fastapi import APIRouter

from app.api.routes import auth, profile

# API nghiệp vụ có phiên bản.
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(profile.router)

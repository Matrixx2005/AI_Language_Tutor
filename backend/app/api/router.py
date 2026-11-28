from fastapi import APIRouter

from app.api.routes import auth, chat, languages, placement, profile, system

# API nghiệp vụ có phiên bản.
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(languages.router)
api_router.include_router(chat.router)
api_router.include_router(placement.router)
api_router.include_router(system.router)

"""Điểm vào FastAPI. Chạy từ thư mục gốc dự án:

    uvicorn app.main:app --app-dir backend --reload --reload-dir backend

`--reload-dir backend`: chỉ theo dõi code backend (không theo dõi .venv, data, docs).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.log_config import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    # Thiếu JWT_SECRET thì dừng ngay khi khởi động, không chạy với secret rỗng/yếu.
    settings.require_jwt_secret()

    app = FastAPI(title=settings.app_name)
    # CORS chỉ cho origin cụ thể: CORS_ORIGINS trong .env, hoặc Vite dev khi development.
    cors_origins = settings.effective_cors_origins()
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
        )
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(api_router)
    return app


app = create_app()

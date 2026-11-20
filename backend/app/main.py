"""Điểm vào FastAPI. Chạy: uvicorn app.main:app --app-dir backend --reload"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers


def create_app() -> FastAPI:
    settings = get_settings()
    # Thiếu JWT_SECRET thì dừng ngay khi khởi động, không chạy với secret rỗng/yếu.
    settings.require_jwt_secret()

    app = FastAPI(title=settings.app_name)
    # CORS chỉ được bật khi phát triển và chỉ cho hai địa chỉ máy chủ Vite cục bộ.
    if settings.environment == "development":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
            allow_credentials=False,
            allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
        )
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(api_router)
    return app


app = create_app()

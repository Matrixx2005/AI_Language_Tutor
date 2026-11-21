"""Định dạng lỗi thống nhất: {"error": {"code", "message", "details"?}}.

`code` ổn định cho frontend xử lý; `message` tiếng Việt để hiển thị.
Lỗi 422 KHÔNG trả lại giá trị người dùng gửi (FastAPI mặc định có trường `input`,
có thể chứa mật khẩu).
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.errors")


class AppError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(code)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = headers


def error_body(code: str, message: str, details: list[dict[str, Any]] | None = None) -> dict:
    error: dict[str, Any] = {"code": code, "message": message}
    if details:
        error["details"] = details
    return {"error": error}


def _log_rejected(request: Request, status_code: int, reason: str) -> None:
    # Chỉ ghi phương thức, đường dẫn, tên ô và mã lỗi. KHÔNG ghi giá trị người dùng gửi.
    logger.info("%s %s %s -> %s", status_code, request.method, request.url.path, reason)


async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    _log_rejected(request, exc.status_code, exc.code)
    return JSONResponse(
        error_body(exc.code, exc.message), status_code=exc.status_code, headers=exc.headers
    )


async def _validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {
            # Bỏ tiền tố "body" để frontend gắn lỗi vào đúng ô nhập.
            "field": ".".join(str(part) for part in error["loc"] if part != "body"),
            "type": error["type"],
            # Bỏ tiền tố "Value error, " Pydantic thêm vào thông báo từ validator của ta.
            "message": error["msg"].removeprefix("Value error, "),
        }
        for error in exc.errors()
    ]
    _log_rejected(
        request,
        422,
        ", ".join(f"{detail['field'] or '(body)'}: {detail['type']}" for detail in details),
    )
    return JSONResponse(
        error_body("validation_error", "Dữ liệu gửi lên không hợp lệ.", details), status_code=422
    )


_HTTP_MESSAGES = {
    404: ("not_found", "Không tìm thấy tài nguyên."),
    405: ("method_not_allowed", "Phương thức không được hỗ trợ."),
}


async def _http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code, message = _HTTP_MESSAGES.get(exc.status_code, ("http_error", "Yêu cầu không thành công."))
    return JSONResponse(
        error_body(code, message), status_code=exc.status_code, headers=getattr(exc, "headers", None)
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)

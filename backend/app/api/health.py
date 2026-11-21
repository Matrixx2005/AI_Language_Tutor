from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["health"])


@router.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Backend chỉ là API: mở địa chỉ gốc thì chuyển sang trang thử API /docs."""
    return RedirectResponse(url="/docs")


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness: chỉ xác nhận tiến trình API đang chạy, không kiểm tra DB."""
    return {"status": "ok"}

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness: chỉ xác nhận tiến trình API đang chạy, không kiểm tra DB."""
    return {"status": "ok"}

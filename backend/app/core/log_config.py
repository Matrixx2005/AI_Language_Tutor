"""Log của app (logger "app.*"), cùng kiểu với log uvicorn trong terminal.

Quy tắc: không bao giờ ghi mật khẩu, token, hay giá trị người dùng nhập vào log.
"""
import logging


class _UvicornStyleFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return f"{record.levelname + ':':<9} {record.getMessage()}"


def configure_logging(level: int = logging.INFO) -> None:
    logger = logging.getLogger("app")
    logger.setLevel(level)
    if not logger.handlers:  # create_app() có thể được gọi nhiều lần (test, --reload)
        handler = logging.StreamHandler()
        handler.setFormatter(_UvicornStyleFormatter())
        logger.addHandler(handler)

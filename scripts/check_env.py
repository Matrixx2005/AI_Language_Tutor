"""Kiểm tra môi trường (chỉ đọc, không cài gì).

Chạy từ thư mục gốc dự án:  .venv\\Scripts\\python.exe scripts/check_env.py
Kết quả in ra màn hình và ghi vào docs/ENVIRONMENT_CHECK.md.

Script chỉ thay phần nằm giữa hai marker AUTO_START/AUTO_END; ghi chép tay
ngoài hai marker được giữ nguyên.
"""
from __future__ import annotations

import ctypes
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "ENVIRONMENT_CHECK.md"
VENV_PYTHON = ROOT / ".venv" / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")
AUTO_START = "<!-- check_env:AUTO_START -->"
AUTO_END = "<!-- check_env:AUTO_END -->"


def run(cmd: list[str]) -> str:
    # shutil.which tìm cả npm.cmd / *.bat trên Windows; subprocess với tên trần thì không.
    exe = shutil.which(cmd[0])
    if exe is None:
        return "KHÔNG TÌM THẤY"
    try:
        res = subprocess.run([exe, *cmd[1:]], capture_output=True, text=True, timeout=20)
        if res.returncode != 0:
            text = (res.stderr or res.stdout).strip()
            first = text.splitlines()[0] if text else "(không có đầu ra)"
            return f"LỖI (exit {res.returncode}): {first}"
        text = (res.stdout or res.stderr).strip()
        return text.splitlines()[0] if text else "(không có đầu ra)"
    except FileNotFoundError:
        return "KHÔNG TÌM THẤY"
    except Exception as exc:  # noqa: BLE001
        return f"LỖI: {exc}"


def ram_gb() -> str:
    if platform.system() != "Windows":
        return "không đo được (không phải Windows)"

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))  # type: ignore[attr-defined]
    return f"{stat.ullTotalPhys / 1024**3:.1f} GB tổng, {stat.ullAvailPhys / 1024**3:.1f} GB trống"


def main() -> None:
    disk = shutil.disk_usage(ROOT)
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    rows = [
        ("Python đang chạy", sys.version.split()[0]),
        ("Đường dẫn Python", sys.executable),
        ("Đang trong venv", "có" if in_venv else "KHÔNG (nên kích hoạt .venv)"),
        ("Yêu cầu Python >= 3.13", "ĐẠT" if sys.version_info >= (3, 13) else "KHÔNG ĐẠT"),
        ("Hệ điều hành", f"{platform.system()} {platform.release()} ({platform.machine()})"),
        ("RAM", ram_gb()),
        ("Ổ đĩa dự án trống", f"{disk.free / 1024**3:.1f} GB"),
        ("git", run(["git", "--version"])),
        ("node", run(["node", "--version"])),
        ("npm", run(["npm", "--version"])),
        ("docker", run(["docker", "--version"])),
        ("docker compose", run(["docker", "compose", "version"])),
    ]
    if platform.system() == "Windows":
        rows.append(("Các bản Python (py -0p)", run(["py", "-0p"]).replace("|", "/")))
    rows.append((
        "Python trong .venv",
        run([str(VENV_PYTHON), "--version"]) if VENV_PYTHON.exists() else "CHƯA CÓ .venv",
    ))

    lines = [
        AUTO_START,
        "## Kết quả tự động (scripts/check_env.py)",
        "",
        f"Chạy lúc: {datetime.now():%Y-%m-%d %H:%M}",
        "",
        "| Mục | Kết quả |",
        "| --- | --- |",
    ]
    lines += [f"| {k} | {v} |" for k, v in rows]
    lines.append(AUTO_END)
    block = "\n".join(lines)
    write_report(block)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # console cp1252 không in được tiếng Việt
    print(block)
    print(f"Đã cập nhật phần tự động trong {OUT}")


def write_report(block: str) -> None:
    """Chỉ thay phần giữa hai marker; không xóa ghi chép tay."""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if not OUT.exists():
        OUT.write_text(f"# Kết quả kiểm tra môi trường\n\n{block}\n", encoding="utf-8")
        return
    old = OUT.read_text(encoding="utf-8")
    start, end = old.find(AUTO_START), old.find(AUTO_END)
    if start != -1 and end > start:
        new = old[:start] + block + old[end + len(AUTO_END):]
    else:
        # File cũ chưa có marker: giữ nguyên toàn bộ nội dung cũ bên dưới.
        new = f"# Kết quả kiểm tra môi trường\n\n{block}\n\n## Ghi chép trước đó\n\n{old}"
    OUT.write_text(new, encoding="utf-8")


if __name__ == "__main__":
    main()

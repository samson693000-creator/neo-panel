import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, unquote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from app.api.deps import require_role
from app.core.config import settings
from app.models.models import Admin

router = APIRouter(prefix="/api/backup", tags=["backup"])


def _sqlite_path() -> Path | None:
    url = settings.database_url
    if not url.startswith("sqlite"):
        return None
    raw = url.split("///", 1)[-1]
    return Path(unquote(raw))


def _pg_env() -> tuple[list[str], dict]:
    url = os.getenv("DATABASE_URL", settings.database_url)
    parsed = urlparse(url.replace("postgresql+asyncpg", "postgresql"))
    if not parsed.hostname or not parsed.path:
        raise HTTPException(500, "Не удалось разобрать DATABASE_URL")

    database = parsed.path.lstrip("/").split("?")[0]
    cmd = [
        "pg_dump",
        "-h", parsed.hostname,
        "-p", str(parsed.port or 5432),
        "-U", unquote(parsed.username or ""),
        "-d", database,
        "--no-owner",
        "--clean",
    ]
    env = {**os.environ, "PGPASSWORD": unquote(parsed.password or "")}
    return cmd, env


@router.get("/download")
async def download_backup(admin: Admin = Depends(require_role("owner"))):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    sqlite_file = _sqlite_path()
    if sqlite_file is not None:
        if not sqlite_file.is_file():
            raise HTTPException(404, "Файл базы ещё не создан")
        return FileResponse(
            sqlite_file,
            media_type="application/vnd.sqlite3",
            filename=f"backup-{stamp}.db",
        )

    cmd, env = _pg_env()
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
    except FileNotFoundError as exc:
        raise HTTPException(500, "pg_dump не установлен") from exc

    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise HTTPException(500, f"pg_dump: {stderr.decode()[:300]}")

    async def stream():
        yield stdout

    return StreamingResponse(
        stream(),
        media_type="application/sql",
        headers={"Content-Disposition": f'attachment; filename="backup-{stamp}.sql"'},
    )

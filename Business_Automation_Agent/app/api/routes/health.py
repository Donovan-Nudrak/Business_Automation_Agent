from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from redis import Redis
from sqlalchemy import text

from app.core.config import settings
from app.database.session import engine

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def liveness_check() -> dict[str, str]:
    return {
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/health/ready")
async def readiness_check() -> dict[str, Any]:
    checks: dict[str, str] = {}
    failed: list[str] = []

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["postgresql"] = "ok"
    except Exception as exc:
        checks["postgresql"] = str(exc)
        failed.append("postgresql")

    try:
        redis_client = Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        redis_client.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = str(exc)
        failed.append("redis")

    if failed:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unavailable",
                "timestamp": datetime.now(UTC).isoformat(),
                "checks": checks,
                "failed": failed,
            },
        )

    return {
        "status": "ready",
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": checks,
    }

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import actions, auth, events, health, reports, webhooks
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(events.router)
app.include_router(webhooks.router)
app.include_router(actions.router)
app.include_router(reports.router)

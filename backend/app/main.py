import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.clients import router as clients_router
from app.api.entries import router as entries_router
from app.api.injury_flags import router as injury_flags_router
from app.api.plans import router as plans_router
from app.api.sessions import router as sessions_router
from app.api.voice import router as voice_router
from app.services.model_health import verify_active_models

logger = logging.getLogger("supertrainer")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await verify_active_models()
    yield


app = FastAPI(title="SuperTrainer API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Lock down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Error Handlers ---


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": f"http_{exc.status_code}", "message": str(exc.detail)}},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    messages = []
    for err in exc.errors():
        loc = " → ".join(str(l) for l in err["loc"])
        messages.append(f"{loc}: {err['msg']}")
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": "; ".join(messages)}},
    )


# --- Request Logging Middleware ---


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s → %d (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# --- Routers ---


app.include_router(clients_router, prefix="/api/v1")
app.include_router(sessions_router, prefix="/api/v1")
app.include_router(entries_router, prefix="/api/v1")
app.include_router(injury_flags_router, prefix="/api/v1")
app.include_router(plans_router, prefix="/api/v1")
app.include_router(voice_router, prefix="/api/v1")


@app.get("/api/v1/health")
async def health_check() -> dict:
    return {"data": {"status": "ok"}, "meta": {}}

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.clients import router as clients_router
from app.api.sessions import router as sessions_router

app = FastAPI(title="SuperTrainer API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Lock down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(clients_router, prefix="/api/v1")
app.include_router(sessions_router, prefix="/api/v1")


@app.get("/api/v1/health")
async def health_check():
    return {"data": {"status": "ok"}, "meta": {}}

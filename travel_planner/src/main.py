from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.database import Base, engine
from src.routers.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Travel Planner API",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(auth_router)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
    )

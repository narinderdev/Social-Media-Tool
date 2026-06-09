from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import FRONTEND_ORIGIN
from app.routes import auth, platforms, posts
from app.storage import UPLOADS_DIR, ensure_storage

ensure_storage()

app = FastAPI(title="Social Media Tool API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

app.include_router(auth.router)
app.include_router(platforms.router)
app.include_router(posts.router)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}

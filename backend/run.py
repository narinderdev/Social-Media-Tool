import uvicorn

from app.config import BACKEND_HOST, PORT


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=BACKEND_HOST,
        port=PORT,
        reload=True,
        reload_dirs=["app", "run.py"],
        reload_excludes=[".venv/*", "data/*"],
    )

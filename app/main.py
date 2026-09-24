import os

from dotenv import load_dotenv
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

# Load .env before anything reads KPI_SECRET_KEY below.
load_dotenv()

from app.routes.admin import router as admin_router
from app.routes.display import router as display_router
from app.routes.scan import router as scan_router

app = FastAPI()

# Signed cookie that keeps an admin logged in. This was the missing piece —
# without it, request.session doesn't exist and /admin crashes.
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ["KPI_SECRET_KEY"],
    https_only=os.environ.get("KPI_HTTPS_ONLY", "false").lower() == "true",
    same_site="strict",
    max_age=8 * 60 * 60,
)

app.include_router(admin_router)
app.include_router(display_router)
app.include_router(scan_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
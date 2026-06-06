from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.forms import router as forms_router
from app.profiles import router as profiles_router
from app.research import router as research_router
from app.tasks import router as tasks_router
from app.worker import router as worker_router


settings = get_settings()

app = FastAPI(title="PortalPilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(profiles_router)
app.include_router(forms_router)
app.include_router(research_router)
app.include_router(tasks_router)
app.include_router(worker_router)

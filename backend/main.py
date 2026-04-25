from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine
from app.models.db_models import Base
from app.routers import analyze, assess, report
from config import settings

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Skill Assessment Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router)
app.include_router(assess.router)
app.include_router(report.router)

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}

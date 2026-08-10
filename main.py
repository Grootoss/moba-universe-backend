from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import admin, articles, auth, profiles, seo

settings = get_settings()

app = FastAPI(title="Moba Universe API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(articles.router)
app.include_router(profiles.router)
app.include_router(admin.router)
app.include_router(seo.router)


@app.get("/health")
def health():
    return {"status": "ok"}

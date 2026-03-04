from fastapi import APIRouter

from app.api.routes import articles, auth, endpoints, health, journals

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(endpoints.router)
api_router.include_router(journals.router)
api_router.include_router(articles.router)

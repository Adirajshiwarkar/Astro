from fastapi import APIRouter

from app.api.v1.endpoints import auth, charts, chat, feedback, health, predictions, profile

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])
api_router.include_router(charts.router, prefix="/charts", tags=["charts"])
api_router.include_router(predictions.router, prefix="/predictions", tags=["predictions"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])


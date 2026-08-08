from fastapi import APIRouter

from app.services.insight_service import (
    generate_insights,
    get_insight_history
)


insights_router = APIRouter(
    prefix="/insights",
    tags=["AI Insights"]
)


@insights_router.get("")
def get_insights():

    return generate_insights()


@insights_router.get("/")
def get_insights_root():

    return generate_insights()


@insights_router.get("/history")
def get_insight_history_route():

    return get_insight_history()
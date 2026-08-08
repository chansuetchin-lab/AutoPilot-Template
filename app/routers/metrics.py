from fastapi import APIRouter

from app.services.metrics_service import calculate_metrics


metrics_router = APIRouter(
    prefix="/metrics",
    tags=["Metrics"],
)


@metrics_router.get("")
def get_metrics():
    """
    Return operational metrics from the latest
    Supervity workflow execution.
    """
    return calculate_metrics()
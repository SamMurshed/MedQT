from typing import List, Dict
import os

import httpx

from app.config import settings  # or equivalent config loader


def get_ml_service_base_url() -> str:
    # Example: ML_SERVICE_URL=http://ml_service:8001
    environment_url = os.getenv("ML_SERVICE_URL", None)
    if environment_url:
        return environment_url.rstrip("/")

    # Fallback to config settings if you use pydantic Settings
    if hasattr(settings, "ML_SERVICE_URL"):
        return settings.ML_SERVICE_URL.rstrip("/")

    return "http://ml_service:8001"


async def request_wait_time_prediction(
    symptom_names: List[str],
    queue_size: int,
) -> Dict[str, float]:
    base_url = get_ml_service_base_url()
    request_body = {
        "symptoms": symptom_names,
        "queue_size": queue_size,
    }

    async with httpx.AsyncClient() as http_client:
        response = await http_client.post(
            f"{base_url}/predict", json=request_body, timeout=5.0
        )
        response.raise_for_status()
        return response.json()

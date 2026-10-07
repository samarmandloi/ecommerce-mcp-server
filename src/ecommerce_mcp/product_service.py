import os
from pathlib import Path

import httpx
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

PRODUCT_SERVICE_BASE_URL = os.environ["PRODUCT_SERVICE_BASE_URL"]


def create_product(payload: dict) -> dict:
    """Create a product through the Product Service API."""

    url = f"{PRODUCT_SERVICE_BASE_URL}/api/v1/products"

    response = httpx.post(
        url,
        json=payload,
        timeout=10.0,
    )

    if response.is_success:
        return response.json()

    try:
        error_body = response.json()
    except ValueError:
        error_body = {
            "message": response.text,
        }

    return {
        "error": True,
        "status": response.status_code,
        "response": error_body,
    }
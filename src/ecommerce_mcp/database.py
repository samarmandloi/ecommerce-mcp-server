import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


# Project root: ecommerce-mcp-server/
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Load .env from project root
load_dotenv(PROJECT_ROOT / ".env")


def get_connection():
    return psycopg.connect(
        host=os.environ["PRODUCT_DB_HOST"],
        port=os.environ["PRODUCT_DB_PORT"],
        dbname=os.environ["PRODUCT_DB_NAME"],
        user=os.environ["PRODUCT_DB_USER"],
        password=os.environ["PRODUCT_DB_PASSWORD"],
    )

def get_inventory_connection():
    return psycopg.connect(
        host=os.environ["INVENTORY_DB_HOST"],
        port=os.environ["INVENTORY_DB_PORT"],
        dbname=os.environ["INVENTORY_DB_NAME"],
        user=os.environ["INVENTORY_DB_USER"],
        password=os.environ["INVENTORY_DB_PASSWORD"],
    )
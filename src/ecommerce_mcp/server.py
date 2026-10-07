import logging
import os
import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from .database import get_connection, get_inventory_connection


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    stream=sys.stderr,
    force=True,
)

logger = logging.getLogger(__name__)

mcp = MCPServer("ecommerce-mcp-server")

SERVICE_LOG_DIRS = {
    "product-service": Path.home() / "IdeaProjects/ecommerce/product-service/logs",
    "inventory-service": Path.home() / "IdeaProjects/ecommerce/inventory-service/logs",
}

@mcp.tool()
def hello(name: str) -> str:
    """Say hello to a user."""

    logger.info("hello called with name: %s", name)

    return f"Hello {name}"


@mcp.tool()
def check_database_environment() -> dict:
    """Check whether database environment variables are available."""

    logger.info("Checking database environment variables")

    return {
        "host": os.getenv("PRODUCT_DB_HOST"),
        "port": os.getenv("PRODUCT_DB_PORT"),
        "database": os.getenv("PRODUCT_DB_NAME"),
        "user": os.getenv("PRODUCT_DB_USER"),
        "password_set": bool(os.getenv("PRODUCT_DB_PASSWORD")),
    }


@mcp.tool()
def get_product(sku: str) -> dict:
    """Get product information by SKU from the Product database."""

    logger.info("get_product called with SKU: %s", sku)

    connection = get_connection()

    try:
        logger.info("Database connection established")

        cursor = connection.cursor()

        logger.info("Executing product query for SKU: %s", sku)

        cursor.execute(
            """
            SELECT
                v.sku,
                v.name AS variant_name,
                c.name AS product_name,
                b.name AS brand_name,
                v.original_price,
                v.discounted_price,
                v.quantity
            FROM variants v
            JOIN checkoutables c
                ON c.id = v.checkoutable_id
            JOIN brands b
                ON b.id = c.brand_id
            WHERE v.sku = %s
            """,
            (sku,)
        )

        product = cursor.fetchone()

        if product is None:
            logger.warning("Product not found for SKU: %s", sku)

            return {
                "error": f"Product with SKU '{sku}' not found"
            }

        logger.info("Product found for SKU: %s", sku)

        return {
            "sku": product[0],
            "variant_name": product[1],
            "product_name": product[2],
            "brand": product[3],
            "original_price": float(product[4]),
            "discounted_price": float(product[5]),
            "quantity": product[6],
        }

    except Exception:
        logger.exception("Error while getting product for SKU: %s", sku)
        raise

    finally:
        connection.close()
        logger.info("Database connection closed")

@mcp.tool()
def get_inventory(sku: str) -> dict:
    """Get inventory information by SKU from the Inventory database."""

    logger.info("get_inventory called with SKU: %s", sku)

    connection = get_inventory_connection()

    try:
        logger.info("Inventory database connection established")

        cursor = connection.cursor()

        logger.info("Executing inventory query for SKU: %s", sku)

        cursor.execute(
            """
            SELECT
                sku,
                quantity,
                reserved_quantity,
                quantity - reserved_quantity AS available_quantity
            FROM inventory
            WHERE sku = %s
            """,
            (sku,)
        )

        inventory = cursor.fetchone()

        if inventory is None:
            logger.warning("Inventory not found for SKU: %s", sku)

            return {
                "error": f"Inventory for SKU '{sku}' not found"
            }

        logger.info("Inventory found for SKU: %s", sku)

        return {
            "sku": inventory[0],
            "quantity": inventory[1],
            "reserved_quantity": inventory[2],
            "available_quantity": inventory[3],
        }

    except Exception:
        logger.exception(
            "Error while getting inventory for SKU: %s",
            sku
        )
        raise

    finally:
        connection.close()
        logger.info("Inventory database connection closed")


@mcp.tool()
def find_data_mismatches(sku: str) -> dict:
    """Compare product and inventory data for a SKU."""

    logger.info("find_data_mismatches called with SKU: %s", sku)

    product_connection = None
    inventory_connection = None

    try:
        product_connection = get_connection()
        inventory_connection = get_inventory_connection()
        # Get product quantity
        product_cursor = product_connection.cursor()

        logger.info(
            "Checking product database for SKU: %s",
            sku
        )

        product_cursor.execute(
            """
            SELECT
                sku,
                quantity
            FROM variants
            WHERE sku = %s
            """,
            (sku,)
        )

        product = product_cursor.fetchone()

        # Get inventory quantity
        inventory_cursor = inventory_connection.cursor()

        logger.info(
            "Checking inventory database for SKU: %s",
            sku
        )

        inventory_cursor.execute(
            """
            SELECT
                sku,
                quantity,
                reserved_quantity
            FROM inventory
            WHERE sku = %s
            """,
            (sku,)
        )

        inventory = inventory_cursor.fetchone()

        # Product missing
        if product is None and inventory is not None:
            logger.warning(
                "SKU %s exists in inventory but is missing from product database",
                sku
            )

            return {
                "sku": sku,
                "mismatch": True,
                "type": "MISSING_IN_PRODUCT",
                "product": None,
                "inventory": {
                    "quantity": inventory[1],
                    "reserved_quantity": inventory[2],
                },
            }

        # Inventory missing
        if product is not None and inventory is None:
            logger.warning(
                "SKU %s exists in product database but is missing from inventory database",
                sku
            )

            return {
                "sku": sku,
                "mismatch": True,
                "type": "MISSING_IN_INVENTORY",
                "product": {
                    "quantity": product[1],
                },
                "inventory": None,
            }

        # Both missing
        if product is None and inventory is None:
            logger.warning(
                "SKU %s does not exist in either database",
                sku
            )

            return {
                "sku": sku,
                "mismatch": False,
                "type": "NOT_FOUND",
                "product": None,
                "inventory": None,
            }

        # Both exist - compare quantities
        product_quantity = product[1]
        inventory_quantity = inventory[1]

        if product_quantity != inventory_quantity:
            logger.warning(
                "Quantity mismatch found for SKU %s: product=%s, inventory=%s",
                sku,
                product_quantity,
                inventory_quantity
            )

            return {
                "sku": sku,
                "mismatch": True,
                "type": "QUANTITY_MISMATCH",
                "product": {
                    "quantity": product_quantity,
                },
                "inventory": {
                    "quantity": inventory_quantity,
                    "reserved_quantity": inventory[2],
                },
            }

        logger.info(
            "No data mismatch found for SKU: %s",
            sku
        )

        return {
            "sku": sku,
            "mismatch": False,
            "type": "MATCH",
            "product": {
                "quantity": product_quantity,
            },
            "inventory": {
                "quantity": inventory_quantity,
                "reserved_quantity": inventory[2],
            },
        }

    except Exception:
        logger.exception(
            "Error while comparing product and inventory data for SKU: %s",
            sku
        )
        raise

    finally:
        if product_connection is not None:
            product_connection.close()

        if inventory_connection is not None:
            inventory_connection.close()

        logger.info(
            "Database connections closed for SKU: %s",
            sku
        )


@mcp.tool()
def get_reservation(request_id: str) -> dict:
    """Get reservation information by request ID from the Inventory database."""

    logger.info("get_reservation called with request ID: %s", request_id)

    connection = get_inventory_connection()

    try:
        logger.info("Inventory database connection established")

        cursor = connection.cursor()

        logger.info(
            "Executing reservation query for request ID: %s",
            request_id
        )

        cursor.execute(
            """
            SELECT
                request_id,
                status,
                items,
                created_at,
                updated_at
            FROM reservation
            WHERE request_id = %s
            """,
            (request_id,)
        )

        reservation = cursor.fetchone()

        if reservation is None:
            logger.warning(
                "Reservation not found for request ID: %s",
                request_id
            )

            return {
                "error": f"Reservation with request ID '{request_id}' not found"
            }

        logger.info(
            "Reservation found for request ID: %s",
            request_id
        )

        return {
            "request_id": str(reservation[0]),
            "status": reservation[1],
            "items": reservation[2],
            "created_at": reservation[3].isoformat(),
            "updated_at": reservation[4].isoformat(),
        }

    except Exception:
        logger.exception(
            "Error while getting reservation for request ID: %s",
            request_id
        )
        raise

    finally:
        connection.close()
        logger.info("Inventory database connection closed")

@mcp.tool()
def search_logs(service: str, query: str) -> dict:
    """Search application logs for a service."""

    logger.info(
        "search_logs called with service=%s, query=%s",
        service,
        query
    )

    if service not in SERVICE_LOG_DIRS:
        logger.warning("Unsupported service requested: %s", service)

        return {
            "error": (
                f"Unsupported service '{service}'. "
                f"Supported services: {list(SERVICE_LOG_DIRS.keys())}"
            )
        }

    if not query.strip():
        return {
            "error": "Log search query cannot be empty"
        }

    log_directory = SERVICE_LOG_DIRS[service]

    if not log_directory.exists():
        logger.warning(
            "Log directory does not exist for service %s: %s",
            service,
            log_directory
        )

        return {
            "error": f"Log directory not found for service '{service}'"
        }

    matches = []

    for log_file in sorted(log_directory.rglob("*.log")):
        try:
            with log_file.open("r", encoding="utf-8", errors="replace") as file:
                for line_number, line in enumerate(file, start=1):
                    if query.lower() in line.lower():
                        matches.append({
                            "file": str(log_file.relative_to(log_directory)),
                            "line": line_number,
                            "message": line.rstrip(),
                        })

        except OSError:
            logger.exception(
                "Error while reading log file: %s",
                log_file
            )

    logger.info(
        "Log search completed for service=%s, query=%s, matches=%d",
        service,
        query,
        len(matches)
    )

    return {
        "service": service,
        "query": query,
        "match_count": len(matches),
        "matches": matches,
    }

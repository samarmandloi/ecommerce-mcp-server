import logging
import os
import sys

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


if __name__ == "__main__":
    logger.info("Starting ecommerce MCP server")
    mcp.run()
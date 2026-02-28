"""Example workflow functions for testing the dashboard.

This file demonstrates:
1. Standalone workflows defined locally
2. Imported workflows from external modules
"""

# Import workflows from other modules
from app_workflows import payment_processing, refund_flow

# Local workflow functions
async def checkout_flow(order_id: str, user_id: str) -> dict:
    """Process a checkout flow for an order."""
    return {"status": "completed", "order_id": order_id}


def sync_order_status(order_id: str) -> str:
    """Synchronously fetch order status (for example)."""
    return "shipped"


async def inventory_check(sku: str, quantity: int) -> bool:
    """Check if inventory is available (imported from inventory module)."""
    return True


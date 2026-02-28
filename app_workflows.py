"""Mock application workflow functions (simulating my_app.workflows module)."""


async def payment_processing(amount: float, card_token: str) -> dict:
    """Handle payment processing."""
    return {"paid": True, "amount": amount}


async def refund_flow(order_id: str, reason: str = "customer_request") -> dict:
    """Process a refund for an order."""
    return {"refunded": True, "order_id": order_id, "reason": reason}
